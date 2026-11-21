"""把阅读笔记（含 12 步研究流）导出为中文 PDF。

使用 reportlab 内置的 STSong-Light CID 字体，不依赖服务器安装中文字体。
Markdown 只做轻量渲染：标题 / 列表 / 段落 / 表格行，够笔记阅读即可。
"""
import io
import re
from datetime import datetime
from typing import List, Optional
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

FONT = "STSong-Light"
_FONT_READY = False


def _ensure_font() -> None:
    global _FONT_READY
    if _FONT_READY:
        return
    try:
        pdfmetrics.registerFont(UnicodeCIDFont(FONT))
    except Exception:
        pass
    _FONT_READY = True


def _styles():
    _ensure_font()
    base = dict(fontName=FONT, textColor="#1F2328", wordWrap="CJK")
    return {
        "kicker": ParagraphStyle("kicker", fontSize=8, leading=12, textColor="#6B7169", **{k: v for k, v in base.items() if k != "textColor"}),
        "title": ParagraphStyle("title", fontSize=19, leading=27, spaceAfter=4 * mm, **base),
        "meta": ParagraphStyle("meta", fontSize=8.5, leading=13, textColor="#7A7F78", **{k: v for k, v in base.items() if k != "textColor"}),
        "h1": ParagraphStyle("h1", fontSize=13.5, leading=21, spaceBefore=4 * mm, spaceAfter=2 * mm, **base),
        "h2": ParagraphStyle("h2", fontSize=11, leading=17, spaceBefore=3 * mm, spaceAfter=1.5 * mm, **base),
        "body": ParagraphStyle("body", fontSize=9.8, leading=16.5, spaceAfter=1.4 * mm, **base),
        "bullet": ParagraphStyle("bullet", fontSize=9.8, leading=16, leftIndent=5 * mm, bulletIndent=1.5 * mm, spaceAfter=0.8 * mm, **base),
        "quote": ParagraphStyle("quote", fontSize=9.2, leading=15.5, leftIndent=4 * mm, textColor="#4A5049", **{k: v for k, v in base.items() if k != "textColor"}),
    }


def _inline(text: str) -> str:
    """转义 XML 后恢复少量 Markdown 行内样式。"""
    s = escape(text)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = s.replace("$", "")
    return s


def _md_flowables(md: str, st) -> list:
    flow = []
    for raw in (md or "").splitlines():
        line = raw.rstrip()
        if not line.strip():
            flow.append(Spacer(1, 1.8 * mm))
            continue
        stripped = line.strip()
        if re.fullmatch(r"[-*_]{3,}", stripped):
            flow.append(Spacer(1, 2.2 * mm))
            continue
        if stripped.startswith("|"):
            if re.fullmatch(r"\|[\s:|-]+\|", stripped):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            flow.append(Paragraph(_inline(" · ".join(c for c in cells if c)), st["quote"]))
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            flow.append(Paragraph(_inline(m.group(2)), st["h1"] if level <= 2 else st["h2"]))
            continue
        m = re.match(r"^\s*[-*+]\s+(.*)$", line)
        if m:
            flow.append(Paragraph(_inline(m.group(1)), st["bullet"], bulletText="•"))
            continue
        m = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if m:
            flow.append(Paragraph(_inline(m.group(1)), st["bullet"], bulletText="•"))
            continue
        flow.append(Paragraph(_inline(stripped), st["body"]))
    return flow


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 8)
    canvas.setFillColor("#8A8F88")
    canvas.drawString(18 * mm, 12 * mm, "LitRead · 12 步研究工作流")
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


def build_pdf(paper_title: str, notes: List[str], fallback_flow: Optional[str] = None) -> bytes:
    """notes 为已保存笔记正文；没有笔记时用 fallback_flow 兜底。"""
    st = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title="LitRead 阅读笔记", author="LitRead",
    )

    flow = [
        Paragraph("LITREAD · READING NOTES", st["kicker"]),
        Spacer(1, 2 * mm),
        Paragraph(_inline(paper_title or "未命名论文"), st["title"]),
        Paragraph(
            f"导出时间 {datetime.now().strftime('%Y-%m-%d %H:%M')} · "
            f"{len(notes)} 条笔记" + ("" if notes else " · 研究流内容"),
            st["meta"],
        ),
        Spacer(1, 5 * mm),
    ]

    if notes:
        for i, n in enumerate(notes, 1):
            flow.append(Paragraph(f"笔记 {i}", st["h1"]))
            flow.extend(_md_flowables(n, st))
            flow.append(Spacer(1, 3 * mm))
    elif fallback_flow:
        flow.append(Paragraph("研究流 12 步", st["h1"]))
        flow.extend(_md_flowables(fallback_flow, st))
    else:
        raise ValueError("暂无笔记")

    doc.build(flow, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
