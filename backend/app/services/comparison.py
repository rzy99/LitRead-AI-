"""多论文思路对比：围绕 12 步研究流，不比较文本相似度。"""
import re
from typing import Any, Dict, List

from ..models import CompareResult, ThinkingAxis, ThinkingPaper
from . import paper_store, pdf_parser, research_flow, research_viz

AXES = [
    {"key": "start", "label": "起点", "phase": "context", "hint": "它从哪个问题或限制出发"},
    {"key": "turn", "label": "转折", "phase": "author", "hint": "哪个观察改变了方向"},
    {"key": "leap", "label": "关键跳跃", "phase": "author", "hint": "最大胆的一步直觉"},
    {"key": "design", "label": "设计取舍", "phase": "method", "hint": "把想法落成方法时赌了什么"},
    {"key": "evidence", "label": "证据策略", "phase": "evidence", "hint": "用什么实验让人相信"},
    {"key": "weakest", "label": "最脆弱假设", "phase": "critique", "hint": "红队最容易从哪里打穿"},
    {"key": "road", "label": "没走的路", "phase": "author", "hint": "作者放弃的备选路线"},
    {"key": "open", "label": "留下的问题", "phase": "idea", "hint": "它把什么问题留给了后人"},
]


def _clip(value, n: int = 120) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _plain(value) -> str:
    text = re.sub(r"[#*_>`]+", "", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def _sentence(value, n: int = 120) -> str:
    text = _plain(value)
    text = re.sub(r"^(研究问题|研究背景|问题|背景)\s*[：:]?\s*", "", text)
    for part in re.split(r"(?<=[。；!?])", text):
        part = part.strip(" ·-—")
        if len(part) >= 8:
            return _clip(part, n)
    return _clip(text, n)


def _beats(fork: dict) -> List[dict]:
    return [b for b in (fork.get("beats") or []) if isinstance(b, dict)]


def _find_beat(beats: List[dict], words: tuple, fallback: int = 1) -> dict:
    for beat in beats:
        move = str(beat.get("move") or "")
        if any(w in move for w in words):
            return beat
    return beats[min(fallback, len(beats) - 1)] if beats else {}


def _pattern(leap_text: str, design_text: str) -> str:
    text = f"{leap_text} {design_text}"
    rules = [
        ("重新定义", ("不该是", "应该是", "重新定义", "改写", "不是固定", "动态决定")),
        ("去依赖", ("不用", "去掉", "放弃", "绕开", "不依赖", "去除")),
        ("类比迁移", ("换成", "类比", "迁移", "借用")),
        ("结构重构", ("解耦", "拆解", "重构", "替换", "分解")),
        ("瓶颈驱动", ("瓶颈", "限制", "无法", "太慢")),
        ("测量驱动", ("评估", "测量", "指标", "基准", "协议", "度量")),
        ("矛盾驱动", ("矛盾", "冲突", "张力", "不一致")),
    ]
    for label, words in rules:
        if any(w in text for w in words):
            return label
    return "问题驱动"


def _design(fork: dict) -> str:
    rows = [r for r in (fork.get("design") or []) if isinstance(r, dict)]
    row = rows[0] if rows else {}
    return _clip(_plain(row.get("design") or row.get("beat") or "—"), 120)


def _road(fork: dict) -> str:
    alts = [a for a in (fork.get("alternatives") or []) if isinstance(a, dict)]
    if not alts:
        return "—"
    alt = alts[0]
    label = _plain(alt.get("label") or "备选路线")
    route = _sentence(alt.get("text"), 100)
    return _clip(route or label, 120)


def _weakest(viz: dict) -> str:
    argument = viz.get("argument") or {}
    fragile = _plain(argument.get("fragile") or "")
    if fragile:
        head = re.split(
            r"(如果它不成立|若它不成立|若该假设不成立|若\s*[A-Z0-9]+\s*不成立)", fragile
        )[0]
        if len(head) >= 18 and "最脆弱的假设" not in head:
            return _clip(head, 120)
    assumptions = argument.get("assumptions") or []
    if assumptions:
        first = assumptions[0]
        return _clip(first.get("title") or first.get("if_broken") or "—", 120)
    return "—"


def _open_question(value) -> str:
    text = _plain(value)
    match = re.search(r"新问题[：:]\s*(.+)", text)
    if match:
        tail = re.split(r"(与原论文的本质区别|与原论文的区别|本质区别)", match.group(1))[0]
        return _sentence(tail, 120)
    return _sentence(text, 120) or "—"


def _evidence(viz: dict, stages: dict) -> str:
    claims = (viz.get("argument") or {}).get("claims") or []
    if claims:
        support = _plain(claims[0].get("support") or "")
        if support:
            return _clip(support, 120)
    q7 = (stages.get("evidence") or {}).get("q7") or {}
    return _sentence(q7.get("content"), 120) or "—"


def _profile(paper_id: str) -> ThinkingPaper:
    info = paper_store.get_paper(paper_id)
    if not info:
        raise ValueError(f"论文 {paper_id} 不存在")

    parsed = pdf_parser.parse_pdf(info["filepath"])
    viz = research_viz.get_viz(parsed)
    fork = viz.get("fork") or {}
    beats = _beats(fork)
    title = info.get("title") or info.get("filename") or paper_id
    if not viz.get("ready") or not beats:
        raise ValueError(f"《{title}》还没有生成研究流，请先到研究流页完成 12 步生成")

    brief = research_flow.get_brief(parsed)
    stages = brief.get("stages") or {}
    q1 = (stages.get("context") or {}).get("q1") or {}
    q12 = (stages.get("idea") or {}).get("q12") or {}

    turn = _find_beat(beats, ("矛盾", "冲突", "转折", "异常"), 1)
    leap = _find_beat(beats, ("跳跃", "类比", "关键"), len(beats) - 1)

    leap_text = leap.get("leap") or leap.get("move") or "—"
    design_text = _design(fork)
    cells = [
        _sentence(q1.get("content"), 120) or _clip(beats[0].get("known"), 120),
        _clip(f"{turn.get('move') or ''}：{turn.get('question') or turn.get('leap') or ''}", 120),
        _clip(leap_text, 120),
        design_text,
        _evidence(viz, stages),
        _weakest(viz),
        _road(fork),
        _open_question(q12.get("content")),
    ]

    path = [
        {
            "index": b.get("index") if b.get("index") is not None else i,
            "move": b.get("move") or "",
            "known": b.get("known") or "",
            "question": b.get("question") or "",
            "leap": b.get("leap") or "",
            "temptation": b.get("temptation") or "",
        }
        for i, b in enumerate(beats)
    ]
    alternatives = [
        {
            "label": a.get("label") or f"备选路线 {i + 1}",
            "text": a.get("text") or "",
            "reason_dropped": a.get("reason_dropped") or "",
            "branch_from": a.get("branch_from"),
        }
        for i, a in enumerate(fork.get("alternatives") or [])
        if isinstance(a, dict)
    ]

    return ThinkingPaper(
        paper_id=paper_id,
        title=title,
        year=str(info.get("year") or ""),
        pattern=_pattern(leap_text, design_text),
        cells=cells,
        alternatives=alternatives,
        path=path,
    )


def _short_title(title: str) -> str:
    base = re.split(r"[：:]", str(title or ""), maxsplit=1)[0].strip() or str(title or "")
    return _clip(base, 32)


def _summary(papers: List[ThinkingPaper]) -> str:
    starts = "；".join(
        f"{_short_title(p.title)}：{_clip(p.cells[0], 26)}" for p in papers
    )
    leaps = "；".join(
        f"{_short_title(p.title)}：{_clip(p.cells[2], 26)}" for p in papers
    )
    return (
        f"起点 —— {starts}。"
        f"关键跳跃 —— {leaps}。"
        f"差异首先发生在起点和跳跃，而不是最后的结论。"
    )


def compare_thinking(paper_ids: List[str]) -> CompareResult:
    if len(paper_ids) < 2:
        raise ValueError("至少需要 2 篇论文才能对比")
    papers = [_profile(pid) for pid in paper_ids]
    return CompareResult(
        axes=[ThinkingAxis(**axis) for axis in AXES],
        papers=papers,
        summary=_summary(papers),
    )
