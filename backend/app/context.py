"""
LLM 客户端：统一封装 OpenAI 兼容协议。

两种调用模式：
1. 全局模式：用 .env 里的 Key（单例，启动时验活）
2. 临时模式：调用时通过 contextvars 注入 user_key，每次创建独立客户端（不保存，用完即丢）

用法（在 FastAPI middleware 里）：
    from litread.context import set_request_user_key
    set_request_user_key(user_key)   # 每个请求开始时设置
"""
import contextvars

# 当前请求的 user_key（如果有）
_current_user_key: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "user_key", default=None
)


def set_request_user_key(key: str | None):
    """middleware 里调用，设置当前请求的用户 Key。"""
    _current_user_key.set(key.strip() if key and key.strip() else None)


def get_request_user_key() -> str | None:
    return _current_user_key.get()
