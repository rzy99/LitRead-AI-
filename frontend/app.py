"""
LitRead · 学术工作台（Design v2 · Editorial Academic）

设计语言：纸感底色、衬线标题、克制排版、发丝线分割、SVG 图标、轻微动效。
功能：解析 / 研究流 / 对比 / 概述图 / 笔记
      + 用户自配 Key（不落盘）+ IP 限流 + Demo 模式
"""
import base64
import html as html_lib
import json
import os
import re
import uuid

import requests
import streamlit as st
import streamlit.components.v1 as components

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── 品牌资源 ──
_ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _asset_uri(name):
    try:
        with open(os.path.join(_ASSET_DIR, name), "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    except OSError:
        return ""


LOGO_URI = _asset_uri("logo.png")
LOGO_MARK_URI = _asset_uri("logo-mark.png")
LOGO_MARK = os.path.join(_ASSET_DIR, "logo-mark.png")

# ── 品牌 SVG（favicon 兜底） ──
FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='7' fill='%2320201C'/%3E"
    "%3Cpath d='M11 8h3.2v11.8H22V23H11z' fill='%23F7F5F0'/%3E%3C/svg%3E"
)

st.set_page_config(
    page_title="LitRead · AI 研究思维训练",
    page_icon=LOGO_MARK if os.path.exists(LOGO_MARK) else FAVICON,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ════════════════════════════════════════════
#  Icons — Lucide 风格线性图标（统一 2px 描边体系）
# ════════════════════════════════════════════
ICONS = {
    "book": '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
    "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "message": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    "scale": '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
    "graph": '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/>',
    "pen": '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    "feather": '<path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"/><line x1="16" x2="2" y1="8" y2="22"/><line x1="17.5" x2="9" y1="15" y2="15"/>',
    "library": '<path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/>',
    "key": '<path d="m15.5 7.5 2.3 2.3a1 1 0 0 0 1.4 0l2.1-2.1a1 1 0 0 0 0-1.4L19 4"/><path d="m21 2-9.6 9.6"/><circle cx="7.5" cy="15.5" r="5.5"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "trash": '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "sparkles": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
    "layers": '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m6.08 9.5-3.5 1.6a1 1 0 0 0 0 1.81l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9a1 1 0 0 0 0-1.83l-3.5-1.59"/><path d="m6.08 14.5-3.5 1.6a1 1 0 0 0 0 1.81l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9a1 1 0 0 0 0-1.83l-3.5-1.59"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
}


def icon(name, size=18, stroke=1.75, cls=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{stroke}" '
        f'stroke-linecap="round" stroke-linejoin="round" class="lr-i {cls}">{ICONS[name]}</svg>'
    )


# ════════════════════════════════════════════
#  界面文案
# ════════════════════════════════════════════
T = {
    "zh": {
        "tagline": "AI · 研究思维训练",
        "hero_sub": "先逆向推演作者怎么想到这个 idea，再拆解方法、审视证据、设计反例，最后提出自己的 follow-up。不是替你读论文，而是训练你做研究。",
        "demo_badge": "演示模式 · 欢迎评审老师随意体验",
        "status_llm": "LLM 就绪",
        "status_demo": "Demo 模式",
        "stat_line": "{papers} 篇论文 · {vecs} 个向量块",
        "quota_line": "免费试用：{used} / {quota}",
        "apikey_title": "API Key",
        "apikey_hint": "每人 30 次试用。粘贴你自己的 Key 可不限量使用，服务器不保存任何信息。",
        "apikey_ph": "sk-… 或其他 OpenAI 兼容 Key",
        "apikey_verify": "验证并使用",
        "apikey_clear": "清除 Key",
        "apikey_ok": "Key 已激活 · 刷新即清空",
        "nav_title": "功能",
        "nav_line": "研究流 · 概述图 · 对比 · 笔记 · 论文库",
        "f1": "智能解析", "f1d": "PDF 自动识别标题、作者、摘要与章节结构",
        "f2": "作者路径逆向", "f2d": "只给方法出现前的知识，推演作者怎么想到 idea",
        "f3": "方法拆解", "f3d": "Intuition + 一个真实样本的完整 pipeline",
        "f4": "数学从零", "f4d": "预备概念 · 符号表 · 逐行推导",
        "f5": "红队与 idea", "f5d": "脆弱假设 · 最小复现 · 反例 · 新问题",
        "f6": "文献问答", "f6d": "RAG 检索，回答带来源与相关度",
        "f7": "对比与概述图", "f7d": "并排对比 · 一键概述图 · Markdown 导出",
        "f8": "笔记与整理", "f8d": "摘录成稿 · 笔记 PDF 导出",
        "tb1": "论文库", "tb2": "研究流", "tb3": "追问", "tb4": "对比",
        "tb5": "图谱", "tb6": "笔记", "tb7": "Related Work",
        "sec_upload": "上传论文", "sec_library": "论文库", "sec_summary": "研究工作流",
        "sec_index": "索引管理", "sec_ask": "提问", "sec_compare": "多论文对比",
        "sec_notes": "阅读笔记",
        "btn_parse": "开始解析", "btn_summary": "生成速读卡片", "btn_ask": "提问",
        "btn_compare": "生成对比", "btn_graph": "生成图谱", "btn_note": "添加笔记",
        "btn_organize": "AI 整理笔记", "btn_rw": "生成 Related Work",
        "btn_export_md": "导出 Markdown",
        "btn_dl": "下载", "btn_structure": "结构", "btn_del": "删除", "btn_index": "建索引",
        "lbl_tldr": "TL;DR", "lbl_core": "核心贡献", "lbl_method": "方法亮点",
        "lbl_findings": "主要结论", "lbl_limits": "局限性", "lbl_answer": "回答",
        "lbl_sources": "参考来源", "lbl_consensus": "共识点", "lbl_divergence": "分歧点",
        "lbl_abstract": "摘要", "lbl_title": "标题", "lbl_authors": "作者", "lbl_pages": "页数",
        "lbl_keywords": "关键词", "lbl_words": "字数", "lbl_sections": "章节",
        "lbl_notes": "笔记列表", "lbl_organized": "整理结果", "lbl_citations": "引用来源",
        "lbl_struct": "结构化内容", "lbl_edges": "边列表",
        "metric_nodes": "论文节点", "metric_edges": "关系边", "metric_sim": "平均相似度",
        "hint_pdf": "拖拽或选择 PDF（最大 50 MB）",
        "empty_lib": "暂无论文。先在「上传与解析」上传一篇 PDF。",
        "need_two": "至少需要 2 篇论文",
        "ph_question": "例如：这些论文用了什么数据集？",
        "ph_focus": "侧重点（可选）如：方法、数据集、指标",
        "ph_topic": "研究主题，例如：retrieval augmented generation for scientific literature",
        "ph_note": "摘录 / 批注",
        "msg_quota": "免费试用次数已用完。粘贴你自己的 API Key 可继续使用，服务器不会保存。",
        "msg_key_ok": "Key 有效，已激活",
        "msg_key_bad": "Key 无效",
        "msg_added": "已添加",
        "msg_indexed": "已索引 {n} 块",
        "msg_saved": "完成 · ID：{pid}",
        "msg_none": "无",
        "spin_parse": "解析中…", "spin_ai": "AI 阅读中…", "spin_rag": "检索 + 生成中…",
        "spin_cmp": "对比分析中…", "spin_graph": "计算语义相似度…",
        "spin_organize": "整理中…", "spin_gen": "生成中…",
        "demo_note": "Demo 模式 · 示例数据可随时体验",
        "foot": "LitRead · 研究思维训练工作台 · FastAPI + Streamlit + ChromaDB · Hackathon 2026",
    },
}


def t(key, **kw):
    s = T["zh"].get(key, key)
    return s.format(**kw) if kw else s


def _qs(key):
    """读取 query 参数（兼容新旧 Streamlit API）。"""
    try:
        v = st.query_params.get(key)
    except Exception:
        try:
            v = st.experimental_get_query_params().get(key)
        except Exception:
            v = None
    if isinstance(v, list):
        v = v[0] if v else None
    return v


# ════════════════════════════════════════════
#  Design Tokens + 组件样式
# ════════════════════════════════════════════
DESIGN_CSS = """
<style>
/* ── Tokens ── */
:root{
  --lr-ink:#20201C; --lr-ink-2:#4E4C45; --lr-ink-3:#6B675D; --lr-ink-4:#8B877C;
  --lr-paper:#F7F5F0; --lr-paper-2:#EFECE3; --lr-surface:#FFFFFF;
  --lr-rule:#DDD9CD; --lr-rule-2:#C6C1B2;
  --lr-accent:#31543F; --lr-accent-2:#4F7361; --lr-accent-wash:#E9EFE9;
  --lr-warn:#96671A; --lr-danger:#97382B; --lr-ok:#3E6B4E;
  --lr-serif:"Noto Serif SC","Source Han Serif SC","Songti SC",Georgia,"Times New Roman",serif;
  --lr-sans:"Inter",-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
  --lr-mono:"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
  --lr-s1:4px; --lr-s2:8px; --lr-s3:12px; --lr-s4:16px; --lr-s5:24px; --lr-s6:40px;
  --lr-fs-xs:.72rem; --lr-fs-sm:.82rem; --lr-fs-base:.955rem; --lr-fs-lg:1.12rem;
  --lr-fs-xl:1.5rem; --lr-fs-2xl:2.1rem;
  --lr-control-h:40px; --lr-line:1.78;
  --lr-r1:4px; --lr-r2:8px; --lr-r3:999px;
  --lr-sh1:0 1px 2px rgba(32,32,28,.05);
  --lr-sh2:0 6px 20px rgba(32,32,28,.08);
  --lr-ease:cubic-bezier(.2,.6,.2,1); --lr-t1:.18s; --lr-t2:.38s;
}

/* ── Base & layered background ── */
.stApp{
  background:
    radial-gradient(1100px 480px at 88% -8%, rgba(49,84,63,.07), transparent 62%),
    radial-gradient(900px 420px at -8% 108%, rgba(150,103,26,.05), transparent 58%),
    var(--lr-paper);
  color:var(--lr-ink);
}
.block-container{ padding-top:2.2rem; padding-bottom:3.2rem; max-width:1180px; }
#MainMenu, footer{ visibility:hidden; }
/* 顶栏压平但不移除：手机端侧栏展开按钮就在这里 */
header[data-testid="stHeader"]{
  background:transparent !important; height:0 !important; min-height:0 !important;
  border:none !important; box-shadow:none !important;
}
header[data-testid="stHeader"] > div{ height:0 !important; }
[data-testid="stToolbar"]{ display:none !important; }
[data-testid="stDecoration"]{ display:none !important; }
/* 侧栏开关：保留并做成可点的小方块（fixed 避免被零高度顶栏压掉） */
[data-testid="stSidebarCollapsedControl"]{
  visibility:visible !important; display:block !important;
  position:fixed !important; top:10px; left:10px; z-index:1000;
}
[data-testid="stSidebarCollapsedControl"] button{
  background:#FFFFFF !important; border:1px solid var(--lr-rule-2) !important;
  border-radius:6px !important; box-shadow:var(--lr-sh1); color:var(--lr-ink) !important;
}
[data-testid="stSidebarCollapsedControl"] button:hover{
  border-color:var(--lr-ink-3) !important; background:var(--lr-paper-2) !important;
}
/* 侧栏关闭按钮 */
[data-testid="stSidebarHeader"] button, [data-testid="baseButton-headerNoPadding"]{
  color:var(--lr-ink-2) !important;
}
section[data-testid="stSidebar"]{
  background:
    linear-gradient(180deg, rgba(49,84,63,.035), transparent 220px),
    var(--lr-paper-2) !important;
  border-right:1px solid var(--lr-rule) !important;
}

/* ── Typography ── */
h1,h2,h3,h4,h5,h6{ font-family:var(--lr-serif) !important; color:var(--lr-ink); letter-spacing:0; }
h1{ font-size:2.15rem !important; font-weight:700; }
h2{ font-size:1.5rem !important; font-weight:700; margin-top:30px; }
h3{ font-size:1.18rem !important; font-weight:600; color:var(--lr-ink-2); }
.stMarkdown p, .element-container p{ font-family:var(--lr-sans); font-size:.955rem; line-height:1.78; color:var(--lr-ink-2); }
.lr-i{ vertical-align:-.18em; }

/* ── Hero ── */
.lr-eyebrow{
  font-family:var(--lr-sans); font-size:.72rem; font-weight:600;
  letter-spacing:.22em; text-transform:uppercase; color:var(--lr-accent);
  display:flex; align-items:center; gap:10px;
}
.lr-eyebrow::after{ content:""; height:1px; width:72px; background:var(--lr-rule-2); }
.lr-title{
  font-family:var(--lr-serif); font-size:3.15rem; font-weight:700;
  letter-spacing:-.015em; color:var(--lr-ink); line-height:1.12; margin:14px 0 0;
}
.lr-logo{ display:block; width:min(300px,64vw); height:auto; margin:16px 0 0; }
.lr-sub{
  font-family:var(--lr-sans); font-size:1.02rem; color:var(--lr-ink-2);
  margin-top:14px; line-height:1.8; max-width:640px;
}
.lr-hero-rule{ border-top:1px solid var(--lr-rule-2); margin:26px 0 6px; }
.lr-hero{ position:relative; }
.lr-hero::before{
  content:""; position:absolute; inset:-28px -40px auto -40px; height:150px;
  background:repeating-linear-gradient(180deg, rgba(32,32,28,.045) 0 1px, transparent 1px 30px);
  mask-image:linear-gradient(180deg, rgba(0,0,0,.8), transparent);
  -webkit-mask-image:linear-gradient(180deg, rgba(0,0,0,.8), transparent);
  pointer-events:none;
}

/* ── Section titles ── */
.lr-section{
  font-family:var(--lr-serif); font-size:1.12rem; font-weight:700; color:var(--lr-ink);
  border-left:3px solid var(--lr-accent); padding-left:12px; margin:30px 0 14px;
  display:flex; align-items:center; gap:9px;
}
.lr-section .lr-i{ color:var(--lr-accent); }

/* ── Feature index grid（发丝线网格） ── */
.feature-grid{
  display:grid; grid-template-columns:repeat(4,1fr); gap:1px;
  background:var(--lr-rule); border:1px solid var(--lr-rule);
  margin:26px 0 6px; overflow:hidden;
}
.feature-cell{
  background:var(--lr-paper); padding:22px 20px 20px;
  transition:background var(--lr-t1) var(--lr-ease);
}
.feature-cell:hover{ background:var(--lr-surface); }
.feature-cell .lr-i{ color:var(--lr-accent); margin-bottom:10px; display:block; }
.feature-cell h4{
  font-family:var(--lr-serif); font-size:.985rem; font-weight:700;
  margin:0 0 5px; color:var(--lr-ink);
}
.feature-cell p{ font-family:var(--lr-sans); font-size:.815rem; color:var(--lr-ink-3); margin:0; line-height:1.6; }

/* ── Buttons：Secondary（白底墨字）/ Primary（墨绿底白字） ── */
.stButton > button, .stDownloadButton > button,
[data-testid="stBaseButton-secondary"]{
  border-radius:var(--lr-r1) !important; font-family:var(--lr-sans) !important;
  font-weight:600 !important; font-size:.885rem !important; letter-spacing:.012em;
  padding:.5rem 1.2rem !important; white-space:nowrap;
  min-height:var(--lr-control-h) !important;
  background:#FFFFFF !important; color:var(--lr-ink) !important;
  border:1px solid var(--lr-rule-2) !important;
  transition:background var(--lr-t1) var(--lr-ease), color var(--lr-t1) var(--lr-ease),
             border-color var(--lr-t1) var(--lr-ease), box-shadow var(--lr-t1) var(--lr-ease) !important;
}
.stButton > button p, .stDownloadButton > button p,
[data-testid="stBaseButton-secondary"] p{ color:var(--lr-ink) !important; }

.stButton > button:hover, .stDownloadButton > button:hover,
[data-testid="stBaseButton-secondary"]:hover{
  background:var(--lr-paper-2) !important; color:var(--lr-ink) !important;
  border-color:var(--lr-ink-3) !important; box-shadow:var(--lr-sh1);
}
.stButton > button:hover p, .stDownloadButton > button:hover p,
[data-testid="stBaseButton-secondary"]:hover p{ color:var(--lr-ink) !important; }

.stButton > button:active, .stDownloadButton > button:active{ transform:translateY(1px); box-shadow:none; }
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible,
[data-testid="stBaseButton-secondary"]:focus-visible{
  outline:2px solid var(--lr-accent) !important; outline-offset:2px;
}

/* Primary：墨绿底 + 白字（含内部文本节点） */
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"],
[data-testid="stBaseButton-primary"]{
  background:var(--lr-accent) !important; color:#FFFFFF !important;
  border:1px solid var(--lr-accent) !important;
}
.stButton > button[kind="primary"] p, .stDownloadButton > button[kind="primary"] p,
[data-testid="stBaseButton-primary"] p{ color:#FFFFFF !important; }

.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover{
  background:#26452F !important; color:#FFFFFF !important; border-color:#26452F !important;
}
.stButton > button[kind="primary"]:hover p, .stDownloadButton > button[kind="primary"]:hover p,
[data-testid="stBaseButton-primary"]:hover p{ color:#FFFFFF !important; }

/* 禁用态：弱化但仍可辨认 */
.stButton > button:disabled, [data-testid="stBaseButton-secondary"]:disabled{
  background:var(--lr-paper-2) !important; color:#716D63 !important;
  border-color:var(--lr-rule) !important; cursor:not-allowed;
}
.stButton > button:disabled p{ color:#716D63 !important; }

/* ── 表单 ── */
.stTextInput input, .stTextArea textarea, [data-baseweb="input"], [data-baseweb="textarea"]{
  border:1px solid var(--lr-rule) !important; border-radius:var(--lr-r1) !important;
  background:var(--lr-surface) !important; font-family:var(--lr-sans) !important;
  font-size:.92rem !important; min-height:var(--lr-control-h) !important;
  transition:border-color var(--lr-t1) var(--lr-ease), box-shadow var(--lr-t1) var(--lr-ease) !important;
}
.stTextArea textarea{ min-height:110px !important; line-height:1.8 !important; padding:.7rem .8rem !important; }
.stTextInput input:focus, .stTextArea textarea:focus{
  border-color:var(--lr-accent) !important; box-shadow:0 0 0 3px var(--lr-accent-wash) !important;
}
[data-baseweb="select"] > div, [data-baseweb="tag"]{
  border:1px solid var(--lr-rule) !important; border-radius:var(--lr-r1) !important;
  background:var(--lr-surface) !important; min-height:var(--lr-control-h) !important;
}
[data-testid="stCheckbox"], [data-testid="stRadio"] label{
  min-height:var(--lr-control-h) !important; display:flex !important; align-items:center !important;
}
.stFileUploader{
  border-radius:var(--lr-r1) !important; border:1px dashed var(--lr-rule-2) !important;
  background:var(--lr-surface) !important;
}
/* 统一 focus-visible */
.stButton > button:focus-visible, .stDownloadButton > button:focus-visible,
.stTextInput input:focus-visible, .stTextArea textarea:focus-visible,
[data-baseweb="select"] > div:focus-visible, [data-testid="stCheckbox"]:focus-within,
[data-testid="stRadio"] label:focus-within, a:focus-visible{
  outline:2px solid var(--lr-accent) !important; outline-offset:2px !important;
}

/* ── Tabs：下划线导航（克制） ── */
.stTabs [data-baseweb="tab-list"]{ gap:2px; border-bottom:1px solid var(--lr-rule-2); }
.stTabs [data-baseweb="tab"]{
  border-radius:0 !important; padding:11px 18px !important;
  font-family:var(--lr-sans) !important; font-size:.885rem !important; font-weight:550 !important;
  letter-spacing:.015em;
  color:var(--lr-ink-3) !important; border-bottom:2px solid transparent !important;
  transition:color var(--lr-t1) var(--lr-ease), border-color var(--lr-t1) var(--lr-ease) !important;
}
.stTabs [data-baseweb="tab"]:hover{ color:var(--lr-ink) !important; }
.stTabs [aria-selected="true"]{
  color:var(--lr-ink) !important; border-bottom:2px solid var(--lr-accent) !important;
  background:transparent !important;
}

/* ── 卡片 / Metric / 展开器 / 表格 ── */
div[data-testid="stMetric"]{
  background:var(--lr-surface) !important; border:1px solid var(--lr-rule) !important;
  border-radius:var(--lr-r2) !important; padding:16px 20px !important;
}
div[data-testid="stMetricLabel"]{
  font-family:var(--lr-sans); font-size:.715rem !important; font-weight:600;
  letter-spacing:.12em; text-transform:uppercase; color:var(--lr-ink-3) !important;
}
div[data-testid="stMetricValue"]{ font-family:var(--lr-serif) !important; color:var(--lr-ink) !important; }
details{
  background:var(--lr-surface) !important; border:1px solid var(--lr-rule) !important;
  border-radius:var(--lr-r2) !important; padding:4px 16px !important;
}
summary{ font-family:var(--lr-sans); font-weight:600; color:var(--lr-ink-2); }
.stDataFrame{ border:1px solid var(--lr-rule); border-radius:var(--lr-r2); overflow:hidden; }
.stCodeBlock, pre{ border-radius:var(--lr-r1) !important; font-family:var(--lr-mono) !important; font-size:.84rem !important; }
[data-testid="stExpander"] details{ background:var(--lr-surface) !important; }

/* ── 提示条：去模板感（左描边 + 纸面） ── */
[data-testid="stAlert"]{
  background:var(--lr-surface) !important; border:1px solid var(--lr-rule) !important;
  border-left:3px solid var(--lr-ink-3) !important;
  border-radius:var(--lr-r1) !important; box-shadow:none !important;
}
[data-testid="stAlert"] p{ color:var(--lr-ink-2) !important; }

/* ── 自定义元件 ── */
.lr-badge{
  display:inline-flex; align-items:center; gap:7px;
  font-family:var(--lr-sans); font-size:.765rem; font-weight:600;
  letter-spacing:.09em; text-transform:uppercase;
  padding:5px 13px; border:1px solid var(--lr-rule-2); border-radius:var(--lr-r3);
  color:var(--lr-accent); background:var(--lr-accent-wash);
}
.lr-note{
  font-family:var(--lr-sans); font-size:.9rem; color:var(--lr-ink-2);
  padding:12px 15px; background:var(--lr-paper-2);
  border-left:3px solid var(--lr-accent); margin:12px 0; border-radius:0 var(--lr-r1) var(--lr-r1) 0;
}
.lr-card{
  background:var(--lr-surface); border:1px solid var(--lr-rule);
  border-radius:var(--lr-r2); padding:16px 18px; margin:10px 0;
}
.quota-bar{ display:flex; align-items:center; gap:8px; font-family:var(--lr-sans); font-size:.76rem; color:var(--lr-ink-2); margin-top:2px; }
.quota-bar .bar{ flex:1; height:4px; background:var(--lr-rule); border-radius:var(--lr-r3); overflow:hidden; }
.quota-bar .bar-fill{ height:100%; background:var(--lr-accent); border-radius:var(--lr-r3); transition:width var(--lr-t2) var(--lr-ease); }
.quota-bar .bar-fill.warn{ background:var(--lr-warn); }
.quota-compact{
  display:flex; align-items:center; gap:8px; font-family:var(--lr-sans);
  font-size:.72rem; color:var(--lr-ink-3); margin:4px 0 2px;
}
.quota-compact .bar{ flex:1; height:3px; background:var(--lr-rule); border-radius:var(--lr-r3); overflow:hidden; }
.quota-compact .bar-fill{
  display:block; height:100%; background:var(--lr-accent); border-radius:var(--lr-r3);
  transition:width var(--lr-t2) var(--lr-ease);
}
.quota-compact .bar-fill.warn{ background:var(--lr-warn); }
.lr-brand{ display:flex; align-items:center; gap:11px; padding:12px 0 6px; }
.lr-brand .lr-i{ color:var(--lr-accent); }
.lr-brand-name{ font-family:var(--lr-serif); font-size:1.32rem; font-weight:700; color:var(--lr-ink); line-height:1.1; }
.lr-brand-sub{
  font-family:var(--lr-sans); font-size:.72rem; color:var(--lr-ink-3);
  letter-spacing:.14em; text-transform:uppercase;
}
.lr-side-label{
  font-family:var(--lr-sans); font-size:.715rem; font-weight:600;
  letter-spacing:.16em; text-transform:uppercase; color:var(--lr-ink-3);
}
.lr-footer{
  text-align:center; font-family:var(--lr-sans); font-size:.755rem;
  letter-spacing:.05em; color:var(--lr-ink-3); padding:14px 0;
}

/* ── Page header（6 页统一） ── */
.pg-head{ margin:2px 0 var(--lr-s5); }
.pg-eyebrow{
  font-family:var(--lr-sans); font-size:var(--lr-fs-xs); font-weight:600;
  letter-spacing:.2em; text-transform:uppercase; color:var(--lr-accent-2);
  display:flex; align-items:center; gap:10px;
}
.pg-eyebrow::after{ content:""; height:1px; width:54px; background:var(--lr-rule-2); }
.pg-title{
  font-family:var(--lr-serif); font-size:var(--lr-fs-2xl); font-weight:700;
  line-height:1.2; color:var(--lr-ink); margin:10px 0 0;
}
.pg-desc{
  font-family:var(--lr-sans); font-size:var(--lr-fs-base); line-height:var(--lr-line);
  color:var(--lr-ink-2); max-width:760px; margin-top:var(--lr-s2);
}
.pg-actions{ margin-top:var(--lr-s4); }
.pg-actions:empty{ display:none; }

/* ── Empty state ── */
.empty{
  border:1px solid var(--lr-rule); border-radius:var(--lr-r2);
  background:var(--lr-surface); padding:var(--lr-s6) var(--lr-s5);
  text-align:center; margin:var(--lr-s4) 0;
}
.empty .ei{ color:var(--lr-accent-2); margin-bottom:var(--lr-s3); }
.empty .et{ font-family:var(--lr-serif); font-size:1.08rem; font-weight:700; color:var(--lr-ink); }
.empty .ed{
  font-family:var(--lr-sans); font-size:.88rem; line-height:1.72; color:var(--lr-ink-2);
  max-width:520px; margin:var(--lr-s2) auto 0;
}
.empty .ec{ margin-top:var(--lr-s4); display:flex; justify-content:center; gap:var(--lr-s2); flex-wrap:wrap; }
.empty.compact{ padding:var(--lr-s5) var(--lr-s4); text-align:left; display:flex; gap:var(--lr-s3); align-items:flex-start; }
.empty.compact .ei{ margin:2px 0 0; flex:0 0 auto; }
.empty.compact .ed{ margin:var(--lr-s1) 0 0; }
.empty.compact .ec{ justify-content:flex-start; margin-top:var(--lr-s3); }

/* ── Skeleton（纸面风） ── */
@keyframes lrShimmer{ 0%{ background-position:100% 0; } 100%{ background-position:-100% 0; } }
.sk{ display:flex; flex-direction:column; gap:10px; padding:var(--lr-s4); border:1px solid var(--lr-rule);
  border-radius:var(--lr-r2); background:var(--lr-surface); }
.sk-line, .sk-block{
  background:linear-gradient(90deg, var(--lr-paper-2) 25%, #F8F6F1 50%, var(--lr-paper-2) 75%);
  background-size:200% 100%; animation:lrShimmer 1.6s linear infinite;
  border-radius:3px;
}
.sk-line{ height:12px; }
.sk-line.w70{ width:70%; } .sk-line.w50{ width:50%; } .sk-line.w85{ width:85%; }
.sk-block{ height:72px; margin-top:2px; }
@media (prefers-reduced-motion:reduce){ .sk-line, .sk-block{ animation:none; background:var(--lr-paper-2); } }

/* ── 危险操作 / 文字链接按钮 ── */
.danger-link button, .linkbtn button{
  background:transparent !important; border:none !important; box-shadow:none !important;
  padding:4px 2px !important; min-height:32px !important; font-size:.8rem !important;
  color:var(--lr-ink-3) !important; text-decoration:underline; text-underline-offset:3px;
}
.danger-marker, .lib-actions-marker, .note-toggle-marker{ display:none; }
/* 只用「离 marker 最近」的 vertical block，避免祖先容器把整页按钮都变成文字链 */
div[data-testid="stVerticalBlock"]:has(.danger-marker):not(:has(div[data-testid="stVerticalBlock"] .danger-marker)) .stButton > button{
  background:transparent !important; border:none !important; box-shadow:none !important;
  padding:2px 0 !important; min-height:28px !important; font-size:.78rem !important;
  color:var(--lr-ink-3) !important; text-decoration:underline; text-underline-offset:3px;
}
div[data-testid="stVerticalBlock"]:has(.danger-marker):not(:has(div[data-testid="stVerticalBlock"] .danger-marker)) .stButton > button:hover{
  color:var(--lr-danger) !important; background:transparent !important;
}
div[data-testid="stVerticalBlock"]:has(.danger-marker):not(:has(div[data-testid="stVerticalBlock"] .danger-marker)) .stButton > button[kind="primary"]{
  background:var(--lr-danger) !important; color:#FFFFFF !important;
  border:1px solid var(--lr-danger) !important; border-radius:var(--lr-r1) !important;
  padding:.5rem 1.2rem !important; min-height:var(--lr-control-h) !important;
  text-decoration:none !important;
}
div[data-testid="stVerticalBlock"]:has(.danger-marker):not(:has(div[data-testid="stVerticalBlock"] .danger-marker)) .stButton > button[kind="primary"] p{
  color:#FFFFFF !important;
}
div[data-testid="stVerticalBlock"]:has(.lib-actions-marker):not(:has(div[data-testid="stVerticalBlock"] .lib-actions-marker)) .stButton > button,
div[data-testid="stVerticalBlock"]:has(.note-toggle-marker):not(:has(div[data-testid="stVerticalBlock"] .note-toggle-marker)) .stButton > button{
  background:transparent !important; border:none !important; box-shadow:none !important;
  padding:2px 4px !important; min-height:30px !important; font-size:.78rem !important;
  color:var(--lr-ink-3) !important; text-decoration:underline; text-underline-offset:3px;
}
div[data-testid="stVerticalBlock"]:has(.lib-actions-marker):not(:has(div[data-testid="stVerticalBlock"] .lib-actions-marker)) .stButton > button:hover,
div[data-testid="stVerticalBlock"]:has(.note-toggle-marker):not(:has(div[data-testid="stVerticalBlock"] .note-toggle-marker)) .stButton > button:hover{
  color:var(--lr-accent) !important; background:transparent !important;
}
.danger-link button:hover{ color:var(--lr-danger) !important; background:transparent !important; }
.linkbtn button:hover{ color:var(--lr-accent) !important; background:transparent !important; }
.danger-confirm{
  border:1px solid #E2C9C4; border-left:3px solid var(--lr-danger);
  background:#FBF3F1; border-radius:var(--lr-r1); padding:10px 12px; margin:8px 0;
  font-family:var(--lr-sans); font-size:.82rem; color:var(--lr-ink-2);
}
.danger-confirm b{ color:var(--lr-danger); }

/* ── 文献架 / 笔记 / 概述图骨架 ── */
.lib-row{ padding:var(--lr-s3) 0 var(--lr-s2); }
.lib-title{ font-family:var(--lr-sans); font-size:.96rem; font-weight:650; line-height:1.55; color:var(--lr-ink); overflow-wrap:anywhere; }
.lib-meta{ font-family:var(--lr-mono); font-size:.68rem; color:var(--lr-ink-3); margin-top:5px; display:flex; gap:8px; flex-wrap:wrap; align-items:center; overflow-wrap:anywhere; }
.lr-chip{ font-family:var(--lr-sans); font-size:.65rem; letter-spacing:.04em; border:1px solid var(--lr-rule-2);
  border-radius:var(--lr-r3); padding:2px 8px; color:var(--lr-ink-2); background:var(--lr-paper); }
.lr-chip.ok{ color:var(--lr-accent); border-color:var(--lr-accent-2); background:var(--lr-accent-wash); }
.note-card{ border:1px solid var(--lr-rule); border-radius:var(--lr-r2); background:var(--lr-surface);
  padding:var(--lr-s4); margin:var(--lr-s3) 0; }
.note-body{ font-family:var(--lr-sans); font-size:.9rem; line-height:1.8; color:var(--lr-ink-2); white-space:pre-wrap; }
.note-body.clamp{ display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.note-meta{ font-family:var(--lr-mono); font-size:.68rem; color:var(--lr-ink-3); margin-top:var(--lr-s2); }
.ov-preview{
  max-width:720px; margin:0 auto; background:var(--lr-surface); border:1px solid var(--lr-rule);
  border-radius:var(--lr-r2); padding:var(--lr-s5); box-shadow:var(--lr-sh1);
}
.ov-preview .ov-k{ font-family:var(--lr-mono); font-size:.62rem; letter-spacing:.14em; color:var(--lr-accent-2); }
.ov-preview .ov-t{ font-family:var(--lr-serif); font-size:1.18rem; font-weight:700; color:var(--lr-ink); margin:8px 0 4px; }
.ov-preview .ov-s{ font-family:var(--lr-sans); font-size:.78rem; color:var(--lr-ink-3); margin-bottom:14px; }
.ov-preview .ov-line{ height:9px; border-radius:2px; background:var(--lr-paper-2); margin:8px 0; }
.ov-preview .ov-line.short{ width:62%; }
.ov-preview .ov-sec{ font-family:var(--lr-sans); font-size:.66rem; letter-spacing:.12em; color:var(--lr-accent-2); margin-top:16px; }
/* 概述图：居中且不超过 720px */
[data-testid="stImage"]{ display:flex; justify-content:center; }
[data-testid="stImage"] img{ max-width:720px; height:auto; margin:0 auto; }
@media (prefers-reduced-motion:reduce){ .sk-line, .sk-block{ animation:none; } }

/* ── 控件标签 ── */
[data-testid="stWidgetLabel"] p{ font-family:var(--lr-sans); }

/* ── 动效（尊重系统减少动态偏好） ── */
@keyframes lrFadeUp{ from{ opacity:0; transform:translateY(12px); } to{ opacity:1; transform:none; } }
.lr-anim{ animation:lrFadeUp .55s var(--lr-ease) both; }
.lr-d1{ animation-delay:.07s; } .lr-d2{ animation-delay:.14s; } .lr-d3{ animation-delay:.21s; }
@media (prefers-reduced-motion:reduce){
  *{ animation-duration:.001s !important; transition-duration:.001s !important; }
}

/* ── 滚动条 ── */
::-webkit-scrollbar{ width:7px; height:7px; }
::-webkit-scrollbar-thumb{ background:var(--lr-rule-2); border-radius:4px; }
::-webkit-scrollbar-thumb:hover{ background:var(--lr-ink-3); }

/* ── 响应式：窄桌面 / 平板 ── */
@media (max-width:1100px){
  .feature-grid{ grid-template-columns:repeat(2,1fr); }
  .feature-cell{ padding:20px 22px; }
  .lr-title{ font-size:2.7rem; }
}

/* ── 响应式：手机 ── */
@media (max-width:768px){
  .block-container{
    padding:2.6rem .85rem 2.4rem !important;
    max-width:100% !important;
  }
  .lr-title{ font-size:2.05rem; letter-spacing:-.01em; }
  .lr-sub{ font-size:.94rem; line-height:1.72; max-width:100%; }
  .lr-eyebrow{ font-size:.665rem; letter-spacing:.18em; }
  .lr-eyebrow::after{ width:40px; }
  .lr-hero::before{ display:none; }

  h1{ font-size:1.55rem !important; }
  h2{ font-size:1.22rem !important; margin-top:20px; }
  h3{ font-size:1.02rem !important; }
  .stMarkdown p, .element-container p{ font-size:.915rem; line-height:1.72; }

  /* Streamlit 多列 → 单列堆叠 */
  [data-testid="stHorizontalBlock"]{ flex-wrap:wrap !important; gap:.45rem !important; }
  [data-testid="column"]{
    width:100% !important; flex:1 1 100% !important;
    min-width:0 !important;
  }

  /* 按钮铺满，便于手指点击 */
  .stButton > button, .stDownloadButton > button{ width:100%; }

  /* Tabs 横向滚动，不挤成一团 */
  .stTabs [data-baseweb="tab-list"]{
    overflow-x:auto; flex-wrap:nowrap; scrollbar-width:none;
    -webkit-overflow-scrolling:touch;
  }
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar{ display:none; }
  .stTabs [data-baseweb="tab"]{
    padding:10px 13px !important; font-size:.83rem !important;
    white-space:nowrap; flex:0 0 auto;
  }

  /* 表格横向滚动，避免挤压 */
  .stDataFrame, [data-testid="stDataFrame"]{ overflow-x:auto !important; }

  /* 指标卡压缩 */
  div[data-testid="stMetric"]{ padding:12px 14px !important; }
  div[data-testid="stMetricValue"]{ font-size:1.3rem !important; }

  /* 侧栏内间距收紧 */
  section[data-testid="stSidebar"] .block-container,
  section[data-testid="stSidebar"] [data-testid="stSidebarContent"]{ padding:0 .55rem !important; }
  .lr-brand-name{ font-size:1.15rem; }

  .lr-section{ margin:22px 0 11px; font-size:1.03rem; }
  .lr-footer{ font-size:.7rem; padding:10px 0; }
}

@media (max-width:420px){
  .lr-title{ font-size:1.78rem; }
  .feature-grid{ grid-template-columns:1fr; }
  .feature-cell{ padding:16px 15px; }
}
</style>
"""
st.markdown(DESIGN_CSS, unsafe_allow_html=True)


# ════════════════════════════════════════════
#  研究工作流样式 + 连续导航
# ════════════════════════════════════════════
RESEARCH_CSS = """
<style>
div[data-testid="stElementContainer"]:has(.rf-rail),
div.element-container:has(.rf-rail){
  position:sticky; top:0; z-index:30; background:var(--lr-paper);
  padding:var(--lr-s3) 0 var(--lr-s2); border-bottom:1px solid var(--lr-rule);
  margin:0 0 var(--lr-s2);
}
.rf-rail{ display:grid; grid-template-columns:repeat(6,1fr); gap:var(--lr-s2); margin:0; }
.rf-pill{ border:1px solid var(--lr-rule); border-radius:var(--lr-r2); padding:7px 10px;
  background:var(--lr-surface); transition:all var(--lr-t1) var(--lr-ease); min-height:44px; }
.rf-pill .n{ font-family:var(--lr-mono); font-size:.62rem; letter-spacing:.1em; color:var(--lr-ink-3); }
.rf-pill .l{ font-family:var(--lr-sans); font-size:.78rem; font-weight:600; color:var(--lr-ink-2); margin-top:2px; }
.rf-pill.done{ border-color:var(--lr-accent-2); background:var(--lr-accent-wash); }
.rf-pill.done .l{ color:var(--lr-accent); }
.rf-pill.now{ border-color:var(--lr-accent); box-shadow:var(--lr-sh1); }
.rf-head{ display:flex; align-items:center; gap:9px; margin:0 0 8px; }
.rf-num{ font-family:var(--lr-mono); font-size:.7rem; font-weight:700; color:#fff;
  background:var(--lr-accent); border-radius:3px; padding:2px 6px; letter-spacing:.04em; }
.rf-title{ font-family:var(--lr-serif); font-size:1.05rem; font-weight:700; color:var(--lr-ink); }
.rf-tag{ margin-left:auto; font-family:var(--lr-sans); font-size:.63rem; letter-spacing:.08em;
  padding:2px 8px; border-radius:var(--lr-r3); border:1px solid var(--lr-rule-2); color:var(--lr-ink-3); }
.rf-tag.paper{ color:var(--lr-accent); border-color:var(--lr-accent-2); background:var(--lr-accent-wash); }
.rf-tag.inference{ color:var(--lr-warn); border-color:#D8C39A; background:#FBF4E6; }
.rf-tag.mixed{ color:var(--lr-ink-2); background:var(--lr-paper-2); }
.rf-summary{ font-family:var(--lr-serif); font-size:.98rem; font-weight:700;
  line-height:1.58; color:var(--lr-ink); margin:2px 0 8px; }
.rf-world{ display:grid; grid-template-columns:1fr 1fr; gap:var(--lr-s2); margin:var(--lr-s3) 0 var(--lr-s1); }
.rf-wcard{ border:1px solid var(--lr-rule); border-left:3px solid var(--lr-accent-2);
  background:var(--lr-surface); border-radius:4px; padding:9px 11px; }
.rf-wcard .k{ font-family:var(--lr-sans); font-size:.6rem; letter-spacing:.1em;
  text-transform:uppercase; color:var(--lr-accent-2); }
.rf-wcard .f{ font-family:var(--lr-sans); font-size:.78rem; line-height:1.65; color:var(--lr-ink-2); margin-top:3px; }
.rf-timeline{ position:relative; padding-left:22px; margin:12px 0 4px; }
.rf-timeline::before{ content:""; position:absolute; left:7px; top:10px; bottom:10px;
  width:1px; background:var(--lr-rule-2); }
.rf-beat{ border:1px solid var(--lr-rule); border-radius:var(--lr-r2); background:var(--lr-surface);
  padding:12px 14px; margin:9px 0; position:relative; }
.rf-beat::before{ content:""; position:absolute; left:-19px; top:14px; width:9px; height:9px;
  border-radius:50%; background:var(--lr-paper); border:2px solid var(--lr-accent); }
.rf-beat .bm{ font-family:var(--lr-mono); font-size:.64rem; letter-spacing:.1em; color:#fff;
  background:var(--lr-accent-2); border-radius:3px; padding:2px 7px; display:inline-block; }
.rf-beat .bl{ font-family:var(--lr-sans); font-size:.7rem; color:var(--lr-ink-3); margin-top:8px; letter-spacing:.06em; }
.rf-beat .bv{ font-family:var(--lr-sans); font-size:.84rem; line-height:1.75; color:var(--lr-ink); }
.rf-gate{ border:1px solid var(--lr-accent); border-left:4px solid var(--lr-accent);
  background:var(--lr-surface); border-radius:var(--lr-r2); padding:var(--lr-s5);
  margin:var(--lr-s4) 0; box-shadow:var(--lr-sh1);
  display:grid; grid-template-columns:1fr 190px; gap:var(--lr-s5); }
.rf-gate .gk{ font-family:var(--lr-mono); font-size:.62rem; letter-spacing:.14em;
  color:var(--lr-accent-2); text-transform:uppercase; }
.rf-gate .gt{ font-family:var(--lr-serif); font-size:1.08rem; font-weight:700; color:var(--lr-accent); margin-top:4px; }
.rf-gate .gd{ font-family:var(--lr-sans); font-size:.86rem; line-height:1.78; color:var(--lr-ink-2); margin-top:6px; }
.rf-gate .gn{ border-left:1px solid var(--lr-rule-2); padding-left:var(--lr-s3);
  font-family:var(--lr-sans); font-size:.76rem; line-height:1.7; color:var(--lr-ink-3); align-self:center; }
.rf-next{ display:flex; gap:var(--lr-s2); flex-wrap:wrap; margin-top:10px; }

/* 对比页：论文选择卡片 + 完整对比表 */
.cmp-select-title{ font-family:var(--lr-serif); font-size:1rem; font-weight:700; color:var(--lr-ink); margin:2px 0 10px; }
.cmp-paper-card{ border:1px solid var(--lr-rule); border-radius:var(--lr-r2); background:var(--lr-surface);
  padding:13px 14px 12px; min-height:118px; transition:border-color var(--lr-t1) var(--lr-ease), background var(--lr-t1) var(--lr-ease); }
.cmp-paper-card.on{ border-color:var(--lr-accent); background:var(--lr-accent-wash); box-shadow:inset 0 0 0 1px var(--lr-accent); }
.cmp-paper-kicker{ font-family:var(--lr-mono); font-size:.62rem; letter-spacing:.12em; color:var(--lr-accent-2); text-transform:uppercase; }
.cmp-paper-title{ font-family:var(--lr-serif); font-size:.98rem; font-weight:700; line-height:1.5; color:var(--lr-ink); margin:5px 0 7px; }
.cmp-paper-meta{ font-family:var(--lr-mono); font-size:.65rem; line-height:1.55; color:var(--lr-ink-3); word-break:break-all; }
.cmp-pick-note{ font-family:var(--lr-sans); font-size:.76rem; color:var(--lr-ink-3); margin:4px 0 12px; }
.cmp-pick-note b{ color:var(--lr-accent); }
.cmp-table-wrap{ border:1px solid var(--lr-rule); border-radius:var(--lr-r2); background:var(--lr-surface);
  overflow:auto; max-height:70vh; margin:6px 0 18px; }
.cmp-table{ width:100%; min-width:660px; border-collapse:separate; border-spacing:0; table-layout:fixed; }
.cmp-table th, .cmp-table td{ padding:12px 13px; border-bottom:1px solid var(--lr-rule);
  vertical-align:top; text-align:left; white-space:normal; word-break:break-word;
  font-family:var(--lr-sans); font-size:.82rem; line-height:1.72; color:var(--lr-ink-2); }
.cmp-table thead th{ background:var(--lr-paper-2); font-family:var(--lr-serif); font-size:.86rem;
  font-weight:700; line-height:1.5; color:var(--lr-ink);
  position:sticky; top:0; z-index:2; }
.cmp-table thead th:first-child{ width:132px; left:0; z-index:3; }
.cmp-table tbody th{ width:132px; background:#FAF8F3; font-size:.7rem; font-weight:600;
  letter-spacing:.04em; color:var(--lr-accent); position:sticky; left:0; z-index:1; }
.cmp-table tbody tr:hover td, .cmp-table tbody tr:hover th{ background:#F6F3EA; }
.cmp-table tr:last-child th, .cmp-table tr:last-child td{ border-bottom:none; }
.cmp-note{ border:1px solid var(--lr-rule); border-radius:var(--lr-r2); background:var(--lr-surface); padding:14px 16px; height:100%; }
.cmp-note .k{ font-family:var(--lr-sans); font-size:.62rem; font-weight:600; letter-spacing:.12em;
  text-transform:uppercase; color:var(--lr-accent-2); }
.cmp-note .v{ font-family:var(--lr-sans); font-size:.86rem; line-height:1.78; color:var(--lr-ink-2); margin-top:5px; }

/* 顶部导航：横向芯片，窄屏可滚动 */
div[data-testid="stRadio"]{ margin:0 0 2px; }
div[data-testid="stRadio"] > label,
div[data-testid="stRadio"] label[data-testid="stWidgetLabel"]{ display:none !important; }
div[data-testid="stRadio"] > div[role="radiogroup"]{
  flex-wrap:nowrap !important; overflow-x:auto; gap:6px; padding:1px 0 3px;
  scrollbar-width:none;
}
div[data-testid="stRadio"] > div[role="radiogroup"]::-webkit-scrollbar{ display:none; }
div[data-testid="stRadio"] div[role="radiogroup"] label{
  border:1px solid var(--lr-rule); border-radius:var(--lr-r3); padding:7px 13px;
  background:var(--lr-surface); white-space:nowrap; min-height:var(--lr-control-h);
}
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked){
  background:var(--lr-accent); border-color:var(--lr-accent);
}
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p{ color:#fff !important; }
div[data-testid="stRadio"] div[role="radiogroup"] label > div:first-child{ display:none; }
@media (max-width:900px){
  .rf-rail{ display:flex; overflow-x:auto; scrollbar-width:none; -webkit-overflow-scrolling:touch; }
  .rf-rail::-webkit-scrollbar{ display:none; }
  .rf-pill{ flex:0 0 118px; }
  .rf-gate{ grid-template-columns:1fr; gap:var(--lr-s3); }
  .rf-gate .gn{ border-left:none; border-top:1px solid var(--lr-rule); padding:var(--lr-s3) 0 0; }
}
@media (max-width:768px){
  .rf-world{ grid-template-columns:1fr; }
  .rf-next-marker + div[data-testid="stHorizontalBlock"]{ flex-wrap:wrap !important; }
  div[data-testid="stVerticalBlock"]:has(.rf-next-marker) > div[data-testid="stHorizontalBlock"]{
    flex-wrap:wrap !important; gap:var(--lr-s2) !important;
  }
  div[data-testid="stVerticalBlock"]:has(.rf-next-marker) > div[data-testid="stHorizontalBlock"] > div[data-testid="column"]{
    width:calc(50% - 4px) !important; flex:0 0 calc(50% - 4px) !important; min-width:0 !important;
  }
}
</style>
"""
st.markdown(RESEARCH_CSS, unsafe_allow_html=True)

NAV_ITEMS = [
    ("flow", "研究流"), ("overview", "概述图"), ("compare", "对比"),
    ("notes", "笔记"), ("upload", "论文库"),
]


def nav_bar():
    """连续导航：横向单选，窄屏可滚动，不会堆成多行。"""
    keys = [k for k, _ in NAV_ITEMS]
    labels = dict(NAV_ITEMS)
    if "_nav" not in st.session_state:
        st.session_state["_nav"] = "flow"
    pending = st.session_state.pop("_nav_pending", None)
    if pending in keys:
        st.session_state["_nav_radio"] = pending
    elif st.session_state.get("_nav_radio") not in keys:
        fallback = st.session_state.get("_nav")
        st.session_state["_nav_radio"] = fallback if fallback in keys else "flow"
    choice = st.radio(
        "导航", keys,
        format_func=lambda k: labels[k],
        horizontal=True, label_visibility="collapsed", key="_nav_radio",
    )
    st.session_state["_nav"] = choice
    return choice


def goto(key):
    st.session_state["_nav"] = key
    st.session_state["_nav_pending"] = key
    st.rerun()


# ── API 工具 ──
def _err(r):
    try: return r.json().get("detail", r.text)
    except Exception: return r.text

def _headers():
    """如果用户贴了 Key，加到请求头里。"""
    k = st.session_state.get("_user_key")
    return {"X-User-Key": k} if k else {}

def api_get(path):
    try:
        r = requests.get(f"{BACKEND_URL}{path}", timeout=60, headers=_headers())
        r.raise_for_status(); return r.json()
    except requests.RequestException as e:
        _handle_err(e); return None

def api_post(path, json=None, files=None):
    try:
        r = requests.post(f"{BACKEND_URL}{path}", json=json, files=files,
                          timeout=180, headers=_headers())
        if r.status_code == 429:
            st.warning(t("msg_quota"))
            return None
        r.raise_for_status(); return r.json()
    except requests.RequestException as e:
        _handle_err(e); return None

def api_delete(path):
    try:
        r = requests.delete(f"{BACKEND_URL}{path}", timeout=30, headers=_headers())
        r.raise_for_status(); return r.json()
    except requests.RequestException as e:
        _handle_err(e); return None


def api_get_bytes(path):
    try:
        r = requests.get(f"{BACKEND_URL}{path}", timeout=120, headers=_headers())
        r.raise_for_status(); return r.content
    except requests.RequestException as e:
        _handle_err(e); return None

def _handle_err(e):
    resp = getattr(e, "response", None)
    if resp is not None:
        try:
            d = resp.json()
            if resp.status_code == 429:
                st.warning(d.get("detail", t("msg_quota")))
            else:
                st.error(f"{d.get('detail', resp.text)}")
        except Exception:
            st.error(f"{resp.text}")
    else:
        st.error(f"{e}")

def fetch_papers():
    data = api_get("/api/papers")
    return data.get("papers", []) if data else []


def paper_title(p):
    return p.get("title") or p.get("filename") or "未命名论文"


def paper_meta(p):
    bits = [str(p.get("year") or "").strip(), p.get("filename") or ""]
    return " · ".join([b for b in bits if b])


def paper_pick_cards(papers, key_prefix, checkbox_label="选择", default_all=True, columns=3):
    """论文选择卡片：完整题目 + 年份/文件名 + 勾选框，返回选中的 paper_id。"""
    selected = []
    cols = st.columns(columns)
    for i, p in enumerate(papers):
        pid = p["paper_id"]
        key = f"{key_prefix}_{pid}"
        checked_now = bool(st.session_state.get(key, default_all))
        with cols[i % columns]:
            st.markdown(
                f'<div class="cmp-paper-card{" on" if checked_now else ""}">'
                f'<div class="cmp-paper-kicker">Paper {i + 1:02d}</div>'
                f'<div class="cmp-paper-title">{html_lib.escape(paper_title(p))}</div>'
                f'<div class="cmp-paper-meta">{html_lib.escape(paper_meta(p))}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.checkbox(checkbox_label, key=key, value=default_all):
                selected.append(pid)
    return selected


# ════════════════════════════════════════════
#  统一页面组件
# ════════════════════════════════════════════
def page_header(eyebrow, title, desc, actions=None):
    """6 个页面共用的页头：眉题 + 衬线标题 + 说明 + 可选操作区。"""
    st.markdown(
        f'<div class="pg-head lr-anim">'
        f'<div class="pg-eyebrow">{html_lib.escape(str(eyebrow or ""))}</div>'
        f'<div class="pg-title">{html_lib.escape(str(title or ""))}</div>'
        f'<div class="pg-desc">{html_lib.escape(str(desc or ""))}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if actions:
        actions()


def empty_state(icon_name, title, desc, cta=None, compact=False):
    """无论文、未生成、无笔记共用；cta 传 callable。"""
    cls = "empty compact" if compact else "empty"
    st.markdown(
        f'<div class="{cls}"><div class="ei">{icon(icon_name, 22)}</div>'
        f'<div><div class="et">{html_lib.escape(str(title or ""))}</div>'
        f'<div class="ed">{html_lib.escape(str(desc or ""))}</div></div></div>',
        unsafe_allow_html=True,
    )
    if cta:
        cta()


def skeleton(lines=4, blocks=0):
    """纸面风骨架屏。"""
    widths = ["w85", "w70", "w50"]
    parts = ['<div class="sk">']
    for i in range(max(1, lines)):
        parts.append(f'<div class="sk-line {widths[i % len(widths)]}"></div>')
    for _ in range(blocks):
        parts.append('<div class="sk-block"></div>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def confirm_delete(kind, item_id, label, on_confirm):
    """弱化文字删除 + 行内二次确认，不使用 dialog。"""
    key = f"pending_del_{kind}_{item_id}"
    if st.session_state.get(key):
        with st.container():
            st.markdown(
                f'<div class="danger-confirm">确定删除 <b>{html_lib.escape(str(label or ""))}</b>？'
                f'此操作不可恢复。</div>',
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="danger-marker"></div>', unsafe_allow_html=True)
                if st.button("确认删除", key=f"confirm_del_{kind}_{item_id}",
                             type="primary", use_container_width=True):
                    on_confirm()
                    st.session_state.pop(key, None)
                    st.rerun()
            with c2:
                if st.button("取消", key=f"cancel_del_{kind}_{item_id}", use_container_width=True):
                    st.session_state.pop(key, None)
                    st.rerun()
    else:
        with st.container():
            st.markdown('<div class="danger-marker"></div>', unsafe_allow_html=True)
            if st.button("删除", key=f"del_{kind}_{item_id}"):
                st.session_state[key] = True
                st.rerun()


def split_lede(text, limit=92):
    """把首句拆成 lede；仅当首句干净、够短且后面还有正文时才拆，避免重复显示。"""
    raw = str(text or "").strip()
    if not raw or raw.startswith(("#", "-", "*", "|", ">", "```")) or re.match(r"^\d+[.)]\s", raw):
        return "", raw
    m = re.match(r"([^。！？.!?\n]+[。！？.!?])[ \t]*(?:\n+|$)", raw)
    if not m:
        return "", raw
    lede = m.group(1).strip()
    rest = raw[m.end():].lstrip()
    if not rest or len(lede) > limit or any(ch in lede for ch in "*_`[]<$\\"):
        return "", raw
    return lede, rest


def stage_status(stages, key):
    if key in stages:
        return "已生成"
    if key == "author" and "context" in stages:
        return "待你先写"
    if key == "idea" and "critique" in stages:
        return "待你先写"
    return "未生成"


def verify_key(key):
    try:
        r = requests.post(f"{BACKEND_URL}/api/verify-key", json={"key": key.strip()}, timeout=15)
        if r.status_code == 200:
            return True, None
        return False, r.json().get("detail", t("msg_key_bad"))
    except Exception as e:
        return False, str(e)


def is_demo_mode():
    return _qs("mode") == "demo" or _qs("demo") == "1"


# ════════════════════════════════════════════
#  ===== VIZ =====
#  研究流可视化：纯 dict 入参，便于单独预览 / 测试。
#  颜色语义：墨绿=作者/论文事实，灰=备选/背景，暖金=用户内容，红=被攻击/风险。
# ════════════════════════════════════════════
VIZ_CSS = """
<style>
.viz-block{ margin:16px 0 18px; }
.viz-kicker{ font-family:var(--lr-mono); font-size:.6rem; letter-spacing:.14em;
  text-transform:uppercase; color:var(--lr-accent-2); }
.viz-title{ font-family:var(--lr-serif); font-size:1.04rem; font-weight:700;
  color:var(--lr-ink); margin:2px 0 3px; }
.viz-concl{ font-family:var(--lr-sans); font-size:.82rem; line-height:1.72;
  color:var(--lr-ink-2); margin:0 0 9px; }
.viz-concl b{ color:var(--lr-accent); }
.viz-details{ margin-top:7px; font-family:var(--lr-sans); font-size:.78rem; color:var(--lr-ink-3); }
.viz-details > summary{ cursor:pointer; color:var(--lr-accent); letter-spacing:.02em;
  text-underline-offset:3px; width:max-content; }
.viz-details > summary:hover{ color:var(--lr-warn); }
.viz-details table{ width:100%; border-collapse:collapse; margin:8px 0 2px;
  border:1px solid var(--lr-rule); background:var(--lr-surface); }
.viz-details th,.viz-details td{ border-bottom:1px solid var(--lr-rule); padding:7px 9px;
  text-align:left; vertical-align:top; font-size:.74rem; line-height:1.62; color:var(--lr-ink-2); }
.viz-details th{ background:var(--lr-paper-2); color:var(--lr-ink); font-weight:650; }
.viz-details tr:last-child td{ border-bottom:none; }
.viz-details .sub{ font-family:var(--lr-mono); font-size:.66rem; color:var(--lr-accent-2);
  margin:12px 0 4px; letter-spacing:.06em; }
.rf-basisbar{ width:46px; height:6px; border-radius:3px; border:1px solid var(--lr-rule);
  flex:0 0 auto; }
.rf-basisbar.b-paper{ background:#31543F; border-color:#31543F; }
.rf-basisbar.b-external{ background:#B9B4A6; border-color:#B9B4A6; }
.rf-basisbar.b-inference{ background:#7A9C87; border-color:#7A9C87; }
.rf-basisbar.b-mixed{ background:repeating-linear-gradient(135deg,#31543F 0 2px,#DDD9CD 2px 4px); }
.viz-demo-wrap{ max-width:1180px; margin:0 auto; padding:8px 4px 48px; }
.viz-demo-head{ font-family:var(--lr-serif); font-size:1.55rem; font-weight:700; color:var(--lr-ink); }
.viz-demo-sub{ font-family:var(--lr-sans); font-size:.82rem; color:var(--lr-ink-3); margin:4px 0 18px; }
.viz-side{ border-top:1px solid var(--lr-rule); margin-top:14px; padding-top:12px; }
.viz-side-k{ font-family:var(--lr-mono); font-size:.6rem; letter-spacing:.14em;
  text-transform:uppercase; color:var(--lr-accent-2); }
.viz-side-t{ font-family:var(--lr-sans); font-size:.78rem; color:var(--lr-ink-2); margin:3px 0 6px; }
.viz-side-t b{ color:var(--lr-accent); }
.viz-side .viz-details{ font-size:.7rem; }
.viz-side .viz-details table{ font-size:.66rem; }
.viz-heat{ border:1px solid var(--lr-rule); background:var(--lr-surface);
  border-radius:var(--lr-r2); padding:11px 12px 9px; margin:4px 0 14px; overflow-x:auto; }
.viz-heat table{ width:100%; border-collapse:separate; border-spacing:3px; min-width:520px; }
.viz-heat th{ font-family:var(--lr-sans); font-size:.68rem; font-weight:600;
  color:var(--lr-ink-3); text-align:left; padding:2px 3px; white-space:nowrap; }
.viz-heat thead th{ text-align:center; color:var(--lr-ink-2); }
.viz-heat tbody th{ max-width:170px; overflow:hidden; text-overflow:ellipsis; }
.viz-heat .hm-cell{ display:block; height:26px; border-radius:2px; text-decoration:none !important;
  background:rgba(32,32,28,var(--a,.12)); border:1px solid rgba(32,32,28,.06); }
.viz-heat .hm-cell:hover{ border-color:var(--lr-accent); }
.viz-heat .hm-lab{ font-family:var(--lr-mono); font-size:.6rem; color:var(--lr-ink-3);
  margin-left:6px; letter-spacing:.05em; }
.viz-heat .hm-note{ font-family:var(--lr-sans); font-size:.72rem; color:var(--lr-ink-3);
  margin-top:7px; line-height:1.6; }
.viz-heat .hm-note b{ color:var(--lr-ink-2); }
.cmp-table tbody tr{ scroll-margin-top:96px; }
.cmp-table tbody tr:target th,.cmp-table tbody tr:target td{ background:#F1EDE1; }
@media (prefers-reduced-motion:reduce){
  html{ scroll-behavior:auto !important; }
  .viz-details > summary:hover{ color:var(--lr-accent); }
}
</style>
"""
st.markdown(VIZ_CSS, unsafe_allow_html=True)


def _vz_esc(value):
    return html_lib.escape("" if value is None else str(value))


def _vz_clip(value, n=120):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _vz_frame(body_html, height, extra_script=""):
    """统一 iframe：内容自适应高度，内部不出现滚动条。"""
    doc = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{{--ink:#20201C;--ink2:#4E4C45;--ink3:#6B675D;--paper:#F7F5F0;--surface:#fff;
--rule:#DDD9CD;--rule2:#C6C1B2;--accent:#31543F;--accent2:#7A9C87;--gold:#96671A;
--danger:#97382B;--serif:"Noto Serif SC","Source Han Serif SC","Songti SC",Georgia,serif;
--sans:"Inter",-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
--mono:"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:transparent;overflow:hidden;}}
body{{font-family:var(--sans);color:var(--ink);font-size:13px;line-height:1.65;}}
svg{{display:block;max-width:100%;}}
:focus-visible{{outline:2px solid var(--gold);outline-offset:2px;}}
.vz-sr{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;}}
@media (prefers-reduced-motion:reduce){{*{{animation:none !important;transition:none !important;}}}}
</style></head><body>
{body_html}
<script>
window.__vzFit=function(){{
  var h=Math.max(document.body.scrollHeight,document.documentElement.scrollHeight);
  try{{window.parent.postMessage({{type:'streamlit:setFrameHeight',height:h}},'*');}}catch(e){{}}
  try{{if(window.frameElement){{window.frameElement.style.height=h+'px';}}}}catch(e){{}}
}};
window.addEventListener('load',function(){{setTimeout(window.__vzFit,30);}});
window.addEventListener('resize',function(){{setTimeout(window.__vzFit,30);}});
setTimeout(window.__vzFit,80); setTimeout(window.__vzFit,360);
</script>
<script>{extra_script}</script>
</body></html>"""
    components.html(doc, height=int(height), scrolling=False)


_VIZ_VARS = """
<style>
.vz-static{--ink:#20201C;--ink2:#4E4C45;--ink3:#6B675D;--paper:#F7F5F0;--surface:#fff;
--rule:#DDD9CD;--rule2:#C6C1B2;--accent:#31543F;--accent2:#7A9C87;--gold:#96671A;
--danger:#97382B;--serif:"Noto Serif SC","Source Han Serif SC","Songti SC",Georgia,serif;
--sans:"Inter",-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
--mono:"SF Mono","JetBrains Mono",Menlo,Consolas,monospace;
font-family:var(--sans);color:var(--ink);line-height:1.65;}
.vz-static svg{display:block;max-width:100%;}
.vz-static :focus-visible{outline:2px solid var(--gold);outline-offset:2px;}
@media (prefers-reduced-motion:reduce){.vz-static *{animation:none !important;transition:none !important;}}
</style>
"""


def _vz_static(body_html):
    """静态图直接进页面文档流，高度自适应，避免 iframe 留白。"""
    st.markdown(_VIZ_VARS + f'<div class="vz-static">{body_html}</div>',
                unsafe_allow_html=True)


def _vz_details(headers, rows, label="数据表", extra_html=""):
    if not rows:
        return
    head = "".join(f"<th>{_vz_esc(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_vz_esc(c)}</td>" for c in row) + "</tr>"
        for row in rows
    )
    st.markdown(
        f'<details class="viz-details"><summary>{_vz_esc(label)}（{len(rows)} 行）</summary>'
        f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>{extra_html}</details>',
        unsafe_allow_html=True,
    )


def _vz_head(kicker, title, concl):
    st.markdown(
        f'<div class="viz-block"><div class="viz-kicker">{_vz_esc(kicker)}</div>'
        f'<div class="viz-title">{_vz_esc(title)}</div>'
        f'<div class="viz-concl">{concl}</div></div>',
        unsafe_allow_html=True,
    )


_KIND_LABEL = {"paper": "论文事实", "external": "背景 / 外部",
               "inference": "AI 推断", "mixed": "事实 + 推断", "missing": "未生成"}
_KIND_COLOR = {"paper": "#31543F", "external": "#B9B4A6",
               "inference": "#7A9C87", "mixed": "url(#vzHatch)", "missing": "#EFECE3"}


def viz_basis_spectrum(basis):
    """P0-1 研究流构成（可信度光谱）。入参：viz['basis']（纯 dict）。"""
    basis = basis or {}
    steps = basis.get("steps") or []
    counts = basis.get("counts") or {}
    shares = basis.get("shares") or {}
    gen = int(basis.get("generated") or 0)
    if not steps or gen <= 0:
        st.caption("研究流尚未生成，暂时没有研究流构成。")
        return

    order = [k for k in ("paper", "external", "inference", "mixed")]
    if counts.get("missing"):
        order.append("missing")
    total = sum(int(counts.get(k, 0)) for k in order) or 12

    segs, x = [], 0.0
    for k in order:
        width = 1000.0 * shares.get(k, 0) / 100.0
        if width <= 0:
            continue
        fill = _KIND_COLOR[k]
        segs.append(f'<rect x="{x:.2f}" y="0" width="{width:.2f}" height="34" fill="{fill}" '
                    f'stroke="#F7F5F0" stroke-width="1"></rect>')
        if width >= 64:
            color = "#FFFFFF" if k in ("paper", "inference") else "#20201C"
            segs.append(f'<text x="{x + width / 2:.2f}" y="22" text-anchor="middle" '
                        f'font-size="12" font-family="var(--mono)" fill="{color}">'
                        f'{shares.get(k, 0)}%</text>')
        x += width

    cards = "".join(
        f'<div class="bs-card"><div class="bs-card-top"><i class="bs-dot b-{k}"></i>'
        f'<span>{_KIND_LABEL[k]}</span></div>'
        f'<div class="bs-card-pct">{shares.get(k, 0)}%</div>'
        f'<div class="bs-card-meta">{counts.get(k, 0)} / {total} 步</div></div>'
        for k in order
    )
    strip = "".join(
        f'<span class="bs-step b-{s.get("kind") or "missing"}" title="第 {s.get("index")} 步 · '
        f'{_KIND_LABEL.get(s.get("kind"), "未生成")}">{int(s.get("index")):02d}</span>'
        for s in steps
    )
    parts = [
        f'{shares.get("paper", 0)}% 是论文事实',
        f'{shares.get("external", 0)}% 是背景/外部知识',
        f'{shares.get("inference", 0)}% 是 AI 推断',
    ]
    if shares.get("mixed"):
        parts.append(f'{shares.get("mixed", 0)}% 是事实与推断混用')
    if shares.get("missing"):
        parts.append(f'{shares.get("missing", 0)}% 尚未生成')
    concl = "；".join(parts) + "。这不是论文质量评分，而是这条研究流的信息来源构成。"

    body = f"""
<div class="bs">
  <div class="bs-top">
    <div class="bs-title">这篇论文的研究流由什么组成？</div>
    <div class="bs-sub">按 12 步的依据来源统计 · 不是质量评分</div>
  </div>
  <div class="bs-bar">
    <svg viewBox="0 0 1000 34" width="100%" role="img"
         aria-label="研究流构成：{_vz_esc('；'.join(f'{_KIND_LABEL[k]} {shares.get(k,0)}%' for k in order))}">
      <defs><pattern id="vzHatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="6" height="6" fill="#DDD9CD"></rect><rect width="3" height="6" fill="#31543F"></rect>
      </pattern></defs>
      <rect x="0" y="0" width="1000" height="34" fill="#EFECE3"></rect>
      {''.join(segs)}
    </svg>
  </div>
  <div class="bs-legend">{cards}</div>
  <div class="bs-concl">{concl}</div>
  <div class="bs-strip-label">逐步骤依据</div>
  <div class="bs-strip">{strip}</div>
</div>"""
    extra = """
<style>
.bs-top{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:7px;}
.bs-title{font-family:var(--sans);font-size:13px;font-weight:600;color:var(--ink);}
.bs-sub{font-family:var(--mono);font-size:9px;letter-spacing:.06em;color:var(--ink3);text-align:right;}
.bs-bar{border-radius:4px;overflow:hidden;}
.bs-bar svg{display:block;}
.bs-legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:8px;margin-top:10px;}
.bs-card{border:1px solid var(--rule);background:#fff;border-radius:5px;padding:8px 10px;min-width:0;}
.bs-card-top{display:flex;align-items:center;gap:6px;font-family:var(--sans);font-size:11px;
  color:var(--ink2);}
.bs-card-pct{font-family:var(--mono);font-size:20px;font-weight:600;color:var(--ink);
  line-height:1.2;margin-top:4px;}
.bs-card-meta{font-family:var(--mono);font-size:9px;color:var(--ink3);margin-top:2px;}
.bs-dot{width:9px;height:9px;border-radius:2px;display:inline-block;flex:0 0 auto;}
.bs-dot.b-mixed{background:repeating-linear-gradient(135deg,#31543F 0 2px,#DDD9CD 2px 4px);}
.bs-concl{margin-top:10px;padding:8px 10px;background:#F3F0E7;border-left:2px solid var(--accent);
  font-family:var(--sans);font-size:11.5px;line-height:1.65;color:var(--ink2);}
.bs-strip-label{font-family:var(--mono);font-size:9px;letter-spacing:.08em;color:var(--ink3);
  margin-top:11px;text-transform:uppercase;}
.bs-strip{display:flex;gap:4px;margin-top:6px;flex-wrap:wrap;}
.bs-step{font-family:var(--mono);font-size:9.5px;color:var(--ink3);border:1px solid var(--rule);
  border-radius:2px;padding:1px 5px;background:#fff;}
.bs-step.b-paper{border-color:#31543F;color:#31543F;}
.bs-step.b-inference{border-color:#7A9C87;color:#31543F;}
.bs-step.b-external{border-color:#B9B4A6;}
.bs-step.b-mixed{background:repeating-linear-gradient(135deg,#E9EFE9 0 2px,#fff 2px 4px);}
.bs-step.b-missing{color:#8B877C;background:#F7F5F0;}
@media(max-width:700px){
  .bs-top{flex-direction:column;align-items:flex-start;gap:2px;}
  .bs-sub{text-align:left;}
  .bs-legend{grid-template-columns:repeat(2,minmax(0,1fr));}
}
</style>"""
    _vz_head(
        "EVIDENCE COMPOSITION",
        "研究流构成",
        f"12 步中已生成 <b>{gen}</b> 步。一条完整色带显示论文事实、背景/外部、"
        f"AI 推断和混合各占多少；颜色只表示信息来源，不是论文质量评分。",
    )
    _vz_static(body + extra)

    rows = []
    for s in steps:
        rows.append([
            f'{int(s.get("index")):02d} {s.get("title") or ""}',
            _KIND_LABEL.get(s.get("kind"), "未生成"),
            " · ".join(s.get("basis") or []) or "—",
        ])
    _vz_details(["步骤", "依据类型", "basis 字段"], rows, "查看 12 步依据表")


def viz_growth_sparkline(growth):
    """P2-5 侧栏成长曲线。入参：/api/research/growth 返回的纯 dict。"""
    growth = growth or {}
    scores = [int(x.get("score", 0)) for x in (growth.get("scores") or [])]
    if not scores:
        st.markdown(
            '<div class="viz-side"><div class="viz-side-k">TRAINING</div>'
            '<div class="viz-side-t">完成第 3 步对照后，这里会出现你的推演成长曲线。</div></div>',
            unsafe_allow_html=True,
        )
        return
    w, h, pad = 220, 48, 5
    if len(scores) == 1:
        pts = [(w / 2, h - pad - scores[0] / 100 * (h - 2 * pad))]
    else:
        pts = [
            (pad + i * (w - 2 * pad) / (len(scores) - 1),
             h - pad - s / 100 * (h - 2 * pad))
            for i, s in enumerate(scores)
        ]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.1" fill="#96671A"></circle>'
                   for x, y in pts[-6:])
    last = pts[-1]
    avg = growth.get("avg", 0)
    papers = growth.get("papers", 0)
    st.markdown(
        f'<div class="viz-side"><div class="viz-side-k">TRAINING</div>'
        f'<div class="viz-side-t">已训练 <b>{papers}</b> 篇 · 平均接近度 <b>{avg}</b></div>'
        f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" '
        f'aria-label="推演成长曲线：最近 {len(scores)} 次对照，平均接近度 {avg}">'
        f'<title>推演成长曲线</title>'
        f'<line x1="{pad}" y1="{h - pad}" x2="{w - pad}" y2="{h - pad}" stroke="#DDD9CD" stroke-width="1"></line>'
        f'<polyline points="{poly}" fill="none" stroke="#96671A" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round"></polyline>{dots}'
        f'<circle cx="{last[0]:.1f}" cy="{last[1]:.1f}" r="3.4" fill="#96671A"></circle>'
        f'</svg>'
        f'<div style="font-family:var(--lr-sans);font-size:.66rem;color:var(--lr-ink-3);">'
        f'近似对照分数，不是能力评分</div></div>',
        unsafe_allow_html=True,
    )
    rows = [[f"#{i + 1}", str(s), x.get("paper_id", "")[:10]]
            for i, (s, x) in enumerate(zip(scores[-12:], (growth.get("scores") or [])[-12:]))]
    _vz_details(["次数", "接近度", "论文"], rows, "查看分数记录")


THINK_CSS = """<style>
.think-head{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin:18px 0 10px}
.think-kicker{font-family:var(--lr-mono);font-size:.66rem;letter-spacing:.14em;color:var(--lr-ink-4);text-transform:uppercase}
.think-title{font-family:var(--lr-serif);font-size:1.28rem;color:var(--lr-ink);margin-top:3px}
.think-count{font-size:.76rem;color:var(--lr-ink-3);white-space:nowrap}
.think-summary{background:var(--lr-accent-wash);border:1px solid rgba(49,84,63,.18);
  border-left:3px solid var(--lr-accent);border-radius:6px;padding:10px 13px;margin:10px 0 14px}
.think-summary .k{font-family:var(--lr-mono);font-size:.66rem;letter-spacing:.12em;
  color:var(--lr-accent);text-transform:uppercase;margin-bottom:3px}
.think-summary .v{font-size:.88rem;line-height:1.7;color:var(--lr-ink-2)}
.think-lanes{display:grid;grid-template-columns:repeat(auto-fit,minmax(238px,1fr));
  gap:14px;align-items:start}
.think-lane{background:var(--lr-surface);border:1px solid var(--lr-rule);border-radius:8px;
  padding:13px 14px 11px;box-shadow:var(--lr-sh1)}
.think-lane-head{padding-bottom:9px;border-bottom:1px solid var(--lr-rule)}
.think-lane-title{font-family:var(--lr-serif);font-size:.94rem;line-height:1.45;color:var(--lr-ink)}
.think-lane-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:5px;
  font-size:.72rem;color:var(--lr-ink-4)}
.think-pattern{font-family:var(--lr-mono);font-size:.63rem;letter-spacing:.04em;
  color:var(--lr-accent);background:var(--lr-accent-wash);border:1px solid rgba(49,84,63,.2);
  border-radius:999px;padding:1px 7px}
.think-step{--think-c:var(--lr-rule-2);padding:8px 0 8px 11px;border-left:2px solid var(--think-c)}
.think-step + .think-step{border-top:1px dashed var(--lr-rule)}
.think-label{display:flex;align-items:center;gap:6px;font-family:var(--lr-mono);
  font-size:.65rem;letter-spacing:.06em;color:var(--lr-ink-3);text-transform:uppercase}
.think-dot{width:6px;height:6px;border-radius:50%;background:var(--think-c);flex:0 0 auto}
.think-text{margin-top:2px;font-size:.82rem;line-height:1.62;color:var(--lr-ink-2);
  white-space:pre-wrap;overflow-wrap:anywhere}
.ph-context{--think-c:#B9B4A6}.ph-author{--think-c:#31543F}.ph-method{--think-c:#7A9C87}
.ph-evidence{--think-c:#4F7361}.ph-critique{--think-c:#97382B}.ph-idea{--think-c:#96671A}
.think-more{margin-top:9px;border-top:1px solid var(--lr-rule);padding-top:7px}
.think-more summary{cursor:pointer;font-size:.73rem;color:var(--lr-ink-3);list-style:none}
.think-more summary::-webkit-details-marker{display:none}
.think-more summary::before{content:"＋ ";color:var(--lr-accent)}
.think-more[open] summary::before{content:"－ "}
.think-alt{padding:6px 0;border-bottom:1px dashed var(--lr-rule);font-size:.76rem;line-height:1.55}
.think-alt:last-child{border-bottom:none}
.think-alt b{display:block;color:var(--lr-ink);font-weight:600}
.think-alt-text{color:var(--lr-ink-2);margin-top:2px}
.think-alt-reason{color:var(--lr-ink-4);margin-top:2px;font-size:.72rem}
.think-path-item{padding:7px 0;border-bottom:1px dashed var(--lr-rule)}
.think-path-item:last-child{border-bottom:none}
.think-path-move{font-size:.75rem;font-weight:600;color:var(--lr-ink)}
.think-path-line{font-size:.72rem;line-height:1.55;color:var(--lr-ink-3);margin-top:2px}
.think-path-line span{display:inline-block;min-width:2.2em;color:var(--lr-ink-4);
  font-family:var(--lr-mono);font-size:.62rem;margin-right:4px}
@media(max-width:820px){
  .think-lanes{grid-template-columns:1fr}
  .think-head{align-items:flex-start;flex-direction:column}
  .think-count{white-space:normal}
}
</style>"""


def viz_thinking_compare(result):
    """按 12 步研究流并排展示论文的思考动作，不做文本相似度。"""
    result = result or {}
    papers = result.get("papers") or []
    axes = result.get("axes") or []
    if not papers or not axes:
        return
    st.markdown(THINK_CSS, unsafe_allow_html=True)

    cards = []
    for paper in papers:
        cells = paper.get("cells") or []
        steps = []
        for i, axis in enumerate(axes):
            phase = str(axis.get("phase") or "context")
            if phase not in ("context", "author", "method", "evidence", "critique", "idea"):
                phase = "context"
            label = _vz_esc(axis.get("label") or axis.get("key") or "")
            hint = _vz_esc(axis.get("hint") or "")
            text = cells[i] if i < len(cells) else "—"
            steps.append(
                f'<div class="think-step ph-{phase}" title="{hint}">'
                f'<div class="think-label"><span class="think-dot"></span>{label}</div>'
                f'<div class="think-text">{_vz_esc(text)}</div></div>'
            )

        meta = []
        if paper.get("year"):
            meta.append(_vz_esc(paper.get("year")))
        meta.append(f'<span class="think-pattern">{_vz_esc(paper.get("pattern") or "研究路径")}</span>')

        alternatives = paper.get("alternatives") or []
        alt_html = ""
        if len(alternatives) > 1:
            items = []
            for alt in alternatives:
                route = alt.get("text") or ""
                reason = alt.get("reason_dropped") or ""
                items.append(
                    f'<div class="think-alt"><b>{_vz_esc(alt.get("label") or "备选路线")}</b>'
                    f'<div class="think-alt-text">{_vz_esc(_vz_clip(route, 180))}</div>'
                    f'<div class="think-alt-reason">放弃原因：{_vz_esc(_vz_clip(reason, 140))}</div>'
                    f'</div>'
                )
            items = "".join(items)
            alt_html = (
                f'<details class="think-more"><summary>全部备选路线（{len(alternatives)} 条）</summary>'
                f'{items}</details>'
            )

        path = paper.get("path") or []
        path_html = ""
        if path:
            items = []
            for i, beat in enumerate(path):
                idx = beat.get("index")
                num = int(idx) + 1 if isinstance(idx, (int, float)) else i + 1
                lines = []
                for key, label in (("known", "已知"), ("question", "疑问"),
                                   ("leap", "跳跃"), ("temptation", "诱惑")):
                    if beat.get(key):
                        lines.append(
                            f'<div class="think-path-line"><span>{label}</span>'
                            f'{_vz_esc(beat.get(key))}</div>'
                        )
                items.append(
                    f'<div class="think-path-item"><div class="think-path-move">'
                    f'{num:02d} · {_vz_esc(beat.get("move") or "")}</div>'
                    f'{"".join(lines)}</div>'
                )
            path_html = (
                f'<details class="think-more"><summary>展开完整作者路径（{len(path)} 个动作）</summary>'
                f'{"".join(items)}</details>'
            )

        cards.append(
            f'<div class="think-lane">'
            f'<div class="think-lane-head">'
            f'<div class="think-lane-title">{_vz_esc(paper.get("title") or "")}</div>'
            f'<div class="think-lane-meta">{" · ".join(meta)}</div>'
            f'</div>'
            f'<div class="think-steps">{"".join(steps)}</div>'
            f'{alt_html}{path_html}'
            f'</div>'
        )

    st.markdown(
        f'<div class="think-head">'
        f'<div><div class="think-kicker">THINKING PATHS</div>'
        f'<div class="think-title">{len(papers)} 篇论文的思维路径</div></div>'
        f'<div class="think-count">{len(papers)} 篇 · {len(axes)} 个思维阶段</div>'
        f'</div>'
        f'<div class="think-summary"><div class="k">一句话看差异</div>'
        f'<div class="v">{_vz_esc(result.get("summary") or "")}</div></div>'
        f'<div class="think-lanes">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def viz_fork_map(viz, user_result=None):
    """P0-2 思维分叉图。入参：viz['fork'] 或整个 viz dict；user_result 为结构化对照结果。"""
    fork = viz.get("fork") if isinstance(viz, dict) and "fork" in viz else (viz or {})
    beats = fork.get("beats") or []
    if not beats:
        st.caption("第 3 步尚未生成，暂时没有思维分叉图。")
        return

    alts = fork.get("alternatives") or []
    design = fork.get("design") or []
    user = user_result if isinstance(user_result, dict) else None
    data_json = json.dumps({
        "beats": beats,
        "alts": alts,
        "design": design,
        "summary": fork.get("summary") or {},
        "paper": fork.get("paper") or {},
        "user": user,
    }, ensure_ascii=False).replace("<", "\\u003c")

    if user:
        concl = ("暖金线是你提交的推演路径；图下方给出自动对照结论。"
                 '<span style="color:var(--lr-ink-3)"> · 近似对照，按文字重合度计算，不调用模型。</span>')
    else:
        concl = (f"作者主路径共 <b>{len(beats)}</b> 个动作；"
                 f"另有 <b>{len(alts)}</b> 条当时也说得通、但被作者放弃的备选路线。"
                 "点击、悬停或用 Tab 聚焦节点查看详情。")
    _vz_head("IDEA FORK MAP · STEP 03", "思维分叉图：作者路径与备选路线", concl)

    body = r"""
<style>
.fk-legend{display:flex;flex-wrap:wrap;gap:5px 14px;margin:0 0 7px;font-family:var(--sans);
  font-size:11px;color:var(--ink3);}
.fk-legend span{display:inline-flex;align-items:center;gap:5px;white-space:nowrap;}
.fk-legend i{display:inline-block;width:20px;height:0;border-top:2px solid var(--accent);}
.fk-legend i.gray{border-top:2px dashed #8B877C;}
.fk-legend i.gold{border-top:2px solid var(--gold);}
.fk-legend i.tri{width:0;height:0;border-top:7px solid transparent;border-bottom:7px solid transparent;
  border-left:8px solid var(--danger);border-right:0;}
.fk-stage{width:100%;}
.fk-note{min-height:240px;border:1px solid var(--rule);border-radius:6px;background:#fff;
  padding:9px 11px;margin-top:5px;}
@media (min-width:900px){ .fk-note{min-height:360px;} }
.fk-note .nk{font-family:var(--mono);font-size:10px;letter-spacing:.1em;color:var(--accent2);
  text-transform:uppercase;display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.fk-note .nbadge{border:1px solid var(--gold);color:var(--gold);border-radius:999px;padding:0 7px;
  font-size:9.5px;letter-spacing:.04em;}
.fk-note .ngrid{display:grid;grid-template-columns:1fr 1fr;gap:5px 16px;margin-top:6px;}
.fk-note .nl{font-family:var(--sans);font-size:9.5px;letter-spacing:.08em;color:var(--ink3);}
.fk-note .nv{font-family:var(--sans);font-size:11.8px;line-height:1.6;color:var(--ink);}
.fk-note .nev{margin-top:6px;border-left:2px solid var(--gold);padding-left:8px;
  font-family:var(--sans);font-size:11px;line-height:1.6;color:var(--ink2);}
.fk-note .nhint{font-family:var(--sans);font-size:11.5px;color:var(--ink3);line-height:1.7;}
.fk-note .nlist{margin:4px 0 0;padding-left:16px;font-family:var(--sans);font-size:11.5px;
  line-height:1.65;color:var(--ink2);}
.fk-note .nlist li{margin:2px 0;}
.fk-note .nidx{display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;margin-top:7px;}
.fk-note .nidx-row{font-family:var(--sans);font-size:11px;line-height:1.6;color:var(--ink2);
  margin:1px 0;}
.fk-note .nidx-n{font-family:var(--mono);font-size:9.5px;color:var(--gold);margin-right:4px;}
.fk-note .nidx-q{color:var(--ink3);}
.fk-note .nfoot{margin-top:7px;padding-top:6px;border-top:1px dashed var(--rule);
  font-family:var(--sans);font-size:10px;line-height:1.6;color:var(--ink3);}
.fk-cue{font-family:var(--sans);font-size:10.5px;color:var(--ink3);margin-top:4px;}
</style>
<div class="fk-legend">
  <span><i></i>作者主路径</span>
  <span><i class="gray"></i>作者放弃的备选</span>
  <span><i class="gold"></i>你的推演</span>
  <span><i class="tri"></i>最容易走错的路</span>
</div>
<div class="fk-stage" id="fk-stage"><svg id="fk-svg" width="100%" role="img" aria-label="作者思维分叉图"></svg></div>
<div class="fk-note" id="fk-note" aria-live="polite"></div>
<div class="fk-cue">键盘：Tab 聚焦节点，Enter / Space 查看页边注。</div>
<script>
(function(){
const DATA = __DATA__;
const NS = 'http://www.w3.org/2000/svg';
const SANS = '"Inter",-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif';
const MONO = '"SF Mono","JetBrains Mono",Menlo,Consolas,monospace';
const svg = document.getElementById('fk-svg');
const stage = document.getElementById('fk-stage');
const note = document.getElementById('fk-note');
const beats = DATA.beats || [];
const alts = DATA.alts || [];
const design = DATA.design || [];
const user = DATA.user || null;
const statusMap = {};
if (user && user.beats) user.beats.forEach(function(x){ statusMap[x.index] = x; });
let selected = null;
let altCoords = {};

function esc(s){
  return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
  });
}
function short(s, n){
  s = String(s == null ? '' : s);
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}
function wrap(s, n, maxLines){
  s = String(s == null ? '' : s);
  const out = [];
  let buf = '';
  for (const ch of s){
    buf += ch;
    if (buf.length >= n){ out.push(buf); buf = ''; if (out.length >= maxLines) break; }
  }
  if (buf && out.length < maxLines) out.push(buf);
  if (out.length >= maxLines && s.length > out.join('').length){
    out[maxLines - 1] = out[maxLines - 1].slice(0, -1) + '…';
  }
  return out;
}
function el(tag, attrs, parent){
  const e = document.createElementNS(NS, tag);
  if (attrs) for (const k in attrs) e.setAttribute(k, attrs[k]);
  (parent || svg).appendChild(e);
  return e;
}
function txt(x, y, s, opt){
  opt = opt || {};
  const t = el('text', {
    x: x, y: y, 'text-anchor': opt.anchor || 'start',
    'dominant-baseline': opt.base || 'middle',
    'font-size': opt.size || 12,
    'font-family': opt.mono ? MONO : SANS,
    'font-weight': opt.weight || 400,
    fill: opt.fill || '#20201C'
  });
  t.textContent = s;
  return t;
}
function path(d, stroke, width, dash, marker){
  return el('path', {
    d: d, fill: 'none', stroke: stroke, 'stroke-width': width,
    'stroke-dasharray': dash || 'none', 'stroke-linecap': 'round',
    'marker-end': marker || ''
  });
}
function connect(a, b, stroke, width, dash, marker){
  const x1 = a.x + a.w, y1 = a.y + a.h / 2;
  const x2 = b.x, y2 = b.y + b.h / 2;
  if (Math.abs(y1 - y2) < 1){
    return path('M ' + x1 + ' ' + y1 + ' L ' + x2 + ' ' + y2, stroke, width, dash, marker);
  }
  const dx = Math.max(18, Math.abs(x2 - x1) * 0.35);
  return path('M ' + x1 + ' ' + y1 + ' C ' + (x1 + dx) + ' ' + y1 + ', ' +
              (x2 - dx) + ' ' + y2 + ', ' + x2 + ' ' + y2, stroke, width, dash, marker);
}
function center(p){ return {x: p.x + p.w / 2, y: p.y + p.h / 2}; }
function select(kind, idx){
  selected = {kind: kind, idx: idx};
  renderNote();
}
function statusLabel(s){
  return s === 'hit' ? '命中' : (s === 'partial' ? '部分' : (s === 'miss' ? '未中' : ''));
}
function renderNote(){
  if (!selected){
    let html = '<div class="nk">页边注 · 点击节点展开</div><div class="nidx">';
    html += '<div><div class="nl">作者路径</div>';
    beats.forEach(function(b, i){
      html += '<div class="nidx-row"><span class="nidx-n">' +
        String(Number(b.index) + 1).padStart(2, '0') + '</span>' +
        esc(b.move || '思考') + ' <span class="nidx-q">' + esc(short(b.question || '', 42)) + '</span></div>';
    });
    html += '</div><div><div class="nl">备选路线</div>';
    if (alts.length){
      alts.forEach(function(a){
        html += '<div class="nidx-row"><b>' + esc(a.label || '备选') + '</b> · 从第 ' +
          (Number(a.branch_from) + 1) + ' 个动作分叉</div>';
      });
    } else {
      html += '<div class="nidx-row">没有留下备选路线。</div>';
    }
    html += '<div class="nhint" style="margin-top:6px">点击、悬停或用 Tab 聚焦节点；' +
      '红色三角是最容易走错的路。</div></div></div>';
    note.innerHTML = html;
    return;
  }
  function withFoot(html){
    return html + '<div class="nfoot"><b>作者路径</b> ' + beats.map(function(b){
      return String(Number(b.index) + 1).padStart(2, '0') + ' ' + esc(b.move || '思考');
    }).join(' · ') + '</div>';
  }
  if (selected.kind === 'beat'){
    const b = beats[selected.idx];
    const st = statusMap[b.index];
    const badge = st ? '<span class="nbadge">你的推演：' + esc(statusLabel(st.status)) + '</span>' : '';
    let html = '<div class="nk">' + String(Number(b.index) + 1).padStart(2, '0') + ' · ' +
      esc(b.move || '思考') + badge + '</div><div class="ngrid">';
    html += '<div><div class="nl">当时已知</div><div class="nv">' + esc(short(b.known || '—', 90)) + '</div></div>';
    html += '<div><div class="nl">自然产生的疑问</div><div class="nv">' + esc(short(b.question || '—', 90)) + '</div></div>';
    html += '<div><div class="nl">直觉跳跃</div><div class="nv">' + esc(short(b.leap || '—', 90)) + '</div></div>';
    html += '<div><div class="nl">最容易走错的路</div><div class="nv">' + esc(short(b.temptation || '—', 90)) + '</div></div>';
    html += '</div>';
    if (st && st.evidence){
      html += '<div class="nev">你的原话：「' + esc(short(st.evidence, 70)) + '」</div>';
    }
    note.innerHTML = withFoot(html);
    return;
  }
  if (selected.kind === 'alt'){
    const a = alts[selected.idx];
    const from = Number(a.branch_from) + 1;
    note.innerHTML = withFoot('<div class="nk">' + esc(a.label || '备选路线') +
      '<span class="nbadge">从第 ' + from + ' 个动作分叉</span></div>' +
      '<div class="ngrid"><div><div class="nl">这条路线</div><div class="nv">' +
      esc(short(a.text || '—', 120)) + '</div></div><div><div class="nl">作者为什么放弃</div><div class="nv">' +
      esc(short(a.reason_dropped || '—', 80)) + '</div></div></div>');
    return;
  }
  if (selected.kind === 'design'){
    let html = '<div class="nk">论文设计 · 从推演到实现</div>';
    if (!design.length){ html += '<div class="nhint">method.design_mapping 尚未生成。</div>'; }
    else {
      html += '<ul class="nlist">';
      design.slice(0, 4).forEach(function(d){
        html += '<li><b>' + esc(short(d.beat || '', 50)) + '</b> → ' +
          esc(short(d.design || '', 70)) +
          (d.comment ? ' <span style="color:var(--ink3)">（' + esc(d.comment) + '）</span>' : '') + '</li>';
      });
      html += '</ul>';
    }
    note.innerHTML = withFoot(html);
    return;
  }
  if (selected.kind === 'summary'){
    const s = DATA.summary || {};
    note.innerHTML = withFoot('<div class="nk">方法出现之前的世界</div>' +
      '<div class="ngrid"><div><div class="nl">问题本身</div><div class="nv">' +
      esc(short(s.problem || '—', 140)) + '</div></div><div><div class="nl">知识条目</div><div class="nv">' +
      esc(String(s.world_count || 0)) + ' 条，只包含方法出现前的知识。</div></div></div>');
    return;
  }
  if (selected.kind === 'novel'){
    let html = '<div class="nk">你的新路线<span class="nbadge">作者没有走</span></div>';
    if (user && user.extra && user.extra.length){
      html += '<ul class="nlist">' + user.extra.slice(0, 3).map(function(x){
        return '<li>' + esc(short(x, 80)) + '</li>';
      }).join('') + '</ul>';
    } else {
      html += '<div class="nhint">你在这里偏离了作者路径，但没有留下可摘录的额外句子。</div>';
    }
    note.innerHTML = withFoot(html);
  }
}
function render(){
  const W = Math.max(320, Math.round(stage.clientWidth || 900));
  const n = beats.length;
  const needSingle = n * 76 + Math.max(0, n - 1) * 8 + 300 + 60;
  const single = needSingle <= W;
  const topPad = 12;
  let H, pos = [], left, right = null;
  if (single){
    const leftW = Math.min(150, Math.max(112, W * 0.13));
    const rightW = design.length ? Math.min(150, Math.max(112, W * 0.13)) : 0;
    const gap = Math.max(8, Math.min(20, (W - leftW - rightW - 60 - n * 84) / Math.max(1, n - 1)));
    const beatW = Math.max(76, Math.min(108, (W - leftW - rightW - 60 - (n - 1) * gap) / n));
    const total = leftW + 30 + n * beatW + (n - 1) * gap + (design.length ? 30 + rightW : 0);
    const x0 = Math.max(4, (W - total) / 2);
    const y = topPad + 16, h = 76;
    left = {x: x0, y: y, w: leftW, h: h};
    pos = beats.map(function(b, i){
      return {x: x0 + leftW + 30 + i * (beatW + gap), y: y, w: beatW, h: h, b: b};
    });
    if (design.length){
      right = {x: x0 + leftW + 30 + n * beatW + (n - 1) * gap + 30, y: y, w: rightW, h: h};
    }
    H = y + h + 104;
  } else {
    const pad = 6;
    const leftW = 112;
    const rightW = design.length ? 104 : 0;
    const k = Math.ceil(n / 2);
    const r1 = beats.slice(0, k);
    const r2 = beats.slice(k);
    const gap = 8, h = 64;
    const bw1 = Math.min(108, Math.max(62, (W - 2 * pad - (r1.length - 1) * gap) / r1.length));
    const row1W = r1.length * bw1 + (r1.length - 1) * gap;
    const start1 = Math.max(pad, (W - row1W) / 2);
    const y1 = topPad + 60;
    const row2Max = W - 2 * pad - rightW - (rightW ? 18 : 0);
    const bw2 = r2.length ? Math.min(108, Math.max(62, (row2Max - (r2.length - 1) * gap) / r2.length)) : 0;
    const y2 = y1 + h + 74;
    left = {x: pad, y: topPad, w: leftW, h: 46};
    pos = r1.map(function(b, i){
      return {x: start1 + i * (bw1 + gap), y: y1, w: bw1, h: h, b: b};
    }).concat(r2.map(function(b, i){
      return {x: pad + i * (bw2 + gap), y: y2, w: bw2, h: h, b: b};
    }));
    if (design.length) right = {x: W - pad - rightW, y: y2, w: rightW, h: h};
    H = y2 + h + 76;
  }

  altCoords = {};
  let maxY = H;
  const lane = {};
  alts.forEach(function(a){
    const bp = pos.find(function(p){ return p.b.index === a.branch_from; }) || pos[pos.length - 1];
    if (!bp) return;
    const l = lane[a.branch_from] || 0;
    lane[a.branch_from] = l + 1;
    const ay = bp.y + bp.h + 26 + l * 29;
    const ax = Math.max(4, Math.min(W - 88, bp.x + bp.w / 2 - 42));
    altCoords[a.id] = {x: ax, y: ay, w: 84, h: 24};
    maxY = Math.max(maxY, ay + 34);
  });
  H = Math.max(H, maxY + 8);
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  svg.setAttribute('height', H);
  svg.style.height = H + 'px';
  svg.innerHTML = '';
  svg.setAttribute('aria-label', '思维分叉图：左侧是方法出现前的世界，中间是作者路径的 ' + n + ' 个动作，右侧是论文设计。');

  const defs = el('defs', {});
  const markers = [
    ['mGreen', '#31543F'], ['mGold', '#96671A'], ['mGray', '#8B877C']
  ];
  markers.forEach(function(m){
    const mk = el('marker', {
      id: m[0], viewBox: '0 0 10 10', refX: '9', refY: '5',
      markerWidth: '6', markerHeight: '6', orient: 'auto-start-reverse'
    }, defs);
    el('path', {d: 'M 0 0 L 10 5 L 0 10 z', fill: m[1]}, mk);
  });

  // 作者主路径
  connect(left, pos[0], '#31543F', 1.8, '', 'url(#mGreen)');
  for (let i = 0; i < pos.length - 1; i++){
    connect(pos[i], pos[i + 1], '#31543F', 1.8, '', 'url(#mGreen)');
  }
  if (right) connect(pos[pos.length - 1], right, '#31543F', 1.8, '', 'url(#mGreen)');

  // 备选路线
  alts.forEach(function(a){
    const bp = pos.find(function(p){ return p.b.index === a.branch_from; }) || pos[pos.length - 1];
    const c = altCoords[a.id];
    if (!bp || !c) return;
    const x1 = bp.x + bp.w / 2, y1 = bp.y + bp.h;
    const x2 = c.x + c.w / 2, y2 = c.y;
    path('M ' + x1 + ' ' + y1 + ' C ' + x1 + ' ' + (y1 + 16) + ', ' +
         x2 + ' ' + (y2 - 12) + ', ' + x2 + ' ' + y2, '#8B877C', 1.3, '4 4', 'url(#mGray)');
    const g = el('g', {tabindex: '0', role: 'button',
      'aria-label': (a.label || '备选路线') + '，点击查看为什么被放弃'});
    el('rect', {x: c.x, y: c.y, width: c.w, height: c.h, rx: 4,
      fill: '#F7F5F0', stroke: '#8B877C', 'stroke-width': 1.1, 'stroke-dasharray': '3 3'}, g);
    txt(c.x + c.w / 2, c.y + c.h / 2, a.label || '备选', {anchor: 'middle', size: 10, fill: '#4E4C45'});
    const t = el('title', {}, g);
    t.textContent = a.text || '';
    g.addEventListener('mouseenter', function(){ select('alt', alts.indexOf(a)); });
    g.addEventListener('focus', function(){ select('alt', alts.indexOf(a)); });
    g.addEventListener('click', function(){ select('alt', alts.indexOf(a)); });
    g.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); select('alt', alts.indexOf(a)); }
    });
  });

  // 节点
  function beatNode(p, i){
    const b = p.b;
    const g = el('g', {tabindex: '0', role: 'button',
      'aria-label': '第 ' + (Number(b.index) + 1) + ' 个动作：' + (b.move || '思考') + '，点击查看详情'});
    el('rect', {x: p.x, y: p.y, width: p.w, height: p.h, rx: 6,
      fill: '#FFFFFF', stroke: '#31543F', 'stroke-width': 1.2}, g);
    txt(p.x + 8, p.y + 14, String(Number(b.index) + 1).padStart(2, '0'),
      {size: 9, mono: true, fill: '#6B675D'});
    const lines = wrap(b.move || '思考', Math.max(4, Math.floor((p.w - 12) / 12)),
      p.h < 70 ? 2 : 3);
    lines.forEach(function(ln, k){
      txt(p.x + p.w / 2, p.y + (p.h < 70 ? 33 : 36) + k * 16, ln,
        {anchor: 'middle', size: p.h < 70 ? 11.5 : 12.5, weight: 600, fill: '#20201C'});
    });
    const st = statusMap[b.index];
    if (st){
      txt(p.x + p.w - 7, p.y + 14, statusLabel(st.status),
        {anchor: 'end', size: 9, weight: 700, fill: '#96671A'});
    }
    const t = el('title', {}, g);
    t.textContent = (b.move || '思考') + '：' + (b.question || '');
    g.addEventListener('mouseenter', function(){ select('beat', i); });
    g.addEventListener('focus', function(){ select('beat', i); });
    g.addEventListener('click', function(){ select('beat', i); });
    g.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); select('beat', i); }
    });
  }

  // 陷阱：短虚线 + 小三角
  pos.forEach(function(p, i){
    const b = p.b;
    if (!b.temptation) return;
    const tx = p.x + p.w - 13, ty = p.y + p.h;
    const g = el('g', {tabindex: '0', role: 'button',
      'aria-label': '第 ' + (Number(b.index) + 1) + ' 个动作最容易走错的路'});
    el('line', {x1: tx, y1: ty, x2: tx, y2: ty + 15,
      stroke: '#97382B', 'stroke-width': 1.1, 'stroke-dasharray': '3 3'}, g);
    el('path', {d: 'M ' + (tx - 4) + ' ' + (ty + 15) + ' L ' + (tx + 4) + ' ' + (ty + 15) +
      ' L ' + tx + ' ' + (ty + 22) + ' Z', fill: 'none', stroke: '#97382B', 'stroke-width': 1.1}, g);
    const t = el('title', {}, g);
    t.textContent = '最容易走错的路：' + b.temptation;
    g.addEventListener('mouseenter', function(){ select('beat', i); });
    g.addEventListener('focus', function(){ select('beat', i); });
    g.addEventListener('click', function(){ select('beat', i); });
    g.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); select('beat', i); }
    });
  });

  // 世界起点
  (function(){
    const g = el('g', {tabindex: '0', role: 'button', 'aria-label': '方法出现之前的世界，点击查看'});
    el('rect', {x: left.x, y: left.y, width: left.w, height: left.h, rx: 6,
      fill: '#F3F0E7', stroke: '#C6C1B2', 'stroke-width': 1}, g);
    const lines = wrap('方法出现前的世界', Math.max(4, Math.floor((left.w - 12) / 12)), 2);
    lines.forEach(function(ln, k){
      txt(left.x + left.w / 2, left.y + 20 + k * 15, ln,
        {anchor: 'middle', size: 11.5, weight: 600, fill: '#20201C'});
    });
    txt(left.x + left.w / 2, left.y + left.h - 12,
      (DATA.summary && DATA.summary.world_count ? DATA.summary.world_count : 0) + ' 条知识',
      {anchor: 'middle', size: 9.5, fill: '#6B675D'});
    g.addEventListener('mouseenter', function(){ select('summary', 0); });
    g.addEventListener('focus', function(){ select('summary', 0); });
    g.addEventListener('click', function(){ select('summary', 0); });
    g.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); select('summary', 0); }
    });
  })();

  pos.forEach(beatNode);

  if (right){
    const g = el('g', {tabindex: '0', role: 'button', 'aria-label': '论文设计，点击查看映射'});
    el('rect', {x: right.x, y: right.y, width: right.w, height: right.h, rx: 6,
      fill: '#E9EFE9', stroke: '#31543F', 'stroke-width': 1.2}, g);
    const lines = wrap('论文设计', Math.max(4, Math.floor((right.w - 12) / 12)), 2);
    lines.forEach(function(ln, k){
      txt(right.x + right.w / 2, right.y + 28 + k * 16, ln,
        {anchor: 'middle', size: 12, weight: 600, fill: '#31543F'});
    });
    txt(right.x + right.w / 2, right.y + right.h - 14, design.length + ' 个映射',
      {anchor: 'middle', size: 9.5, fill: '#4E4C45'});
    g.addEventListener('mouseenter', function(){ select('design', 0); });
    g.addEventListener('focus', function(){ select('design', 0); });
    g.addEventListener('click', function(){ select('design', 0); });
    g.addEventListener('keydown', function(e){
      if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); select('design', 0); }
    });
  }

  // 用户路径（仅提交后）
  if (user){
    const end = (user.diverge_at == null) ? pos.length - 1 : Math.max(0, Number(user.diverge_at));
    const pts = [{x: left.x + left.w, y: left.y + left.h / 2}];
    for (let i = 0; i <= end && i < pos.length; i++) pts.push(center(pos[i]));
    if (end >= pos.length - 1 && right) pts.push({x: right.x, y: right.y + right.h / 2});
    for (let i = 0; i < pts.length - 1; i++){
      const a = pts[i], b = pts[i + 1];
      if (Math.abs(a.y - b.y) < 1){
        path('M ' + a.x + ' ' + a.y + ' L ' + b.x + ' ' + b.y,
          '#96671A', 2.4, '', '');
      } else {
        const dx = Math.max(18, Math.abs(b.x - a.x) * 0.35);
        path('M ' + a.x + ' ' + a.y + ' C ' + (a.x + dx) + ' ' + a.y + ', ' +
             (b.x - dx) + ' ' + b.y + ', ' + b.x + ' ' + b.y, '#96671A', 2.4, '', '');
      }
    }
    if (user.diverge_at != null && pos[end]){
      const bp = pos[end], c = center(bp);
      if (String(user.diverge_to || '').indexOf('alt-') === 0 && altCoords[user.diverge_to]){
        const a = altCoords[user.diverge_to];
        path('M ' + c.x + ' ' + (bp.y + bp.h) + ' C ' + c.x + ' ' + (bp.y + bp.h + 18) + ', ' +
             (a.x + a.w / 2) + ' ' + (a.y - 14) + ', ' + (a.x + a.w / 2) + ' ' + a.y,
          '#96671A', 2.2, '5 4', 'url(#mGold)');
        el('rect', {x: a.x - 2, y: a.y - 2, width: a.w + 4, height: a.h + 4, rx: 6,
          fill: 'none', stroke: '#96671A', 'stroke-width': 2});
      } else if (user.diverge_to === 'novel'){
        const nx = Math.max(4, Math.min(W - 100, c.x - 48));
        const ny = bp.y + bp.h + 30;
        const g = el('g', {tabindex: '0', role: 'button', 'aria-label': '你的新路线'});
        path('M ' + c.x + ' ' + (bp.y + bp.h) + ' C ' + c.x + ' ' + (bp.y + bp.h + 14) + ', ' +
             (nx + 48) + ' ' + (ny - 12) + ', ' + (nx + 48) + ' ' + ny,
          '#96671A', 2.2, '5 4', 'url(#mGold)');
        el('rect', {x: nx, y: ny, width: 96, height: 26, rx: 5,
          fill: '#FBF4E6', stroke: '#96671A', 'stroke-width': 1.6, 'stroke-dasharray': '4 3'}, g);
        txt(nx + 48, ny + 13, '你的新路线', {anchor: 'middle', size: 10.5, weight: 600, fill: '#96671A'});
        g.addEventListener('click', function(){ select('novel', 0); });
        g.addEventListener('focus', function(){ select('novel', 0); });
        g.addEventListener('keydown', function(e){
          if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); select('novel', 0); }
        });
        maxY = Math.max(maxY, ny + 34);
      }
    }
    // 命中 / 部分 / 未中 外圈
    (user.beats || []).forEach(function(st){
      const p = pos.find(function(x){ return x.b.index === st.index; });
      if (!p) return;
      const ring = el('rect', {
        x: p.x - 5, y: p.y - 5, width: p.w + 10, height: p.h + 10, rx: 9,
        fill: 'none', stroke: '#96671A',
        'stroke-width': st.status === 'miss' ? 1.2 : 2.6,
        opacity: st.status === 'miss' ? 0.62 : 0.95
      });
      if (st.status === 'partial') ring.setAttribute('stroke-dasharray', '15 9');
      if (st.status === 'miss') ring.setAttribute('stroke-dasharray', '2 6');
      txt(p.x + p.w / 2, p.y - 9, statusLabel(st.status),
        {anchor: 'middle', size: 9, weight: 700, fill: '#96671A'});
    });
  }

  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  svg.setAttribute('height', H);
  svg.style.height = H + 'px';
  renderNote();
  setTimeout(function(){ if (window.__vzFit) window.__vzFit(); }, 30);
}
render();
window.addEventListener('resize', function(){ setTimeout(render, 40); });
setTimeout(function(){ if (window.__vzFit) window.__vzFit(); }, 120);
})();
</script>
"""
    body = body.replace("__DATA__", data_json)
    _vz_frame(body, 700)
    if user:
        st.markdown(
            f'<div class="viz-concl" style="margin:5px 0 2px">'
            f'<b>近似对照</b>：{_vz_esc(user.get("summary") or "")}</div>',
            unsafe_allow_html=True,
        )

    rows = []
    status_map = {x.get("index"): x for x in ((user or {}).get("beats") or [])}
    for b in beats:
        ust = status_map.get(b.get("index"))
        rows.append([
            f'{int(b.get("index")) + 1:02d} {b.get("move") or ""}',
            b.get("known") or "", b.get("question") or "",
            b.get("leap") or "", b.get("temptation") or "",
            status_label(ust.get("status")) if ust else "—",
            (ust or {}).get("evidence") or "—",
        ])
    alt_rows = [[a.get("label") or "", f'第 {int(a.get("branch_from", 0)) + 1} 个动作',
                 a.get("reason_dropped") or "", a.get("text") or ""] for a in alts]
    design_rows = [[d.get("beat") or "", d.get("design") or "", d.get("comment") or ""]
                   for d in design]
    extra_html = ""
    if alt_rows:
        extra_html += '<div class="sub">备选路线</div>' + _vz_table_html(
            ["备选", "分叉点", "为什么放弃", "完整说明"], alt_rows
        )
    if design_rows:
        extra_html += '<div class="sub">推演 ↔ 论文设计</div>' + _vz_table_html(
            ["推演节拍", "论文设计", "判断"], design_rows
        )
    _vz_details(["动作", "当时已知", "自然疑问", "直觉跳跃", "最容易走错的路", "你的状态", "你的原话"],
                rows, "查看分叉图数据", extra_html)


def _vz_table_html(headers, rows):
    head = "".join(f"<th>{_vz_esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{_vz_esc(c)}</td>" for c in r) + "</tr>"
                   for r in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def status_label(value):
    return {"hit": "命中", "partial": "部分", "miss": "未中"}.get(str(value or ""), "")


def viz_argument_map(viz):
    """P1-3 论证结构图。入参：viz['argument'] 或整个 viz dict。"""
    arg = viz.get("argument") if isinstance(viz, dict) and "argument" in viz else (viz or {})
    claims = arg.get("claims") or []
    assumptions = arg.get("assumptions") or []
    counters = arg.get("counterexamples") or []
    if not claims:
        st.caption("第 7 步尚未生成，暂时没有论证结构图。")
        return

    attacked = sum(1 for c in claims if c.get("attacks"))
    concl = (f"<b>{len(claims)}</b> 条主张中，<b>{attacked}</b> 条被具体的脆弱假设或反例攻击。"
             "红色断裂线表示这条主张的证据链最容易被推翻。")
    if arg.get("fragile"):
        concl += f' 最脆弱的一条：{_vz_esc(_vz_clip(arg["fragile"], 100))}'
    _vz_head("ARGUMENT MAP · STEP 07 / 09 / 11", "论证结构图：主张、实验与红队攻击", concl)

    def card(kind, kicker, title, body):
        return (f'<div class="am-card {kind}"><div class="am-k">{_vz_esc(kicker)}</div>'
                f'<div class="am-t">{_vz_esc(_vz_clip(title, 120))}</div>'
                f'<div class="am-v">{_vz_esc(_vz_clip(body, 150))}</div></div>')

    rows = []
    for c in claims:
        attack_cards = ""
        for a in c.get("attacks") or []:
            attack_cards += card("attack", f'{a.get("kind") or "攻击"} · {a.get("id") or ""}',
                                 a.get("title") or "", a.get("detail") or "")
        if not attack_cards:
            attack_cards = card("empty", "红队攻击", "未匹配到具体攻击",
                                "先完成第 9 / 11 步，或该主张没有对应的假设/反例。")
        rows.append(
            '<div class="am-row">'
            + card("claim", "主张", c.get("question") or "",
                   "答案：" + (c.get("answer") or "—"))
            + '<div class="am-link"><span class="ln"></span><span class="ar">›</span></div>'
            + card("exp", "支撑实验", "实验设计", c.get("support") or "—")
            + '<div class="am-link broken"><span class="ln"></span><span class="ar">›</span></div>'
            + '<div class="am-attacks">' + attack_cards + '</div>'
            + '</div>'
        )

    body = r"""
<style>
.am-head{display:grid;grid-template-columns:1.12fr 30px 1fr 30px 1fr;gap:0;
  font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;color:var(--accent2);
  text-transform:uppercase;margin:0 0 5px;padding:0 2px;}
.am-head span:nth-child(2),.am-head span:nth-child(4){text-align:center;}
.am-row{display:grid;grid-template-columns:1.12fr 30px 1fr 30px 1fr;align-items:stretch;
  margin:0 0 9px;}
.am-card{border:1px solid var(--rule);background:#fff;border-radius:5px;padding:9px 10px;
  min-width:0;}
.am-card.claim{border-left:3px solid var(--accent);}
.am-card.exp{border-left:3px solid var(--accent2);}
.am-card.attack{border-left:3px solid var(--danger);background:#FBF3F1;margin-bottom:5px;}
.am-card.empty{border-left:3px solid var(--rule2);background:#FAF8F3;}
.am-attacks{min-width:0;}
.am-k{font-family:var(--mono);font-size:9px;letter-spacing:.1em;color:var(--ink3);
  text-transform:uppercase;margin-bottom:3px;}
.am-t{font-family:var(--sans);font-size:11.5px;font-weight:650;line-height:1.5;color:var(--ink);}
.am-v{font-family:var(--sans);font-size:10.8px;line-height:1.55;color:var(--ink2);margin-top:3px;}
.am-link{position:relative;display:flex;align-items:center;justify-content:center;min-width:0;}
.am-link .ln{width:100%;border-top:1px solid var(--rule2);}
.am-link .ar{position:absolute;right:1px;color:var(--ink3);font-size:14px;line-height:1;}
.am-link.broken .ln{border-top:1.6px dashed var(--danger);}
.am-link.broken .ar{color:var(--danger);}
.am-link.broken::after{content:"";position:absolute;left:50%;top:50%;width:2px;height:12px;
  background:var(--danger);transform:translate(-50%,-50%) rotate(24deg);}
@media (max-width:820px){
  .am-head{display:none;}
  .am-row{grid-template-columns:1fr;gap:0;}
  .am-link{height:17px;}
  .am-link .ln{width:1px;height:17px;border-top:none;border-left:1px solid var(--rule2);}
  .am-link .ar{right:auto;bottom:-2px;transform:rotate(90deg);}
  .am-link.broken .ln{border-left:1.6px dashed var(--danger);border-top:none;}
  .am-link.broken::after{width:12px;height:2px;transform:translate(-50%,-50%) rotate(-24deg);}
  .am-card.attack{margin:0 0 4px;}
}
</style>
<div class="am-wrap">
  <div class="am-head"><span>主张 · 来自问题 → 答案</span><span></span>
    <span>支撑实验</span><span></span><span>红队攻击 · 最脆弱假设 / 反例</span></div>
  __ROWS__
</div>
"""
    body = body.replace("__ROWS__", "".join(rows))
    _vz_static(body)

    claim_rows = []
    for c in claims:
        atk = "；".join(f'{a.get("kind")} {a.get("id")}：{a.get("title")}'
                        for a in (c.get("attacks") or [])) or "—"
        claim_rows.append([c.get("question") or "", c.get("answer") or "",
                           c.get("support") or "", atk])
    extra_html = ""
    if assumptions:
        extra_html += '<div class="sub">脆弱假设（Q9）</div>' + _vz_table_html(
            ["编号", "假设", "若不成立", "严重程度", "被打破的容易度"],
            [[a.get("id"), a.get("title"), _vz_clip(a.get("body"), 260),
              a.get("severity"), a.get("fragility")] for a in assumptions],
        )
    if counters:
        extra_html += '<div class="sub">反例方案（Q11）</div>' + _vz_table_html(
            ["编号", "方案", "攻击的假设", "预期失败模式", "成本"],
            [[c.get("id"), c.get("title"), c.get("attack"), c.get("failure"), c.get("cost")]
             for c in counters],
        )
    _vz_details(["提出的问题", "答案与边界", "支撑实验", "红队攻击"],
                claim_rows, "查看论证结构数据", extra_html)


def viz_timeline(viz):
    """P1-4 前史时间线。入参：viz['timeline'] 或整个 viz dict。"""
    tl = viz.get("timeline") if isinstance(viz, dict) and "timeline" in viz else (viz or {})
    items = list(tl.get("items") or [])
    undated = list(tl.get("undated") or [])
    paper = tl.get("paper") or {}
    if not items and not undated:
        st.caption("阶段一尚未生成，暂时没有前史时间线。")
        return

    if items:
        concl = (f"world_before 共 <b>{len(items) + len(undated)}</b> 条："
                 f"<b>{len(items)}</b> 条有可追溯年份，按时间排到本文；"
                 f"<b>{len(undated)}</b> 条没有年份，放在下方背景常识，不推测年代。")
    else:
        concl = (f"world_before 共 <b>{len(undated)}</b> 条，但都没有可追溯的年份；"
                 "它们放在下方背景常识，时间轴只保留本文节点。不推测年代。")
    _vz_head("PRE-HISTORY TIMELINE · STEP 01", "前史时间线", concl)

    paper_year = paper.get("year")
    paper_label = f"本文 · {paper_year}" if paper_year else "本文 · 年份未识别"

    def _year(value):
        return str(value) if value not in (None, "") else "—"

    dated_nodes = "".join(
        f'<div class="tl-item">'
        f'<div class="tl-year">{_vz_esc(_year(x.get("year")))}</div>'
        f'<div class="tl-rail"><span class="tl-dot"></span></div>'
        f'<div class="tl-card"><div class="tl-fact">{_vz_esc(x.get("fact") or "")}</div>'
        f'<div class="tl-src">{_vz_esc(x.get("source") or "")}</div></div></div>'
        for x in items
    )
    if not items:
        dated_nodes = (
            '<div class="tl-item pre"><div class="tl-year">年代未标注</div>'
            '<div class="tl-rail"><span class="tl-dot"></span></div>'
            '<div class="tl-card"><div class="tl-fact">world_before 里的前史条目没有可追溯年份，'
            '不推测年代；它们放在下方「背景常识」。</div></div></div>'
        )
    dated_nodes += (
        f'<div class="tl-item paper"><div class="tl-year">{_vz_esc(paper_label)}</div>'
        f'<div class="tl-rail"><span class="tl-dot"></span></div>'
        f'<div class="tl-card"><div class="tl-fact">'
        f'{_vz_esc(paper.get("title") or "本文")}</div>'
        f'<div class="tl-src">论文元数据</div></div></div>'
    )

    bg_cards = "".join(
        f'<div class="tl-bg"><div class="tl-bg-k">{_vz_esc(x.get("kind") or "背景")}</div>'
        f'<div class="tl-bg-fact">{_vz_esc(x.get("fact") or "")}</div>'
        f'<div class="tl-bg-src">{_vz_esc(x.get("source") or "")}</div></div>'
        for x in undated
    )
    background = (
        f'<div class="tl-bg-wrap"><div class="tl-bg-head">背景常识 · 无年份'
        f'<span>{len(undated)} 条 · 不推测年代</span></div>'
        f'<div class="tl-grid">{bg_cards}</div></div>'
    ) if undated else ""

    body = r"""
<style>
.tl-wrap{min-width:0;}
.tl-track{position:relative;margin-top:2px;}
.tl-track::before{content:"";position:absolute;left:86px;top:10px;bottom:10px;width:1px;
  background:var(--rule2);}
.tl-item{display:grid;grid-template-columns:76px 20px minmax(0,1fr);gap:8px;padding:6px 0;}
.tl-year{text-align:right;font-family:var(--mono);font-size:10px;line-height:1.45;
  color:var(--ink2);padding-top:4px;overflow-wrap:anywhere;}
.tl-rail{position:relative;display:flex;justify-content:center;padding-top:7px;}
.tl-dot{width:9px;height:9px;border-radius:50%;background:#fff;border:2px solid var(--accent);
  position:relative;z-index:1;}
.tl-card{border:1px solid var(--rule);background:#fff;border-radius:6px;padding:8px 10px;
  min-width:0;}
.tl-fact{font-family:var(--sans);font-size:11.5px;line-height:1.65;color:var(--ink2);
  overflow-wrap:anywhere;}
.tl-src{font-family:var(--mono);font-size:9px;line-height:1.4;color:var(--ink3);margin-top:4px;}
.tl-item.paper .tl-dot{background:var(--accent);}
.tl-item.paper .tl-year{color:var(--accent);font-weight:600;}
.tl-item.paper .tl-card{background:var(--accent-wash);border-color:rgba(49,84,63,.25);}
.tl-item.paper .tl-fact{color:var(--ink);font-weight:600;}
.tl-item.pre .tl-dot{border-color:#8B877C;border-style:dashed;background:#F7F5F0;}
.tl-item.pre .tl-year{color:var(--ink3);}
.tl-bg-wrap{margin-top:14px;border-top:1px solid var(--rule);padding-top:12px;}
.tl-bg-head{display:flex;align-items:baseline;justify-content:space-between;gap:12px;
  font-family:var(--mono);font-size:9.5px;letter-spacing:.1em;color:var(--accent2);
  text-transform:uppercase;}
.tl-bg-head span{font-family:var(--sans);font-size:10px;letter-spacing:0;color:var(--ink3);
  text-transform:none;}
.tl-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:8px;
  margin-top:8px;}
.tl-bg{background:#F3F0E7;border:1px solid var(--rule);border-radius:5px;padding:8px 10px;
  min-width:0;}
.tl-bg-k{font-family:var(--mono);font-size:8.5px;letter-spacing:.08em;color:var(--ink3);
  text-transform:uppercase;margin-bottom:3px;}
.tl-bg-fact{font-family:var(--sans);font-size:11px;line-height:1.6;color:var(--ink2);
  overflow-wrap:anywhere;}
.tl-bg-src{font-family:var(--mono);font-size:8.5px;color:var(--ink3);margin-top:3px;}
@media(max-width:700px){
  .tl-track::before{left:64px;}
  .tl-item{grid-template-columns:56px 16px minmax(0,1fr);gap:6px;}
  .tl-year{font-size:9px;}
  .tl-bg-head{flex-direction:column;gap:2px;}
  .tl-grid{grid-template-columns:1fr;}
}
</style>
<div class="tl-wrap">
  <div class="tl-track">__NODES__</div>
  __BACKGROUND__
</div>
"""
    body = body.replace("__NODES__", dated_nodes).replace("__BACKGROUND__", background)
    _vz_static(body)

    dated_rows = [[str(x.get("year")), x.get("kind") or "", x.get("fact") or "",
                   x.get("source") or ""] for x in items]
    undated_rows = [[x.get("kind") or "", x.get("fact") or "", x.get("source") or ""]
                    for x in undated]
    extra = ""
    if undated_rows:
        extra = '<div class="sub">背景常识（无年份）</div>' + _vz_table_html(
            ["类型", "事实", "来源"], undated_rows)
    _vz_details(["年份", "类型", "事实", "来源"], dated_rows,
                "查看前史时间线数据", extra)


# 可视化预览页已下线：正式页面直接使用真实论文的预生成数据。


# ════════════════════════════════════════════
#  开屏页（Landing）
# ════════════════════════════════════════════
LANDING_CSS = """
<style>
.lp{ max-width:1120px; margin:0 auto; padding:6px 0 44px; }

/* 顶栏 */
.lp-top{
  display:flex; align-items:center; justify-content:space-between;
  padding-bottom:15px; border-bottom:1px solid var(--lr-rule-2);
}
.lp-logo{
  display:flex; align-items:center; gap:9px;
  font-family:var(--lr-serif); font-size:1.16rem; font-weight:700; color:var(--lr-ink);
}
.lp-logo img{ height:36px; width:auto; display:block; }
.lp-logo .lr-i{ color:var(--lr-accent); }
.lp-top-r{
  font-family:var(--lr-sans); font-size:.7rem; font-weight:600;
  letter-spacing:.17em; text-transform:uppercase; color:var(--lr-ink-3);
}

/* Hero */
.lp-hero{
  display:grid; grid-template-columns:1.08fr .92fr; gap:58px;
  align-items:center; padding:58px 0 50px;
}
.lp-kicker{
  font-family:var(--lr-sans); font-size:.72rem; font-weight:600;
  letter-spacing:.22em; text-transform:uppercase; color:var(--lr-accent);
  display:flex; align-items:center; gap:10px;
}
.lp-kicker::after{ content:""; height:1px; width:56px; background:var(--lr-rule-2); }
.lp-h1{
  font-family:var(--lr-serif); font-size:3.45rem; font-weight:700;
  line-height:1.12; letter-spacing:-.022em; margin:16px 0 0; color:var(--lr-ink);
}
.lp-p{
  font-family:var(--lr-sans); font-size:1rem; line-height:1.88;
  color:var(--lr-ink-2); margin-top:20px; max-width:520px;
}
.lp-cta{ display:flex; gap:11px; margin-top:30px; flex-wrap:wrap; }
.lp-btn{
  display:inline-flex; align-items:center; justify-content:center;
  font-family:var(--lr-sans); font-size:.9rem; font-weight:600; letter-spacing:.015em;
  padding:.78rem 1.5rem; border-radius:var(--lr-r1);
  text-decoration:none !important; cursor:pointer;
  transition:background var(--lr-t1) var(--lr-ease), color var(--lr-t1) var(--lr-ease),
             border-color var(--lr-t1) var(--lr-ease), transform var(--lr-t1) var(--lr-ease);
}
.lp-primary{
  background:var(--lr-accent) !important; color:#FFFFFF !important;
  border:1px solid var(--lr-accent);
}
.lp-primary:hover{ background:#26452F !important; color:#FFFFFF !important; transform:translateY(-1px); }
.lp-ghost{
  background:#FFFFFF !important; color:var(--lr-ink) !important;
  border:1px solid var(--lr-rule-2);
}
.lp-ghost:hover{ background:var(--lr-paper-2) !important; border-color:var(--lr-ink-3); transform:translateY(-1px); }
.lp-fine{
  font-family:var(--lr-sans); font-size:.775rem; color:var(--lr-ink-3);
  letter-spacing:.035em; margin-top:18px;
}

/* 纸卡预览 */
.lp-visual{ position:relative; padding:6px; }
.lp-visual::before{
  content:""; position:absolute; inset:14px -6px -6px 14px;
  background:#FFFFFF; border:1px solid var(--lr-rule);
  border-radius:2px; transform:rotate(1.4deg);
}
.lp-sheet{
  position:relative; background:#FFFFFF; border:1px solid var(--lr-rule-2);
  border-radius:2px; padding:24px 22px 22px;
  box-shadow:0 20px 44px -26px rgba(32,32,28,.42);
  transform:rotate(-1.1deg);
  transition:transform var(--lr-t2) var(--lr-ease);
}
.lp-visual:hover .lp-sheet{ transform:rotate(0deg) translateY(-3px); }
.lp-sheet-head{
  display:flex; justify-content:space-between;
  font-family:var(--lr-mono); font-size:.66rem; font-weight:600;
  letter-spacing:.16em; text-transform:uppercase; color:var(--lr-accent);
  padding-bottom:11px; border-bottom:1px solid var(--lr-rule);
}
.lp-sheet-title{
  font-family:var(--lr-serif); font-size:1.06rem; font-weight:700;
  color:var(--lr-ink); margin-top:14px; line-height:1.4;
}
.lp-sheet-meta{
  font-family:var(--lr-sans); font-size:.735rem; color:var(--lr-ink-3);
  margin-top:5px; letter-spacing:.02em;
}
.lp-sheet-k{
  font-family:var(--lr-sans); font-size:.665rem; font-weight:700;
  letter-spacing:.14em; text-transform:uppercase; color:var(--lr-accent);
  margin-top:16px;
}
.lp-sheet-p{
  font-family:var(--lr-sans); font-size:.8rem; line-height:1.72;
  color:var(--lr-ink-2); margin:5px 0 0;
}
.lp-line{
  display:block; height:5px; border-radius:3px;
  background:var(--lr-paper-2); margin-top:7px;
}
.lp-badge-q{
  position:absolute; right:-20px; bottom:34px; left:auto;
  font-family:var(--lr-sans); font-size:.7rem; font-weight:600;
  letter-spacing:.06em; color:var(--lr-accent);
  background:var(--lr-paper); border:1px solid var(--lr-rule-2);
  padding:6px 12px; border-radius:999px; box-shadow:var(--lr-sh1);
}

/* 能力清单 */
.lp-feats{
  display:grid; grid-template-columns:repeat(4,1fr); gap:1px;
  background:var(--lr-rule); border:1px solid var(--lr-rule);
}
.lp-feat{
  background:var(--lr-paper); padding:15px 16px;
  display:flex; align-items:baseline; gap:10px;
  transition:background var(--lr-t1) var(--lr-ease);
}
.lp-feat:hover{ background:#FFFFFF; }
.lp-feat b{
  font-family:var(--lr-mono); font-size:.68rem; font-weight:600;
  color:var(--lr-accent); letter-spacing:.05em;
}
.lp-feat span{
  font-family:var(--lr-sans); font-size:.845rem; color:var(--lr-ink-2);
}

/* 页脚 */
.lp-foot{
  display:flex; justify-content:space-between; align-items:center;
  gap:14px; flex-wrap:wrap;
  padding-top:18px; margin-top:22px; border-top:1px solid var(--lr-rule);
  font-family:var(--lr-sans); font-size:.735rem; color:var(--lr-ink-3);
  letter-spacing:.03em;
}
.lp-foot a{ color:var(--lr-ink-2) !important; text-decoration:none !important; border-bottom:1px solid var(--lr-rule-2); }
.lp-foot a:hover{ color:var(--lr-accent) !important; border-color:var(--lr-accent); }

/* 入场 */
@keyframes lpIn{ from{opacity:0; transform:translateY(14px);} to{opacity:1; transform:none;} }
.lp-a1{ animation:lpIn .6s var(--lr-ease) both; }
.lp-a2{ animation:lpIn .6s var(--lr-ease) .09s both; }
.lp-a3{ animation:lpIn .6s var(--lr-ease) .18s both; }
.lp-a4{ animation:lpIn .6s var(--lr-ease) .27s both; }

/* 移动端 */
@media (max-width:1024px){
  .lp-feats{ grid-template-columns:1fr 1fr; }
  .feature-grid{ grid-template-columns:repeat(2,1fr); }
}
@media (max-width:860px){
  .lp-hero{ grid-template-columns:1fr; gap:38px; padding:34px 0 32px; }
  .lp-h1{ font-size:2.4rem; }
  .lp-p{ font-size:.945rem; max-width:100%; }
  .lp-sheet{ transform:none; }
  .lp-visual::before{ display:none; }
  .lp-badge-q{ left:auto; right:8px; bottom:-12px; }
  .lp-feats{ grid-template-columns:1fr 1fr; }
  .lp-top-r{ display:none; }
}
@media (max-width:520px){
  .lp{ padding-bottom:26px; }
  .lp-h1{ font-size:1.98rem; }
  .lp-cta{ flex-direction:column; gap:9px; }
  .lp-btn{ width:100%; }
  .lp-sheet{ padding:20px 17px 18px; }
  .lp-feats{ grid-template-columns:1fr; }
  .lp-foot{ flex-direction:column; align-items:flex-start; }
}
@media (prefers-reduced-motion:reduce){
  .lr-anim,.lr-d1,.lr-d2,.lr-d3{ animation:none; }
  .lp-a1,.lp-a2,.lp-a3,.lp-a4{ animation:none; }
}
</style>
"""


def render_landing():
    st.markdown(LANDING_CSS, unsafe_allow_html=True)

    feats = [
        ("01", "背景与前史"), ("02", "作者路径推演"), ("03", "方法拆解"), ("04", "数学推导"),
        ("05", "实验证据"), ("06", "红队审稿"), ("07", "反例设计"), ("08", "Follow-up idea"),
    ]
    feat_html = "".join(
        f'<div class="lp-feat"><b>{n}</b><span>{name}</span></div>' for n, name in feats
    )

    st.markdown(
        '<div class="lp">'
        '<div class="lp-top">'
        f'<div class="lp-logo"><img src="{LOGO_URI}" alt="LitRead"></div>'
        '<div class="lp-top-r">AI 研究思维训练工作台 · Hackathon 2026</div>'
        '</div>'

        '<div class="lp-hero">'
        '<div class="lp-lead lp-a1">'
        '<div class="lp-kicker">为研究者做的思维训练</div>'
        '<h1 class="lp-h1">像作者一样思考，<br/>再超越作者。</h1>'
        '<p class="lp-p">上传一篇论文，不是得到一份摘要，而是走完 12 步研究动作：先建立背景，'
        '只凭方法出现前的知识推演作者怎么想到 idea；再拆解方法与数学、审视实验证据、'
        '做红队攻击、设计反例，最后提出自己的 follow-up。第 3 步是核心——你先写，再对照 AI 的重建。</p>'
        '<div class="lp-cta">'
        '<a class="lp-btn lp-primary" href="?enter=1" target="_top">进入工作台</a>'
        '<a class="lp-btn lp-ghost" href="?enter=1&mode=demo" target="_top">先看演示</a>'
        '</div>'
        '<div class="lp-fine">12 步研究流 · 作者路径推演 · 红队审稿 · 不保存你的 API Key</div>'
        '</div>'

        '<div class="lp-visual lp-a2">'
        '<div class="lp-sheet">'
        '<div class="lp-sheet-head"><span>Research Path</span><span>Step 03</span></div>'
        '<div class="lp-sheet-title">作者是怎么想到这个 idea 的？</div>'
        '<div class="lp-sheet-meta">只使用方法出现前的知识 · 逆向推演</div>'
        '<div class="lp-sheet-k">当时已知</div>'
        '<p class="lp-sheet-p">负样本一直被当作等价处理，但关系语义其实各不相同。</p>'
        '<div class="lp-sheet-k">直觉跳跃</div>'
        '<i class="lp-line" style="width:93%"></i>'
        '<i class="lp-line" style="width:81%"></i>'
        '<i class="lp-line" style="width:66%"></i>'
        '<div class="lp-sheet-k">最容易走错的路</div>'
        '<i class="lp-line" style="width:74%"></i>'
        '</div>'
        '<div class="lp-badge-q">你先推演，再看 AI 的重建</div>'
        '</div>'
        '</div>'

        f'<div class="lp-feats lp-a3">{feat_html}</div>'

        '<div class="lp-foot lp-a4">'
        '<span>LitRead · 研究思维训练工作台 · FastAPI + Streamlit · 数据留在你的服务器上</span>'
        '<a href="?enter=1&mode=demo" target="_top">直接体验 Demo →</a>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# 开屏页拦截：未点击「进入」前只显示 Landing（Demo 链接直达工作台）
if _qs("enter") in ("1", "true") or _qs("mode") == "demo":
    st.session_state["_entered"] = True

if not st.session_state.get("_entered"):
    render_landing()
    st.stop()

if "_viz_session" not in st.session_state:
    st.session_state["_viz_session"] = uuid.uuid4().hex[:16]


# ── 侧栏 ──
with st.sidebar:
    _brand_mark = (f'<img src="{LOGO_MARK_URI}" width="30" height="30" alt="" '
                   'style="display:block;flex:0 0 auto;">' if LOGO_MARK_URI else icon('book', 27, 1.6))
    st.markdown(
        f"""<div class="lr-brand">
        {_brand_mark}
        <div>
            <div class="lr-brand-name">LitRead</div>
            <div class="lr-brand-sub">{t('tagline')}</div>
        </div>
    </div>""",
        unsafe_allow_html=True,
    )
    st.markdown('<div style="border-top:1px solid var(--lr-rule); margin:14px 0;"></div>', unsafe_allow_html=True)

    health = api_get("/api/health") or {}
    if health.get("demo_mode"):
        st.caption(f"{icon('sparkles', 12)} {t('status_demo')}", unsafe_allow_html=True)
    elif health.get("llm_ready"):
        st.caption(f"{icon('shield', 12)} {t('status_llm')}", unsafe_allow_html=True)

    stats = api_get("/api/library/stats") or {}
    st.markdown(
        f"""<div style="font-family:var(--lr-serif); font-size:1.02rem; color:var(--lr-ink); margin:6px 0 2px;">
        {t('stat_line', papers=f"<b>{stats.get('papers', 0)}</b>", vecs=f"<b>{stats.get('vectors', 0)}</b>")}
    </div>""",
        unsafe_allow_html=True,
    )

    quota = api_get("/api/rate-status") or {}
    used, cap = quota.get("used", 0), quota.get("quota", 30)
    if cap:
        pct = min(used / cap * 100, 100)
        warn = " warn" if used >= cap else ""
        st.markdown(
            f"""<div class="quota-compact">
            <span>{t('quota_line', used=used, quota=cap)}</span>
            <span class="bar"><span class="bar-fill{warn}" style="width:{pct}%"></span></span>
        </div>""",
            unsafe_allow_html=True,
        )

    _growth = api_get(f"/api/research/growth?session_id={st.session_state['_viz_session']}") or {}
    if _growth.get("scores"):
        viz_growth_sparkline(_growth)

    st.markdown('<div style="border-top:1px solid var(--lr-rule); margin:16px 0;"></div>', unsafe_allow_html=True)

    has_user_key = bool(st.session_state.get("_user_key"))
    with st.expander(f"API Key{' · 已设置' if has_user_key else ''}", expanded=False):
        if has_user_key:
            st.success(t("apikey_ok"))
            if st.button(t("apikey_clear")):
                del st.session_state["_user_key"]
                st.rerun()
        else:
            st.caption(t("apikey_hint"))
            key = st.text_input(t("apikey_title"), type="password",
                                placeholder=t("apikey_ph"),
                                label_visibility="collapsed",
                                key="key_input")
            if key and st.button(t("apikey_verify"), type="primary"):
                ok, err = verify_key(key)
                if ok:
                    st.session_state["_user_key"] = key.strip()
                    st.success(t("msg_key_ok"))
                    st.rerun()
                else:
                    st.error(f"{t('msg_key_bad')}：{err}")

    st.markdown('<div style="border-top:1px solid var(--lr-rule); margin:16px 0;"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="lr-side-label">{t("nav_title")}</div>', unsafe_allow_html=True)
    st.caption(t("nav_line"))

    st.markdown(
        '<div style="margin-top:16px; padding:10px 11px; background:#F3F0E7; '
        'border:1px solid var(--lr-rule); border-left:2px solid var(--lr-accent-2); '
        'border-radius:4px;">'
        '<div style="font-family:var(--lr-mono); font-size:8.5px; letter-spacing:.08em; '
        'color:var(--lr-ink-4); text-transform:uppercase;">Reviewer view · 开发中</div>'
        '<div style="font-family:var(--lr-sans); font-size:.72rem; line-height:1.65; '
        'color:var(--lr-ink-2); margin-top:4px;">'
        '同一套 12 步也适用于审稿：判断这篇论文的主张是否成立、证据是否足够、值不值得入选。'
        '后续会在这里增加切换按钮：<b>学习论文思路</b> / <b>评审视角</b>。'
        '</div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="margin-top:16px; padding-top:14px; border-top:1px solid var(--lr-rule);">'
        '<a href="/" target="_top" style="font-family:var(--lr-sans); font-size:.755rem; '
        'color:var(--lr-ink-3) !important; text-decoration:none; '
        'border-bottom:1px solid var(--lr-rule-2);">返回首页</a>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── 主入口 ──
def main():
    demo = is_demo_mode()

    # Hero
    logo_html = (f'<img class="lr-logo" src="{LOGO_URI}" alt="LitRead">'
                 if LOGO_URI else '<div class="lr-title">LitRead</div>')
    st.markdown(
        f"""<div class="lr-hero lr-anim">
        <div class="lr-eyebrow">AI Reading Workbench</div>
        {logo_html}
        <div class="lr-sub">{t('hero_sub')}</div>
    </div>""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="lr-hero-rule"></div>', unsafe_allow_html=True)

    if demo:
        st.markdown(
            f'<div class="lr-badge lr-anim lr-d1">{icon("sparkles", 13)} {t("demo_badge")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # 连续导航（替代割裂的 tabs）
    page = nav_bar()
    st.markdown('<div class="lr-hero-rule" style="margin:0 0 18px;"></div>', unsafe_allow_html=True)

    def get_papers_or_warn():
        papers = fetch_papers()
        if not papers:
            st.info(t("empty_lib"))
        return papers

    def sec(title, ic="layers"):
        st.markdown(f'<div class="lr-section">{icon(ic, 17)} {title}</div>', unsafe_allow_html=True)

    # ════════════════════════════════════════
    #  12 步研究工作流
    # ════════════════════════════════════════
    TAG_LABEL = {
        "paper": "论文依据", "external": "外部背景",
        "inference": "模型推演", "mixed": "事实 + 推演",
    }
    PHASES = [
        ("context", "背景与前史", "01–02"),
        ("author", "作者路径", "03"),
        ("method", "方法与数学", "04–06"),
        ("evidence", "实验证据", "07–08"),
        ("critique", "红队审稿", "09–11"),
        ("idea", "我的 idea", "12"),
    ]

    def step_card(num, title, tag, data, beats=False, basis_kind=None):
        data = data or {}
        kind = basis_kind
        if kind not in ("paper", "external", "inference", "mixed"):
            text = " ".join(str(x) for x in (data.get("basis") or []))
            if any(k in text for k in ("论文", "§", "Abstract", "Method", "Experiments", "Related Work")):
                has_infer = any(k in text for k in ("推演", "推测", "模型知识", "未核验"))
                kind = "mixed" if has_infer else "paper"
            elif any(k in text for k in ("推演", "推测", "模型知识", "未核验")):
                kind = "inference"
            elif any(k in text for k in ("领域背景", "领域常识", "背景知识")):
                kind = "external"
            else:
                kind = tag if tag in ("paper", "external", "inference", "mixed") else None
        bar = ""
        if kind:
            bar = (f'<span class="rf-basisbar b-{kind}" title="本步依据：'
                   f'{_KIND_LABEL.get(kind, kind)}"></span>')
        with st.container(border=True):
            st.markdown(
                f'<div class="rf-head"><span class="rf-num">{num:02d}</span>'
                f'<span class="rf-title">{title}</span>{bar}'
                f'<span class="rf-tag {tag}">{TAG_LABEL.get(tag, "")}</span></div>',
                unsafe_allow_html=True,
            )
            content = data.get("content") or ""
            lede, body = split_lede(content)
            if lede:
                st.markdown(
                    f'<div class="rf-summary">{html_lib.escape(lede)}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(body)
            else:
                st.markdown(content or "_（本步未生成内容）_")
            if beats:
                rows = []
                for i, b in enumerate(data.get("beats", []), 1):
                    rows.append(
                        f'<div class="rf-beat"><span class="bm">{i:02d} · '
                        f'{html_lib.escape(str(b.get("move", "思考")))}</span>'
                        f'<div class="bl">当时已知</div><div class="bv">{html_lib.escape(str(b.get("known", "")))}</div>'
                        f'<div class="bl">自然产生的疑问</div><div class="bv">{html_lib.escape(str(b.get("question", "")))}</div>'
                        f'<div class="bl">直觉跳跃</div><div class="bv">{html_lib.escape(str(b.get("leap", "")))}</div>'
                        f'<div class="bl">最容易走错的路</div><div class="bv">{html_lib.escape(str(b.get("temptation", "")))}</div></div>'
                    )
                if rows:
                    st.markdown('<div class="rf-timeline">' + "".join(rows) + "</div>",
                                unsafe_allow_html=True)
            basis = data.get("basis") or []
            if basis:
                st.caption("依据：" + " · ".join(str(x) for x in basis))

    def render_compare(cmp):
        with st.container(border=True):
            st.markdown("##### 对照结果")
            st.markdown(f"**你已经想到的**：{cmp.get('aligned', '')}")
            st.markdown(f"**你漏掉的**：{cmp.get('gap', '')}")
            st.markdown(f"**这次对照的方法课**：{cmp.get('lesson', '')}")

    def render_research():
        page_header(
            "RESEARCH WORKFLOW",
            "12 步研究工作流",
            "先建立背景，再只凭方法出现前的知识推演作者的思路；然后读懂方法、审视证据、红队攻击，最后提出自己的 follow-up。",
        )
        st.markdown(
            '<div style="margin:0 0 14px; padding:9px 12px; background:#F3F0E7; '
            'border:1px solid var(--lr-rule); border-left:2px solid var(--lr-accent-2); '
            'border-radius:4px; font-family:var(--lr-sans); font-size:.755rem; '
            'line-height:1.7; color:var(--lr-ink-2);">'
            '<b>这套流程也适用于审稿。</b>阶段四的实验证据、阶段五的红队与反例、'
            '阶段六的 follow-up，正好对应评审要回答的三个问题：主张成立吗？证据够吗？值不值得入选？'
            '评审视角的切换按钮将放在左侧导航，目前开发中。'
            '</div>',
            unsafe_allow_html=True,
        )
        papers = fetch_papers()
        if not papers:
            def _go_upload():
                if st.button("去上传论文", type="primary", key="empty_flow_upload"):
                    goto("upload")
            empty_state("upload", "还没有论文", "先上传一篇 PDF，再开始 12 步研究流。",
                        cta=_go_upload)
            return

        pmap = {p["paper_id"]: (p.get("title") or p.get("filename")) for p in papers}
        ids = list(pmap.keys())
        cur = st.session_state.get("_active_paper", ids[0])
        idx = ids.index(cur) if cur in ids else 0
        pid = st.selectbox("选择论文", ids, index=idx, format_func=lambda x: pmap[x],
                           key="rf_paper", label_visibility="collapsed")
        st.session_state["_active_paper"] = pid
        st.caption(pmap[pid])

        skey = f"rf_{pid}"
        if skey not in st.session_state:
            st.session_state[skey] = api_get(f"/api/papers/{pid}/research") or {"stages": {}}
        brief = st.session_state[skey] or {"stages": {}}
        stages = brief.get("stages", {})

        viz_key = f"viz_{pid}"
        if viz_key not in st.session_state:
            st.session_state[viz_key] = api_get(f"/api/papers/{pid}/research/viz") or {}
        viz = st.session_state.get(viz_key) or {}

        def bk(n):
            for s in (viz.get("basis") or {}).get("steps") or []:
                if s.get("index") == n:
                    return s.get("kind")
            return None

        # 进度轨道
        done = [s for s, _, _ in PHASES if s in stages]
        nxt = next((s for s, _, _ in PHASES if s not in stages), None)
        last_done = done[-1] if done else None
        cells = []
        for key, label, rng in PHASES:
            cls = "rf-pill"
            if key in stages:
                cls += " done"
            elif key == nxt:
                cls += " now"
            cells.append(
                f'<div class="{cls}"><div class="n">{rng}</div><div class="l">{label}</div></div>'
            )
        st.markdown('<div class="rf-rail">' + "".join(cells) + "</div>", unsafe_allow_html=True)
        st.caption("01–02 建立背景 → 03 先自己推演、再看 AI 重建 → 04–06 读懂方法 → 07–08 审视证据 → 09–11 红队攻击 → 12 提出自己的 idea")

        if viz.get("ready"):
            viz_basis_spectrum(viz.get("basis") or {})

        def expanded(stage):
            return stage == nxt or stage == last_done or (not done and stage == "context")

        def run(stage, label):
            ph = st.empty()
            with ph.container():
                skeleton(lines=4, blocks=1)
            with st.spinner(f"{label} · AI 推演中…"):
                res = api_post(f"/api/papers/{pid}/research/{stage}")
            ph.empty()
            if res:
                st.session_state[skey] = res
                st.session_state.pop(viz_key, None)  # 新阶段会改变 viz 的抽取结果
                st.rerun()

        def stage_empty(icon_name, title, desc, btn_label, key, stage, run_label):
            def _cta():
                if st.button(btn_label, type="primary", key=key):
                    run(stage, run_label)
            empty_state(icon_name, title, desc, cta=_cta, compact=True)

        # ── 阶段一：背景与前史 ──
        with st.expander(f"阶段一 · 背景与前史（第 1–2 步）· {stage_status(stages, 'context')}",
                         expanded=expanded("context")):
            ctx = stages.get("context")
            if not ctx:
                stage_empty(
                    "layers", "还没有生成背景与前史",
                    "先回答：这篇论文在问什么、为什么重要、前人为什么没解决。",
                    "① 生成背景与前史", f"go_ctx_{pid}", "context", "背景与前史",
                )
            else:
                step_card(1, "研究问题：它为什么值得做", "mixed", ctx.get("q1"), basis_kind=bk(1))
                step_card(2, "前史：前人为什么不够", "paper", ctx.get("q2"), basis_kind=bk(2))
                world = ctx.get("world_before") or []
                if world:
                    st.markdown('<div class="lr-section">方法出现之前，作者知道的世界</div>',
                                unsafe_allow_html=True)
                    cards = "".join(
                        f'<div class="rf-wcard"><div class="k">{html_lib.escape(str(w.get("kind", "")))}</div>'
                        f'<div class="f">{html_lib.escape(str(w.get("fact", "")))}</div></div>'
                        for w in world
                    )
                    st.markdown(f'<div class="rf-world">{cards}</div>', unsafe_allow_html=True)
                    st.caption("这些条目只包含方法出现前的知识，是下一步推演的唯一材料。")
                tl = viz.get("timeline") or {}
                if tl.get("items") or tl.get("undated"):
                    viz_timeline(tl)

        # ── 阶段二：作者路径（核心） ──
        with st.expander(f"阶段二 · 逆向推演作者思路（第 3 步 · 核心）· {stage_status(stages, 'author')}",
                         expanded=expanded("author")):
            if "context" not in stages:
                st.info("先完成阶段一：推演需要先有「作者当时知道的世界」。")
            elif "author" not in stages:
                st.markdown(
                    '<div class="rf-gate"><div>'
                    '<div class="gk">STEP 03 · 先写再揭晓</div>'
                    '<div class="gt">先别急着看答案</div>'
                    '<div class="gd">只看上面那些方法出现前的知识。如果你是作者，你会从哪里下手？'
                    '先写下你的猜测，再揭晓 AI 的重建。</div></div>'
                    '<div class="gn">不用写完整。<br>一句话、一个直觉，也算数。</div></div>',
                    unsafe_allow_html=True,
                )
                st.text_area("我的推演", key=f"guess3_{pid}", height=150,
                             placeholder="我会先注意到……因为……于是想到可以……",
                             label_visibility="collapsed")
                if st.button("② 揭晓 AI 的推演", type="primary", key=f"go_auth_{pid}"):
                    run("author", "作者路径")
            else:
                a = stages["author"]
                q3 = a.get("q3") or {}
                fork_data = viz.get("fork") or {}
                has_fork = bool(fork_data.get("beats"))
                step_card(3, "作者最可能的思考路径", "inference", q3,
                          beats=not has_fork, basis_kind=bk(3))
                if has_fork:
                    viz_fork_map(fork_data, st.session_state.get(f"cmp3s_{pid}"))
                else:
                    alts = a.get("alternative_paths") or []
                    if alts:
                        st.markdown("**当时也说得通、但作者没走的路线**")
                        for x in alts:
                            st.markdown(f"- {x}")
                if a.get("confidence_note"):
                    st.caption(f"重建置信度：{a.get('confidence', 'medium')} · {a['confidence_note']}")

                st.markdown("##### 对照你刚才的推演")
                st.caption("近似对照：按中文二元字 / 英文词 / 数字的重合度计算，不调用模型。")
                guess = st.text_area("我的推演", key=f"guess3_{pid}", height=120,
                                     placeholder="如果刚才没写，现在补上也可以",
                                     label_visibility="collapsed")
                if st.button("对照我的推演", key=f"cmp_auth_{pid}"):
                    if not guess.strip():
                        st.warning("先写一句你的推演，再点对照。")
                    else:
                        with st.spinner("对照中…"):
                            if has_fork:
                                sid = st.session_state.get("_viz_session") or uuid.uuid4().hex[:16]
                                st.session_state["_viz_session"] = sid
                                res = api_post(
                                    f"/api/papers/{pid}/research/author/compare-structured",
                                    json={"guess": guess, "session_id": sid},
                                )
                            else:
                                res = api_post(f"/api/papers/{pid}/research/author/compare",
                                               json={"guess": guess})
                        if has_fork:
                            if res:
                                st.session_state[f"cmp3s_{pid}"] = res
                                st.rerun()
                        else:
                            st.session_state[f"cmp3_{pid}"] = res
                cmp3 = (st.session_state.get(f"cmp3s_{pid}") if has_fork
                        else st.session_state.get(f"cmp3_{pid}"))
                if cmp3:
                    if has_fork:
                        st.markdown(f"**近似对照**：{cmp3.get('summary', '')}")
                        extra = cmp3.get("extra") or []
                        if extra:
                            st.markdown("**你想到、但作者主路径没写的点**")
                            for x in extra:
                                st.markdown(f"- {x}")
                        st.caption("分数只表示文字重合度，不是能力评分；每次对照会记入侧栏成长曲线。")
                    else:
                        render_compare(cmp3)

        # ── 阶段三：方法与数学 ──
        with st.expander(f"阶段三 · 方法与数学（第 4–6 步）· {stage_status(stages, 'method')}",
                         expanded=expanded("method")):
            if "author" not in stages:
                st.info("建议先完成第 3 步，再看作者实际怎么做的。")
            elif "method" not in stages:
                stage_empty(
                    "layers", "还没有拆方法",
                    "接下来看 Intuition、一个真实样本的完整 pipeline，以及从零开始的数学推导。",
                    "③ 读懂方法、例子与数学", f"go_method_{pid}", "method", "方法与数学",
                )
            else:
                m = stages["method"]
                step_card(4, "Intuition：核心 idea 的本质", "paper", m.get("q4"), basis_kind=bk(4))
                step_card(5, "具体方法：一个真实样本的 pipeline", "paper", m.get("q5"), basis_kind=bk(5))
                step_card(6, "数学推导：从零开始", "paper", m.get("q6"), basis_kind=bk(6))
                mapping = m.get("design_mapping") or []
                if mapping:
                    lines = ["| 第 3 步的推演 | 论文里的设计 | 判断 |", "|---|---|---|"]
                    for x in mapping:
                        lines.append(
                            f"| {x.get('beat', '')} | {x.get('design', '')} | {x.get('comment', '')} |"
                        )
                    st.markdown("**推演 ↔ 论文设计对照**")
                    st.markdown("\n".join(lines))

        # ── 阶段四：实验证据 ──
        with st.expander(f"阶段四 · 实验证据（第 7–8 步）· {stage_status(stages, 'evidence')}",
                         expanded=expanded("evidence")):
            if "method" not in stages:
                st.info("先读懂方法，再判断实验是否支撑 claim。")
            elif "evidence" not in stages:
                stage_empty(
                    "scale", "还没有拆实验",
                    "把每个 claim 对应到实验、指标和答案，再看作者希望你带走什么。",
                    "④ 拆解实验证据链", f"go_ev_{pid}", "evidence", "实验证据",
                )
            else:
                ev = stages["evidence"]
                step_card(7, "问题 → 实验 → 答案", "paper", ev.get("q7"), basis_kind=bk(7))
                step_card(8, "Take-aways", "mixed", ev.get("q8"), basis_kind=bk(8))

        # ── 阶段五：红队审稿 ──
        with st.expander(f"阶段五 · 红队审稿（第 9–11 步）· {stage_status(stages, 'critique')}",
                         expanded=expanded("critique")):
            if "evidence" not in stages:
                st.info("先看完实验，再判断哪条假设最脆弱。")
            elif "critique" not in stages:
                stage_empty(
                    "shield", "还没有进入红队",
                    "找出最脆弱的假设、设计一周最小复现，再想一个能推翻它的反例。",
                    "⑤ 进入红队审稿", f"go_crit_{pid}", "critique", "红队审稿",
                )
            else:
                cr = stages["critique"]
                arg = viz.get("argument") or {}
                if arg.get("claims"):
                    viz_argument_map(arg)
                step_card(9, "最脆弱的假设", "inference", cr.get("q9"), basis_kind=bk(9))
                step_card(10, "一周最小复现", "inference", cr.get("q10"), basis_kind=bk(10))
                step_card(11, "如果我反对它：反例设计", "inference", cr.get("q11"), basis_kind=bk(11))

        # ── 阶段六：我的 idea ──
        with st.expander(f"阶段六 · 我的 follow-up idea（第 12 步）· {stage_status(stages, 'idea')}",
                         expanded=expanded("idea")):
            if "critique" not in stages:
                st.info("先完成红队审稿，你的 idea 才有攻击点。")
            elif "idea" not in stages:
                st.markdown(
                    '<div class="rf-gate"><div>'
                    '<div class="gk">STEP 12 · 先写再对照</div>'
                    '<div class="gt">这次先写你的</div>'
                    '<div class="gd">基于上面的脆弱假设或反例，你会提出什么新问题？'
                    '先写下来，再和 AI 的方向对照——研究能力就是这样练出来的。</div></div>'
                    '<div class="gn">从缺陷出发。<br>不是把方法再改一遍。</div></div>',
                    unsafe_allow_html=True,
                )
                st.text_area("我的 follow-up idea", key=f"guess12_{pid}", height=140,
                             placeholder="我觉得真正的缺口是……所以应该把问题重新定义成……",
                             label_visibility="collapsed")
                if st.button("⑥ 揭晓 AI 的 follow-up", type="primary", key=f"go_idea_{pid}"):
                    run("idea", "Follow-up idea")
            else:
                step_card(12, "Follow-up idea：从缺陷到新问题", "inference",
                          (stages["idea"] or {}).get("q12"), basis_kind=bk(12))

                st.markdown("##### 对照你的 idea")
                idea = st.text_area("我的 follow-up idea", key=f"guess12_{pid}", height=120,
                                    placeholder="如果刚才没写，现在补上也可以",
                                    label_visibility="collapsed")
                if st.button("对照我的 idea", key=f"cmp_idea_{pid}"):
                    if not idea.strip():
                        st.warning("先写一句你的 idea，再点对照。")
                    else:
                        with st.spinner("对照中…"):
                            res = api_post(f"/api/papers/{pid}/research/idea/compare",
                                           json={"guess": idea})
                        st.session_state[f"cmp12_{pid}"] = res
                cmp = st.session_state.get(f"cmp12_{pid}")
                if cmp:
                    render_compare(cmp)

        # ── 下一步：把研究流接到其他工具 ──
        st.markdown('<div class="lr-hero-rule" style="margin:26px 0 14px;"></div>', unsafe_allow_html=True)
        st.markdown("**下一步**")
        st.markdown('<div class="rf-next-marker"></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("找另一篇论文对比", key=f"cta_cmp_{pid}", use_container_width=True):
                goto("compare")
        with c2:
            if st.button("生成概述图", key=f"cta_ov_{pid}", use_container_width=True):
                st.session_state["_active_paper"] = pid
                st.session_state["ov_paper"] = pid
                goto("overview")
        with c3:
            if st.button("把想法记成笔记", key=f"cta_note_{pid}", use_container_width=True):
                goto("notes")

    # ── 1. 上传 & 解析 ──
    if page == "upload":
        page_header(
            "LIBRARY",
            "论文库",
            "上传 PDF，自动解析标题、作者、摘要与章节结构；这里也是你的文献架。",
        )
        sec(t("sec_upload"), "upload")
        uploaded = st.file_uploader(t("hint_pdf"), type=["pdf"], key="uploader", label_visibility="collapsed")
        if uploaded and st.button(t("btn_parse"), type="primary"):
            with st.spinner(t("spin_parse")):
                result = api_post("/api/papers/upload",
                                  files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")})
            if result:
                st.success(t("msg_saved", pid=f"`{result['paper_id']}`"))
                meta = result.get("meta", {})
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**{t('lbl_title')}**：{meta.get('title') or '—'}")
                    st.markdown(f"**{t('lbl_authors')}**：{meta.get('authors') or '—'}")
                    st.markdown(f"**{t('lbl_pages')}**：{meta.get('total_pages')}")
                with c2:
                    st.markdown(f"**{t('lbl_keywords')}**：{meta.get('keywords') or '—'}")
                    st.markdown(f"**{t('lbl_words')}**：{result.get('text_length')}")
                    st.markdown(f"**{t('lbl_sections')}**：{result.get('section_count')}")
                if meta.get("abstract"):
                    with st.expander(t("lbl_abstract")):
                        st.write(meta["abstract"])

        sec("文献架", "library")
        papers = fetch_papers()
        if not papers:
            empty_state(
                "library", "文献架还是空的",
                "上传第一篇 PDF，解析完成后会自动出现在这里。",
            )
        else:
            for p in papers:
                with st.container(border=True):
                    pid = p["paper_id"]
                    year = str(p.get("year") or "").strip()
                    pages = p.get("total_pages")
                    indexed = bool(p.get("indexed"))
                    meta_bits = [
                        f'<span class="lr-chip">{html_lib.escape(year)}</span>' if year else "",
                        f'<span class="lr-chip">{pages} 页</span>' if pages else "",
                        '<span class="lr-chip ok">已索引</span>' if indexed else '<span class="lr-chip">未索引</span>',
                    ]
                    st.markdown(
                        f'<div class="lib-row"><div class="lib-title">{html_lib.escape(paper_title(p))}</div>'
                        f'<div class="lib-meta">{html_lib.escape(p.get("filename") or "")} {"".join(meta_bits)}</div></div>',
                        unsafe_allow_html=True,
                    )
                    with st.container():
                        st.markdown('<div class="lib-actions-marker"></div>', unsafe_allow_html=True)
                        a1, _ = st.columns([1, 5])
                        with a1:
                            if st.button(t("btn_structure"), key=f"parse_{pid}"):
                                st.session_state[f"d_{pid}"] = api_post(f"/api/papers/{pid}/parse")
                    d = st.session_state.get(f"d_{pid}")
                    if d:
                        with st.expander(t("lbl_struct")):
                            meta = d.get("meta", {})
                            st.markdown(f"**{t('lbl_abstract')}**：{meta.get('abstract') or '—'}")
                            for sec_ in d.get("sections", [])[:20]:
                                st.markdown(f"**{sec_['heading']}**")
                                st.caption(sec_["content"][:300] + "…")
                    confirm_delete(
                        "paper", pid, paper_title(p),
                        lambda pid=pid: api_delete(f"/api/papers/{pid}"),
                    )

    # ── 2. 12 步研究工作流 ──
    if page == "flow":
        render_research()

    # ── 3. 思路对比 ──
    if page == "compare":
        page_header(
            "THINKING",
            "思路对比",
            "不比摘要相似度。按 12 步研究流并排看论文：从哪里出发、在哪里转折、赌了什么、放弃了什么。",
        )
        papers = fetch_papers()
        if len(papers) < 2:
            def _go_upload_cmp():
                if st.button("去上传论文", type="primary", key="empty_cmp_upload"):
                    goto("upload")
            if not papers:
                empty_state("upload", "还没有论文", "先上传至少两篇论文，才能对比思路。", cta=_go_upload_cmp)
            else:
                empty_state("library", "还需要一篇论文", "再上传一篇论文，就可以并排看两条研究路径了。",
                            cta=_go_upload_cmp)
        else:
            st.markdown('<div class="cmp-select-title">选择要对比思路的论文</div>', unsafe_allow_html=True)
            selected = paper_pick_cards(papers, "cmp_sel", "加入对比", default_all=len(papers) <= 3)

            st.markdown(
                f'<div class="cmp-pick-note">已选 <b>{len(selected)}</b> 篇 · 至少 2 篇；'
                f'生成后会读取每篇论文已生成的研究流。</div>',
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns([3, 1])
            with c1:
                st.caption("没生成过研究流的论文会提示先完成 12 步，不会退回摘要相似度。")
            with c2:
                run = st.button("生成思路对比", type="primary",
                                disabled=len(selected) < 2, use_container_width=True)

            if run:
                with st.spinner("正在对齐研究流…"):
                    res = api_post("/api/compare", json={"paper_ids": selected})
                if res:
                    st.session_state["cmp"] = res
                    st.session_state["cmp_ids"] = selected
                else:
                    st.session_state.pop("cmp", None)

            result = st.session_state.get("cmp")
            if result and not result.get("axes"):
                st.session_state.pop("cmp", None)
                result = None
            cmp_ids = st.session_state.get("cmp_ids", [])
            if result and set(cmp_ids) == set(selected):
                viz_thinking_compare(result)
                md = api_post("/api/compare/export", json=result)
                if md:
                    st.download_button("下载思路对比 Markdown", data=md.get("markdown", ""),
                                       file_name="论文思路对比.md", mime="text/markdown")
            elif result:
                st.info("论文选择已变化，点「生成思路对比」刷新。")

    # ── 4. 概述图 ──
    if page == "overview":
        page_header(
            "PAPER NOTE",
            "论文概述图",
            "把一篇论文压成一张竖版网页笔记：一句话总结、研究问题、方法直觉、关键结果、局限和 takeaway。",
        )
        papers = fetch_papers()
        if not papers:
            def _go_upload_ov():
                if st.button("去上传论文", type="primary", key="empty_ov_upload"):
                    goto("upload")
            empty_state("upload", "还没有论文", "先上传一篇 PDF，再生成论文概述图。", cta=_go_upload_ov)
        else:
            pmap = {p["paper_id"]: paper_title(p) for p in papers}
            ids = list(pmap.keys())
            cur = st.session_state.get("_active_paper", ids[0])
            idx = ids.index(cur) if cur in ids else 0
            pid = st.selectbox("选择论文", ids, index=idx, format_func=lambda x: pmap[x],
                               key="ov_paper", label_visibility="collapsed")
            st.session_state["_active_paper"] = pid
            st.caption(pmap[pid])
            st.markdown(
                '<div class="cmp-pick-note">你会得到：一句话总结 · 研究问题 · 方法直觉（3 步）'
                ' · 关键结果（3 条） · 局限 · takeaway。</div>',
                unsafe_allow_html=True,
            )

            png_key = f"ov_png_{pid}"
            png = st.session_state.get(png_key)
            preview = st.empty()
            preview_title = pmap[pid]
            if len(preview_title) > 52:
                preview_title = preview_title[:51].rstrip() + "…"
            if not png:
                with preview.container():
                    st.markdown(
                        '<div class="ov-preview">'
                        '<div class="ov-k">LITREAD / PAPER NOTE</div>'
                        f'<div class="ov-t">{html_lib.escape(preview_title)}</div>'
                        '<div class="ov-s">一句话总结 · 研究问题 · 方法直觉 · 关键结果 · 局限 · takeaway</div>'
                        '<div class="ov-line"></div><div class="ov-line short"></div>'
                        '<div class="ov-sec">01 研究问题</div><div class="ov-line"></div><div class="ov-line short"></div>'
                        '<div class="ov-sec">02 方法直觉</div><div class="ov-line"></div><div class="ov-line short"></div>'
                        '<div class="ov-sec">03 关键结果</div><div class="ov-line"></div><div class="ov-line short"></div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
            st.caption("首次调用模型，之后同一篇论文直接读缓存。")
            if st.button("一键生成概述图", type="primary", use_container_width=True):
                preview.empty()
                with preview.container():
                    skeleton(lines=3, blocks=2)
                with st.spinner("正在把论文压缩成一张笔记…"):
                    png = api_get_bytes(f"/api/papers/{pid}/overview.png")
                preview.empty()
                if png:
                    st.session_state[png_key] = png

            png = st.session_state.get(png_key)
            if png:
                c1, c2, c3 = st.columns([0.9, 3.2, 0.9])
                with c2:
                    st.image(png, use_column_width=True)
                    st.download_button(
                        "下载概述图 PNG", data=png,
                        file_name=f"paper-note-{pid}.png", mime="image/png",
                        type="primary", use_container_width=True,
                    )
                st.caption("这张图由论文全文 + 研究流生成；数字只来自论文，没有让图像模型自由发挥。")

    # ── 5. 笔记 ──
    if page == "notes":
        page_header(
            "NOTES",
            "阅读笔记",
            "写你的想法、疑问或反思。留空时自动写入研究流 12 步；有内容时，你的想法在上，研究流附后。",
        )
        papers = fetch_papers()
        if not papers:
            def _go_upload_note():
                if st.button("去上传论文", type="primary", key="empty_note_upload"):
                    goto("upload")
            empty_state("upload", "还没有论文", "先上传一篇 PDF，再开始写阅读笔记。", cta=_go_upload_note)
        else:
            pmap = {p["paper_id"]: paper_title(p) for p in papers}
            pid = st.selectbox(t("sec_notes"), list(pmap.keys()), format_func=lambda x: pmap[x],
                               key="note_paper", label_visibility="collapsed")
            st.caption(pmap[pid])
            note_content = st.text_area(
                t("ph_note"), height=130, key="note_input", label_visibility="collapsed",
                placeholder="写你的想法、疑问或反思。留空时，会把研究流 12 步直接写成笔记。",
            )
            st.caption("留空 → 自动写入研究流 12 步；有内容 → 你的想法在上，研究流附在后面。")
            if st.button(t("btn_note"), type="primary"):
                flow = api_get(f"/api/papers/{pid}/research/markdown") or {}
                flow_md = (flow.get("markdown") or "").strip()
                user_txt = note_content.strip()
                if not user_txt and not flow_md:
                    st.warning("研究流还没有生成内容，先写一句你的想法吧。")
                else:
                    if not user_txt:
                        merged, msg = flow_md, "已把研究流 12 步写入笔记。"
                    elif not flow_md:
                        merged, msg = user_txt, "已保存你的笔记（研究流尚未生成）。"
                    else:
                        merged = f"{user_txt}\n\n---\n\n# 附：研究流 12 步\n\n{flow_md}"
                        msg = "已把你的想法与研究流合并写入笔记。"
                    api_post(f"/api/papers/{pid}/notes", json={"content": merged})
                    st.success(msg)
                    st.rerun()

            all_notes = api_get(f"/api/notes?paper_id={pid}")
            note_list = all_notes.get("notes", []) if all_notes else []
            if note_list:
                st.markdown(f"**{t('lbl_notes')}（{len(note_list)}）**")
            for n in note_list:
                nid = n["id"]
                open_key = f"note_open_{nid}"
                is_open = bool(st.session_state.get(open_key))
                with st.container(border=True):
                    if is_open:
                        st.markdown(n.get("content", ""))
                    else:
                        preview = html_lib.escape(n.get("content", ""))
                        st.markdown(f'<div class="note-body clamp">{preview}</div>',
                                    unsafe_allow_html=True)
                    st.markdown(f'<div class="note-meta">#{nid} · {n.get("created_at", "")[:16]}</div>',
                                unsafe_allow_html=True)
                    with st.container():
                        st.markdown('<div class="note-toggle-marker"></div>', unsafe_allow_html=True)
                        if st.button("收起" if is_open else "展开全文", key=f"toggle_{nid}"):
                            st.session_state[open_key] = not is_open
                            st.rerun()
                    confirm_delete(
                        "note", nid, "这条笔记",
                        lambda nid=nid: api_delete(f"/api/notes/{nid}"),
                    )

            if note_list:
                c1, c2 = st.columns(2)
                with c1:
                    pdf = api_get_bytes(f"/api/papers/{pid}/notes/pdf")
                    if pdf:
                        st.download_button(
                            "下载笔记 PDF", data=pdf,
                            file_name=f"litread-notes-{pid}.pdf",
                            mime="application/pdf", type="primary",
                            use_container_width=True,
                        )
                with c2:
                    if st.button(t("btn_organize"), use_container_width=True):
                        with st.spinner(t("spin_organize")):
                            org = api_post(f"/api/papers/{pid}/notes/organize")
                        st.session_state[f"org_{pid}"] = org
            else:
                brief = api_get(f"/api/papers/{pid}/research") or {}
                empty_state(
                    "pen", "还没有笔记",
                    "写一句你的想法，或者直接点「添加笔记」，把研究流 12 步写进来。",
                )
                if brief.get("stages"):
                    pdf = api_get_bytes(f"/api/papers/{pid}/notes/pdf")
                    if pdf:
                        st.download_button(
                            "下载研究流 PDF（无需先写笔记）", data=pdf,
                            file_name=f"litread-research-{pid}.pdf",
                            mime="application/pdf", use_container_width=True,
                        )

            org = st.session_state.get(f"org_{pid}")
            if org:
                st.markdown(f"##### {t('lbl_organized')}")
                st.markdown(org.get("organized", ""))

    # Footer
    st.markdown('<div class="lr-hero-rule" style="margin:44px 0 0;"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="lr-footer">{t("foot")}</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
