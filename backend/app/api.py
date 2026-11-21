"""FastAPI 路由 + 中间件（IP 限流 + 用户 Key 注入）。"""
import shutil
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from .config import get_settings, get_abs_path
from .context import set_request_user_key
from .database import init_db
from .rate_limit import (
    check_and_consume, get_status, init_persist_path, reset_ip, QUOTA_PER_IP,
)
from .models import (
    QuestionRequest, AnswerResult, SummaryResult,
    CompareRequest, CompareResult, GraphResult,
    NoteCreate, NoteResult, NotesOrganizeResult,
)
from .services import (
    pdf_parser, paper_store, summarizer, rag, vector_store,
    comparison, graph, notes, related_work, research_flow, research_viz, note_pdf, overview_note,
)
from .services.llm_client import is_llm_ready, verify_user_key

_settings = get_settings()
app = FastAPI(title="LitRead AI", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 启动 ──
@app.on_event("startup")
def on_startup():
    init_db()
    # 限流数据持久化到 data 目录
    persist_file = str(get_abs_path(_settings.DATA_DIR) / ".rate_limit.json")
    init_persist_path(persist_file)


# ── 中间件：用户 Key 注入 + IP 限流 ──
@app.middleware("http")
async def auth_and_rate_limit(request: Request, call_next):
    # 1. 提取用户 Key（header 或 query param）
    user_key = (
        request.headers.get("x-user-key")
        or request.headers.get("X-User-Key")
        or request.query_params.get("user_key")
        or request.query_params.get("key")
    )
    set_request_user_key(user_key)

    # 2. IP 限流（只对 LLM 接口生效）
    path = request.url.path
    llm_paths = {
        "/api/papers/{paper_id}/summary",
        "/api/papers/{paper_id}/notes/organize",
        "/api/ask",
        "/api/compare",
        "/api/related-work",
    }
    if path in llm_paths or (
        path.startswith("/api/")
        and not any(path.endswith(s) for s in ["/parse", "/index", "/notes", "/export", "/research", "/pdf", "/markdown", "/overview", "/overview.png", "/viz", "/compare-structured", "/growth"])
        and path not in {"/api/graph", "/api/library/stats", "/api/papers", "/api/health"}
    ):
        allowed, reason, info = check_and_consume(request, user_key=user_key)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": reason,
                    "quota": QUOTA_PER_IP,
                    "used": info.get("used", 0),
                    "tip": "粘贴你自己的 DeepSeek / OpenAI 兼容 API Key 即可继续使用，服务器不会保存。",
                },
            )

    response = await call_next(request)
    return response


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# ── 基础 ──
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "papers": len(paper_store.list_papers()),
        "llm_ready": is_llm_ready(),
        "demo_mode": not is_llm_ready(),
        "quota_per_ip": QUOTA_PER_IP,
    }


@app.get("/api/library/stats")
def stats():
    return {
        "papers": len(paper_store.list_papers()),
        "vectors": vector_store.get_vector_store().count(),
    }


# ── 限流查询 & Key 验证（方便前端） ──
@app.get("/api/rate-status")
def rate_status(request: Request, ip: Optional[str] = None):
    return get_status(ip or request.client.host if request.client else None)


@app.post("/api/verify-key")
def verify_key(payload: dict):
    key = payload.get("key", "")
    err = verify_user_key(key)
    if err:
        raise HTTPException(400, err)
    return {"ok": True, "message": "Key 有效，可以正常使用"}


# ── 论文 CRUD ──
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
        paper_id=parsed.paper_id, filename=safe_name,
        filepath=str(dest), meta=parsed.meta,
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


# ── 速读卡片（LLM + 限流） ──
@app.post("/api/papers/{paper_id}/summary", response_model=SummaryResult)
def summarize(paper_id: str):
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    parsed = pdf_parser.parse_pdf(info["filepath"])
    return summarizer.summarize_paper(parsed)


# ── RAG 索引与问答 ──
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


# ── 多论文对比 ──
@app.post("/api/compare", response_model=CompareResult)
def compare(req: CompareRequest):
    if len(req.paper_ids) < 2:
        raise HTTPException(400, "至少选择 2 篇论文")
    try:
        return comparison.compare_thinking(req.paper_ids)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── 文献图谱 ──
@app.get("/api/graph", response_model=GraphResult)
def get_graph():
    try:
        return graph.build_graph()
    except RuntimeError as e:
        raise HTTPException(503, str(e))


# ── 阅读笔记 ──
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


@app.get("/api/papers/{paper_id}/notes/pdf")
def export_notes_pdf(paper_id: str):
    """导出该论文的阅读笔记 PDF；没有笔记时导出研究流内容。"""
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    contents = [n.content for n in notes.list_notes(paper_id) if (n.content or "").strip()]
    fallback = None
    if not contents:
        parsed = pdf_parser.parse_pdf(info["filepath"])
        fallback = research_flow.brief_to_markdown(research_flow.get_brief(parsed))
        if not fallback:
            raise HTTPException(404, "暂无笔记，也没有研究流内容")
    try:
        data = note_pdf.build_pdf(info.get("title") or "", contents, fallback)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="litread-notes-{paper_id}.pdf"'},
    )


# ── 论文速览笔记 ──
def _overview_source(paper_id: str):
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    return pdf_parser.parse_pdf(info["filepath"])


@app.get("/api/papers/{paper_id}/overview")
def paper_overview(paper_id: str):
    parsed = _overview_source(paper_id)
    note, _ = overview_note.get_or_create(parsed)
    return {"paper_id": paper_id, "note": note}


@app.get("/api/papers/{paper_id}/overview.png")
def paper_overview_png(paper_id: str):
    parsed = _overview_source(paper_id)
    _, png = overview_note.get_or_create(parsed)
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Disposition": f'inline; filename="litread-note-{paper_id}.png"',
        },
    )


# ── Related Work ──
class RelatedWorkRequest(BaseModel):
    topic: str
    paper_ids: List[str]


@app.post("/api/related-work")
def make_related(req: RelatedWorkRequest):
    if not req.topic.strip():
        raise HTTPException(400, "请填写研究主题")
    return related_work.generate_related_work(req.topic, req.paper_ids)


# ── 12 步研究工作流 ──
class GuessRequest(BaseModel):
    guess: str


@app.get("/api/papers/{paper_id}/research")
def get_research(paper_id: str):
    """读取已生成的工作流分段（不消耗额度）。"""
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    parsed = pdf_parser.parse_pdf(info["filepath"])
    return research_flow.get_brief(parsed)


@app.post("/api/papers/{paper_id}/research/{stage}")
def make_research(paper_id: str, stage: str):
    """生成一个阶段：context / author / method / evidence / critique。"""
    if stage not in research_flow.STAGES:
        raise HTTPException(400, "未知阶段")
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    parsed = pdf_parser.parse_pdf(info["filepath"])
    try:
        return research_flow.generate_stage(parsed, stage)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@app.get("/api/papers/{paper_id}/research/markdown")
def research_markdown(paper_id: str):
    """把已生成的 12 步内容导出为 Markdown（供笔记合并）。"""
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    parsed = pdf_parser.parse_pdf(info["filepath"])
    return {
        "paper_id": paper_id,
        "markdown": research_flow.brief_to_markdown(research_flow.get_brief(parsed)),
    }


@app.post("/api/papers/{paper_id}/research/{stage}/compare")
def compare_research(paper_id: str, stage: str, req: GuessRequest):
    """把用户自己的推演与 AI 的重建做对照。"""
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    parsed = pdf_parser.parse_pdf(info["filepath"])
    brief = research_flow.get_brief(parsed)
    try:
        return research_flow.compare_guess(parsed, stage, req.guess, brief)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))


# ── 研究流可视化（独立缓存，不调用模型） ──
@app.get("/api/papers/{paper_id}/research/viz")
def get_research_viz(paper_id: str):
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    parsed = pdf_parser.parse_pdf(info["filepath"])
    return research_viz.get_viz(parsed)


class StructuredGuessRequest(BaseModel):
    guess: str
    session_id: Optional[str] = None


@app.post("/api/papers/{paper_id}/research/author/compare-structured")
def compare_author_structured(paper_id: str, req: StructuredGuessRequest):
    """第 3 步：确定性近似对照，返回用户路径上的命中/分叉。"""
    info = paper_store.get_paper(paper_id)
    if not info:
        raise HTTPException(404, "论文不存在")
    parsed = pdf_parser.parse_pdf(info["filepath"])
    viz = research_viz.get_viz(parsed)
    try:
        return research_viz.compare_guess_structured(
            parsed, req.guess, viz, session_id=req.session_id or "anonymous"
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/research/growth")
def research_growth(session_id: Optional[str] = None):
    """侧栏推演成长曲线：按匿名会话统计近似对照分数。"""
    return research_viz.get_growth(session_id or "")


# ── 对比表导出 Markdown ──
@app.post("/api/compare/export")
def export_compare_markdown(payload: dict):
    axes = [a for a in (payload.get("axes") or []) if isinstance(a, dict)]
    papers = [p for p in (payload.get("papers") or []) if isinstance(p, dict)]
    if not axes or not papers:
        raise HTTPException(400, "思路对比为空，请先生成")

    def _cell(value) -> str:
        text = "" if value is None else str(value).strip()
        return text.replace("|", "\\|").replace("\n", "<br>") or "—"

    labels = [_cell(a.get("label") or a.get("key") or "") for a in axes]
    titles = [_cell(p.get("title") or p.get("paper_id") or "未命名论文") for p in papers]
    md_lines = [
        f"# 论文思路对比：{' vs '.join(titles)}",
        "",
        f"> {len(papers)} 篇论文 · {len(axes)} 个思维阶段",
        "",
        _cell(payload.get("summary") or ""),
        "",
        "| 思维阶段 | " + " | ".join(titles) + " |",
        "|" + "---|" * (len(titles) + 1),
    ]
    for ai, label in enumerate(labels):
        cells = []
        for p in papers:
            values = p.get("cells") or []
            cells.append(_cell(values[ai] if ai < len(values) else "—"))
        md_lines.append("| " + label + " | " + " | ".join(cells) + " |")

    md_lines += ["", "## 没走的路"]
    for p in papers:
        md_lines += ["", f"### {_cell(p.get('title') or '')}"]
        alternatives = p.get("alternatives") or []
        if not alternatives:
            md_lines.append("- —")
        for alt in alternatives:
            if isinstance(alt, dict):
                md_lines.append(
                    f"- {_cell(alt.get('label') or '备选路线')}："
                    f"{_cell(alt.get('reason_dropped') or '')}"
                )
    return {"markdown": "\n".join(md_lines)}


# ── 限流重置（仅内部/运维用） ──
@app.post("/admin/reset-rate")
def admin_reset(payload: dict):
    ip = payload.get("ip")
    if not ip:
        raise HTTPException(400, "需要 ip 参数")
    reset_ip(ip)
    return {"ok": True, "ip": ip}
