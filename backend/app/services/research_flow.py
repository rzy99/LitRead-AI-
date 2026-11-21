"""
12 步研究工作流。

设计原则：
1. 分阶段生成：背景 → 作者路径 → 方法 → 验证 → 批判与创新，
   每段单独调用 LLM，避免一次输出过长导致质量塌陷。
2. 第 3 步做「信息隔离」：先从论文中抽取「方法出现前的知识库」，
   再让模型只看知识库推演作者思路，结构上防止用论文结论反推。
3. 每个结论标注依据类型：论文 / 外部背景 / 模型推演。

对外接口：
    generate_stage(paper, stage) -> dict
    get_brief(paper) -> dict            # 读取已缓存的分段结果
    compare_guess(paper, stage, user_text, brief) -> dict
"""
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from ..config import get_abs_path, get_settings
from ..models import ParsedPaper
from .llm_client import get_llm, is_llm_ready

_settings = get_settings()
_log = logging.getLogger(__name__)

PROMPT_VERSION = "rf-4"
STAGES = ("context", "author", "method", "evidence", "critique", "idea")

_COMMON_RULES = """通用规则：
- 用中文回答；英文术语首次出现时在括号里保留原文，例如「对比学习 (contrastive learning)」。
- 读者是本科生或低年级研究生，数学基础一般，想学“怎么做研究”，不是只要一个摘要。
- 不写没有信息量的套话（如“具有重要意义”“效果显著”）。每个判断尽量落到具体对象、机制或数字。
- 论文没写清楚的地方，直接写「论文未说明」，不要编造。
- 只输出 JSON，不要 Markdown 代码围栏，不要额外解释。"""


# ─────────────────────────────────────────────
#  文本摘取
# ─────────────────────────────────────────────

def _excerpt(text: str, cap: int) -> str:
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= cap:
        return text
    return text[: int(cap * 0.8)] + "\n...[后文省略]...\n" + text[-int(cap * 0.2):]


def _sections_by_keyword(paper: ParsedPaper, keywords: List[str], cap: int) -> str:
    """按标题关键词挑章节，找不到就退回全文开头。"""
    picked = []
    for sec in paper.sections:
        heading = (sec.get("heading") or "").lower()
        if any(k in heading for k in keywords):
            picked.append(f"[{sec['heading']}]\n{sec['content']}")
        if sum(len(p) for p in picked) > cap:
            break
    if picked:
        return _excerpt("\n\n".join(picked), cap)
    return ""


def _digest_context(paper: ParsedPaper) -> str:
    """第 1、2 步：摘要 + 引言 + 相关工作。"""
    parts = []
    if paper.meta and paper.meta.abstract:
        parts.append(f"[Abstract]\n{paper.meta.abstract}")
    intro = _sections_by_keyword(paper, ["introduction", "引言", "前言"], 5000)
    if not intro:
        intro = _excerpt(paper.full_text[:6000], 5000)
    parts.append(intro)
    related = _sections_by_keyword(paper, ["related work", "related", "相关工作", "文献综述"], 4000)
    if related:
        parts.append(related)
    return _excerpt("\n\n".join(p for p in parts if p), 13000)


def _digest_method(paper: ParsedPaper) -> str:
    """第 4-6 步：摘要 + 方法 + 关键定义。"""
    parts = []
    if paper.meta and paper.meta.abstract:
        parts.append(f"[Abstract]\n{paper.meta.abstract}")
    method = _sections_by_keyword(
        paper, ["method", "approach", "proposed", "model", "formulation", "方法", "模型"], 9000
    )
    parts.append(method or _excerpt(paper.full_text, 9000))
    return _excerpt("\n\n".join(p for p in parts if p), 14000)


def _digest_evidence(paper: ParsedPaper) -> str:
    """第 7-8 步：摘要 + 实验/结果。"""
    parts = []
    if paper.meta and paper.meta.abstract:
        parts.append(f"[Abstract]\n{paper.meta.abstract}")
    exp = _sections_by_keyword(
        paper, ["experiment", "evaluation", "result", "ablation", "实验", "结果", "评估"], 9000
    )
    if exp:
        parts.append(exp)
    parts.append(_excerpt(paper.full_text[-6000:], 5000))
    return _excerpt("\n\n".join(p for p in parts if p), 14000)


def _paper_header(paper: ParsedPaper) -> str:
    m = paper.meta
    return (
        f"标题：{m.title or '(未识别)'}\n"
        f"作者：{m.authors or '(未识别)'}\n"
        f"年份：{m.year or '(未识别)'}\n"
        f"关键词：{m.keywords or '(未识别)'}"
    )


# ─────────────────────────────────────────────
#  Prompt
# ─────────────────────────────────────────────

S1_SYSTEM = f"""你是研究方法教练。当前负责 12 步研究工作流的第 1、2 步，以及“方法出现前的知识库”。

第 1 步要回答：
- 论文提出并解决的研究问题是什么？补充必要背景，让外行也能明白问题在问什么。
- 为什么这个问题重要？（对领域、对下游应用、对评估方式分别意味着什么）
- 解决它能带来什么价值？要具体，不要空泛。
- 注意：q1 只讲问题与价值，不得描述本文提出的解法、模块或技术路线；价值要写成“对领域/应用/评估的意义”，不要写成“本文方法的收益”。

第 2 步要回答：
- 这个问题之前被解决了吗？列出 3-6 条代表性前作思路（没有具体论文名时用方法类别描述），逐条说明它的做法与代价。
- 这些前作为什么不够？是假设太强、代价太高、场景不匹配，还是评估掩盖了问题？
- 追问结构性原因：是什么共同的隐含假设，导致大家都没解决？

最后抽取「方法出现前的知识库」：
- 只能写这篇论文的方法提出之前就已经存在的知识。
- 不能包含本文提出的任何技术方案、模块名或贡献结论。
- 按类别给出 10-14 条：领域共识 / 已有方法 / 失败模式 / 经验观察 / 可借用的外部工具。
- 每条一句话，必须具体，尽量带机制或条件；标注来源是「论文 Related Work」「论文 Introduction 的背景描述」还是「领域常识（模型知识，未核验）」。

另给 problem_only：只用 2-3 句描述「问题本身与它为什么难」。
- 不得出现本文提出的方法、模块、技术路线或贡献动词（如“提出…”“引入…”）。
- 不得出现论文标题里的方法关键词。
- 这一段会交给另一个模型做盲推演，泄漏会直接毁掉这一步的价值。

{_COMMON_RULES}

返回 JSON：
{{
  "title_zh": "中文标题（没有就保留原文）",
  "one_line": "一句话说清这篇论文干了什么（不超过 40 字）",
  "problem_only": "只描述问题与困难，不出现任何解法/方法名/技术路线",
  "q1": {{
    "content": "Markdown，含三个小标题：### 研究问题 / ### 为什么重要 / ### 解决后的价值",
    "basis": ["论文 §Introduction", "领域背景（模型知识，未核验）"]
  }},
  "q2": {{
    "content": "Markdown，含三个小标题：### 前人的解法 / ### 为什么不够 / ### 结构性原因",
    "basis": ["论文 §Related Work"]
  }},
  "world_before": [
    {{"kind": "共识|已有方法|失败模式|经验观察|可借用工具", "fact": "一句话", "source": "论文 Related Work"}}
  ]
}}"""


S2_SYSTEM = f"""你是「作者思路逆向推演器」。这是整个 12 步工作流最重要的一步。

你拿到的只有：论文标题、研究问题，以及「方法出现之前作者可能知道的知识条目」。
你拿不到论文的方法，也不允许猜测论文具体用了什么模块名。

任务：重建作者当时的思考路径。要求：
1. 严格站在方法提出之前的时间点思考，不能使用论文自己的贡献作为前提。
2. 按顺序给出 5-7 个思考节拍，每个节拍包含：
   - move：这一步在做什么（观察 / 发现矛盾 / 拆解 / 类比 / 借用 / 关键跳跃）
   - known：只使用给定知识条目里的信息，并注明用了第几条
   - question：由此自然产生的疑问
   - leap：作者可能的直觉跳跃（这是最关键的一环，要具体）
   - temptation：此时最容易被想到、但其实走不通的路
3. 节拍之间要有因果推进：后一个节拍必须建立在前一个节拍暴露的矛盾之上。
4. 不要写成“作者提出了 XX 方法”。要写“如果我是作者，看到 A 与 B 冲突，我会先试 C，因为 D”。
5. 最后给出 blind_spots：作者当时最可能忽略的假设，以及一条没走的替代路线。
6. 明确说明：这是基于有限信息的重建，不是作者自述；不确定处标注「推测」。

{_COMMON_RULES}

返回 JSON：
{{
  "q3": {{
    "content": "一段总述：作者最可能从哪条线索出发，为什么这条线在当时最自然（150 字以内）",
    "beats": [
      {{"move": "观察", "known": "…（知识条目 #3）", "question": "…", "leap": "…", "temptation": "…"}}
    ],
    "blind_spots": "作者最可能忽略的假设 + 一条没走的替代路线",
    "basis": ["基于知识条目 #2 #5 的推演（非作者原话）"]
  }},
  "alternative_paths": [
    "另一条在当时也合理、但作者没选的路线：…（说明它为什么也说得通，以及可能卡在哪）"
  ],
  "confidence": "high|medium|low",
  "confidence_note": "为什么给出这个置信度"
}}"""


S3_SYSTEM = f"""你是方法讲解教练。负责 12 步工作流的第 4、5、6 步，并补上「作者路径 → 论文设计」的映射。

第 4 步 Intuition：
- 用一段话讲清核心 idea 的本质：它到底把什么问题换成了什么更好处理的问题？
- 给一个生活化类比，再说明类比的边界（哪里像、哪里不像）。

第 5 步 具体方法：
- 结合论文中的真实例子（数据集里的一个具体样本；理论论文用最小玩具例子），
  按「输入 → 处理① → 处理② → … → 输出」写完整 pipeline，至少 4 个处理步骤。
- 每一步说明：输入长什么样（维度/表示）、做了什么操作、输出变成什么、为什么需要这一步。

第 6 步 数学推导（面向零基础）：
- 先列「需要的预备概念」：每个概念一句人话解释，不堆定义。
- 给符号表：符号 | 含义 | 维度。
- 用 4-8 步推导链，每步一行公式 + 一句人话解释「这一步在干什么、为什么可以这样推」。
- 最后说明：这个式子在优化/约束什么；如果去掉某一项会发生什么。
- 如果论文没有实质数学推导，content 写清楚原因并给「理论视角下仍需理解的最小概念」，不要硬编公式。
- 公式用 LaTeX（$...$ 或 $$...$$）。

补一个映射：把第 3 步的每个思考节拍对应到论文里的具体设计（不要求逐字，讲清对应关系即可）。
如果第 3 步的推演与论文设计不一致，要诚实指出「作者实际走的是另一条路」。

{_COMMON_RULES}

返回 JSON：
{{
  "q4": {{"content": "Markdown：本质 + 类比 + 类比的边界", "basis": ["论文 §Method"]}},
  "q5": {{"content": "Markdown：输入 → 处理 → 输出，带一个具体例子", "basis": ["论文 §Method", "论文 §Experiments"]}},
  "q6": {{"content": "Markdown：预备概念 + 符号表 + 推导链 + 直觉", "skipped": false, "basis": ["论文 §Method"]}},
  "design_mapping": [
    {{"beat": "节拍 1 的简述", "design": "论文里对应的设计", "comment": "一致 / 部分一致 / 作者走了另一条路"}}
  ]
}}"""


S4_SYSTEM = f"""你是实验审稿教练。负责 12 步工作流的第 7、8 步。

第 7 步：把实验还原成「问题 → 实验 → 答案」的证据链，不要罗列数字。
- 提出 3-5 个论文真正想验证的问题（不是“性能好不好”，而是“如果我的解释成立，应该观察到什么”）。
- 每个问题对应一个实验设计（数据集、基线、消融、指标，只写核心思路）。
- 给出答案：结果是否支持 claim？是部分支持、还是只在特定设置下成立？
- 用 Markdown 表格呈现：| 提出的问题 | 设计的实验 | 答案与边界 |
- 表格后补一段：哪个 claim 的证据最强，哪个最弱。

第 8 步 Take-aways：
- 3-5 条，每条是「可迁移的研究经验」，不是论文结论复述。
- 区分两类：领域结论（这个方法有效）与研究策略（作者怎么把一个模糊想法变成可验证的实验）。

{_COMMON_RULES}

返回 JSON：
{{
  "q7": {{"content": "Markdown 表格 + 证据强弱点评", "basis": ["论文 §Experiments"]}},
  "q8": {{"content": "Markdown 列表：领域结论 + 研究策略，分开写", "basis": ["论文 §Experiments", "论文 §Discussion"]}}
}}"""


S5_SYSTEM = f"""你是红队审稿人 + 研究选题教练。负责 12 步工作流的第 9-12 步。要求锋利、具体、可执行。

第 9 步 最脆弱的假设：
- 拆出 4-6 条支撑论文结论的隐含假设（数据假设、分布假设、度量假设、实现假设、场景假设）。
- 对每条判断：如果它不成立，哪个 claim 会先崩？崩得多严重？现实中它有多容易被打破？
- 最后指出「最脆弱的一条」，并说明为什么是它。

第 10 步 一周最小复现：
- 只复现一个最核心的 claim，不要复现整篇论文。
- 给出 7 天安排：每天做什么、产出什么。
- 明确：最小数据规模、可用的开源模型/基线、评价指标、成功判据、失败判据、最大风险。
- 预算要现实：单卡、公开数据、一周人力。

第 11 步 反例设计：
- 如果我反对这篇论文，我会构造什么输入/数据分布/实验设置来攻击它？
- 说明：攻击的是哪条假设、预期会观察到什么失败模式、如何判定方法真的失败（而不是调参没调好）。
- 如果方法在这种情况下仍然成立，说明它的边界比作者声称的更宽——这本身也是结论。
- 给 3 个反例方案，按成本从低到高排序，标出最值得先做的一个。

{_COMMON_RULES}

返回 JSON：
{{
  "q9": {{"content": "Markdown：假设清单 + 逐条影响 + 最脆弱的一条", "basis": ["论文 §Method", "论文 §Experiments"]}},
  "q10": {{"content": "Markdown：复现目标 + 7 天安排 + 判据 + 风险", "basis": ["论文 §Experiments"]}},
  "q11": {{"content": "Markdown：2-3 个反例方案 + 最该先做的那个", "basis": ["论文 §Method", "模型推演（未核验）"]}}
}}"""


S6_SYSTEM = f"""你是研究选题教练。负责 12 步工作流的第 12 步：提出一个非增量的 follow-up idea。

你不是在给原论文加模块、换数据集、调参。你要重新定义问题本身：
- 从最脆弱的假设出发：如果那条假设不成立，任务应该怎么重新定义？
- 从需求/场景出发：原论文的设定遗漏了哪类真实用户或哪种真实约束？
- 从评价目标出发：原指标优化错了什么，应该换成什么？

给出 2 个方向：
1. 一个「修正缺陷」方向：针对最脆弱的假设，设计一个在新假设下仍然成立的方法或评测。
2. 一个「换需求/换场景」方向：把问题放到原文没覆盖但真实存在的场景里，说明为什么原方法会失效。

每个方向都要写清：
- 新问题是什么（一句话）
- 与原论文的本质区别（不是增量：不能只是“在我们的方法上再加一个模块”）
- 为什么现在可行（数据/模型/算力/评测哪个条件变了）
- 第一个验证实验（一周内能跑的最小实验，含数据和指标）
- 最大风险（最可能失败的原因）

最后推荐一个，并说明如果你只有一周会先做哪个。

{_COMMON_RULES}

返回 JSON：
{{
  "q12": {{
    "content": "Markdown：方向 A（修正缺陷）+ 方向 B（换需求/场景）+ 推荐与理由",
    "basis": ["论文 §Limitations", "模型推演（未核验）"]
  }}
}}"""


# ─────────────────────────────────────────────
#  缓存
# ─────────────────────────────────────────────

def _cache_path(paper: ParsedPaper) -> Path:
    d = get_abs_path(_settings.DATA_DIR) / "research"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{paper.paper_id}.json"


def _cache_key() -> str:
    raw = f"{PROMPT_VERSION}|{_settings.LLM_MODEL}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]


def get_brief(paper: ParsedPaper) -> Dict:
    p = _cache_path(paper)
    if not p.exists():
        return {"paper_id": paper.paper_id, "stages": {}, "version": PROMPT_VERSION}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"paper_id": paper.paper_id, "stages": {}, "version": PROMPT_VERSION}
    if data.get("key") != _cache_key():
        return {"paper_id": paper.paper_id, "stages": {}, "version": PROMPT_VERSION}
    return data


def _save_brief(paper: ParsedPaper, brief: Dict) -> None:
    brief["paper_id"] = paper.paper_id
    brief["key"] = _cache_key()
    brief["version"] = PROMPT_VERSION
    try:
        _cache_path(paper).write_text(
            json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as e:
        _log.warning("研究工作流缓存写入失败：%s", e)


# ─────────────────────────────────────────────
#  生成
# ─────────────────────────────────────────────

def _require_llm():
    if not is_llm_ready():
        raise RuntimeError("LLM 未就绪。请在侧边栏粘贴你的 API Key，或让管理员配置 .env。")


def _chat_json(messages, max_tokens: int) -> Dict:
    return _unwrap(get_llm().chat_json(messages, temperature=0.3, max_tokens=max_tokens))


def _unwrap(data: Dict) -> Dict:
    """模型偶尔会把 JSON 再包一层字符串（{"raw": "{...}"}），这里拆开。"""
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
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return data


def _stage_context(paper: ParsedPaper) -> Dict:
    user = f"{_paper_header(paper)}\n\n【论文正文（摘要 / 引言 / 相关工作）】\n{_digest_context(paper)}"
    return _chat_json(
        [{"role": "system", "content": S1_SYSTEM}, {"role": "user", "content": user}],
        max_tokens=5200,
    )


def _stage_author(paper: ParsedPaper, brief: Dict) -> Dict:
    """信息隔离：只传问题描述 + 方法出现前的知识条目，不传标题和摘要。"""
    ctx = brief["stages"].get("context", {})
    world = ctx.get("world_before", [])
    lines = []
    for i, w in enumerate(world, 1):
        lines.append(f"#{i} [{w.get('kind', '')}] {w.get('fact', '')}")
    problem = ctx.get("problem_only") or (ctx.get("q1") or {}).get("content", "")
    user = (
        f"【要解决的问题（不含解法）】\n{problem}\n\n"
        f"【方法出现之前，作者可能知道的知识条目】\n" + "\n".join(lines)
    )
    return _chat_json(
        [{"role": "system", "content": S2_SYSTEM}, {"role": "user", "content": user}],
        max_tokens=5600,
    )


def _stage_method(paper: ParsedPaper, brief: Dict) -> Dict:
    ctx = brief["stages"].get("context", {})
    auth = brief["stages"].get("author", {})
    beats = (auth.get("q3") or {}).get("beats", [])
    beat_lines = "\n".join(
        f"{i}. [{b.get('move', '')}] 已知：{b.get('known', '')} → 跳跃：{b.get('leap', '')}"
        for i, b in enumerate(beats, 1)
    )
    user = (
        f"{_paper_header(paper)}\n\n"
        f"【第 3 步的推演节拍（用于最后做映射，不要照抄）】\n{beat_lines or '(无)'}\n\n"
        f"【论文方法与摘要】\n{_digest_method(paper)}"
    )
    return _chat_json(
        [{"role": "system", "content": S3_SYSTEM}, {"role": "user", "content": user}],
        max_tokens=6800,
    )


def _stage_evidence(paper: ParsedPaper) -> Dict:
    user = f"{_paper_header(paper)}\n\n【论文摘要与实验部分】\n{_digest_evidence(paper)}"
    return _chat_json(
        [{"role": "system", "content": S4_SYSTEM}, {"role": "user", "content": user}],
        max_tokens=5000,
    )


def _stage_critique(paper: ParsedPaper) -> Dict:
    parts = [
        f"{_paper_header(paper)}",
        f"【摘要】\n{(paper.meta.abstract or '(未识别)')}",
        f"【方法片段】\n{_excerpt(_digest_method(paper), 7000)}",
        f"【结论/局限片段】\n{_excerpt(_digest_evidence(paper), 7000)}",
    ]
    return _chat_json(
        [{"role": "system", "content": S5_SYSTEM}, {"role": "user", "content": "\n\n".join(parts)}],
        max_tokens=6200,
    )


def _stage_idea(paper: ParsedPaper, brief: Dict) -> Dict:
    crit = brief["stages"].get("critique", {})
    q9 = (crit.get("q9") or {}).get("content", "")
    q11 = (crit.get("q11") or {}).get("content", "")
    user = (
        f"{_paper_header(paper)}\n\n"
        f"【第 9 步：最脆弱的假设】\n{q9 or '(无)'}\n\n"
        f"【第 11 步：反例设计】\n{q11 or '(无)'}\n\n"
        f"【摘要】\n{(paper.meta.abstract or '(未识别)')}"
    )
    return _chat_json(
        [{"role": "system", "content": S6_SYSTEM}, {"role": "user", "content": user}],
        max_tokens=5200,
    )


def generate_stage(paper: ParsedPaper, stage: str) -> Dict:
    """生成指定阶段，合并进缓存后返回完整 brief。"""
    if stage not in STAGES:
        raise ValueError(f"未知阶段：{stage}")
    _require_llm()

    brief = get_brief(paper)
    brief.setdefault("stages", {})

    if stage == "context":
        data = _stage_context(paper)
    elif stage == "author":
        if "context" not in brief["stages"]:
            brief["stages"]["context"] = _stage_context(paper)
            _save_brief(paper, brief)
        data = _stage_author(paper, brief)
    elif stage == "method":
        if "author" not in brief["stages"]:
            if "context" not in brief["stages"]:
                brief["stages"]["context"] = _stage_context(paper)
            brief["stages"]["author"] = _stage_author(paper, brief)
            _save_brief(paper, brief)
        data = _stage_method(paper, brief)
    elif stage == "evidence":
        data = _stage_evidence(paper)
    elif stage == "critique":
        data = _stage_critique(paper)
    else:
        if "critique" not in brief["stages"]:
            brief["stages"]["critique"] = _stage_critique(paper)
            _save_brief(paper, brief)
        data = _stage_idea(paper, brief)

    brief["stages"][stage] = data
    brief["paper_id"] = paper.paper_id
    brief["title"] = (
        brief.get("title")
        or (brief["stages"].get("context") or {}).get("title_zh")
        or (data.get("title_zh") if isinstance(data, dict) else None)
        or paper.meta.title
        or ""
    )
    _save_brief(paper, brief)
    return brief


def brief_to_markdown(brief: Dict) -> str:
    """把 12 步结果拼成一份 Markdown，供笔记合并与 PDF 导出复用。"""
    stages = (brief or {}).get("stages", {})
    if not stages:
        return ""

    out: List[str] = []

    def add(num: int, title: str, data, beats: bool = False):
        if not isinstance(data, dict) or not (data.get("content") or "").strip():
            return
        out.append(f"### {num:02d} {title}")
        out.append(data["content"].strip())
        if beats:
            for i, b in enumerate(data.get("beats", []), 1):
                out.append(
                    f"{i}. **{b.get('move', '思考')}** — 当时已知：{b.get('known', '')}；"
                    f"疑问：{b.get('question', '')}；跳跃：{b.get('leap', '')}；"
                    f"最容易走错：{b.get('temptation', '')}"
                )
            if data.get("blind_spots"):
                out.append(f"**盲点**：{data['blind_spots']}")
        out.append("")

    ctx = stages.get("context", {})
    title = brief.get("title") or ctx.get("title_zh") or ""
    out.append(f"# 研究流：{title}".strip())
    if ctx.get("one_line"):
        out.append(f"> {ctx['one_line']}")
        out.append("")

    add(1, "研究问题：它为什么值得做", ctx.get("q1"))
    add(2, "前史：前人为什么不够", ctx.get("q2"))

    world = ctx.get("world_before") or []
    if world:
        out.append("### 方法出现之前，作者知道的世界")
        for w in world:
            out.append(f"- [{w.get('kind', '')}] {w.get('fact', '')}")
        out.append("")

    auth = stages.get("author", {})
    add(3, "作者最可能的思考路径", auth.get("q3"), beats=True)
    if auth.get("alternative_paths"):
        out.append("**当时也说得通、但作者没走的路线**")
        for x in auth["alternative_paths"]:
            out.append(f"- {x}")
        out.append("")

    method = stages.get("method", {})
    add(4, "Intuition：核心 idea 的本质", method.get("q4"))
    add(5, "具体方法：一个真实样本的 pipeline", method.get("q5"))
    add(6, "数学推导：从零开始", method.get("q6"))

    mapping = method.get("design_mapping") or []
    if mapping:
        out.append("### 推演 ↔ 论文设计对照")
        out.append("| 推演 | 论文设计 | 判断 |")
        out.append("|---|---|---|")
        for x in mapping:
            out.append(f"| {x.get('beat', '')} | {x.get('design', '')} | {x.get('comment', '')} |")
        out.append("")

    ev = stages.get("evidence", {})
    add(7, "问题 → 实验 → 答案", ev.get("q7"))
    add(8, "Take-aways", ev.get("q8"))

    crit = stages.get("critique", {})
    add(9, "最脆弱的假设", crit.get("q9"))
    add(10, "一周最小复现", crit.get("q10"))
    add(11, "如果我反对它：反例设计", crit.get("q11"))

    add(12, "Follow-up idea：从缺陷到新问题", stages.get("idea", {}).get("q12"))

    return "\n".join(out).strip()


def compare_guess(paper: ParsedPaper, stage: str, guess: str, brief: Dict) -> Dict:
    """把用户自己的推演和 AI 的重建做对照，给一条研究思维反馈。"""
    _require_llm()
    guess = (guess or "").strip()
    if not guess:
        raise ValueError("请先写下你的想法")

    if stage == "author":
        ai_view = json.dumps((brief.get("stages", {}).get("author") or {}).get("q3", {}),
                             ensure_ascii=False)[:6000]
        focus = "作者思路重建"
    elif stage == "critique":
        ai_view = json.dumps((brief.get("stages", {}).get("critique") or {}).get("q11", {}),
                             ensure_ascii=False)[:6000]
        focus = "反例设计"
    elif stage == "idea":
        ai_view = json.dumps((brief.get("stages", {}).get("idea") or {}).get("q12", {}),
                             ensure_ascii=False)[:6000]
        focus = "follow-up idea"
    else:
        ai_view = json.dumps(brief.get("stages", {}), ensure_ascii=False)[:6000]
        focus = "研究判断"

    system = f"""你是研究思维教练。用户先自己写了对「{focus}」的想法，现在要和 AI 的分析做对照。

只做三件事，每件 2-3 句，锋利、具体：
1. 对齐：用户已经想到了什么（指出具体点，不要泛泛表扬）。
2. 缺口：用户漏掉了哪个关键因果环节或哪条知识，为什么这个缺口会导致错误结论。
3. 方法课：从这次对照里，提炼一条可迁移的研究思考习惯（例如“先找失败模式，再找工具”）。

不要重写用户的答案，不要长篇教学。{_COMMON_RULES}

返回 JSON：{{"aligned": "…", "gap": "…", "lesson": "…"}}"""

    user = f"【用户的想法】\n{guess}\n\n【AI 的分析】\n{ai_view}"
    return _chat_json(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=2000,
    )
