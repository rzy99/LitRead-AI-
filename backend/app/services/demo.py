"""
Demo 模式：当 LLM 不可用时，基于论文的摘要/关键词/元数据生成一份结构完整但不依赖外部调用的结果。
所有内容都直接来自 PDF 解析结果，不会编造数据。
"""
import re
from typing import List, Dict, Optional


def _sentences(text: str) -> List[str]:
    """把文本切成句子（中英文兼容）。"""
    if not text:
        return []
    s = re.sub(r"\s+", " ", text).strip()
    # 用中英文句号/问号/感叹号分句
    parts = re.split(r"(?<=[。！？.!?])\s+", s)
    return [p.strip() for p in parts if p.strip()]


# ---------- Summary ----------

def demo_summary(title: Optional[str], abstract: Optional[str]) -> dict:
    sents = _sentences(abstract or "")
    title = title or "该论文"

    # TL;DR：从摘要取前三句
    tldr_parts = sents[:3]
    tldr = " ".join(tldr_parts) if tldr_parts else "未识别到可用摘要，请使用真实 LLM 获得更好的效果。"
    if len(tldr) > 300:
        tldr = tldr[:300] + "..."

    # 核心贡献：标题 + 首句
    first = sents[0] if sents else f"围绕「{title}」主题展开研究"
    core = first[:140]

    # 方法亮点：把中间句子当方法
    method = (sents[1] if len(sents) > 1 else
              "方法细节在当前 Demo 模式下无法自动提取；请配置 LLM_API_KEY 启用完整能力。")

    # 关键结论：最后一句
    findings = (sents[-1] if sents else
                "实验结论需真实 LLM 从正文中归纳，Demo 模式仅做占位。")

    # 局限性：模板
    lim = "Demo 模式下无法自动分析局限性；真实 LLM 会从正文中客观归纳。"

    return {
        "core_contribution": core,
        "method_highlights": method,
        "key_findings": findings,
        "limitations": lim,
        "tldr": tldr,
    }


# ---------- Compare ----------

def demo_compare(papers: List[dict]) -> dict:
    """papers = [{title, abstract, keywords, year, paper_id}]"""
    headers = ["论文", "核心主题", "研究问题", "关键词"]
    rows = []
    for p in papers:
        title = p.get("title") or p.get("filename") or "(未命名)"
        abs_text = p.get("abstract") or ""
        kws = p.get("keywords") or ""
        sents = _sentences(abs_text)

        rows.append({
            "paper_id": p.get("paper_id", ""),
            "title": title,
            "论文": title,
            "核心主题": (sents[0] if sents else "未识别"),
            "研究问题": (sents[0] if sents else "未识别")[:80],
            "关键词": kws or "未识别",
        })

    # 找共识/分歧：用关键词重叠度
    kw_sets = []
    for p in papers:
        kws = p.get("keywords") or ""
        tokens = set(re.split(r"[,，;；\s]+", kws.strip()))
        tokens.discard("")
        kw_sets.append(tokens)

    common = set.intersection(*kw_sets) if kw_sets else set()
    union = set.union(*kw_sets) if kw_sets else set()
    diff = union - common

    consensus = (
        f"关键词重叠：{', '.join(sorted(common))}（{len(common)} 个）"
        if common else "这几篇论文关键词无明显重叠。"
    )
    divergence = (
        f"关键词差异：{', '.join(sorted(diff)[:8])}"
        if diff else "关键词高度一致。"
    )

    return {
        "headers": headers,
        "rows": rows,
        "consensus": consensus,
        "divergence": divergence,
    }


# ---------- RAG ----------

def demo_answer(question: str, sources: List[dict]) -> dict:
    """sources 是向量检索的 top-k 片段（已经带 paper_id 和 snippet）。"""
    q = question.strip()
    if not sources:
        answer = (
            f"我在你的论文库中没有找到与「{q}」相关的片段。"
            "请先上传论文并建立向量索引（在📖 问答页面的索引区点击「➕ 索引」）。"
        )
    else:
        intro = f"以下是关于「{q}」的相关片段（Demo 模式基于向量检索的真实内容，未经过 LLM 综合）：\n\n"
        parts = []
        for i, s in enumerate(sources[:3], 1):
            parts.append(f"[{i}] {s.get('metadata', {}).get('paper_id', '')}\n{s.get('document', '')}")
        answer = intro + "\n\n---\n\n".join(parts)

    return {
        "answer": answer,
        "sources": sources,
    }


# ---------- Notes organize ----------

def demo_organize(paper_title: Optional[str], raw_notes: List[str]) -> dict:
    """把笔记按长度分桶塞进伪分类。"""
    buckets: Dict[str, List[str]] = {
        "研究问题": [],
        "方法": [],
        "实验/数据": [],
        "结论/发现": [],
    }
    keywords_map = {
        "研究问题": ["problem", "question", "问题", "挑战", "challenge"],
        "方法": ["method", "approach", "model", "方法", "模型", "pipeline", "框架"],
        "实验/数据": ["dataset", "experiment", "实验", "数据", "dataset", "benchmark"],
        "结论/发现": ["result", "conclusion", "结果", "结论", "发现", "we find"],
    }

    organized_lines = [f"# 结构化笔记：{paper_title or '某篇论文'}（Demo 模式）", ""]
    for raw in raw_notes:
        lowered = raw.lower()
        placed = False
        for cat, kws in keywords_map.items():
            if any(k in lowered for k in kws):
                buckets[cat].append(raw)
                placed = True
                break
        if not placed:
            # 按长度启发式：短的进方法，长的进结论
            if len(raw) < 60:
                buckets["方法"].append(raw)
            else:
                buckets["结论/发现"].append(raw)

    structure = []
    for cat, items in buckets.items():
        if items:
            organized_lines.append(f"## {cat}")
            for item in items:
                organized_lines.append(f"- {item}")
            organized_lines.append("")
            structure.append({"category": cat, "items": items})

    if not any(buckets.values()):
        organized_lines.append("（暂无笔记内容）")

    return {
        "organized": "\n".join(organized_lines),
        "structure": structure,
    }


# ---------- BibTeX ----------

def make_bibtex(meta: dict) -> str:
    """根据论文元数据生成 BibTeX（无 LLM 也能跑）。"""
    title = (meta.get("title") or "").strip() or "Untitled"
    year = (meta.get("year") or "").strip() or "n.d."
    authors_raw = (meta.get("authors") or "").strip()
    if authors_raw:
        # 统一作者分隔符
        authors_raw = authors_raw.replace(", and ", " and ").replace(" and ", " and ")
        authors = authors_raw.replace(", ", " and ")
    else:
        authors = "Unknown"

    tag = _cite_key(authors, year, title)

    return (
        "@article{" + tag + ",\n"
        f"  title     = {{{title}}},\n"
        f"  author    = {{{authors}}},\n"
        f"  year      = {{{year}}},\n"
        "  journal   = {Preprint or Unknown},\n"
        "}\n"
    )


def _cite_key(authors: str, year: str, title: str) -> str:
    """生成形如 zhang2024scirag 的引用键。"""
    first = authors.split(" and ")[0].split(",")[0].strip()
    surname = re.sub(r"[^A-Za-z]", "", first.split()[-1]).lower() if first else ""
    y = re.sub(r"\D", "", year) or "nd"
    stop = {"a", "an", "the", "on", "of", "for", "with", "and", "to", "in", "via", "towards"}
    words = [w for w in re.findall(r"[A-Za-z]+", title) if w.lower() not in stop]
    head = (words[0].lower() if words else "paper")[:12]
    return f"{surname or 'anon'}{y}{head}"


# ---------- Related Work ----------

def demo_related_work(your_topic: str, papers: List[dict]) -> dict:
    """基于关键词交集生成 Related Work 草稿（不调 LLM）。"""
    if not papers:
        return {"paragraph": "（库中暂无论文，无法生成 Related Work）", "citations": []}

    topic_tokens = set(re.split(r"[,，;；\s]+", your_topic.lower()))
    topic_tokens.discard("")

    scored = []
    for p in papers:
        kws_raw = p.get("keywords") or ""
        kws = set(re.split(r"[,，;；\s]+", kws_raw.lower()))
        title = (p.get("title") or p.get("filename") or "").strip()
        title_tokens = set(re.split(r"[\s\-]+", title.lower()))
        score = len((kws | title_tokens) & topic_tokens)
        scored.append((score, p))
    scored.sort(key=lambda x: -x[0])

    cited = scored[:3]
    lines = [f"本文与以下工作在「{your_topic}」方向上密切相关："]
    for score, p in cited:
        title = p.get("title") or p.get("filename", "")
        if score == 0:
            lines.append(f"- 与《{title}》同属相关研究方向（关键词匹配 {score} 个）。")
        else:
            lines.append(f"- 《{title}》讨论了相关话题（关键词匹配 {score} 个）。")

    return {
        "paragraph": "\n".join(lines),
        "citations": [{"title": p.get("title"), "paper_id": p.get("paper_id")} for _, p in cited],
    }
