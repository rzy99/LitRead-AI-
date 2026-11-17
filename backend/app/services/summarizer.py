"""论文速读卡片：先试 LLM，失败走 demo。"""
import logging
from typing import Dict

from ..config import get_settings
from ..models import ParsedPaper, SummaryResult
from . import demo
from .llm_client import get_llm, is_llm_ready

_settings = get_settings()
_log = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个资深学术论文解读助手。请基于用户提供的论文内容，输出一份结构化的速读卡片。
要求：
1. 用中文回答，简洁专业。
2. 严格返回 JSON，包含以下字段：
   - core_contribution: 一句话核心贡献（不超过 60 字）
   - method_highlights: 方法亮点（2-3 句，讲清楚关键技术）
   - key_findings: 实验/主要结论（2-3 句，含关键结果）
   - limitations: 局限性（1-2 句，客观指出不足）
   - tldr: 三句话 TL;DR，让外行也能看懂这篇论文做了什么、怎么做、效果如何
3. 只输出 JSON，不要多余文字。"""


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.7)]
    tail = text[-int(max_chars * 0.3):]
    return head + "\n...[中间省略]...\n" + tail


def summarize_paper(paper: ParsedPaper) -> SummaryResult:
    if is_llm_ready():
        try:
            content_parts = []
            if paper.meta.abstract:
                content_parts.append(f"【摘要】\n{paper.meta.abstract}")
            body = _truncate_text(paper.full_text, _settings.SUMMARY_MAX_CHARS)
            content_parts.append(f"【正文】\n{body}")

            result: Dict = get_llm().chat_json(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": "\n\n".join(content_parts)},
                ],
                temperature=0.2,
            )
            return SummaryResult(
                core_contribution=result.get("core_contribution", "(未提取到)"),
                method_highlights=result.get("method_highlights", "(未提取到)"),
                key_findings=result.get("key_findings", "(未提取到)"),
                limitations=result.get("limitations", "(未提取到)"),
                tldr=result.get("tldr", result.get("raw", "(生成失败)")),
            )
        except Exception as e:
            _log.warning("LLM 摘要失败，回退 demo：%s", e)

    d = demo.demo_summary(paper.meta.title, paper.meta.abstract)
    return SummaryResult(
        core_contribution=d["core_contribution"],
        method_highlights=d["method_highlights"],
        key_findings=d["key_findings"],
        limitations=d["limitations"],
        tldr=d["tldr"],
    )
