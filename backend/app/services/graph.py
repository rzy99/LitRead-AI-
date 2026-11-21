"""
论文关系图：用标题 + 摘要的语义相似度连接论文。

说明：
- 节点 = 论文；边 = 两篇论文的语义相近程度，不是引用关系。
- 每条边额外给出「共同高频术语」，让用户知道它们为什么相连。
- 小库（3-10 篇）时每篇至少连到最相近的 2 篇，避免出现空图。
"""
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Dict, List

import numpy as np

from ..config import get_settings
from ..models import GraphResult, GraphNode, GraphEdge
from . import embeddings, paper_store, pdf_parser

_settings = get_settings()

# 高频但无信息量的词（英文摘要场景）
_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "have", "has",
    "been", "their", "which", "these", "such", "using", "used", "based", "into", "than", "more",
    "most", "can", "may", "not", "our", "its", "also", "between", "over", "under", "two", "three",
    "all", "any", "each", "how", "what", "when", "where", "who", "will", "would", "could",
    "should", "about", "after", "before", "during", "through", "while", "within", "without",
    "across", "via", "per", "as", "at", "by", "in", "of", "on", "or", "to", "is", "it", "we",
    "a", "an", "be", "do", "does", "did", "one", "new", "use", "show", "shows", "result",
    "results", "paper", "propose", "proposed", "approach", "method", "methods", "work", "works",
    "data", "figure", "table", "section", "however", "therefore", "thus", "both", "only", "very",
    "much", "many", "some", "other", "others", "first", "second", "third", "high", "low", "large",
    "small", "good", "better", "best", "state", "art", "via", "toward", "towards", "novel",
    "existing", "current", "recent", "well", "significantly", "compared", "number", "based",
    "they", "them", "these", "those", "different", "various", "respectively", "shown", "see",
    "given", "case", "cases", "set", "sets", "value", "values", "time", "times", "order",
    "example", "further", "moreover", "additionally", "finally", "last", "next", "total",
    "due", "however", "therefore", "thus", "also", "such", "other", "others", "each", "both",
    "only", "very", "much", "many", "some", "first", "second", "third", "high", "low", "large",
    "small", "good", "better", "best", "new", "novel", "existing", "current", "recent",
    "well", "significantly", "compared", "number", "based", "used", "uses", "use", "using",
    "propose", "proposes", "proposed", "present", "presents", "presented", "describe",
    "paper", "section", "figure", "table", "equation", "appendix", "reference", "references",
    "result", "results", "they", "their", "there", "then", "than", "that",
}

_COLORS = ["#2F5D46", "#4E7C59", "#7A9A6E", "#A8874F", "#5E7C8C", "#8C6A5E"]


def _keywords(text: str) -> Counter:
    """词 + 二元短语的频次（只保留出现 >=2 次的）。"""
    t = (text or "").lower()
    for a, b in {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}.items():
        t = t.replace(a, b)
    t = re.sub(r"-\s*\n\s*", "", t)  # 合并 PDF 断词
    words = re.findall(r"[a-z][a-z\-]{2,}", t)
    counts: Counter = Counter()
    for w in words:
        if w not in _STOP:
            counts[w] += 1
    for a, b in zip(words, words[1:]):
        if a not in _STOP and b not in _STOP:
            counts[f"{a} {b}"] += 1
    return Counter({k: v for k, v in counts.items() if v >= 2})


def _short_title(title: str, width: int = 24) -> str:
    t = re.sub(r"\s+", " ", title or "").strip()
    if len(t) <= width:
        return t
    return t[: width - 1] + "…"


def build_graph() -> GraphResult:
    papers = paper_store.list_papers()
    if len(papers) < 2:
        return GraphResult(nodes=[], edges=[], html="<p>至少需要 2 篇论文才能构建关系图。</p>")

    texts = [
        f"{p.get('title') or p.get('filename', '')}. {p.get('abstract') or ''}"[:1200]
        for p in papers
    ]
    vecs = embeddings.embed(texts)  # 已 normalize

    # 共同术语从全文提取（摘要太短，容易一个词都不重合）
    kw_sources = []
    for i, p in enumerate(papers):
        try:
            parsed = pdf_parser.parse_pdf(p["filepath"])
            kw_sources.append((parsed.full_text or texts[i])[:20000])
        except Exception:
            kw_sources.append(texts[i])
    kws = [_keywords(t) for t in kw_sources]
    top_terms = [set(w for w, _ in c.most_common(40)) for c in kws]

    threshold = _settings.GRAPH_SIMILARITY_THRESHOLD
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    linked = set()

    for idx, p in enumerate(papers):
        meta_bits = [str(x) for x in [p.get("year"), (p.get("authors") or "")[:38]] if x]
        nodes.append(
            GraphNode(
                id=p["paper_id"],
                label=_short_title(p.get("title") or p.get("filename", "")),
                title=p.get("title") or p.get("filename", ""),
                meta=" · ".join(meta_bits),
                size=22,
                color=_COLORS[idx % len(_COLORS)],
            )
        )

    n = len(papers)
    sims = []
    for i in range(n):
        for j in range(i + 1, n):
            sims.append((i, j, float(np.dot(vecs[i], vecs[j]))))

    def _link(i: int, j: int, sim: float) -> None:
        key = (min(i, j), max(i, j))
        if key in linked:
            return
        linked.add(key)
        shared = sorted(
            top_terms[i] & top_terms[j],
            key=lambda w: -((kws[i][w] + kws[j][w]) * (1.7 if " " in w else 1.0)),
        )[:5]
        why = (
            "共同高频术语：" + "、".join(shared[:4])
            if shared
            else "标题与摘要语义相近，但没有共享的高频术语（多为同一大类、不同子方向）"
        )
        edges.append(
            GraphEdge(
                source=papers[i]["paper_id"],
                target=papers[j]["paper_id"],
                weight=round(sim, 3),
                label=f"{sim:.2f}",
                shared_terms=shared[:6],
                why=why,
            )
        )

    # 1) 超过绝对阈值：强关联
    for i, j, sim in sims:
        if sim >= threshold:
            _link(i, j, sim)

    # 2) 小库兜底：每篇至少连到最相近的 2 篇（相似度 >= 0.3）
    for i in range(n):
        peers = sorted(
            [(sim, j) for a, b, sim in sims for j in ([b] if a == i else ([a] if b == i else []))],
            reverse=True,
        )[:2]
        for sim, j in peers:
            if sim >= 0.3:
                _link(i, j, sim)

    html = _render_pyvis(nodes, edges)
    return GraphResult(nodes=nodes, edges=edges, html=html)


def _render_pyvis(nodes: List[GraphNode], edges: List[GraphEdge]) -> str:
    try:
        from pyvis.network import Network
    except ImportError:
        return "<p>pyvis 未安装，无法渲染交互图。</p>"

    net = Network(height="680px", width="100%", bgcolor="#FFFFFF", font_color="#1F2328",
                  directed=False, notebook=False)
    net.force_atlas_2based(gravity=-90, central_gravity=0.005, spring_length=260, spring_strength=0.05)
    net.set_options("""{
      "nodes": {"font": {"size": 17, "face": "arial", "strokeWidth": 3, "strokeColor": "#FFFFFF"},
                "borderWidth": 3, "shadow": {"enabled": true, "size": 10, "color": "rgba(0,0,0,0.12)"}},
      "edges": {"font": {"size": 14, "align": "middle", "background": "#FFFFFF"},
                "smooth": {"enabled": true, "type": "continuous"},
                "color": {"color": "#9DB3A0", "highlight": "#2F5D46", "hover": "#2F5D46"},
                "width": 1.5},
      "physics": {"solver": "forceAtlas2Based",
                  "forceAtlas2Based": {"gravitationalConstant": -90, "springLength": 260,
                                       "springConstant": 0.05, "damping": 0.6},
                  "stabilization": {"enabled": true, "iterations": 300}},
      "interaction": {"hover": true, "tooltipDelay": 80, "navigationButtons": true}
    }""")

    for node in nodes:
        tooltip = node.title + (f"\n{node.meta}" if node.meta else "")
        net.add_node(node.id, label=node.label, title=tooltip, size=node.size, color=node.color)

    for edge in edges:
        tooltip = f"相似度 {edge.weight:.2f}\n{edge.why}"
        net.add_edge(edge.source, edge.target, value=max(edge.weight * 6, 1.2),
                     label=edge.label, title=tooltip, color={"color": "#9DB3A0"})

    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        tmp_path = f.name
    try:
        net.write_html(tmp_path, notebook=False)
        html = Path(tmp_path).read_text(encoding="utf-8")
    finally:
        try:
            Path(tmp_path).unlink()
        except OSError:
            pass
    return html
