"""多论文对比：先试 LLM，失败走 demo。"""
import logging
from typing import List

from ..models import CompareResult
from . import demo, paper_store, pdf_parser
from .llm_client import get_llm, is_llm_ready

_log = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个学术对比分析助手。用户会提供多篇论文的摘要与正文片段，请生成一份结构化对比。
要求：
1. 返回 JSON，字段如下：
   - headers: 对比维度列表（如：研究问题、核心方法、数据集、评价指标、主要结果、局限性）
   - rows: 数组，每个元素是一篇论文的对比结果，key 必须与 headers 完全一致，另含 "paper_id" 和 "title" 字段
   - consensus: 多篇论文的共识点（1-2 句）
   - divergence: 多篇论文的分歧点（1-2 句）
2. 内容用中文，简洁准确。
3. 只输出 JSON。"""


def compare_papers(paper_ids: List[str], focus: str = "") -> CompareResult:
    if len(paper_ids) < 2:
        raise ValueError("至少需要 2 篇论文才能对比")

    paper_meta: List[dict] = []
    for pid in paper_ids:
        info = paper_store.get_paper(pid)
        if not info:
            raise ValueError(f"论文 {pid} 不存在")
        paper_meta.append(info)

    if is_llm_ready():
        try:
            paper_blocks = []
            for info in paper_meta:
                parsed = pdf_parser.parse_pdf(info["filepath"])
                paper_blocks.append(
                    f"【论文 {info['paper_id']}】\n"
                    f"标题：{info.get('title') or info.get('filename')}\n"
                    f"摘要：{parsed.meta.abstract or '（无）'}\n"
                    f"正文片段：{parsed.full_text[:8000]}"
                )
            user_content = "\n\n=====\n\n".join(paper_blocks)
            if focus:
                user_content += f"\n\n【对比侧重点】{focus}"

            result = get_llm().chat_json(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
            )
            headers = result.get("headers", [])
            rows = result.get("rows", [])
            for row, pid in zip(rows, paper_ids):
                row.setdefault("paper_id", pid)
            return CompareResult(
                headers=headers,
                rows=rows,
                consensus=result.get("consensus", ""),
                divergence=result.get("divergence", ""),
            )
        except Exception as e:
            _log.warning("LLM 对比失败，回退 demo：%s", e)

    d = demo.demo_compare(paper_meta)
    return CompareResult(
        headers=d["headers"],
        rows=d["rows"],
        consensus=d["consensus"],
        divergence=d["divergence"],
    )
