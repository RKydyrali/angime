"""OpenRouter-клиент с ретраями (портировано из AIKERIM)."""

import asyncio
import json
import re
import structlog
from typing import Optional

import httpx
from pydantic import BaseModel, ValidationError

from app.config import config

logger = structlog.get_logger("angime.ai")

RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
PERMANENT_STATUSES = {400, 401, 403, 404, 405, 406, 409, 410, 413, 415, 422}


class PermanentOpenRouterError(Exception):
    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"OpenRouter permanent error {status_code}: {body[:300]}")


_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=120.0)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def _post_chat(payload: dict, referer: str = "https://danyshpan.xyz") -> str:
    client = get_client()
    last_resp: httpx.Response | None = None
    for attempt in range(MAX_ATTEMPTS):
        resp = await client.post(
            config.OPENROUTER_BASE_URL,
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "HTTP-Referer": referer,
                "Content-Type": "application/json",
                "X-Title": "Angime",
            },
            json=payload,
        )
        if resp.status_code == 200:
            try:
                content = resp.json()["choices"][0]["message"]["content"]
            except (KeyError, IndexError, ValueError) as exc:
                logger.error("Unexpected OpenRouter response: %s", resp.text[:500])
                raise
            if not content:
                raise ValueError("Empty content from OpenRouter")
            return content
        last_resp = resp
        retryable = resp.status_code in RETRYABLE_STATUSES
        if not retryable:
            if resp.status_code in PERMANENT_STATUSES:
                raise PermanentOpenRouterError(resp.status_code, resp.text)
            raise RuntimeError(
                f"OpenRouter unexpected status {resp.status_code}: {resp.text[:300]}"
            )
        logger.error(
            "OpenRouter API error %s (attempt %d/%d): %s",
            resp.status_code, attempt + 1, MAX_ATTEMPTS, resp.text[:500],
        )
        await asyncio.sleep(2 ** attempt)
    if last_resp is not None:
        last_resp.raise_for_status()
    raise RuntimeError("OpenRouter request failed without a response")


def _extract_json(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    try:
        json.loads(text)
        return text
    except (json.JSONDecodeError, ValueError):
        pass
    if text.startswith("```"):
        return re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start : end + 1]
    return text


async def chat_structured(
    messages: list[dict],
    name: str,
    schema: dict,
    temperature: float = 0.3,
    referer: str = "https://danyshpan.xyz",
) -> dict:
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": True,
                "schema": schema,
            },
        },
    }
    content = await _post_chat(payload, referer=referer)
    return json.loads(_extract_json(content))


async def chat_freeform(messages: list[dict], temperature: float = 0.5) -> str:
    payload = {
        "model": config.OPENROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    return await _post_chat(payload)
