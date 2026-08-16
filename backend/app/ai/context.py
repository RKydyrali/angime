"""Построение системного промпта тенанта из его данных: знания, услуги,
расписание записей, часы работы. AI отвечает только на основе этих данных."""

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, Service, Tenant
from app.redis_service import get_user_context

WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAY_RU = {
    "mon": "понедельник", "tue": "вторник", "wed": "среда",
    "thu": "четверг", "fri": "пятница", "sat": "суббота", "sun": "воскресенье",
}


def format_business_hours(tenant: Tenant) -> str:
    hours = tenant.business_hours or {}
    lines = []
    for key in WEEKDAY_KEYS:
        day = hours.get(key)
        if day and day.get("open") and day.get("close"):
            lines.append(f"{WEEKDAY_RU[key]}: {day['open']}–{day['close']}")
        else:
            lines.append(f"{WEEKDAY_RU[key]}: выходной")
    return "; ".join(lines)


def format_services(services: list[Service], language: str) -> str:
    lines = []
    for s in services:
        name = s.name_kz if language == "kz" and s.name_kz else s.name_ru
        name_alt = s.name_ru if language == "kz" else s.name_kz
        desc = s.description_kz if language == "kz" and s.description_kz else s.description_ru
        alt = f" (также: {name_alt})" if name_alt and name_alt != name else ""
        line = f"«{name}»{alt} — {s.price} тенге, {s.duration_min} мин"
        if desc:
            line += f". Описание: {desc}"
        lines.append(line)
    return "\n".join(lines) if lines else "(услуги не добавлены)"


def format_bookings(bookings: list[Booking], services_by_id: dict) -> str:
    lines = []
    for b in sorted(bookings, key=lambda x: (x.date, x.time)):
        service = services_by_id.get(b.service_id)
        sname = service.name_ru if service else (b.notes or "—")
        lines.append(
            f"{b.date.isoformat()} {b.time.strftime('%H:%M')} — {sname} — {b.client_name}"
        )
    return "\n".join(lines) if lines else "(записей нет)"


async def build_tenant_context(
    db: AsyncSession,
    tenant: Tenant,
    language: str = "ru",
    include_history: bool = False,
    sender_id: str = "",
    days_ahead: int = 7,
) -> str:
    """Актуальный контекст тенанта для AI-ответа клиенту."""
    services_result = await db.execute(
        select(Service)
        .where(Service.tenant_id == tenant.id, Service.is_active.is_(True))
        .order_by(Service.sort, Service.name_ru)
    )
    services = list(services_result.scalars().all())
    services_by_id = {s.id: s for s in services}

    today = date.today()
    until = today + timedelta(days=days_ahead)
    bookings_result = await db.execute(
        select(Booking).where(
            Booking.tenant_id == tenant.id,
            Booking.status == "confirmed",
            Booking.date >= today,
            Booking.date <= until,
        )
    )
    bookings = list(bookings_result.scalars().all())

    parts = [
        f"Бизнес: «{tenant.name}» ({tenant.whatsapp_business_name or tenant.name}).",
        f"Сегодня: {today.isoformat()}.",
        f"Часы работы (время {tenant.timezone}): {format_business_hours(tenant)}",
        "",
        "УСЛУГИ (название — цена, длительность):",
        format_services(services, language),
        "",
        "БЛИЖАЙШИЕ ЗАПИСИ (занятые слоты, дата время — услуга — клиент):",
        format_bookings(bookings, services_by_id),
    ]

    knowledge = tenant.knowledge_kz if language == "kz" and tenant.knowledge_kz else tenant.knowledge_ru
    if not knowledge:
        knowledge = tenant.knowledge_ru or tenant.knowledge_kz or ""
    if knowledge.strip():
        parts.append("")
        parts.append("ЗНАНИЯ О БИЗНЕСЕ (единственный источник фактов о ценах, правилах, акциях, услугах, политике):")
        parts.append(knowledge)

    context = "\n".join(parts)

    if include_history and sender_id:
        history = await get_user_context(str(tenant.id), sender_id, limit=8)
        if history:
            hlines = [f"{m['role']}: {m['content']}" for m in history]
            context += "\n\nИСТОРИЯ ДИАЛОГА С ЭТИМ КЛИЕНТОМ (последние сообщения):\n" + "\n".join(hlines)

    return context
