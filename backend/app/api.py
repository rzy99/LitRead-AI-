"""FastAPI 路由。"""
import shutil
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import get_settings, get_abs_path
from .database import init_db
from .models import (
    QuestionRequest,
    AnswerResult,
    SummaryResult,
    CompareRequest,
    CompareResult,
    GraphResult,
    NoteCreate,
    NoteResult,
    NotesOrganizeResult,
)
from .services import (
    pdf_parser,
    paper_store,
    summarizer,
    rag,
    vector_store,
    comparison,
    graph,
    notes,
    bibtex,
    related_work,
)
from .services.llm_client import is_llm_ready

_settings = get_settings()
app = FastAPI(title="LitRead AI", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request, exc: RuntimeError):
    """依赖/模型不可用时返回 503，而不是 500。"""
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.on_event("startup")
def on_startup():
    init_db()


# ---------- 基础 ----------
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "papers": len(paper_store.list_papers()),
        "llm_ready": is_llm_ready(),
        "demo_mode": not is_llm_ready(),
    }


@app.get("/api/library/stats")
def stats():
    return {
        "papers": len(paper_store.list_papers()),
        "vectors": vector_store.get_vector_store().count(),
    }


# ---------- 论文 CRUD ----------
@app.post("/api/papers/upload")
async def upload_paper(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "仅支持 PDF 文件")

    papers_dir = get_abs_path(_settings.PAPERS_DIR)
    papers_dir.mkdir(parents=True, exist_ok=True)

    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    dest = papers_dir / safe_name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    parsed = pdf_parser.parse_pdf(str(dest))
    info = paper_store.add_paper(
        paper_id=parsed.paper_id,
        filename=safe_name,
        filepath=str(dest),
        meta=parsed.meta,
    )

    return {
        "paper_id": parsed.paper_id,
        "meta": parsed.meta.model_dump(),
        "text_length": len(parsed.full_text),
        "section_count": len(parsed.sections),
        **{k: info[k] for k in ("indexed", "indexed_chunks")},
    }


@app.get("/api/papers")
def list_papers():
    return {"papers": paper_store.list_papers()}


@app.delete("/api/papers/{paper_id}")
def remove_paper(paper_id: str):
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    paper_store.delete_paper(paper_id)
    try:
        vector_store.get_vector_store().delete_paper(paper_id)
    except Exception:
        pass
    return {"deleted": paper_id}


@app.post("/api/papers/{paper_id}/parse")
def parse_paper_detail(paper_id: str):
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    parsed = pdf_parser.parse_pdf(info["filepath"])
    return {
        "paper_id": parsed.paper_id,
        "meta": parsed.meta.model_dump(),
        "sections": parsed.sections[:30],
        "text_preview": parsed.full_text[:2000],
    }


# ---------- 速读卡片 ----------
@app.post("/api/papers/{paper_id}/summary", response_model=SummaryResult)
def summarize(paper_id: str):
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    parsed = pdf_parser.parse_pdf(info["filepath"])
    return summarizer.summarize_paper(parsed)


# ---------- RAG 索引与问答 ----------
@app.post("/api/papers/{paper_id}/index")
def index_for_rag(paper_id: str):
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    parsed = pdf_parser.parse_pdf(info["filepath"])
    n = rag.index_paper(parsed)
    return {"paper_id": paper_id, "indexed_chunks": n}


@app.post("/api/ask", response_model=AnswerResult)
def ask(req: QuestionRequest):
    if not req.question.strip():
        raise HTTPException(400, "问题不能为空")
    return rag.answer_question(req.question, paper_ids=req.paper_ids)


# ---------- 多论文对比 ----------
@app.post("/api/compare", response_model=CompareResult)
def compare(req: CompareRequest):
    if len(req.paper_ids) < 2:
        raise HTTPException(400, "至少选择 2 篇论文")
    try:
        return comparison.compare_papers(req.paper_ids, focus=req.focus or "")
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------- 文献图谱 ----------
@app.get("/api/graph", response_model=GraphResult)
def get_graph():
    try:
        return graph.build_graph()
    except RuntimeError as e:
        raise HTTPException(503, str(e))


# ---------- 阅读笔记 ----------
@app.post("/api/papers/{paper_id}/notes", response_model=NoteResult)
def create_note(paper_id: str, note: NoteCreate):
    try:
        return notes.add_note(paper_id, note.content)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/api/notes")
def list_all_notes(paper_id: Optional[str] = None):
    return {"notes": notes.list_notes(paper_id)}


@app.delete("/api/notes/{note_id}")
def remove_note(note_id: int):
    if not notes.delete_note(note_id):
        raise HTTPException(404, "笔记不存在")
    return {"deleted": note_id}


@app.post("/api/papers/{paper_id}/notes/organize", response_model=NotesOrganizeResult)
def organize_notes(paper_id: str):
    return notes.organize_notes(paper_id)


# ---------- BibTeX ----------
@app.get("/api/papers/{paper_id}/bibtex")
def get_bibtex(paper_id: str):
    try:
        return {"paper_id": paper_id, "bibtex": bibtex.generate_bibtex(paper_id)}
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/api/bibtex/export")
def export_bibtex(payload: dict):
    ids = payload.get("paper_ids", [])
    if not ids:
        raise HTTPException(400, "请选择论文")
    return {"bibtex": bibtex.export_bibtex(ids)}


# ---------- Related Work ----------
class RelatedWorkRequest(BaseModel):
    topic: str
    paper_ids: List[str]


@app.post("/api/related-work")
def make_related(req: RelatedWorkRequest):
    if not req.topic.strip():
        raise HTTPException(400, "请填写研究主题")
    result = related_work.generate_related_work(req.topic, req.paper_ids)
    return result


# ---------- 对比表导出 Markdown ----------
@app.post("/api/compare/export")
def export_compare_markdown(payload: dict):
    headers = payload.get("headers", [])
    rows = payload.get("rows", [])
    if not headers or not rows:
        raise HTTPException(400, "对比表为空，请先生成")
    md_lines = ["| 论文 | " + " | ".join(headers) + " |",
                "|" + "|" * (len(headers) + 1) + "|"]
    for row in rows:
        title = row.get("title", row.get("paper_id", ""))
        cells = [str(row.get(h, "")) for h in headers]
        md_lines.append("| " + title + " | " + " | ".join(cells) + " |")
    consensus = payload.get("consensus", "")
    divergence = payload.get("divergence", "")
    if consensus:
        md_lines += ["", "**共识点：** " + consensus]
    if divergence:
        md_lines += ["", "**分歧点：** " + divergence]
    return {"markdown": "\n".join(md_lines)}
