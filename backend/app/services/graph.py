"""
文献知识图谱：基于语义相似度构建论文关系网络。
节点=论文，边=语义相似度（超过阈值才连边）。
返回数据 + pyvis 可交互 HTML。
"""
import tempfile
from pathlib import Path
from typing import List

import numpy as np

from ..config import get_settings
from ..models import GraphResult, GraphNode, GraphEdge
from . import embeddings, paper_store

_settings = get_settings()


def build_graph() -> GraphResult:
    papers = paper_store.list_papers()
    if len(papers) < 2:
        return GraphResult(nodes=[], edges=[], html="<p>至少需要 2 篇论文才能构建图谱。</p>")

    # 用摘要 + 标题做 embedding
    texts = []
    for p in papers:
        t = p.get("title") or p.get("filename", "")
        a = p.get("abstract") or ""
        texts.append(f"{t}. {a}"[:1000])

    vecs = embeddings.embed(texts)  # (n, dim)，已 normalize

    threshold = _settings.GRAPH_SIMILARITY_THRESHOLD
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []

    for i, p in enumerate(papers):
        nodes.append(
            GraphNode(
                id=p["paper_id"],
                label=(p.get("title") or p.get("filename", ""))[:30],
                title=p.get("title") or p.get("filename", ""),
                size=15,
            )
        )

    # 两两计算相似度
    n = len(papers)
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(np.dot(vecs[i], vecs[j]))
            if sim >= threshold:
                edges.append(
                    GraphEdge(
                        source=papers[i]["paper_id"],
                        target=papers[j]["paper_id"],
                        weight=round(sim, 3),
                        label=f"{sim:.2f}",
                    )
                )

    html = _render_pyvis(nodes, edges)
    return GraphResult(nodes=nodes, edges=edges, html=html)


def _render_pyvis(nodes: List[GraphNode], edges: List[GraphEdge]) -> str:
    """用 pyvis 生成可交互 HTML。"""
    try:
        from pyvis.network import Network
    except ImportError:
        return "<p>pyvis 未安装，无法渲染交互图。</p>"

    net = Network(
        height="600px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#222222",
        directed=False,
        notebook=False,
    )
    net.force_atlas_2based(gravity=-50, central_gravity=0.01)

    for node in nodes:
        net.add_node(node.id, label=node.label, title=node.title, size=node.size)
    for edge in edges:
        net.add_edge(
            edge.source,
            edge.target,
            value=edge.weight * 5,
            title=f"相似度: {edge.weight}",
        )

    # 写入临时文件再读回（pyvis 只能写文件）
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
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
