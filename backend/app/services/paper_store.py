"""论文存储：基于 SQLAlchemy 的 CRUD。"""
from typing import List, Optional
from pathlib import Path

from ..database import SessionLocal
from ..db_models import Paper
from ..models import PaperMeta


def _to_dict(p: Paper) -> dict:
    return {
        "paper_id": p.id,
        "filename": p.filename,
        "filepath": p.filepath,
        "title": p.title,
        "authors": p.authors,
        "abstract": p.abstract,
        "keywords": p.keywords,
        "year": p.year,
        "total_pages": p.total_pages,
        "indexed": bool(p.indexed),
        "indexed_chunks": p.indexed_chunks,
    }


def add_paper(paper_id: str, filename: str, filepath: str, meta: PaperMeta) -> dict:
    db = SessionLocal()
    try:
        paper = Paper(
            id=paper_id,
            filename=filename,
            filepath=filepath,
            title=meta.title,
            authors=meta.authors,
            abstract=meta.abstract,
            keywords=meta.keywords,
            year=meta.year,
            total_pages=meta.total_pages,
        )
        db.merge(paper)  # 存在则更新
        db.commit()
        return _to_dict(db.get(Paper, paper_id))
    finally:
        db.close()


def list_papers() -> List[dict]:
    db = SessionLocal()
    try:
        papers = db.query(Paper).order_by(Paper.created_at.desc()).all()
        return [_to_dict(p) for p in papers]
    finally:
        db.close()


def get_paper(paper_id: str) -> Optional[dict]:
    db = SessionLocal()
    try:
        p = db.get(Paper, paper_id)
        return _to_dict(p) if p else None
    finally:
        db.close()


def mark_indexed(paper_id: str, chunks: int):
    db = SessionLocal()
    try:
        p = db.get(Paper, paper_id)
        if p:
            p.indexed = 1
            p.indexed_chunks = chunks
            db.commit()
    finally:
        db.close()


def delete_paper(paper_id: str) -> bool:
    db = SessionLocal()
    try:
        p = db.get(Paper, paper_id)
        if not p:
            return False
        fp = p.filepath
        db.delete(p)
        db.commit()
        if fp and Path(fp).exists():
            try:
                Path(fp).unlink()
            except OSError:
                pass
        return True
    finally:
        db.close()
