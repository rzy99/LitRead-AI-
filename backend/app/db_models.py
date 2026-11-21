"""ORM 模型。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String(64), primary_key=True)  # paper_id (md5 hash)
    filename = Column(String(255), nullable=False)
    filepath = Column(Text, nullable=False)
    title = Column(Text)
    authors = Column(Text)
    abstract = Column(Text)
    keywords = Column(Text)
    year = Column(String(20))
    total_pages = Column(Integer, default=0)
    indexed = Column(Integer, default=0)  # 是否已加入向量索引
    indexed_chunks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    notes = relationship("Note", back_populates="paper", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(String(64), ForeignKey("papers.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)  # 用户高亮/批注原文
    ai_summary = Column(Text)  # AI 整理后的结构化笔记
    created_at = Column(DateTime, default=datetime.utcnow)

    paper = relationship("Paper", back_populates="notes")


class CompareScore(Base):
    """第 3 步「用户推演 ↔ 作者路径」的近似对照分数（本地成长曲线用）。"""
    __tablename__ = "compare_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(String(64), index=True)
    session_id = Column(String(64), index=True)
    score = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
