"""大模型调用：OpenAI 兼容协议（DeepSeek / 通义 / Kimi / 本地 Ollama 都能用）。

只做一件事：发请求、拿回 JSON。任何异常都返回 None，交给离线引擎兜底。
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import API_KEY, BASE_URL, LLM_ENABLED, MODEL

JSON_HINT = {"type": "json_object"}

# 最后一次失败原因。降级是静默的，但完全看不见原因的话，
# 用户填了 key 也分不清"模型没生效"和"模型生效了但这次抽风"。
LAST_ERROR = ""


def last_error() -> str:
    return LAST_ERROR


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


async def chat_json(
    system: str,
    user: str,
    temperature: float = 0.95,
    max_tokens: int = 900,
) -> dict[str, Any] | None:
    global LAST_ERROR
    if not LLM_ENABLED:
        return None
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": JSON_HINT,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=50) as client:
            resp = await client.post(
                f"{BASE_URL}/chat/completions", headers=headers, json=payload
            )
            if resp.status_code >= 400:
                # 有的平台返回一坨 JSON，只摘出人话那一段，报错才看得懂
                detail = resp.text[:160]
                try:
                    body = resp.json()
                    detail = str(
                        (body.get("error") or {}).get("message") or body.get("message") or detail
                    )[:160]
                except Exception:  # noqa: BLE001 - 不是 JSON 就用原文
                    pass
                LAST_ERROR = f"HTTP {resp.status_code}: {detail}"
                print(f"[llm] {LAST_ERROR}")
                return None
            data = resp.json()
        content = data["choices"][0]["message"]["content"]
        result = _extract_json(content)
        LAST_ERROR = ""
        return result
    except Exception as exc:  # noqa: BLE001 - 任何问题都降级，不让用户看到报错
        LAST_ERROR = f"{type(exc).__name__}: {exc}"
        print(f"[llm] fallback to offline: {LAST_ERROR}")
        return None
