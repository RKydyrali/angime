"""Смарт-приветствия: по времени суток, раз в день на клиента."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.redis_service import is_greeted_today, mark_greeted

RU_BY_HOUR = {
    "morning": ["Доброе утро! 🌅", "Доброе утро! ☀️"],
    "day": ["Добрый день! 🌞", "Здравствуйте! 🌤️"],
    "evening": ["Добрый вечер! 🌆", "Добрый вечер! 🌙"],
    "night": ["Доброй ночи! 🌙", "Здравствуйте! 🌌"],
}
KZ_BY_HOUR = {
    "morning": ["Қайырлы таң! 🌅", "Қайырлы таң! ☀️"],
    "day": ["Қайырлы күн! 🌞", "Сәлеметсіз бе! 🌤️"],
    "evening": ["Қайырлы кеш! 🌆", "Қайырлы кеш! 🌙"],
    "night": ["Қайырлы түн! 🌙", "Сәлеметсіз бе! 🌌"],
}


def _bucket(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "day"
    if 18 <= hour < 23:
        return "evening"
    return "night"


def _now_in(tz_name: str) -> datetime:
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now(timezone.utc)


def pick_greeting(language: str = "ru", hour: int | None = None) -> str:
    pool = RU_BY_HOUR if language == "ru" else KZ_BY_HOUR
    return pool[_bucket(hour or 12)][0]


def greeting_hint(language: str = "ru", now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now(timezone.utc)
    bucket = _bucket(now.hour)
    return pool_name(language, bucket)


def pool_name(language: str, bucket: str) -> str:
    pool = RU_BY_HOUR if language == "ru" else KZ_BY_HOUR
    return pool[bucket][0]


def ttl_to_midnight(tz_name: str) -> int:
    """Секунды до полуночи в таймзоне тенанта."""
    now = _now_in(tz_name)
    midnight = datetime.combine(now.date() + timedelta(days=1), time(0, 0), tzinfo=now.tzinfo)
    return max(60, int((midnight - now).total_seconds()))


async def ensure_greeting(
    tenant_id: str, sender_id: str, tz_name: str = "Asia/Almaty"
) -> tuple[str, bool]:
    """Возвращает (подсказку приветствия, greeted_today)."""
    if await is_greeted_today(tenant_id, sender_id):
        return "", True
    await mark_greeted(tenant_id, sender_id, ttl_to_midnight(tz_name))
    now = _now_in(tz_name)
    hint = greeting_hint("ru", now)
    return hint, False
