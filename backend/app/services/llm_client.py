"""
LLM 客户端：统一封装 OpenAI 兼容协议。
换供应商只需改 .env 的 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL。

Demo 模式（DEMO_MODE=true 或未配置 key）：
  自动回退到基于摘要/关键词的模板化输出，让所有功能链路都能跑通，
  方便黑客松现场演示，避免因没配 key 而页面报错。
"""
import json
import logging
from typing import List, Dict, Optional

from openai import OpenAI

from ..config import get_settings

_settings = get_settings()
_log = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        if not _settings.LLM_API_KEY:
            raise RuntimeError(
                "未配置 LLM_API_KEY，请在 backend/.env 中填写（参考 .env.example）。"
            )
        try:
            self.client = OpenAI(
                base_url=_settings.LLM_BASE_URL,
                api_key=_settings.LLM_API_KEY,
                timeout=30,
            )
            self.model = _settings.LLM_MODEL
            # 简单验活：真正调一次
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
        except Exception as e:
            raise RuntimeError(f"LLM 连接失败：{e}") from e

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1500,
        response_format: Optional[dict] = None,
    ) -> str:
        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if response_format:
            kwargs["response_format"] = response_format

        resp = self.client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def chat_json(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> dict:
        content = self.chat(
            messages,
            temperature=temperature,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )
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
    """返回 True=LLM 可用；False=Demo 模式。"""
    global _llm, _llm_ready
    if _llm_ready is None:
        try:
            _llm = LLMClient()
            _llm_ready = True
            _log.info("LLM 就绪：%s", _settings.LLM_MODEL)
        except RuntimeError as e:
            _log.warning("进入 Demo 模式（LLM 不可用）：%s", e)
            _llm = None
            _llm_ready = False
    return bool(_llm_ready)


def get_llm() -> LLMClient:
    if not is_llm_ready():
        raise RuntimeError(
            "LLM 未就绪。若你想直接跑 Demo，请忽略此异常，改用 demo 函数。"
        )
    assert _llm is not None
    return _llm
