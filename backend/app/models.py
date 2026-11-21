"""Pydantic 数据模型。"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PaperMeta(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    keywords: Optional[str] = None
    year: Optional[str] = None
    total_pages: int = 0
    filename: str = ""


class ParsedPaper(BaseModel):
    paper_id: str
    meta: PaperMeta
    full_text: str
    sections: List[dict] = Field(default_factory=list)


class SummaryResult(BaseModel):
    core_contribution: str = Field(..., description="一句话核心贡献")
    method_highlights: str = Field(..., description="方法亮点")
    key_findings: str = Field(..., description="实验/主要结论")
    limitations: str = Field(..., description="局限性")
    tldr: str = Field(..., description="三句话 TL;DR")


class QuestionRequest(BaseModel):
    question: str
    paper_ids: Optional[List[str]] = None


class AnswerResult(BaseModel):
    answer: str
    sources: List[dict] = Field(default_factory=list)


# ---------- 多论文思路对比 ----------
class CompareRequest(BaseModel):
    paper_ids: List[str]


class ThinkingAxis(BaseModel):
    key: str
    label: str
    phase: str = ""
    hint: str = ""


class ThinkingPaper(BaseModel):
    paper_id: str
    title: str
    year: str = ""
    pattern: str = ""
    cells: List[str] = Field(default_factory=list)
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    path: List[Dict[str, Any]] = Field(default_factory=list)


class CompareResult(BaseModel):
    axes: List[ThinkingAxis] = Field(default_factory=list)
    papers: List[ThinkingPaper] = Field(default_factory=list)
    summary: str = ""


# ---------- 文献图谱 ----------
class GraphNode(BaseModel):
    id: str
    label: str
    title: str = ""
    size: int = 10
    meta: str = ""
    color: str = "#2F5D46"


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float
    label: str = ""
    shared_terms: List[str] = Field(default_factory=list)
    why: str = ""


class GraphResult(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    html: str = ""  # pyvis 生成的可交互 HTML


# ---------- 阅读笔记 ----------
class NoteCreate(BaseModel):
    content: str


class NoteResult(BaseModel):
    id: int
    paper_id: str
    content: str
    ai_summary: Optional[str] = None
    created_at: str = ""


class NotesOrganizeResult(BaseModel):
    organized: str = Field(..., description="AI 整理后的结构化笔记")
    structure: List[Dict[str, Any]] = Field(default_factory=list)


# ---------- 12 步研究工作流 ----------
class ReasoningBeat(BaseModel):
    move: str = ""
    known: str = ""
    question: str = ""
    leap: str = ""
    temptation: str = ""


class ResearchStage(BaseModel):
    """单个阶段的原始输出（字段按阶段不同而不同）。"""
    data: Dict[str, Any] = Field(default_factory=dict)


class ResearchCompareResult(BaseModel):
    aligned: str = ""
    gap: str = ""
    lesson: str = ""
