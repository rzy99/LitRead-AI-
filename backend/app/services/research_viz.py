"""
研究流可视化数据（viz.json）。

设计约束：
- 不调用模型，不修改 research_flow 的 PROMPT_VERSION / 缓存。
- 独立缓存 data/research/{paper_id}.viz.json，版本 VIZ_VERSION。
- 所有结构化内容都从已有研究流字段确定性抽取；抽不到就留空，不编造。
"""
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..config import get_abs_path, get_settings
from ..database import SessionLocal
from ..db_models import CompareScore
from ..models import ParsedPaper
from . import research_flow

_settings = get_settings()
_log = logging.getLogger(__name__)

VIZ_VERSION = "vz-4"

STEP_TITLES = {
    1: "研究问题：它为什么值得做",
    2: "前史：前人为什么不够",
    3: "作者最可能的思考路径",
    4: "Intuition：核心 idea 的本质",
    5: "具体方法：一个真实样本的 pipeline",
    6: "数学推导：从零开始",
    7: "问题 → 实验 → 答案",
    8: "Take-aways",
    9: "最脆弱的假设",
    10: "一周最小复现",
    11: "如果我反对它：反例设计",
    12: "Follow-up idea：从缺陷到新问题",
}
STEP_STAGE = {
    1: ("context", "q1"), 2: ("context", "q2"), 3: ("author", "q3"),
    4: ("method", "q4"), 5: ("method", "q5"), 6: ("method", "q6"),
    7: ("evidence", "q7"), 8: ("evidence", "q8"),
    9: ("critique", "q9"), 10: ("critique", "q10"), 11: ("critique", "q11"),
    12: ("idea", "q12"),
}
# 没有 basis 字段时的兜底语义（与前端步骤卡原来的 tag 一致）
STEP_FALLBACK = {
    1: "mixed", 2: "paper", 3: "inference",
    4: "paper", 5: "paper", 6: "paper",
    7: "paper", 8: "mixed",
    9: "inference", 10: "inference", 11: "inference", 12: "inference",
}
KINDS = ("paper", "external", "inference", "mixed")


# ─────────────────────────────────────────────
#  文本工具
# ─────────────────────────────────────────────

def _clip(text, n: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _norm(text: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(text or "").lower())


def _tokens(text: str) -> set:
    s = _norm(text)
    if not s:
        return set()
    out = set()
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]", s))
    if len(cjk) >= 2:
        out |= {cjk[i:i + 2] for i in range(len(cjk) - 1)}
    elif cjk:
        out.add(cjk)
    out |= set(re.findall(r"[a-z][a-z0-9_\-]{1,}", s))
    out |= set(re.findall(r"\d+(?:\.\d+)?", s))
    return out


def _dice(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return 2.0 * len(a & b) / (len(a) + len(b))


def _coverage(part: set, whole: set) -> float:
    if not part or not whole:
        return 0.0
    return len(part & whole) / len(part)


def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[。！？!?；;])\s*|\n+", str(text or ""))
    return [p.strip() for p in parts if p.strip()]


def _find_year(text: str) -> Optional[int]:
    m = re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", str(text or ""))
    if not m:
        return None
    year = int(m.group(1))
    return year if 1900 <= year <= 2030 else None


def _basis_kind(basis: List[str], fallback: str = "paper") -> str:
    text = " ".join(str(x) for x in (basis or []))
    low = text.lower()
    paper_keys = ("论文", "§", "abstract", "introduction", "method", "experiment",
                  "related work", "discussion", "limitation")
    infer_keys = ("推演", "推测", "模型知识", "模型推演", "未核验")
    ext_keys = ("领域背景", "领域常识", "外部", "背景知识", "领域常识")
    has_paper = any(k in low for k in paper_keys)
    has_infer = any(k in text for k in infer_keys)
    has_ext = any(k in text for k in ext_keys)
    if has_paper and (has_infer or has_ext):
        return "mixed"
    if has_paper:
        return "paper"
    if has_infer:
        return "inference"
    if has_ext:
        return "external"
    return fallback if fallback in KINDS else "paper"


# ─────────────────────────────────────────────
#  Markdown 结构解析
# ─────────────────────────────────────────────

def _parse_md_table(md: str) -> Tuple[List[str], List[Dict[str, str]]]:
    lines = [l.strip() for l in str(md or "").splitlines() if l.strip().startswith("|")]
    if len(lines) < 2:
        return [], []

    def cells(line: str) -> List[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    headers = cells(lines[0])
    rows: List[Dict[str, str]] = []
    for line in lines[1:]:
        if re.fullmatch(r"\|?[\s:\-|]+\|?", line):
            continue
        vals = cells(line)
        if len(vals) < len(headers):
            vals += [""] * (len(headers) - len(vals))
        row = dict(zip(headers, vals[: len(headers)]))
        if any(v for v in row.values()):
            rows.append(row)
    return headers, rows


def _parse_assumptions(md: str) -> List[Dict[str, str]]:
    text = str(md or "")
    heads: List[Tuple[int, str]] = []
    head_pat = r"^\s*(?:\*\*\s*(?:假设\s*[A-Z0-9]+|[A-Z]\d+)[^\n]*\*\*|###\s*(?:假设\s*[A-Z0-9]+|[A-Z]\d+)[^\n]*)\s*$"
    for m in re.finditer(head_pat, text, flags=re.M):
        title = m.group(0).strip().lstrip("#").strip().strip("*").strip()
        heads.append((m.start(), title))
    out: List[Dict[str, str]] = []
    for i, (pos, title) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        body = text[pos:end].split("\n", 1)[1] if "\n" in text[pos:end] else ""
        body = body.strip()
        ident = re.match(r"(假设\s*[A-Z0-9]+|[A-Z]\d+)", title)
        if_broken = ""
        for line in body.splitlines():
            if "不成立" in line and ("若" in line or "如果" in line):
                if_broken = re.sub(r"^\s*[-*]\s*", "", line).strip()
                break
        severity = ""
        fragility = ""
        for line in body.splitlines():
            if "严重程度" in line:
                severity = re.sub(r"^\s*[-*]\s*", "", line).strip()
            if ("易破" in line or "被打破" in line or "脆弱" in line) and (
                    "容易" in line or "程度" in line or "高" in line):
                fragility = re.sub(r"^\s*[-*]\s*", "", line).strip()
        out.append({
            "id": ident.group(1) if ident else f"假设 {i + 1}",
            "title": title,
            "body": body,
            "if_broken": if_broken,
            "severity": severity,
            "fragility": fragility,
        })
    return out


def _parse_counterexamples(md: str) -> List[Dict[str, str]]:
    text = str(md or "")
    parts = re.split(r"\n(?=###\s*反例(?:方案)?\s*\d+)", text)
    out: List[Dict[str, str]] = []
    for part in parts:
        if not part.strip().startswith("###"):
            continue
        lines = [l.strip() for l in part.strip().splitlines() if l.strip()]
        if not lines:
            continue
        title = lines[0].lstrip("#").strip()
        fields = {"attack": "", "construction": "", "failure": "", "verdict": "", "cost": ""}
        for line in lines[1:]:
            body = re.sub(r"^\s*[-*]\s*", "", line).strip()
            body = body.replace("**", "")
            if body.startswith("攻击的假设"):
                fields["attack"] = body
            elif body.startswith("构造"):
                fields["construction"] = body
            elif body.startswith("预期失败模式"):
                fields["failure"] = body
            elif body.startswith("判定方法真的失败"):
                fields["verdict"] = body
            elif body.startswith("成本"):
                fields["cost"] = body
        m = re.match(r"反例(?:方案)?\s*(\d+)", title)
        out.append({
            "id": f"counter-{m.group(1) if m else len(out) + 1}",
            "title": title,
            "attack": fields["attack"],
            "construction": fields["construction"],
            "failure": fields["failure"],
            "verdict": fields["verdict"],
            "cost": fields["cost"],
        })
    return out


# ─────────────────────────────────────────────
#  各可视化结构
# ─────────────────────────────────────────────

def _shares(counts: Dict[str, int], total: int) -> Dict[str, int]:
    if total <= 0:
        return {k: 0 for k in counts}
    raw = {k: counts.get(k, 0) * 100.0 / total for k in counts}
    floors = {k: int(v) for k, v in raw.items()}
    remain = 100 - sum(floors.values())
    order = sorted(raw, key=lambda k: raw[k] - floors[k], reverse=True)
    for k in order[:max(0, remain)]:
        floors[k] += 1
    return floors


def _build_basis(stages: Dict) -> Dict:
    steps = []
    counts = {k: 0 for k in KINDS}
    for num in range(1, 13):
        stage_key, qkey = STEP_STAGE[num]
        data = (stages.get(stage_key) or {}).get(qkey) or {}
        basis = data.get("basis") or []
        if not data:
            steps.append({"index": num, "title": STEP_TITLES[num], "kind": None, "basis": []})
            continue
        kind = _basis_kind(basis, STEP_FALLBACK.get(num, "paper"))
        counts[kind] += 1
        steps.append({
            "index": num,
            "title": STEP_TITLES[num],
            "kind": kind,
            "basis": [str(x) for x in basis],
        })
    generated = sum(counts.values())
    missing = max(0, 12 - generated)
    counts["missing"] = missing
    return {
        "steps": steps,
        "counts": counts,
        "shares": _shares(counts, 12),
        "generated": generated,
        "total": 12,
    }


def _reason_dropped(text: str) -> str:
    segs = [s.strip() for s in re.split(r"(?<=[。！？；;])", str(text or "")) if s.strip()]
    keys = ("卡在", "撞上", "代价", "问题在于", "限制", "无法", "难以", "不如")
    picked = [s for s in segs if any(k in s for k in keys)]
    if picked:
        reason = "".join(picked[-2:]) if len(picked) >= 2 else picked[0]
    else:
        reason = segs[-1] if segs else str(text or "")
    return _clip(reason, 180)


def _build_fork(stages: Dict, meta: Dict) -> Dict:
    auth = stages.get("author") or {}
    q3 = auth.get("q3") or {}
    raw_beats = q3.get("beats") or []
    beats = []
    for i, b in enumerate(raw_beats):
        b = b if isinstance(b, dict) else {}
        beats.append({
            "index": i,
            "move": _clip(b.get("move") or "思考", 24),
            "known": _clip(b.get("known") or "", 420),
            "question": _clip(b.get("question") or "", 320),
            "leap": _clip(b.get("leap") or "", 420),
            "temptation": _clip(b.get("temptation") or "", 320),
        })

    alts = []
    for i, raw in enumerate(auth.get("alternative_paths") or []):
        text = str(raw or "").strip()
        if not text:
            continue
        best_idx, best_score = (len(beats) - 1 if beats else 0), 0.0
        alt_tokens = _tokens(text)
        for b in beats:
            score = _coverage(alt_tokens, _tokens(
                " ".join([b["move"], b["known"], b["question"], b["leap"], b["temptation"]])
            ))
            if score > best_score:
                best_idx, best_score = b["index"], score
        alts.append({
            "id": f"alt-{i + 1}",
            "label": f"备选路线 {'ABCDEFGH'[i] if i < 8 else i + 1}",
            "text": _clip(text, 600),
            "branch_from": best_idx,
            "reason_dropped": _reason_dropped(text),
        })

    mapping = []
    for m in (stages.get("method") or {}).get("design_mapping") or []:
        if not isinstance(m, dict):
            continue
        mapping.append({
            "beat": _clip(m.get("beat") or "", 180),
            "design": _clip(m.get("design") or "", 260),
            "comment": _clip(m.get("comment") or "", 80),
        })

    ctx = stages.get("context") or {}
    return {
        "paper": {"title": meta.get("title") or "", "year": meta.get("year") or ""},
        "summary": {
            "problem": _clip(ctx.get("problem_only") or "", 500),
            "world_count": len(ctx.get("world_before") or []),
        },
        "beats": beats,
        "alternatives": alts,
        "design": mapping,
        "confidence": auth.get("confidence") or "",
        "confidence_note": _clip(auth.get("confidence_note") or "", 220),
        "blind_spots": _clip(q3.get("blind_spots") or "", 400),
    }


def _build_argument(stages: Dict) -> Dict:
    ev = stages.get("evidence") or {}
    cr = stages.get("critique") or {}
    headers, rows = _parse_md_table((ev.get("q7") or {}).get("content") or "")
    assumptions = _parse_assumptions((cr.get("q9") or {}).get("content") or "")
    counters = _parse_counterexamples((cr.get("q11") or {}).get("content") or "")

    candidates = []
    for a in assumptions:
        candidates.append({
            "kind": "假设",
            "id": a["id"],
            "title": a["title"],
            "detail": a["if_broken"] or _clip(a["body"], 260),
            "tokens": _tokens(a["title"] + " " + a["body"]),
        })
    counter_cands = []
    for c in counters:
        counter_cands.append({
            "kind": "反例",
            "id": c["id"],
            "title": c["title"],
            "detail": c["failure"] or _clip(c["construction"], 260),
            "tokens": _tokens(" ".join([c["title"], c["attack"], c["construction"], c["failure"]])),
        })

    def pair(a: set, b: set) -> float:
        return max(_coverage(a, b), _coverage(b, a), _dice(a, b))

    def pick(cands, target, used, threshold):
        ranked = sorted(((pair(c["tokens"], target), c) for c in cands),
                        key=lambda x: x[0], reverse=True)
        for score, cand in ranked:
            if cand["id"] in used:
                continue
            if score >= threshold:
                used.add(cand["id"])
                return cand
        return None

    claims = []
    used_a, used_c = set(), set()
    for i, row in enumerate(rows):
        vals = list(row.values())
        question = vals[0] if len(vals) > 0 else ""
        experiment = vals[1] if len(vals) > 1 else ""
        answer = vals[2] if len(vals) > 2 else ""
        target = _tokens(" ".join(vals))
        best_a = pick(candidates, target, used_a, 0.14)
        best_c = pick(counter_cands, target, used_c, 0.075)
        attacks = []
        for cand in (best_a, best_c):
            if not cand:
                continue
            attacks.append({
                "kind": cand["kind"],
                "id": cand["id"],
                "title": _clip(cand["title"], 160),
                "detail": _clip(cand["detail"], 260),
                "broken": True,
            })
        claims.append({
            "id": f"claim-{i + 1}",
            "question": _clip(question, 260),
            "answer": _clip(answer, 300),
            "claim": _clip(answer or question, 300),
            "support": _clip(experiment, 300),
            "attacks": attacks,
        })

    fragile = ""
    for a in assumptions:
        if "高" in a["severity"] and ("高" in a["fragility"] or "较高" in a["fragility"]):
            fragile = _clip(a["title"] + " " + a["if_broken"], 320)
            break
    if not fragile:
        m = re.search(r"[^\n]*最脆弱[^\n]*", (cr.get("q9") or {}).get("content") or "")
        fragile = _clip(m.group(0) if m else "", 320)

    return {
        "headers": headers,
        "claims": claims,
        "assumptions": [
            {
                "id": a["id"], "title": _clip(a["title"], 220),
                "body": _clip(a["body"], 500),
                "severity": a["severity"], "fragility": a["fragility"],
            }
            for a in assumptions
        ],
        "counterexamples": [
            {
                "id": c["id"], "title": _clip(c["title"], 220),
                "attack": c["attack"], "construction": _clip(c["construction"], 420),
                "failure": _clip(c["failure"], 320), "verdict": _clip(c["verdict"], 260),
                "cost": c["cost"],
            }
            for c in counters
        ],
        "fragile": fragile,
    }


def _build_timeline(stages: Dict, meta: Dict) -> Dict:
    ctx = stages.get("context") or {}
    dated, undated = [], []
    for w in ctx.get("world_before") or []:
        if not isinstance(w, dict):
            continue
        fact = str(w.get("fact") or "").strip()
        if not fact:
            continue
        item = {
            "kind": str(w.get("kind") or ""),
            "fact": _clip(fact, 220),
            "source": _clip(w.get("source") or "", 100),
        }
        year = _find_year(fact)
        if year is None:
            year = _find_year(item["source"])
        if year is None:
            undated.append(item)
        else:
            item["year"] = year
            dated.append(item)
    dated.sort(key=lambda x: x["year"])

    paper_year = _find_year(meta.get("year") or "")
    paper = {
        "year": paper_year,
        "title": meta.get("title") or "",
        "label": "本文" + (f" · {paper_year}" if paper_year else ""),
    }
    return {"items": dated, "undated": undated[:9], "paper": paper}


def build_viz(paper: ParsedPaper, brief: Dict) -> Dict:
    stages = brief.get("stages") or {}
    meta = {
        "title": (paper.meta.title if paper.meta else "") or "",
        "year": (paper.meta.year if paper.meta else "") or "",
    }
    return {
        "paper_id": paper.paper_id,
        "version": VIZ_VERSION,
        "ready": bool(stages),
        "source_key": _fingerprint(brief),
        "basis": _build_basis(stages),
        "fork": _build_fork(stages, meta),
        "argument": _build_argument(stages),
        "timeline": _build_timeline(stages, meta),
    }


# ─────────────────────────────────────────────
#  缓存
# ─────────────────────────────────────────────

def _cache_path(paper: ParsedPaper) -> Path:
    d = get_abs_path(_settings.DATA_DIR) / "research"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{paper.paper_id}.viz.json"


def _fingerprint(brief: Dict) -> str:
    raw = json.dumps(brief.get("stages") or {}, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def get_viz(paper: ParsedPaper) -> Dict:
    brief = research_flow.get_brief(paper)
    fp = _fingerprint(brief)
    p = _cache_path(paper)
    if p.exists():
        try:
            cached = json.loads(p.read_text(encoding="utf-8"))
            if (cached.get("version") == VIZ_VERSION
                    and cached.get("source_key") == fp
                    and cached.get("paper_id") == paper.paper_id):
                return cached
        except Exception:
            pass
    data = build_viz(paper, brief)
    try:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        _log.warning("viz 缓存写入失败：%s", e)
    return data


# ─────────────────────────────────────────────
#  用户推演对照（确定性，不调模型）
# ─────────────────────────────────────────────

def _save_score(paper_id: str, session_id: str, score: int) -> None:
    try:
        db = SessionLocal()
        try:
            db.add(CompareScore(
                paper_id=paper_id,
                session_id=session_id,
                score=int(score),
            ))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        _log.warning("推演成长分数写入失败：%s", e)


def compare_guess_structured(paper: ParsedPaper, guess: str, viz: Dict,
                             session_id: str = "anonymous") -> Dict:
    guess = (guess or "").strip()
    if not guess:
        raise ValueError("请先写下你的推演")
    beats = (viz.get("fork") or {}).get("beats") or []
    if not beats:
        raise ValueError("这篇论文还没有第 3 步推演，无法对照")

    guess_sents = _sentences(guess)
    guess_tokens = _tokens(guess)
    statuses = []
    hits = partials = 0

    for b in beats:
        beat_text = " ".join([b.get("move", ""), b.get("known", ""),
                              b.get("question", ""), b.get("leap", ""), b.get("temptation", "")])
        beat_tokens = _tokens(beat_text)
        score = max(_dice(guess_tokens, beat_tokens),
                    _coverage(guess_tokens, beat_tokens))
        if score >= 0.20:
            status = "hit"
            hits += 1
        elif score >= 0.10:
            status = "partial"
            partials += 1
        else:
            status = "miss"
        best_sent, best_score = "", -1.0
        for s in guess_sents:
            s_tokens = _tokens(s)
            s_score = max(_dice(s_tokens, beat_tokens),
                          _coverage(s_tokens, beat_tokens))
            if s_score > best_score:
                best_sent, best_score = s, s_score
        statuses.append({
            "index": b["index"],
            "status": status,
            "evidence": _clip(best_sent, 90) if best_score > 0 else "",
        })

    n = len(beats)
    score = round(100.0 * (hits + 0.5 * partials) / n) if n else 0
    stage_tokens = {b["index"]: _tokens(" ".join(
        [b.get("move", ""), b.get("known", ""), b.get("question", ""),
         b.get("leap", ""), b.get("temptation", "")]
    )) for b in beats}

    extra = []
    for s in guess_sents:
        if len(s) < 8:
            continue
        s_tokens = _tokens(s)
        if max((max(_dice(s_tokens, t), _coverage(s_tokens, t))
                for t in stage_tokens.values()), default=0.0) >= 0.10:
            continue
        if s not in extra:
            extra.append(_clip(s, 120))
        if len(extra) >= 5:
            break

    diverge_at = next((s["index"] for s in statuses if s["status"] == "miss"), None)
    diverge_to = "none"
    if diverge_at is not None:
        # 整段推演更像某条备选路线时才改道；否则先看用户有没有提出作者路径外的点。
        author_tokens = _tokens(" ".join(
            " ".join([b.get("move", ""), b.get("known", ""), b.get("question", ""),
                      b.get("leap", ""), b.get("temptation", "")]) for b in beats
        ))
        author_sim = max(_dice(guess_tokens, author_tokens),
                         _coverage(guess_tokens, author_tokens),
                         _coverage(author_tokens, guess_tokens))
        best_alt, best_score = None, 0.0
        for alt in (viz.get("fork") or {}).get("alternatives") or []:
            alt_tokens = _tokens(alt.get("text") or "")
            score_alt = max(
                _coverage(alt_tokens, guess_tokens),
                _coverage(guess_tokens, alt_tokens),
                _dice(alt_tokens, guess_tokens),
            )
            if score_alt > best_score:
                best_alt, best_score = alt, score_alt
        if best_alt and best_score >= 0.18 and best_score > author_sim:
            diverge_to = best_alt["id"]
            branch = int(best_alt.get("branch_from") or 0)
            if branch < len(statuses) and statuses[branch]["status"] != "hit":
                diverge_at = branch
        elif extra:
            # 只有作者路径外的句子才可能支撑「你的新路线」或另一条备选。
            best_alt, best_score = None, 0.0
            for alt in (viz.get("fork") or {}).get("alternatives") or []:
                alt_tokens = _tokens(alt.get("text") or "")
                score_alt = max((_coverage(alt_tokens, _tokens(s)) for s in extra), default=0.0)
                if score_alt > best_score:
                    best_alt, best_score = alt, score_alt
            diverge_to = best_alt["id"] if (best_alt and best_score >= 0.18) else "novel"

    if diverge_at is None:
        if partials:
            summary = f"你命中 {hits}/{n} 个关键动作，其余 {partials} 个只对上了一部分；整体路径与作者基本重合。"
        else:
            summary = f"你命中了全部 {n} 个关键动作，路径与作者基本重合。"
    else:
        move = beats[diverge_at].get("move") or "关键动作"
        prefix = f"你命中了 {hits}/{n} 个关键动作"
        if partials:
            prefix += f"，另有 {partials} 个只对上了一部分"
        if diverge_to.startswith("alt-"):
            alt = next((a for a in (viz.get("fork") or {}).get("alternatives") or []
                        if a.get("id") == diverge_to), None)
            reason = (alt or {}).get("reason_dropped") or "它在当时有难以回避的代价。"
            reason = _clip(reason, 90).rstrip("。；;")
            summary = (f"{prefix}，在第 {diverge_at + 1} 个动作"
                       f"「{move}」处走向了{(alt or {}).get('label', '备选路线')}——"
                       f"作者当年放弃它，是因为{reason}。")
        elif diverge_to == "novel":
            summary = (f"{prefix}，在第 {diverge_at + 1} 个动作"
                       f"「{move}」处走向了一条作者没有走的路线。")
        else:
            summary = (f"{prefix}，但在第 {diverge_at + 1} 个动作"
                       f"「{move}」处没有覆盖到作者的这一步。")

    sid = re.sub(r"[^0-9A-Za-z_\-]", "", str(session_id or ""))[:64] or "anonymous"
    _save_score(paper.paper_id, sid, score)

    return {
        "score": score,
        "beats": statuses,
        "extra": extra,
        "diverge_at": diverge_at,
        "diverge_to": diverge_to,
        "summary": summary,
        "method": "近似对照：按中文二元字 / 英文词 / 数字的重合度计算，不调用模型。",
    }


def get_growth(session_id: str) -> Dict:
    sid = re.sub(r"[^0-9A-Za-z_\-]", "", str(session_id or ""))[:64]
    if not sid:
        return {"scores": [], "papers": 0, "avg": 0, "count": 0}
    try:
        db = SessionLocal()
        try:
            rows = (db.query(CompareScore)
                    .filter(CompareScore.session_id == sid)
                    .order_by(CompareScore.created_at.asc(), CompareScore.id.asc())
                    .limit(200).all())
            scores = [{
                "paper_id": r.paper_id,
                "score": int(r.score),
                "created_at": r.created_at.isoformat() + "Z" if r.created_at else "",
            } for r in rows]
        finally:
            db.close()
    except Exception as e:
        _log.warning("读取推演成长失败：%s", e)
        return {"scores": [], "papers": 0, "avg": 0, "count": 0}
    avg = round(sum(x["score"] for x in scores) / len(scores), 1) if scores else 0
    return {
        "scores": scores,
        "papers": len({x["paper_id"] for x in scores}),
        "avg": avg,
        "count": len(scores),
    }
