"""Redis-слой: контекст диалогов, дедупликация, rate limit, окно 24ч,
состояния booking-флоу и коды подключения Telegram."""

import json
import time
from datetime import datetime, timezone
from typing import Optional

from app.database import redis_client
from app.models import Conversation

MSG_SEEN_PREFIX = "angime:seen:"
CONTEXT_PREFIX = "angime:ctx:"
BF_PREFIX = "angime:bf:"
TGCODE_PREFIX = "angime:tgcode:"
TG_LINKED_PREFIX = "angime:tglinked:"

CONTEXT_LIMIT = 10


# ---------- Дедупликация сообщений ----------
async def is_message_processed(tenant_id: str, msg_id: str) -> bool:
    return await redis_client.exists(f"{MSG_SEEN_PREFIX}{tenant_id}:{msg_id}") == 1


async def claim_message(tenant_id: str, msg_id: str, ttl: int = 86400) -> bool:
    ok = await redis_client.set(
        f"{MSG_SEEN_PREFIX}{tenant_id}:{msg_id}", "1", nx=True, ex=ttl
    )
    return bool(ok)


async def forget_message(tenant_id: str, msg_id: str) -> None:
    await redis_client.delete(f"{MSG_SEEN_PREFIX}{tenant_id}:{msg_id}")


# ---------- Контекст диалога ----------
async def save_user_message(
    tenant_id: str, sender_id: str, role: str, content: str
) -> None:
    key = f"{CONTEXT_PREFIX}{tenant_id}:{sender_id}"
    entry = json.dumps(
        {"role": role, "content": content[:2000], "ts": time.time()},
        ensure_ascii=False,
    )
    await redis_client.lpush(key, entry)
    await redis_client.ltrim(key, 0, CONTEXT_LIMIT - 1)
    await redis_client.expire(key, 60 * 60 * 12)


async def get_user_context(
    tenant_id: str, sender_id: str, limit: int = CONTEXT_LIMIT
) -> list[dict]:
    raw = await redis_client.lrange(f"{CONTEXT_PREFIX}{tenant_id}:{sender_id}", 0, limit - 1)
    messages: list[dict] = []
    for item in raw:
        try:
            data = json.loads(item)
        except (ValueError, TypeError):
            continue
        if data.get("role") in ("user", "assistant"):
            messages.append({"role": data["role"], "content": data["content"]})
    messages.reverse()
    return messages


# ---------- Rate limit ----------
async def is_rate_limited(tenant_id: str, sender_id: str, limit: int, window: int) -> bool:
    key = f"angime:rl:{tenant_id}:{sender_id}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, window)
    return count > limit


# ---------- Приветствие (раз в день) ----------
async def is_greeted_today(tenant_id: str, sender_id: str) -> bool:
    key = f"angime:greet:{tenant_id}:{sender_id}"
    return await redis_client.exists(key) == 1


async def mark_greeted(tenant_id: str, sender_id: str, ttl_seconds: int) -> None:
    await redis_client.set(f"angime:greet:{tenant_id}:{sender_id}", "1", ex=ttl_seconds)


# ---------- Окно 24 часа (Meta) ----------
def within_24h(last_seen_at: Optional[datetime], now: Optional[datetime] = None) -> bool:
    if not last_seen_at:
        return False
    now = now or datetime.now(timezone.utc)
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    return (now - last_seen_at).total_seconds() < 24 * 3600


# ---------- Booking-флоу (state machine) ----------
def _bf_key(tenant_id: str, sender_id: str) -> str:
    return f"{BF_PREFIX}{tenant_id}:{sender_id}"


async def get_bf_state(tenant_id: str, sender_id: str) -> Optional[dict]:
    raw = await redis_client.get(_bf_key(tenant_id, sender_id))
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if time.time() - data.get("ts", 0) > 60 * 60:
        await redis_client.delete(_bf_key(tenant_id, sender_id))
        return None
    return data


async def set_bf_state(tenant_id: str, sender_id: str, state: dict) -> None:
    state["ts"] = time.time()
    await redis_client.set(
        _bf_key(tenant_id, sender_id),
        json.dumps(state, ensure_ascii=False),
        ex=60 * 60,
    )


async def clear_bf_state(tenant_id: str, sender_id: str) -> None:
    await redis_client.delete(_bf_key(tenant_id, sender_id))


# ---------- Коды подключения Telegram (6 цифр) ----------
async def create_tg_code(tenant_id: str, ttl: int = 300) -> str:
    code = ""
    for _ in range(20):
        import random

        code = f"{random.randint(0, 999999):06d}"
        ok = await redis_client.set(
            f"{TGCODE_PREFIX}{code}", tenant_id, nx=True, ex=ttl
        )
        if ok:
            return code
    raise RuntimeError("Failed to generate tg code")


async def resolve_tg_code(code: str) -> Optional[str]:
    tenant_id = await redis_client.get(f"{TGCODE_PREFIX}{code.strip()}")
    if tenant_id:
        await redis_client.delete(f"{TGCODE_PREFIX}{code.strip()}")
    return tenant_id


async def get_tg_linked_tenant(chat_id: str) -> Optional[str]:
    return await redis_client.get(f"{TG_LINKED_PREFIX}{chat_id}")


async def set_tg_linked_tenant(chat_id: str, tenant_id: str) -> None:
    await redis_client.set(f"{TG_LINKED_PREFIX}{chat_id}", tenant_id, ex=60 * 60 * 24 * 90)
