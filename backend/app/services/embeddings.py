"""
Embedding 服务：sentence-transformers，惰性加载。
首次调用时才下载/加载模型，避免模块导入阶段阻塞 FastAPI 启动。
"""
from typing import List, Optional
import numpy as np

from ..config import get_settings

_settings = get_settings()

_model = None
_available: Optional[bool] = None  # None=未尝试, True=可用, False=不可用
_error_msg: str = ""


def _load_model():
    """惰性加载 sentence-transformers 模型。"""
    global _model, _available, _error_msg
    if _model is not None:
        return
    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(
            _settings.EMBEDDING_MODEL,
            device=_settings.EMBEDDING_DEVICE,
        )
        _available = True
    except ImportError as e:
        _available = False
        _error_msg = f"sentence-transformers 未安装：{e}"
    except Exception as e:
        _available = False
        _error_msg = f"Embedding 模型加载失败：{e}"


def is_available() -> bool:
    if _available is None:
        _load_model()
    return _available


def get_error() -> str:
    return _error_msg


_onnx_ef = None


def _get_onnx_ef():
    """ChromaDB 内置的 ONNX MiniLM 模型，作为轻量回退。"""
    global _onnx_ef
    if _onnx_ef is None:
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

        _onnx_ef = ONNXMiniLM_L6_V2()
    return _onnx_ef


def embed(texts: List[str]) -> np.ndarray:
    """返回已归一化的 numpy 数组 (n, dim)。

    优先用 sentence-transformers；未安装时回退到 ChromaDB 内置 ONNX 模型，
    保证未装 PyTorch 的环境也有可用的向量能力。
    """
    if is_available():
        assert _model is not None
        return _model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

    try:
        vecs = np.asarray(_get_onnx_ef()(texts), dtype=np.float32)
    except Exception as e:
        detail = f"{e}；降级原因：{_error_msg}" if _error_msg else str(e)
        raise RuntimeError(f"Embedding 不可用：{detail}") from e

    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.clip(norms, 1e-9, None)


def embed_one(text: str) -> np.ndarray:
    return embed([text])[0]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """计算两个向量的余弦相似度（已 normalize 时即为点积）。"""
    return float(np.dot(a, b))
