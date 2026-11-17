"""阅读笔记：先试 LLM 整理，失败走 demo（关键词分类）。"""
import logging
from typing import List, Optional

from ..database import SessionLocal
from ..db_models import Note, Paper
from ..models import NoteResult, NotesOrganizeResult
from . import demo, paper_store
from .llm_client import get_llm, is_llm_ready

_log = logging.getLogger(__name__)

ORGANIZE_PROMPT = """你是一个学术阅读笔记整理助手。用户会提供若干条从论文中摘录的片段（可能杂乱）。
请把它们整理成结构化笔记，要求：
1. 按「研究问题 / 方法 / 实验 / 结论 / 待深入」分类。
2. 用中文，保持原意，可适度归纳但不要编造。
3. 返回 JSON：
   - organized: 整理后的 Markdown 文本
   - structure: 数组，每项 {"category": "...", "items": ["..."]}
4. 只输出 JSON。"""


def add_note(paper_id: str, content: str) -> NoteResult:
    db = SessionLocal()
    try:
        paper = db.get(Paper, paper_id)
        if not paper:
            raise ValueError("论文不存在")
        note = Note(paper_id=paper_id, content=content)
        db.add(note)
        db.commit()
        db.refresh(note)
        return NoteResult(
            id=note.id,
            paper_id=note.paper_id,
            content=note.content,
            ai_summary=note.ai_summary,
            created_at=note.created_at.isoformat() if note.created_at else "",
        )
    finally:
        db.close()


def list_notes(paper_id: Optional[str] = None) -> List[NoteResult]:
    db = SessionLocal()
    try:
        q = db.query(Note)
        if paper_id:
            q = q.filter(Note.paper_id == paper_id)
        notes = q.order_by(Note.created_at.desc()).all()
        return [
            NoteResult(
                id=n.id,
                paper_id=n.paper_id,
                content=n.content,
                ai_summary=n.ai_summary,
                created_at=n.created_at.isoformat() if n.created_at else "",
            )
            for n in notes
        ]
    finally:
        db.close()


def delete_note(note_id: int) -> bool:
    db = SessionLocal()
    try:
        n = db.get(Note, note_id)
        if not n:
            return False
        db.delete(n)
        db.commit()
        return True
    finally:
        db.close()


def organize_notes(paper_id: str) -> NotesOrganizeResult:
    notes = list_notes(paper_id)
    if not notes:
        return NotesOrganizeResult(organized="该论文暂无笔记。", structure=[])

    paper_info = paper_store.get_paper(paper_id)
    paper_title = paper_info.get("title") if paper_info else None
    raw_contents = [n.content for n in notes]

    if is_llm_ready():
        try:
            result = get_llm().chat_json(
                [
                    {"role": "system", "content": ORGANIZE_PROMPT},
                    {
                        "role": "user",
                        "content": f"【论文 ID】{paper_id}\n【原始笔记】\n"
                                   + "\n\n".join(f"---\n{c}" for c in raw_contents),
                    },
                ],
                temperature=0.3,
            )
            organized = result.get("organized", "")
            if organized:
                db = SessionLocal()
                try:
                    first = db.query(Note).filter(Note.paper_id == paper_id).first()
                    if first:
                        first.ai_summary = organized
                        db.commit()
                finally:
                    db.close()
            return NotesOrganizeResult(
                organized=organized,
                structure=result.get("structure", []),
            )
        except Exception as e:
            _log.warning("LLM 笔记整理失败，回退 demo：%s", e)

    d = demo.demo_organize(paper_title, raw_contents)
    return NotesOrganizeResult(organized=d["organized"], structure=d["structure"])
