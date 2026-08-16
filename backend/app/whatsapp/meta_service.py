"""Meta Cloud API: отправка сообщений (текст, кнопки, список), загрузка медиа.
Всё — с токеном конкретного тенанта."""

import base64
import structlog
from typing import Optional

import httpx

from app.config import config
from app.models import Tenant

logger = structlog.get_logger("angime.meta")

GRAPH_BASE = "https://graph.facebook.com"


class PermanentSendError(Exception):
    pass


_client: httpx.AsyncClient | None = None


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


def _send_url(phone_number_id: str) -> str:
    return f"{GRAPH_BASE}/{config.META_GRAPH_VERSION}/{phone_number_id}/messages"


def _headers(tenant: Tenant) -> dict:
    return {
        "Authorization": f"Bearer {tenant.meta_access_token}",
        "Content-Type": "application/json",
    }


async def _post(tenant: Tenant, payload: dict) -> bool:
    if not tenant.meta_phone_number_id or not tenant.meta_access_token:
        logger.warning("Tenant %s has no Meta credentials", tenant.slug)
        return False
    resp = await get_client().post(
        _send_url(tenant.meta_phone_number_id), headers=_headers(tenant), json=payload
    )
    if resp.status_code in (200, 201):
        return True
    body = resp.text[:500]
    if resp.status_code in (400, 401, 403, 404):
        logger.error("Meta send permanent error %s: %s", resp.status_code, body)
        raise PermanentSendError(f"Meta send {resp.status_code}: {body}")
    logger.error("Meta send error %s: %s", resp.status_code, body)
    return False


async def send_text(tenant: Tenant, wa_id: str, text: str) -> bool:
    return await _post(
        tenant,
        {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        },
    )


async def send_buttons(
    tenant: Tenant,
    wa_id: str,
    text: str,
    buttons: list[dict],
) -> bool:
    """buttons: [{"id": "...", "title": "..."}] — максимум 3."""
    rows = [
        {"type": "reply", "reply": {"id": b["id"], "title": b["title"][:20]}}
        for b in buttons[:3]
    ]
    return await _post(
        tenant,
        {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": text[:1024]},
                "action": {"buttons": rows},
            },
        },
    )


async def send_list(
    tenant: Tenant,
    wa_id: str,
    text: str,
    button_text: str,
    sections: list[dict],
) -> bool:
    """sections: [{"title": "...", "rows": [{"id": "...", "title": "...", "description": "..."}]}]"""
    return await _post(
        tenant,
        {
            "messaging_product": "whatsapp",
            "to": wa_id,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": text[:1024]},
                "action": {
                    "button": button_text[:20],
                    "sections": sections[:1],
                },
            },
        },
    )


async def send_test_message(tenant: Tenant, wa_id: str) -> bool:
    text = (
        f"✅ Подключение WhatsApp для «{tenant.name}» работает!\n"
        f"Это тестовое сообщение из панели Angime."
    )
    return await send_text(tenant, wa_id, text)


async def download_whatsapp_media(
    tenant: Tenant, media_id: str, max_bytes: int = 25 * 1024 * 1024
) -> Optional[bytes]:
    """Скачивает медиа по ID (нужен fetch медиа + токен тенанта)."""
    try:
        resp = await get_client().get(
            f"{GRAPH_BASE}/{config.META_GRAPH_VERSION}/{media_id}",
            headers=_headers(tenant),
        )
        if resp.status_code != 200:
            logger.error("Meta media fetch %s: %s", resp.status_code, resp.text[:300])
            return None
        url = resp.json().get("url")
        if not url:
            return None
        data_resp = await get_client().get(
            url, headers=_headers(tenant), follow_redirects=True
        )
        if data_resp.status_code != 200:
            logger.error("Meta media download %s", data_resp.status_code)
            return None
        return data_resp.content[:max_bytes]
    except httpx.HTTPError:
        logger.exception("Meta media download failed")
        return None


def wa_to_data_url(data: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64," + base64.b64encode(data).decode()
