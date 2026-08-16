"""Telegram Bot API: асинхронный клиент для уведомлений и обработки команд."""

import asyncio
import structlog
from typing import Optional

import httpx

from app.config import config

logger = structlog.get_logger("angime.telegram")

API_BASE = "https://api.telegram.org/bot{token}"
MAX_MESSAGE_LENGTH = 4000

_client: httpx.AsyncClient | None = None


def _api_url(method: str) -> str:
    return f"{API_BASE.format(token=config.TELEGRAM_BOT_TOKEN)}/{method}"


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=70.0)
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def api_call(method: str, **params) -> dict:
    resp = await get_client().post(_api_url(method), json=params)
    if resp.status_code != 200:
        logger.error("Telegram API error %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {data}")
    return data


async def send_message(chat_id: str, text: str, keyboard: Optional[dict] = None) -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        return
    payload: dict = {
        "chat_id": chat_id,
        "text": text[:MAX_MESSAGE_LENGTH],
    }
    if keyboard is not None:
        payload["reply_markup"] = keyboard
    await api_call("sendMessage", **payload)


async def send_chat_action(chat_id: str, action: str = "typing") -> None:
    try:
        await api_call("sendChatAction", chat_id=chat_id, action=action)
    except Exception:
        logger.warning("sendChatAction failed", exc_info=True)


async def safe_send(chat_id: str, text: str) -> None:
    try:
        await send_message(chat_id, text)
    except Exception:
        logger.warning("Failed to send telegram message to %s", chat_id, exc_info=True)
