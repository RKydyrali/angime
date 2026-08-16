"""Telegram-бот уведомлений: подключение по 6-значному коду, ИИ-ассистент
владельца бизнеса. Поллер в отдельном потоке с собственным event loop."""

import asyncio
import structlog
import threading
import uuid
from datetime import datetime, timezone

import httpx
import redis as redis_sync
from sqlalchemy import select

from app.config import config
from app.database import AsyncSessionLocal
from app.models import Tenant, TenantNotification
from app.notifications.telegram import get_client
from app.redis_service import (
    get_tg_linked_tenant,
    resolve_tg_code,
    set_tg_linked_tenant,
)
from app.text_utils import detect_language
from app.translations import t

logger = structlog.get_logger("angime.tgbot")

API_BASE = "https://api.telegram.org/bot{token}"
MAX_MESSAGE_LENGTH = 4000

_running = False
_offset = 0
_poll_thread: threading.Thread | None = None
_poll_stop: threading.Event | None = None
_poll_http: httpx.Client | None = None
_poll_redis: redis_sync.Redis | None = None
_main_loop: asyncio.AbstractEventLoop | None = None
_active_tasks: set[asyncio.Task] = set()

POLL_LOCK_KEY = "angime:tg:polling_lock"
POLL_LOCK_TTL_SECONDS = 90
_instance_id = uuid.uuid4().hex


def _api_url(method: str) -> str:
    return f"{API_BASE.format(token=config.TELEGRAM_BOT_TOKEN)}/{method}"


# ---------- Асинхронная отправка (для событий) ----------
async def notify_tenant_chat(chat_id: str, text: str) -> None:
    from app.notifications.telegram import safe_send

    await safe_send(chat_id, text)


async def _sync_link(chat_id: str, tenant_id: str) -> None:
    async with AsyncSessionLocal() as db:
        tenant = await db.get(Tenant, uuid.UUID(tenant_id))
        if tenant is None:
            return
        result = await db.execute(
            select(TenantNotification).where(
                TenantNotification.tenant_id == tenant.id
            )
        )
        link = result.scalar_one_or_none()
        if link is None:
            link = TenantNotification(tenant_id=tenant.id)
            db.add(link)
        link.tg_chat_id = str(chat_id)
        link.linked_at = datetime.now(timezone.utc)
        await db.commit()


async def _get_linked_tenant(chat_id: str):
    cached = await get_tg_linked_tenant(str(chat_id))
    if cached:
        async with AsyncSessionLocal() as db:
            try:
                return await db.get(Tenant, uuid.UUID(cached))
            except ValueError:
                return None
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TenantNotification).where(
                TenantNotification.tg_chat_id == str(chat_id)
            )
        )
        link = result.scalar_one_or_none()
        if link is None:
            return None
        tenant = await db.get(Tenant, link.tenant_id)
        if tenant:
            await set_tg_linked_tenant(str(chat_id), str(tenant.id))
        return tenant


async def _handle_code(chat_id: str, text: str, username: str) -> str:
    tenant_id = await resolve_tg_code(text)
    if not tenant_id:
        return t("tg_code_invalid", "ru")
    async with AsyncSessionLocal() as db:
        try:
            tenant = await db.get(Tenant, uuid.UUID(tenant_id))
        except ValueError:
            return t("tg_code_invalid", "ru")
        if tenant is None:
            return t("tg_no_tenant", "ru")
        existing = await _get_linked_tenant(chat_id)
        if existing and existing.id != tenant.id:
            return t("tg_linked_other", "ru", name=existing.name)
    await _sync_link(chat_id, str(tenant.id))
    await set_tg_linked_tenant(str(chat_id), str(tenant.id))
    return t("tg_linked", "ru")


async def _handle_owner_message(tenant: Tenant, chat_id: str, text: str) -> None:
    """ИИ-ассистент владельца: отвечает по данным тенанта."""
    from app.notifications.telegram import api_call, send_chat_action

    await send_chat_action(str(chat_id))
    language = detect_language(text)
    try:
        async with AsyncSessionLocal() as db:
            from app.ai import business
            from app.ai.context import build_tenant_context

            ctx = await build_tenant_context(db, tenant, language=language)
            reply = await business.generate_business_response(
                question=text, data_context=ctx, language=language
            )
    except Exception:
        logger.exception("Owner AI reply failed")
        reply = (
            "Не удалось получить ответ. Попробуйте ещё раз чуть позже. 🌸"
            if language == "ru"
            else "Жауап алу мүмкін болмады. Сәл кейінірек қайталап көріңіз. 🌸"
        )
    await api_call("sendMessage", chat_id=chat_id, text=reply[:MAX_MESSAGE_LENGTH])


async def _handle_message_async(msg: dict) -> None:
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return
    text = (msg.get("text") or "").strip()
    username = (msg.get("from") or {}).get("username") or ""
    if not text:
        await _reply(chat_id, t("tg_greeting", "ru"))
        return
    lowered = text.lower()
    if lowered in ("/start", "/menu", "start"):
        await _reply(chat_id, t("tg_greeting", "ru"))
        return
    tenant = await _get_linked_tenant(chat_id)
    if text.isdigit() and len(text) == 6:
        reply = await _handle_code(chat_id, text, username)
        await _reply(chat_id, reply)
        return
    if tenant is None:
        await _reply(chat_id, t("tg_not_linked", "ru"))
        return
    await _handle_owner_message(tenant, chat_id, text)


async def _reply(chat_id, text: str) -> None:
    from app.notifications.telegram import api_call

    try:
        await api_call("sendMessage", chat_id=chat_id, text=text[:MAX_MESSAGE_LENGTH])
    except Exception:
        logger.warning("Failed to send tg reply", exc_info=True)


async def _process_update(update: dict) -> None:
    if "message" in update:
        msg = update["message"]
        if msg.get("from", {}).get("is_bot"):
            return
        await _handle_message_async(msg)


async def _run_update(update: dict) -> None:
    try:
        await _process_update(update)
    except Exception:
        logger.exception("TG update processing failed")


def _dispatch_update(update: dict) -> None:
    global _main_loop
    if _main_loop is None or not _main_loop.is_running():
        logger.warning("Main loop not running; TG update dropped")
        return
    task = asyncio.run_coroutine_threadsafe(_run_update(update), _main_loop)
    _active_tasks.add(task)
    task.add_done_callback(_active_tasks.discard)


def _poll_api_call(method: str, **params) -> dict:
    assert _poll_http is not None
    resp = _poll_http.post(_api_url(method), json=params, timeout=50)
    if resp.status_code != 200:
        logger.error("Telegram API error %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {data}")
    return data


def _poll_once_sync() -> None:
    global _offset
    data = _poll_api_call(
        "getUpdates", offset=_offset, allowed_updates=["message"]
    )
    for update in data.get("result", []):
        _offset = update["update_id"] + 1
        _dispatch_update(update)
    try:
        assert _poll_redis is not None
        _poll_redis.set("angime:tg:offset", _offset)
    except Exception:
        logger.warning("Failed to persist tg offset", exc_info=True)


def _poll_thread_main() -> None:
    global _poll_http, _poll_redis, _offset, _running
    logger.info("Telegram polling thread started")
    try:
        _poll_http = httpx.Client(timeout=70.0)
        _poll_redis = redis_sync.Redis.from_url(
            config.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5.0,
            socket_timeout=5.0,
        )
    except Exception:
        logger.exception("Failed to init poller clients")
        return

    while _running and not _poll_stop.is_set():
        try:
            acquired = bool(
                _poll_redis.set(
                    POLL_LOCK_KEY, _instance_id, nx=True, ex=POLL_LOCK_TTL_SECONDS
                )
            )
        except Exception:
            logger.warning("Redis unavailable; skipping polling lock check")
            acquired = True
        if not acquired:
            _poll_stop.wait(15)
            continue
        break
    logger.info("Telegram polling lock acquired: %s", _instance_id[:8])

    try:
        raw_offset = _poll_redis.get("angime:tg:offset")
        if raw_offset:
            try:
                _offset = int(raw_offset)
            except ValueError:
                _offset = 0
    except Exception:
        pass

    while _running and not _poll_stop.is_set():
        try:
            _poll_once_sync()
            try:
                _poll_redis.expire(POLL_LOCK_KEY, POLL_LOCK_TTL_SECONDS)
            except Exception:
                pass
        except Exception:
            logger.exception("Telegram polling error")
            _poll_stop.wait(10)
        else:
            _poll_stop.wait(0.3)
    logger.warning("Telegram polling thread exited (_running=%s)", _running)


def start_telegram_bot() -> None:
    global _poll_thread, _poll_stop, _main_loop, _running
    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram bot not started: missing token")
        return
    if _poll_thread is not None and _poll_thread.is_alive():
        return
    try:
        _main_loop = asyncio.get_running_loop()
    except RuntimeError:
        _main_loop = None
    _running = True
    _poll_stop = threading.Event()
    _poll_thread = threading.Thread(
        target=_poll_thread_main, name="angime-tg-poller", daemon=True
    )
    _poll_thread.start()
    logger.info("Telegram bot polling started")


async def stop_telegram_bot() -> None:
    global _poll_thread, _poll_stop, _running
    _running = False
    if _poll_stop is not None:
        _poll_stop.set()
    if _poll_thread is not None and _poll_thread.is_alive():
        _poll_thread.join(timeout=5)
    _poll_thread = None
    if _active_tasks:
        for task in list(_active_tasks):
            task.cancel()
        try:
            await asyncio.wait_for(
                asyncio.gather(*list(_active_tasks), return_exceptions=True),
                timeout=5,
            )
        except asyncio.TimeoutError:
            pass
    await get_client().aclose()
