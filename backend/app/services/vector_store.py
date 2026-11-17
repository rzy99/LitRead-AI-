"""
向量数据库：ChromaDB 持久化 + 自定义 bge embedding。
若 bge 不可用，软降级到 ChromaDB 默认 embedding，并显式标记。
"""
import logging
from typing import List, Dict, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import get_settings, get_abs_path
from . import embeddings

_settings = get_settings()
logger = logging.getLogger(__name__)


class _BGEEmbeddingFunction:
    """ChromaDB 自定义 embedding function，封装 bge 模型。"""

    def __call__(self, input: List[str]) -> List[List[float]]:
        vecs = embeddings.embed(input)
        return vecs.tolist()


class VectorStore:
    def __init__(self):
        chroma_dir = str(get_abs_path(_settings.CHROMA_DIR))
        self.client = chromadb.PersistentClient(
            path=chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # 统一走 embeddings.embed：有 sentence-transformers 用它，
        # 没有则自动回退到 ChromaDB 内置 ONNX 模型，避免两套向量空间混用。
        self.ef = _BGEEmbeddingFunction()
        if not embeddings.is_available():
            logger.warning(
                "sentence-transformers 不可用，回退到 ONNX 内置 embedding：%s",
                embeddings.get_error(),
            )

        self.collection = self.client.get_or_create_collection(
            name="papers",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(
        self,
        paper_id: str,
        chunks: List[str],
        metadatas: Optional[List[Dict]] = None,
    ):
        if not chunks:
            return
        ids = [f"{paper_id}_{i}" for i in range(len(chunks))]
        if metadatas is None:
            metadatas = [{"paper_id": paper_id} for _ in chunks]
        else:
            for m in metadatas:
                m.setdefault("paper_id", paper_id)

        batch = 50
        for i in range(0, len(chunks), batch):
            self.collection.upsert(
                ids=ids[i : i + batch],
                documents=chunks[i : i + batch],
                metadatas=metadatas[i : i + batch],
            )

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        paper_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        where = None
        if paper_ids:
            where = {"paper_id": {"$in": paper_ids}}

        cnt = self.collection.count()
        if cnt == 0:
            return []

        result = self.collection.query(
            query_texts=[query_text],
            n_results=min(n_results, cnt),
            where=where,
        )
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        dists = result.get("distances", [[]])[0]

        return [
            {"document": d, "metadata": m, "distance": dist}
            for d, m, dist in zip(docs, metas, dists)
        ]

    def delete_paper(self, paper_id: str):
        self.collection.delete(where={"paper_id": paper_id})

    def count(self) -> int:
        return self.collection.count()


_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
