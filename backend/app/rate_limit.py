"""
IP 使用记录与限流。

设计：
- 内存 dict 实时计数，JSON 文件持久化（重启不丢）
- LLM 相关接口每调一次 +1，上限 QUOTA_PER_IP
- 达到上限后返回 429 并提示用户粘贴自己的 Key
- 用户粘贴自己的 Key 后，通过 ?bypass=key 头绕过限流（但也不消耗服务器 Key）
"""
import json
import os
import threading
import time
from pathlib import Path
from typing import Optional

QUOTA_PER_IP = 30
# 所有"消耗服务器 Key"的 LLM 接口路径（精确匹配）
LLM_ENDPOINTS = {
    "/api/papers/{paper_id}/summary",
    "/api/ask",
    "/api/compare",
    "/api/papers/{paper_id}/notes/organize",
    "/api/related-work",
}

_state_lock = threading.Lock()
_state = {
    "counts": {},     # ip -> int
    "records": {},    # ip -> [{endpoint, ts}]
}

# 持久化路径（放到 /opt/litread/data/.rate_limit.json）
_persist_path: Optional[Path] = None


def init_persist_path(path: str):
    global _persist_path
    _persist_path = Path(path)
    if _persist_path.exists():
        try:
            data = json.loads(_persist_path.read_text())
            _state["counts"] = data.get("counts", {})
            _state["records"] = data.get("records", {})
        except Exception:
            pass


def _persist():
    if _persist_path is None:
        return
    try:
        _persist_path.parent.mkdir(parents=True, exist_ok=True)
        _persist_path.write_text(json.dumps(_state, ensure_ascii=False))
    except Exception:
        pass


def _client_ip(request) -> str:
    """从请求中提取客户端 IP（考虑反向代理）。"""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    xrp = request.headers.get("x-real-ip", "")
    if xrp:
        return xrp.strip()
    return request.client.host if request.client else "unknown"


def is_llm_endpoint(path: str) -> bool:
    """简化判断：只要路径以 /api/ 开头且不是 upload/index/graph/stats/health/papers/notes，就视为 LLM 端点。"""
    llm_prefixes = (
        "/api/papers/",  # summary, notes/organize
        "/api/ask",
        "/api/compare",
        "/api/related-work",
    )
    non_llm_suffixes = (
        "/parse", "/index", "/notes", "/viz", "/compare", "/compare-structured", "/growth",
    )
    # 先排除明显非 LLM 的
    for suf in non_llm_suffixes:
        if path.endswith(suf):
            return False
    if path == "/api/compare/export":
        return False
    # 再看是否命中 LLM 前缀
    for p in llm_prefixes:
        if path.startswith(p):
            return True
    return False


def check_and_consume(request, user_key: Optional[str] = None) -> tuple[bool, str, dict]:
    """
    检查并消耗一次额度。

    Returns: (allowed, reason, info)
    """
    ip = _client_ip(request)

    # 用户自带 Key → 不限流、不消耗
    if user_key:
        return True, "", {"ip": ip, "quota": QUOTA_PER_IP, "used": 0, "bypass": "user_key"}

    if not is_llm_endpoint(request.url.path):
        return True, "", {"ip": ip, "quota": QUOTA_PER_IP, "used": 0, "bypass": None}

    with _state_lock:
        count = _state["counts"].get(ip, 0)
        if count >= QUOTA_PER_IP:
            info = {
                "ip": ip,
                "quota": QUOTA_PER_IP,
                "used": count,
                "bypass": None,
            }
            return False, f"试用次数已用完（{QUOTA_PER_IP} 次）。请粘贴你自己的 API Key 继续使用。", info

        _state["counts"][ip] = count + 1
        _state["records"].setdefault(ip, []).append({
            "endpoint": request.url.path,
            "ts": int(time.time()),
        })
        # 只保留最近 50 条记录
        _state["records"][ip] = _state["records"][ip][-50:]
        info = {"ip": ip, "quota": QUOTA_PER_IP, "used": count + 1, "bypass": None}
        _persist()
        return True, "", info


def get_status(ip: Optional[str] = None) -> dict:
    """查询 IP 的当前额度。不填则返回全局统计。"""
    with _state_lock:
        if ip:
            return {
                "ip": ip,
                "quota": QUOTA_PER_IP,
                "used": _state["counts"].get(ip, 0),
                "remaining": QUOTA_PER_IP - _state["counts"].get(ip, 0),
            }
        # 全局
        return {
            "total_ips": len(_state["counts"]),
            "total_requests": sum(_state["counts"].values()),
            "quota_per_ip": QUOTA_PER_IP,
        }


def reset_ip(ip: str):
    with _state_lock:
        _state["counts"].pop(ip, None)
        _state["records"].pop(ip, None)
        _persist()
