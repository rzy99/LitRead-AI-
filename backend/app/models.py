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


# ---------- 多论文对比 ----------
class CompareRequest(BaseModel):
    paper_ids: List[str]
    focus: Optional[str] = None  # 可选：对比侧重点（如"方法"、"数据集"）


class CompareResult(BaseModel):
    headers: List[str] = Field(..., description="对比维度列表")
    rows: List[Dict[str, str]] = Field(..., description="每行一篇论文，key=维度")
    consensus: str = Field("", description="共识点")
    divergence: str = Field("", description="分歧点")


# ---------- 文献图谱 ----------
class GraphNode(BaseModel):
    id: str
    label: str
    title: str = ""
    size: int = 10


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float
    label: str = ""


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
