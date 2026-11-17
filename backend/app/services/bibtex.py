"""BibTeX 自动生成 + 批量导出。"""
import logging
from typing import List

from ..services import demo, paper_store
from .llm_client import get_llm, is_llm_ready

_log = logging.getLogger(__name__)


def generate_bibtex(paper_id: str) -> str:
    info = paper_store.get_paper(paper_id)
    if not info:
        raise ValueError(f"论文 {paper_id} 不存在")
    return demo.make_bibtex(info)


def export_bibtex(paper_ids: List[str]) -> str:
    parts = []
    for pid in paper_ids:
        try:
            parts.append(generate_bibtex(pid))
        except ValueError:
            continue
    return "\n".join(parts)
