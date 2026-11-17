"""
PDF 解析：PyMuPDF 提取文本 + 启发式识别结构。
服务器可用，后续可在此基础上接入 Marker 做版面解析。
"""
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

import fitz

from ..models import PaperMeta, ParsedPaper


def _make_paper_id(filepath: str) -> str:
    return hashlib.md5(filepath.encode("utf-8")).hexdigest()[:12]


def _extract_title(doc: fitz.Document, first_page_text: str) -> Optional[str]:
    meta_title = doc.metadata.get("title")
    if meta_title and len(meta_title.strip()) > 5:
        return meta_title.strip()

    # 按字号找最大的那行作为标题
    try:
        page = doc[0]
        blocks = page.get_text("dict")["blocks"]
        candidates = []
        for b in blocks:
            if b.get("type") != 0:
                continue
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    txt = span["text"].strip()
                    if len(txt) > 3:
                        candidates.append((span["size"], txt))
        if candidates:
            candidates.sort(key=lambda x: -x[0])
            # 取最大字号的连续行拼起来
            max_size = candidates[0][0]
            title_parts = [t for s, t in candidates if s >= max_size - 1]
            title = " ".join(title_parts).strip()
            if 5 < len(title) < 300:
                return title
    except Exception:
        pass

    lines = [l.strip() for l in first_page_text.splitlines() if l.strip()]
    if lines and len(lines[0]) < 200:
        return lines[0]
    return None


def _extract_abstract(text: str) -> Optional[str]:
    patterns = [
        r"(?:^|\n)\s*Abstract\s*[\.:\-]?\s*\n(.+?)(?=\n\s*(?:1\.?\s+Introduction|I\.?\s+Introduction|Keywords|Index Terms)\b)",
        r"(?:^|\n)\s*Abstract\s*[\.:\-]?\s*\n(.+?)(?=\n\s*\d+\.?\s+[A-Z])",
        r"(?:^|\n)\s*Abstract\s*[\.:\-]?\s*(.+?)(?=\n\s*Keywords)",
        r"(?:^|\n)\s*摘\s*要\s*[\.:\-]?\s*\n?(.+?)(?=\n\s*(?:关键词|Key words|1\.|一、))",
    ]
    head = text[:8000]
    for pat in patterns:
        m = re.search(pat, head, re.IGNORECASE | re.DOTALL)
        if m:
            abs_text = re.sub(r"\s+", " ", m.group(1)).strip()
            if 80 < len(abs_text) < 4000:
                return abs_text
    return None


def _extract_keywords(text: str) -> Optional[str]:
    patterns = [
        r"Keywords?\s*[\.:\-]?\s*(.+?)(?=\n\s*(?:1\.?\s+Introduction|I\.|Abstract|Index Terms|©|$))",
        r"Index Terms\s*[\.:\-]?\s*(.+?)(?=\n)",
        r"关键词\s*[\.:\-]?\s*(.+?)(?=\n\s*(?:1\.|一、|Abstract|$))",
    ]
    head = text[:8000]
    for pat in patterns:
        m = re.search(pat, head, re.IGNORECASE | re.DOTALL)
        if m:
            kw = re.sub(r"\s+", " ", m.group(1)).strip(" .;,，；")
            if 3 < len(kw) < 500:
                return kw
    return None


def _split_sections(text: str) -> List[Dict]:
    pattern = re.compile(
        r"(?:^|\n)\s*(\d+(?:\.\d+)?)\s+([A-Z\u4e00-\u9fa5][A-Za-z0-9 \-\u4e00-\u9fa5]{2,80})\s*\n",
        re.MULTILINE,
    )
    sections: List[Dict] = []
    last_end = 0
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        if m.start() > last_end:
            body = text[last_end:m.start()].strip()
            if body:
                sections.append({"heading": "Preamble", "content": body[:3000]})
        heading = f"{m.group(1)} {m.group(2)}"
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[m.end():end].strip()
        if content:
            sections.append({"heading": heading, "content": content[:3000]})
        last_end = end
    if not sections and text.strip():
        sections.append({"heading": "Full Text", "content": text[:3000]})
    return sections


def parse_pdf(filepath: str) -> ParsedPaper:
    filepath = str(Path(filepath).resolve())
    doc = fitz.open(filepath)
    pages_text: List[str] = [page.get_text("text") for page in doc]
    full_text = "\n".join(pages_text)
    first_page = pages_text[0] if pages_text else ""

    meta = PaperMeta(
        title=_extract_title(doc, first_page),
        authors=_clean_authors(doc.metadata.get("author")),
        abstract=_extract_abstract(full_text),
        keywords=_extract_keywords(full_text),
        year=_extract_year(doc, full_text),
        total_pages=doc.page_count,
        filename=Path(filepath).name,
    )
    doc.close()

    return ParsedPaper(
        paper_id=_make_paper_id(filepath),
        meta=meta,
        full_text=full_text,
        sections=_split_sections(full_text),
    )


def _clean_authors(author: Optional[str]) -> Optional[str]:
    if not author:
        return None
    author = author.replace(" and ", ", ").replace("&", ",")
    return author.strip() or None


def _extract_year(doc: fitz.Document, text: str) -> Optional[str]:
    cd = doc.metadata.get("creationDate")
    if cd and len(cd) >= 6:
        # D:YYYYMMDD...
        m = re.search(r"D?:(\d{4})", cd)
        if m:
            return m.group(1)
    m = re.search(r"\b(19|20)\d{2}\b", text[:2000])
    return m.group(0) if m else None
