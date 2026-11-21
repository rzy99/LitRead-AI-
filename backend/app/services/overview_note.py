"""论文速览笔记：把一篇论文压成一张竖版网页笔记（PNG）。

内容先由 LLM 从论文全文 / 已有研究流中抽取成结构化字段，
再用固定模板渲染成图片。图片里的文字全部来自结构化结果，
不依赖图像生成模型，避免虚构数字和公式。
"""
import io
import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont

from ..config import get_abs_path
from ..models import ParsedPaper
from . import research_flow
from .llm_client import get_llm, is_llm_ready

VERSION = "on-1"

W = 1080
MARGIN = 36
PAD = 64
SHEET_W = W - 2 * MARGIN
CONTENT_W = SHEET_W - 2 * PAD

BG = "#F3F0E8"
SHEET = "#FCFBF7"
INK = "#20201C"
BODY = "#3F3E39"
MUTED = "#8B877C"
ACCENT = "#31543F"
ACCENT_WASH = "#E9EFE9"
RULE = "#DDD9CD"
WARM = "#96671A"

FONT_DIR = get_abs_path("../data/fonts")
SANS_PATH = FONT_DIR / "NotoSansSC-VF.ttf"
SERIF_PATH = FONT_DIR / "NotoSerifSC-VF.ttf"
MONO_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf")

_NO_START = set("，。！？；：、）》」』】,.!?;:%)]}")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-_./%:+×≈]*|[\u4e00-\u9fff]|[ \t]+|[^\s]")


@lru_cache(maxsize=128)
def _font(kind: str, size: int, weight: int = 400) -> ImageFont.FreeTypeFont:
    path = {"sans": SANS_PATH, "serif": SERIF_PATH, "mono": MONO_PATH}[kind]
    font = ImageFont.truetype(str(path), size)
    if kind != "mono":
        try:
            font.set_variation_by_axes([weight])
        except Exception:
            pass
    return font


def _clean(text) -> str:
    if not isinstance(text, str):
        return ""
    for a, b in {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}.items():
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip()


def _clip(text, limit: int) -> str:
    text = _clean(text)
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> List[str]:
    """中英混排换行：中文按字，英文尽量按词；长 token 强制断开。"""
    text = _clean(text)
    if not text:
        return [""]
    units = _TOKEN.findall(text)
    lines: List[str] = []
    line = ""
    for unit in units:
        if unit.isspace():
            if line and not line.endswith(" "):
                line += " "
            continue
        cand = line + unit
        if draw.textlength(cand, font=font) <= max_w or not line.strip():
            line = cand
        elif unit[0] in _NO_START:
            line += unit
        else:
            lines.append(line.rstrip())
            line = unit
        while draw.textlength(line, font=font) > max_w and len(line) > 1:
            cut = len(line) - 1
            while cut > 1 and draw.textlength(line[:cut], font=font) > max_w:
                cut -= 1
            while cut < len(line) and line[cut] in _NO_START:
                cut += 1
            lines.append(line[:cut])
            line = line[cut:]
    if line.strip():
        lines.append(line.rstrip())
    return lines or [""]


class _Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (SHEET_W, 9000), SHEET)
        self.d = ImageDraw.Draw(self.img)
        self.y = 46
        self.last_step_cy = None

    def text(self, text, kind: str, size: int, weight: int, fill: str,
             x: int = PAD, max_w: int = CONTENT_W, line_h: int = None) -> int:
        font = _font(kind, size, weight)
        lh = line_h or int(size * 1.55)
        for line in _wrap(self.d, text, font, max_w):
            self.d.text((x, self.y), line, font=font, fill=fill)
            self.y += lh
        return self.y

    def gap(self, h: int) -> None:
        self.y += h


def _display_title(title: str) -> str:
    text = _clean(title)
    text = re.sub(
        r"^arXiv:\S+\s*(?:\[[^\]]+\])?\s*\d{1,2}\s+\w+\s+\d{4}\s*",
        "",
        text,
        flags=re.I,
    )
    return text.strip() or "未命名论文"


def _header(c: _Canvas, paper: ParsedPaper, note: Dict) -> None:
    meta = paper.meta
    c.y = 48
    d = c.d
    d.text((PAD, c.y), "LITREAD  /  PAPER NOTE",
           font=_font("sans", 16, 700), fill=ACCENT)
    right = f"{meta.year} · 阅读笔记" if meta.year else "阅读笔记"
    rfont = _font("sans", 15, 500)
    d.text((SHEET_W - PAD - d.textlength(right, font=rfont), c.y), right,
           font=rfont, fill=MUTED)
    c.y += 30
    d.line((PAD, c.y, SHEET_W - PAD, c.y), fill=RULE, width=1)
    c.y += 32

    kicker = _clean(note.get("kicker"))
    if kicker:
        c.text(kicker, "sans", 16, 600, ACCENT)
        c.gap(4)

    title = _display_title(meta.title)
    c.text(title, "serif", 42, 700, INK, line_h=57)
    c.gap(8)

    headline = _clean(note.get("headline"))
    if headline:
        c.text(headline, "sans", 22, 500, ACCENT, line_h=34)
        c.gap(4)

    authors = _clean(meta.authors)
    bits = []
    if authors:
        bits.append(authors)
    if meta.year:
        bits.append(meta.year)
    if bits:
        c.text(" · ".join(bits), "sans", 17, 400, MUTED, line_h=27)
    c.gap(24)
    d.line((PAD, c.y, SHEET_W - PAD, c.y), fill=RULE, width=1)
    c.y += 28


def _quote(c: _Canvas, text: str) -> None:
    text = _clean(text)
    if not text:
        return
    font = _font("serif", 25, 500)
    lh = 38
    lines = _wrap(c.d, text, font, CONTENT_W - 58)
    top = c.y
    h = 54 + len(lines) * lh + 20
    c.d.rounded_rectangle((PAD - 14, top, SHEET_W - PAD + 14, top + h),
                          radius=10, fill=ACCENT_WASH)
    c.d.rectangle((PAD - 14, top, PAD - 8, top + h), fill=ACCENT)
    c.d.text((PAD + 10, top + 12), "一句话总结",
             font=_font("sans", 13, 700), fill=ACCENT)
    yy = top + 38
    for line in lines:
        c.d.text((PAD + 10, yy), line, font=font, fill=INK)
        yy += lh
    c.y = top + h + 28


def _section(c: _Canvas, num: int, title: str) -> None:
    c.y += 30
    c.d.text((PAD, c.y + 4), f"{num:02d}",
             font=_font("mono", 15), fill=ACCENT)
    c.d.text((PAD + 40, c.y), title,
             font=_font("sans", 22, 700), fill=INK)
    c.y += 34
    c.d.line((PAD, c.y, SHEET_W - PAD, c.y), fill=RULE, width=1)
    c.y += 18


def _body(c: _Canvas, text: str) -> None:
    text = _clean(text)
    if not text:
        text = "论文未说明。"
    c.text(text, "sans", 20, 400, BODY, line_h=33)
    c.gap(4)


def _steps(c: _Canvas, steps: List[Dict]) -> None:
    for i, step in enumerate(steps, 1):
        top = c.y
        cx, cy, r = PAD + 14, top + 14, 14
        if c.last_step_cy is not None:
            c.d.line((cx, c.last_step_cy + r, cx, cy - r - 5),
                     fill=RULE, width=1)
        c.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ACCENT)
        nf = _font("mono", 12)
        box = c.d.textbbox((0, 0), str(i), font=nf)
        c.d.text((cx - (box[2] - box[0]) / 2,
                  cy - (box[3] - box[1]) / 2 - box[1]),
                 str(i), font=nf, fill="#FFFFFF")

        label = _clean(step.get("label")) or f"步骤 {i}"
        c.d.text((PAD + 44, top + 1), label,
                 font=_font("sans", 19, 700), fill=INK)
        yy = top + 31
        font = _font("sans", 19, 400)
        for line in _wrap(c.d, step.get("text"), font, CONTENT_W - 44):
            c.d.text((PAD + 44, yy), line, font=font, fill=BODY)
            yy += 30
        c.last_step_cy = cy
        c.y = yy + 16


def _results(c: _Canvas, results: List[Dict]) -> None:
    for i, item in enumerate(results):
        top = c.y
        value = _clean(item.get("value")) or "—"
        label = _clean(item.get("label")) or "论文结果"
        note = _clean(item.get("note"))

        big = _font("serif", 30, 700)
        if c.d.textlength(value, font=big) <= 190:
            vf, vstep = big, 38
        else:
            vf, vstep = _font("serif", 24, 700), 32
        vy = top
        for line in _wrap(c.d, value, vf, 190):
            c.d.text((PAD, vy), line, font=vf, fill=ACCENT)
            vy += vstep

        c.d.text((PAD + 210, top + 2), label,
                 font=_font("sans", 19, 700), fill=INK)
        ny = top + 35
        nf = _font("sans", 18, 400)
        for line in _wrap(c.d, note, nf, CONTENT_W - 210):
            c.d.text((PAD + 210, ny), line, font=nf, fill=MUTED)
            ny += 28

        c.y = max(vy, ny) + 16
        if i < len(results) - 1:
            c.d.line((PAD, c.y - 8, SHEET_W - PAD, c.y - 8),
                     fill=RULE, width=1)
            c.y += 12


def _bullets(c: _Canvas, items: List[str]) -> None:
    for item in items:
        top = c.y
        c.d.text((PAD, top), "—", font=_font("sans", 18, 700), fill=WARM)
        yy = top
        font = _font("sans", 19, 400)
        for line in _wrap(c.d, item, font, CONTENT_W - 30):
            c.d.text((PAD + 30, yy), line, font=font, fill=BODY)
            yy += 31
        c.y = yy + 10


def _takeaway(c: _Canvas, text: str) -> None:
    text = _clean(text)
    if not text:
        return
    font = _font("serif", 24, 600)
    lh = 36
    lines = _wrap(c.d, text, font, CONTENT_W - 44)
    top = c.y
    h = 54 + len(lines) * lh + 20
    c.d.rounded_rectangle((PAD - 14, top, SHEET_W - PAD + 14, top + h),
                          radius=10, fill=SHEET, outline=ACCENT, width=2)
    c.d.text((PAD + 8, top + 13), "TAKEAWAY",
             font=_font("sans", 13, 700), fill=ACCENT)
    yy = top + 40
    for line in lines:
        c.d.text((PAD + 8, yy), line, font=font, fill=INK)
        yy += lh
    c.y = top + h + 24


def _footer(c: _Canvas) -> None:
    c.y += 12
    c.d.line((PAD, c.y, SHEET_W - PAD, c.y), fill=RULE, width=1)
    c.y += 16
    left = "LitRead · 论文速览笔记"
    right = "基于论文全文与 12 步研究流生成"
    c.d.text((PAD, c.y), left, font=_font("sans", 14, 500), fill=MUTED)
    rf = _font("sans", 13, 400)
    c.d.text((SHEET_W - PAD - c.d.textlength(right, font=rf), c.y),
             right, font=rf, fill=MUTED)
    c.y += 34


def build_note_png(paper: ParsedPaper, note: Dict) -> bytes:
    c = _Canvas()
    _header(c, paper, note)
    _quote(c, note.get("one_liner"))
    _section(c, 1, "研究问题")
    _body(c, note.get("question"))
    _section(c, 2, "方法直觉")
    _body(c, note.get("intuition"))
    if note.get("steps"):
        _steps(c, note["steps"])
    _section(c, 3, "关键结果")
    if note.get("results"):
        _results(c, note["results"])
    else:
        _body(c, "论文未给出可核对的结果数字。")
    _section(c, 4, "局限")
    _bullets(c, note.get("limits") or ["论文未明确说明。"])
    _section(c, 5, "一句话带走")
    _takeaway(c, note.get("takeaway"))
    _footer(c)

    sheet = c.img.crop((0, 0, SHEET_W, min(c.y + 40, c.img.height)))
    final_h = sheet.height + 2 * MARGIN
    final = Image.new("RGB", (W, final_h), BG)
    shadow = Image.new("RGBA", final.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rectangle((MARGIN + 6, MARGIN + 8,
                  MARGIN + SHEET_W + 6, MARGIN + sheet.height + 8),
                 fill=(32, 32, 28, 22))
    final = Image.alpha_composite(final.convert("RGBA"), shadow).convert("RGB")
    final.paste(sheet, (MARGIN, MARGIN))
    d = ImageDraw.Draw(final)
    d.rectangle((MARGIN, MARGIN, MARGIN + SHEET_W, MARGIN + sheet.height),
                outline=RULE, width=1)
    d.rectangle((MARGIN, MARGIN, MARGIN + SHEET_W, MARGIN + 5), fill=ACCENT)

    buf = io.BytesIO()
    final.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# ─────────────────────────────────────────────
#  内容生成
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """你是一名论文阅读编辑，把一篇论文压缩成一张竖版「阅读笔记」。
只输出 JSON，字段如下：
{
  "kicker": "方向 · 年份，不超过 20 字",
  "headline": "编辑式标题，不超过 26 字，不要照抄论文标题",
  "one_liner": "一句话总结，不超过 70 字",
  "question": "研究问题，不超过 90 字",
  "intuition": "核心直觉，不超过 110 字",
  "steps": [{"label": "不超过 6 字", "text": "不超过 55 字"}, 共 3 条],
  "results": [{"value": "不超过 12 字", "label": "不超过 18 字", "note": "不超过 45 字"}, 共 3 条],
  "limits": ["不超过 60 字", "不超过 60 字"],
  "takeaway": "不超过 70 字"
}

硬性要求：
- 所有事实、数字必须来自给定材料；材料没有就写定性结论，禁止编造。
- 用中文；英文术语首次出现时在括号里保留原文。
- 不写“具有重要意义”“效果显著”这类空话。
- 不要用海报或宣传文案的口吻，像写给同学看的网页笔记。
- 只输出 JSON，不要代码围栏，不要额外解释。"""


def _unwrap(data: Dict) -> Dict:
    if not isinstance(data, dict) or set(data.keys()) != {"raw"}:
        return data
    raw = data.get("raw")
    if not isinstance(raw, str):
        return data
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else data
    except Exception:
        return data


def _brief_digest(brief: Dict) -> str:
    stages = (brief or {}).get("stages", {})
    ctx = stages.get("context") or {}
    method = stages.get("method") or {}
    ev = stages.get("evidence") or {}
    crit = stages.get("critique") or {}

    def content(node) -> str:
        if not isinstance(node, dict):
            return ""
        return _clean(node.get("content"))

    parts = []
    if _clean(ctx.get("one_line")):
        parts.append("一句话：\n" + _clean(ctx.get("one_line")))
    for label, text in [
        ("研究问题", content(ctx.get("q1"))),
        ("前人不足", content(ctx.get("q2"))),
        ("核心直觉", content(method.get("q4"))),
        ("具体方法", content(method.get("q5"))),
        ("实验与答案", content(ev.get("q7"))),
        ("Take-aways", content(ev.get("q8"))),
        ("最脆弱假设", content(crit.get("q9"))),
    ]:
        if text:
            parts.append(f"{label}：\n{_clip(text, 1500)}")
    return "\n\n".join(parts)


def _fallback_note(paper: ParsedPaper) -> Dict:
    meta = paper.meta
    abstract = _clean(meta.abstract)
    sentences = [s.strip() for s in re.split(r"(?<=[。！？.!?])\s*", abstract) if s.strip()]
    first = sentences[0] if sentences else "论文未提供摘要。"
    kws = _clean(meta.keywords).split(",")[0].strip()
    kicker = " · ".join([x for x in [kws, meta.year] if x])
    steps = []
    for i, label in enumerate(["问题", "做法", "取舍"], 1):
        text = sentences[i - 1] if i <= len(sentences) else first
        steps.append({"label": label, "text": _clip(text, 110)})
    return {
        "kicker": _clip(kicker, 20),
        "headline": _clip(first, 26),
        "one_liner": _clip(first, 120),
        "question": _clip(first, 180),
        "intuition": _clip(first, 220),
        "steps": steps,
        "results": [{"value": "—", "label": "论文结果", "note": _clip(first, 90)}],
        "limits": ["论文未明确说明。"],
        "takeaway": _clip(first, 130),
    }


def _normalize(data: Dict, paper: ParsedPaper) -> Dict:
    base = _fallback_note(paper)

    def text(key: str, limit: int, fallback: str = "") -> str:
        return _clip(data.get(key) if isinstance(data.get(key), str) else fallback, limit)

    steps = []
    for item in (data.get("steps") or []):
        if isinstance(item, str):
            steps.append({"label": "步骤", "text": _clip(item, 110)})
        elif isinstance(item, dict):
            steps.append({
                "label": _clip(item.get("label"), 14) or "步骤",
                "text": _clip(item.get("text"), 150),
            })
        if len(steps) >= 3:
            break

    results = []
    for item in (data.get("results") or []):
        if isinstance(item, dict):
            value = _clip(item.get("value"), 40) or "—"
            label = _clip(item.get("label"), 30) or "论文结果"
            note = _clip(item.get("note"), 110)
            if len(value) > 12 and " " in value and " vs " not in value:
                head, tail = value.split(" ", 1)
                if any(ch.isdigit() for ch in head) and len(head) <= 12:
                    value = head
                    label = f"{label} · {tail}"
            results.append({
                "value": value,
                "label": label,
                "note": note,
            })
        elif isinstance(item, str):
            results.append({"value": "—", "label": "论文结果", "note": _clip(item, 110)})
        if len(results) >= 3:
            break

    limits = []
    for item in (data.get("limits") or []):
        if isinstance(item, (str, int, float)):
            limits.append(_clip(str(item), 140))
        if len(limits) >= 3:
            break

    return {
        "kicker": text("kicker", 30, base["kicker"]) or base["kicker"],
        "headline": text("headline", 40, base["headline"]) or base["headline"],
        "one_liner": text("one_liner", 150, base["one_liner"]) or base["one_liner"],
        "question": text("question", 240, base["question"]) or base["question"],
        "intuition": text("intuition", 280, base["intuition"]) or base["intuition"],
        "steps": steps or base["steps"],
        "results": results or base["results"],
        "limits": limits or base["limits"],
        "takeaway": text("takeaway", 180, base["takeaway"]) or base["takeaway"],
    }


def _generate_note(paper: ParsedPaper) -> Dict:
    if not is_llm_ready():
        return _fallback_note(paper)

    brief = research_flow.get_brief(paper)
    digest = _brief_digest(brief)
    meta = paper.meta
    abstract = _clip(meta.abstract, 1800)
    body = _clip(paper.full_text, 5000) if not digest else ""

    user = (
        "【论文信息】\n"
        f"标题：{meta.title or '（未识别）'}\n"
        f"作者：{meta.authors or '（未识别）'}\n"
        f"年份：{meta.year or '（未识别）'}\n"
        f"关键词：{meta.keywords or '（未识别）'}\n\n"
        f"【摘要】\n{abstract or '（无）'}\n\n"
    )
    if digest:
        user += f"【研究流要点】\n{digest}\n\n"
    else:
        user += f"【正文片段】\n{body}\n\n"

    try:
        data = get_llm().chat_json(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
            max_tokens=2600,
        )
        return _normalize(_unwrap(data), paper)
    except Exception:
        return _fallback_note(paper)


def _cache_paths(paper_id: str) -> Tuple[Path, Path]:
    folder = get_abs_path("../data/overview")
    folder.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", paper_id or "paper")
    base = folder / safe
    return base.with_suffix(".json"), base.with_suffix(".png")


def get_or_create(paper: ParsedPaper, force: bool = False) -> Tuple[Dict, bytes]:
    json_path, png_path = _cache_paths(paper.paper_id)

    note = None
    if not force and json_path.exists():
        try:
            cached = json.loads(json_path.read_text(encoding="utf-8"))
            if cached.get("version") == VERSION:
                note = cached.get("note")
        except Exception:
            note = None

    fresh = note is None
    if fresh:
        note = _generate_note(paper)
        json_path.write_text(
            json.dumps(
                {
                    "version": VERSION,
                    "paper_id": paper.paper_id,
                    "note": note,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    png = None
    if not force and not fresh and png_path.exists():
        png = png_path.read_bytes()
    if not png:
        png = build_note_png(paper, note)
        png_path.write_bytes(png)

    return note, png
