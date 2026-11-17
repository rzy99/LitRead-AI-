"""RAG 问答：先检索，再试 LLM，失败就返回检索片段（demo 模式）。"""
import logging
import re
from typing import List, Optional

from ..config import get_settings
from ..models import ParsedPaper, AnswerResult
from . import demo, paper_store
from .llm_client import get_llm, is_llm_ready
from .vector_store import get_vector_store

_log = logging.getLogger(__name__)
_settings = get_settings()

SYSTEM_PROMPT = """你是一个基于文献库的问答助手。请仅依据下方【参考资料】回答用户问题。
规则：
1. 如果参考资料中没有相关信息，直接回答"根据已有文献，无法找到相关信息"，不要编造。
2. 回答用中文，准确、简洁、有条理。
3. 回答末尾用 [来源: 论文ID-块序号] 标注关键依据。"""


def _chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    buf = ""
    for para in paragraphs:
        if len(buf) + len(para) + 2 <= chunk_size:
            buf = (buf + "\n" + para).strip()
        else:
            if buf:
                chunks.append(buf)
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - overlap):
                    chunks.append(para[i : i + chunk_size])
                buf = ""
            else:
                buf = para
    if buf:
        chunks.append(buf)
    return chunks


def index_paper(paper: ParsedPaper) -> int:
    chunks = _chunk_text(
        paper.full_text,
        chunk_size=_settings.RAG_CHUNK_SIZE,
        overlap=_settings.RAG_CHUNK_OVERLAP,
    )
    metadatas = [
        {"paper_id": paper.paper_id, "chunk_idx": i, "title": paper.meta.title or ""}
        for i in range(len(chunks))
    ]
    get_vector_store().add_chunks(paper.paper_id, chunks, metadatas)
    paper_store.mark_indexed(paper.paper_id, len(chunks))
    return len(chunks)


def answer_question(question: str, paper_ids: Optional[List[str]] = None) -> AnswerResult:
    store = get_vector_store()
    hits = store.query(question, n_results=_settings.RAG_TOP_K, paper_ids=paper_ids)

    if not hits:
        return AnswerResult(answer="文献库为空，请先上传并建立向量索引。", sources=[])

    sources = []
    for h in hits:
        meta = h["metadata"] or {}
        sources.append({
            "paper_id": meta.get("paper_id", "?"),
            "chunk_idx": meta.get("chunk_idx", 0),
            "title": meta.get("title", ""),
            "snippet": h.get("document", "")[:200],
            "distance": h.get("distance", 0),
            "document": h.get("document", ""),
            "metadata": meta,
        })

    if is_llm_ready():
        try:
            ref_blocks = []
            for s in sources:
                ref_blocks.append(
                    f"[来源: {s['paper_id']}-{s['chunk_idx']}]\n{s['document']}"
                )
            answer = get_llm().chat(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"【参考资料】\n{chr(10).join(ref_blocks)}\n\n【问题】\n{question}",
                    },
                ],
                temperature=0.3,
                max_tokens=1200,
            )
            return AnswerResult(answer=answer.strip(), sources=sources)
        except Exception as e:
            _log.warning("LLM 问答失败，回退 demo：%s", e)

    d = demo.demo_answer(question, sources)
    return AnswerResult(answer=d["answer"], sources=d["sources"])
