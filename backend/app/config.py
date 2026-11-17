"""全局配置。"""
from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-chat"

    # 服务
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # 数据路径
    DATA_DIR: str = "../data"
    PAPERS_DIR: str = "../data/papers"
    CHROMA_DIR: str = "../data/chroma"
    DB_PATH: str = "../data/litread.db"

    # Embedding
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DEVICE: str = "cpu"

    # RAG
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 120
    RAG_TOP_K: int = 6

    # 图谱
    GRAPH_SIMILARITY_THRESHOLD: float = 0.55

    # 摘要
    SUMMARY_MAX_CHARS: int = 15000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_abs_path(relative: str) -> Path:
    base = Path(__file__).resolve().parent.parent
    return (base / relative).resolve()
