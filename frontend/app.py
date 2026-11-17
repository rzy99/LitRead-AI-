"""
LitRead AI — 前端（Streamlit）
功能：解析 / 速读 / 问答 / 对比 / 图谱 / 笔记 / Related Work / BibTeX 导出
"""
import io
import os

import requests
import streamlit as st
import streamlit.components.v1 as components

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="LitRead AI · 文献阅读助手",
    page_icon="📚",
    layout="wide",
)


# ---------- 工具 ----------
def _err(r):
    try:
        return r.json().get("detail", r.text)
    except Exception:
        return r.text


def api_get(path):
    try:
        r = requests.get(f"{BACKEND_URL}{path}", timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        resp = getattr(e, "response", None)
        st.error(f"请求失败：{_err(resp) if resp is not None else e}")
        return None


def api_post(path, json=None, files=None):
    try:
        r = requests.post(f"{BACKEND_URL}{path}", json=json, files=files, timeout=180)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        resp = getattr(e, "response", None)
        st.error(f"请求失败：{_err(resp) if resp is not None else e}")
        return None


def api_delete(path):
    try:
        r = requests.delete(f"{BACKEND_URL}{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        resp = getattr(e, "response", None)
        st.error(f"请求失败：{_err(resp) if resp is not None else e}")
        return None


def fetch_papers():
    data = api_get("/api/papers")
    return data.get("papers", []) if data else []


# ---------- 侧边栏 ----------
with st.sidebar:
    st.title("📚 LitRead AI")
    st.caption("AI for Learning & Research")
    st.markdown("---")
    stats = api_get("/api/library/stats") or {}
    st.metric("已上传论文", stats.get("papers", 0))
    st.metric("向量索引块", stats.get("vectors", 0))

    health = api_get("/api/health") or {}
    if health.get("demo_mode"):
        st.warning(
            "🟡 **Demo 模式**：未配置 LLM API Key。\n"
            "速读/问答/对比 会用检索结果或模板替代，\n"
            "上传/索引/图谱/笔记 全部正常。"
        )
    elif health.get("llm_ready"):
        st.success("🟢 LLM 已就绪")

    st.markdown("---")
    st.caption(f"后端：{BACKEND_URL}")
    if st.button("🔄 刷新"):
        st.rerun()


# ---------- Tabs ----------
tabs = st.tabs(
    [
        "📄 解析",
        "⚡ 速读",
        "💬 问答",
        "⚖️ 对比",
        "🕸️ 图谱",
        "📝 笔记",
        "✍️ Related Work",
        "📑 BibTeX",
    ]
)
tab_parse, tab_summary, tab_ask, tab_compare, tab_graph, tab_notes, tab_rw, tab_bib = tabs


# ===================== 论文解析 =====================
with tab_parse:
    st.header("📄 上传并解析论文")
    st.caption("PDF → 自动提取标题/作者/摘要/章节结构")

    uploaded = st.file_uploader("选择 PDF", type=["pdf"], key="uploader")
    if uploaded:
        if st.button("开始解析", type="primary"):
            with st.spinner("解析中..."):
                files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
                result = api_post("/api/papers/upload", files=files)
            if result:
                st.success(f"完成！ID: `{result['paper_id']}`")
                meta = result.get("meta", {})
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**标题**：{meta.get('title') or '（未识别）'}")
                    st.markdown(f"**作者**：{meta.get('authors') or '（未识别）'}")
                    st.markdown(f"**页数**：{meta.get('total_pages')}")
                with c2:
                    st.markdown(f"**关键词**：{meta.get('keywords') or '（未识别）'}")
                    st.markdown(f"**字数**：{result.get('text_length')}")
                    st.markdown(f"**章节**：{result.get('section_count')}")
                if meta.get("abstract"):
                    with st.expander("摘要"):
                        st.write(meta["abstract"])

    st.markdown("---")
    st.subheader("已上传论文")
    papers = fetch_papers()
    if not papers:
        st.info("暂无论文")
    else:
        for p in papers:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
                with c1:
                    st.markdown(f"**{p.get('title', p.get('filename'))}**")
                    idx_badge = "🟢 已索引" if p.get("indexed") else "⚪ 未索引"
                    st.caption(f"`{p['paper_id']}` · {p.get('filename')} · {idx_badge}")
                with c2:
                    if st.button("📖", key=f"parse_{p['paper_id']}"):
                        st.session_state[f"detail_{p['paper_id']}"] = api_post(
                            f"/api/papers/{p['paper_id']}/parse"
                        )
                with c3:
                    if st.button("📑", key=f"bib_{p['paper_id']}"):
                        st.session_state[f"bib_{p['paper_id']}"] = api_get(
                            f"/api/papers/{p['paper_id']}/bibtex"
                        )
                with c4:
                    if st.button("🗑️", key=f"del_{p['paper_id']}"):
                        api_delete(f"/api/papers/{p['paper_id']}")
                        st.rerun()
                detail = st.session_state.get(f"detail_{p['paper_id']}")
                if detail:
                    with st.expander("结构化内容"):
                        meta = detail.get("meta", {})
                        st.markdown(f"**摘要**：{meta.get('abstract') or '无'}")
                        for sec in detail.get("sections", [])[:20]:
                            st.markdown(f"**{sec['heading']}**")
                            st.caption(sec["content"][:300] + "...")
                bib = st.session_state.get(f"bib_{p['paper_id']}")
                if bib:
                    with st.expander("BibTeX"):
                        st.code(bib.get("bibtex", ""), language="bibtex")


# ===================== 速读卡片 =====================
with tab_summary:
    st.header("⚡ 论文速读卡片")
    papers = fetch_papers()
    if not papers:
        st.info("请先上传论文")
    else:
        options = {f"{p.get('title', p['filename'])} ({p['paper_id']})": p["paper_id"] for p in papers}
        choice = st.selectbox("选择论文", list(options.keys()), key="sum_sel")
        pid = options[choice]
        if st.button("生成速读卡片", type="primary"):
            with st.spinner("AI 阅读中..."):
                st.session_state[f"sum_{pid}"] = api_post(f"/api/papers/{pid}/summary")
        result = st.session_state.get(f"sum_{pid}")
        if result:
            st.markdown("### 📌 TL;DR")
            st.info(result.get("tldr", ""))
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 🎯 核心贡献")
                st.write(result.get("core_contribution", ""))
                st.markdown("#### 🔬 方法亮点")
                st.write(result.get("method_highlights", ""))
            with c2:
                st.markdown("#### 📊 主要结论")
                st.write(result.get("key_findings", ""))
                st.markdown("#### ⚠️ 局限性")
                st.write(result.get("limitations", ""))


# ===================== 文献问答 =====================
with tab_ask:
    st.header("💬 基于文献库的问答")
    papers = fetch_papers()
    if papers:
        st.subheader("1️⃣ 管理索引")
        for p in papers:
            with st.container(border=True):
                cc1, cc2 = st.columns([5, 1])
                with cc1:
                    st.markdown(f"**{p.get('title', p['filename'])}**")
                    st.caption(f"`{p['paper_id']}` · 块数: {p.get('indexed_chunks', 0)}")
                with cc2:
                    if st.button("➕ 索引", key=f"idx_{p['paper_id']}"):
                        with st.spinner("建立向量索引..."):
                            res = api_post(f"/api/papers/{p['paper_id']}/index")
                        if res:
                            st.success(f"已索引 {res.get('indexed_chunks')} 块")
                            st.rerun()
    st.markdown("---")
    st.subheader("2️⃣ 提问")
    question = st.text_input("问题", placeholder="例如：这些论文用了什么数据集？")
    if st.button("提问", type="primary") and question.strip():
        with st.spinner("检索 + 生成中..."):
            result = api_post("/api/ask", json={"question": question})
        if result:
            st.markdown("### 🤖 回答")
            st.write(result.get("answer", ""))
            sources = result.get("sources", [])
            if sources:
                with st.expander(f"📎 参考来源（{len(sources)}）"):
                    for i, s in enumerate(sources, 1):
                        sim = 1 - float(s.get("distance", 0))
                        st.markdown(
                            f"**{i}.** `{s.get('paper_id')}-{s.get('chunk_idx')}` "
                            f"（相关度 {sim:.3f}）"
                        )
                        st.caption(s.get("snippet", ""))


# ===================== 多论文对比 =====================
with tab_compare:
    st.header("⚖️ 多论文对比")
    st.caption("选择 2+ 篇论文，AI 生成并排对比表 + 共识/分歧分析")
    papers = fetch_papers()
    if len(papers) < 2:
        st.warning("至少上传 2 篇论文才能对比")
    else:
        paper_map = {p["paper_id"]: p.get("title", p["filename"]) for p in papers}
        selected = st.multiselect(
            "选择论文",
            options=list(paper_map.keys()),
            format_func=lambda pid: paper_map[pid],
        )
        focus = st.text_input("对比侧重点（可选）", placeholder="如：方法、数据集、指标")
        if st.button("生成对比", type="primary", disabled=len(selected) < 2):
            with st.spinner("对比分析中..."):
                result = api_post(
                    "/api/compare",
                    json={"paper_ids": selected, "focus": focus or None},
                )
            st.session_state["compare_result"] = result

        result = st.session_state.get("compare_result")
        if result:
            headers = result.get("headers", [])
            rows = result.get("rows", [])
            if headers and rows:
                # 对比表
                table_data = []
                for row in rows:
                    line = {"论文": row.get("title", row.get("paper_id", ""))}
                    for h in headers:
                        line[h] = row.get(h, "")
                    table_data.append(line)
                st.dataframe(table_data, use_container_width=True, hide_index=True)

                # 导出 Markdown
                md_result = api_post("/api/compare/export", json=result)
                if md_result:
                    md_text = md_result.get("markdown", "")
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        st.download_button(
                            "⬇️ 导出 Markdown",
                            data=md_text,
                            file_name="comparison.md",
                            mime="text/markdown",
                        )
                    with c2:
                        with st.expander("预览导出的 Markdown"):
                            st.code(md_text, language="markdown")

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### ✅ 共识点")
                st.write(result.get("consensus", "无"))
            with c2:
                st.markdown("#### ❗ 分歧点")
                st.write(result.get("divergence", "无"))


# ===================== 文献图谱 =====================
with tab_graph:
    st.header("🕸️ 文献知识图谱")
    st.caption("基于语义相似度的论文关系网络（边越粗相似度越高）")
    if st.button("🔄 重新生成图谱", type="primary"):
        with st.spinner("计算语义相似度..."):
            st.session_state["graph"] = api_get("/api/graph")

    g = st.session_state.get("graph")
    if g:
        nodes = g.get("nodes", [])
        edges = g.get("edges", [])
        c1, c2, c3 = st.columns(3)
        c1.metric("论文节点", len(nodes))
        c2.metric("关系边", len(edges))
        c3.metric(
            "平均相似度",
            round(sum(e["weight"] for e in edges) / max(len(edges), 1), 3)
            if edges
            else 0,
        )

        html = g.get("html", "")
        if html and "pyvis" in html.lower():
            components.html(html, height=650, scrolling=True)
        else:
            st.info(html or "暂无图谱")

        with st.expander("边列表"):
            for e in edges:
                src = next((n["title"] for n in nodes if n["id"] == e["source"]), e["source"])
                tgt = next((n["title"] for n in nodes if n["id"] == e["target"]), e["target"])
                st.markdown(f"- **{src[:25]}** ↔ **{tgt[:25]}** · 相似度 {e['weight']}")
    else:
        st.info("点击上方按钮生成图谱")


# ===================== 阅读笔记 =====================
with tab_notes:
    st.header("📝 阅读笔记")
    st.caption("摘录论文片段 → AI 自动整理成结构化笔记")
    papers = fetch_papers()
    if not papers:
        st.info("请先上传论文")
    else:
        paper_map = {p["paper_id"]: p.get("title", p["filename"]) for p in papers}
        pid = st.selectbox(
            "选择论文",
            options=list(paper_map.keys()),
            format_func=lambda x: paper_map[x],
            key="note_paper",
        )

        col_a, col_b = st.columns([3, 1])
        with col_a:
            note_content = st.text_area("摘录片段 / 批注", height=100, key="note_input")
        with col_b:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ 添加笔记", type="primary"):
                if note_content.strip():
                    api_post(f"/api/papers/{pid}/notes", json={"content": note_content})
                    st.success("已添加")
                    st.rerun()

        st.markdown("---")
        all_notes = api_get(f"/api/notes?paper_id={pid}")
        note_list = all_notes.get("notes", []) if all_notes else []

        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader(f"笔记列表（{len(note_list)}）")
        with c2:
            if st.button("✨ AI 整理笔记", disabled=len(note_list) == 0):
                with st.spinner("AI 整理中..."):
                    org = api_post(f"/api/papers/{pid}/notes/organize")
                st.session_state[f"org_{pid}"] = org

        for n in note_list:
            with st.container(border=True):
                st.write(n.get("content", ""))
                st.caption(f"#{n['id']} · {n.get('created_at', '')[:19]}")

        org = st.session_state.get(f"org_{pid}")
        if org:
            st.markdown("---")
            st.subheader("✨ 整理结果")
            st.markdown(org.get("organized", ""))


# ===================== Related Work =====================
with tab_rw:
    st.header("✍️ Related Work 草稿")
    st.caption("输入你的研究主题，基于库中论文生成一段 Related Work。未配置 LLM 时用关键词匹配。")
    papers = fetch_papers()
    if not papers:
        st.info("请先上传论文")
    else:
        topic = st.text_input(
            "你的研究主题（英文，效果更好）",
            placeholder="例如：retrieval augmented generation for scientific literature",
        )
        paper_map = {p["paper_id"]: p.get("title", p["filename"]) for p in papers}
        selected = st.multiselect(
            "参考哪些论文",
            options=list(paper_map.keys()),
            format_func=lambda x: paper_map[x],
            default=list(paper_map.keys()),
            key="rw_sel",
        )
        if st.button("生成 Related Work", type="primary") and topic.strip():
            with st.spinner("生成中..."):
                result = api_post(
                    "/api/related-work",
                    json={"topic": topic, "paper_ids": selected},
                )
            st.session_state["rw_result"] = result

        result = st.session_state.get("rw_result")
        if result:
            st.markdown("### 📄 Related Work 段落")
            st.write(result.get("paragraph", ""))

            # 下载按钮
            c1, c2 = st.columns([1, 5])
            with c1:
                st.download_button(
                    "⬇️ 下载 .md",
                    data="# Related Work\n\n" + result.get("paragraph", ""),
                    file_name="related_work.md",
                    mime="text/markdown",
                )

            cites = result.get("citations", [])
            if cites:
                with st.expander("📚 引用来源"):
                    for c in cites:
                        st.markdown(f"- **{c.get('title', '')}** (`{c.get('paper_id', '')}`)")


# ===================== BibTeX =====================
with tab_bib:
    st.header("📑 BibTeX 导出")
    papers = fetch_papers()
    if not papers:
        st.info("请先上传论文")
    else:
        paper_map = {p["paper_id"]: p.get("title", p["filename"]) for p in papers}
        selected = st.multiselect(
            "选择要导出 BibTeX 的论文",
            options=list(paper_map.keys()),
            format_func=lambda x: paper_map[x],
            default=list(paper_map.keys()),
            key="bib_sel",
        )

        if st.button("生成 BibTeX", type="primary") and selected:
            with st.spinner("生成中..."):
                result = api_post("/api/bibtex/export", json={"paper_ids": selected})
            st.session_state["bib_result"] = result

        result = st.session_state.get("bib_result")
        if result:
            bib = result.get("bibtex", "")
            st.code(bib, language="bibtex")
            st.download_button(
                "⬇️ 下载 references.bib",
                data=bib,
                file_name="references.bib",
                mime="text/plain",
            )
