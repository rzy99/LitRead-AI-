"""
LLM 客户端：统一封装 OpenAI 兼容协议。

优先使用 contextvars 注入的 user_key（前端粘贴的），
没有的话用 .env 全局 Key，都没有则 Demo 模式。
"""
import json
import logging
from typing import List, Dict, Optional

from openai import OpenAI

from ..config import get_settings
from ..context import get_request_user_key

_settings = get_settings()
_log = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, base_url=None, api_key=None, model=None, verify=True):
        self.base_url = base_url or _settings.LLM_BASE_URL
        self.api_key = api_key or _settings.LLM_API_KEY
        self.model = model or _settings.LLM_MODEL
        if not self.api_key:
            raise RuntimeError("LLM API Key 未配置")
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=30)
        if verify:
            self._verify()

    def _verify(self):
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
        except Exception as e:
            raise RuntimeError(f"LLM 连接失败：{e}") from e

    def chat(self, messages, temperature=0.3, max_tokens=1500, response_format=None):
        kwargs = dict(model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        if response_format:
            kwargs["response_format"] = response_format
        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def chat_json(self, messages, temperature=0.2, max_tokens=2000):
        content = self.chat(messages, temperature=temperature, max_tokens=max_tokens,
                            response_format={"type": "json_object"})
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            return {"raw": content}


_llm: Optional[LLMClient] = None
_llm_ready: Optional[bool] = None


def is_llm_ready() -> bool:
    global _llm, _llm_ready
    if _llm_ready is None:
        try:
            _llm = LLMClient(verify=True)
            _llm_ready = True
            _log.info("LLM 就绪：%s", _settings.LLM_MODEL)
        except RuntimeError as e:
            _log.warning("进入 Demo 模式（LLM 不可用）：%s", e)
            _llm = None
            _llm_ready = False
    return bool(_llm_ready)


def get_llm() -> LLMClient:
    """
    获取 LLM 客户端。
    - 优先：用户请求里粘贴的 Key（contextvars）
    - 次选：.env 全局 Key（单例）
    - 都没有：抛异常，由上层降级到 Demo 模式
    """
    user_key = get_request_user_key()
    if user_key:
        return LLMClient(api_key=user_key, verify=False)
    if not is_llm_ready():
        raise RuntimeError("LLM 未就绪。请在 .env 配置 Key，或调用时传入 user_key。")
    assert _llm is not None
    return _llm


def verify_user_key(user_key: str) -> Optional[str]:
    """验证 Key 是否有效。返回 None=有效，否则错误信息。"""
    if not user_key or len(user_key.strip()) < 10:
        return "Key 格式不正确"
    try:
        LLMClient(api_key=user_key.strip(), verify=True)
        return None
    except RuntimeError as e:
        return str(e)
