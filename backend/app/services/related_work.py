"""Related Work 草稿：先试 LLM，失败走 demo 关键词匹配。"""
import logging
from typing import List

from ..services import demo, paper_store
from .llm_client import get_llm, is_llm_ready

_log = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一位学术写作助手。请基于提供的论文列表和用户的研究主题，
生成一段 150-250 字的 Related Work 段落。

要求：
1. 用英文写，正式学术风格。
2. 提及与主题最相关的 3-5 篇论文，用作者年份法引用，如（Smith et al., 2023）。
3. 避免编造：如果某篇论文的作者/年份未提取到，用它的标题代替。
4. 返回 JSON：{"paragraph": "...", "citations": [{"title": "...", "authors": "...", "year": "..."}]}"""


def generate_related_work(your_topic: str, paper_ids: List[str]) -> dict:
    infos = []
    for pid in paper_ids:
        info = paper_store.get_paper(pid)
        if info:
            infos.append(info)

    if is_llm_ready():
        try:
            papers_text = "\n".join(
                f"- [{p['paper_id']}] {p.get('title') or p.get('filename')} | "
                f"作者: {p.get('authors') or '?'} | 年份: {p.get('year') or '?'} | "
                f"摘要: {(p.get('abstract') or '')[:200]}"
                for p in infos
            )
            result = get_llm().chat_json(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"【我的研究主题】\n{your_topic}\n\n【论文库】\n{papers_text}",
                    },
                ],
                temperature=0.4,
            )
            return {
                "paragraph": result.get("paragraph", ""),
                "citations": result.get("citations", []),
            }
        except Exception as e:
            _log.warning("LLM Related Work 失败，回退 demo：%s", e)

    return demo.demo_related_work(your_topic, infos)
