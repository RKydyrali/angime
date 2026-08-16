"""Booking-флоу: пошаговый сбор полей через ИИ, проверка доступности,
создание записи, кнопки подтверждения/отмены."""

import uuid
from datetime import date, datetime, time
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import openrouter
from app.ai.concierge import collect_booking
from app.bookings import service as bookings_service
from app.models import Booking, Service, Tenant
from app.redis_service import (
    clear_bf_state,
    get_bf_state,
    set_bf_state,
)
from app.translations import t

logger = structlog.get_logger("angime.booking_flow")

FIELDS = ["service", "date", "time", "name"]
FIELD_QUESTIONS_RU = {
    "service": "На какую услугу хотите записаться?",
    "date": "На какой день? (например: завтра или 25.08)",
    "time": "На какое время?",
    "name": "Как вас зовут?",
}
FIELD_QUESTIONS_KZ = {
    "service": "Қай қызметке жазылғыңыз келеді?",
    "date": "Қай күнге? (мысалы: ертең немесе 25.08)",
    "time": "Қай уақытқа?",
    "name": "Атыңыз кім?",
}


def _booking_summary(
    tenant: Tenant, service: Optional[Service], name: str, d: date, start: time
) -> str:
    sname = ""
    if service:
        sname = service.name_kz if tenant.language == "kz" and service.name_kz else service.name_ru
    price = f"{service.price} ₸" if service and service.price else "—"
    return (
        f"Услуга: {sname}\nДата: {d.isoformat()}\nВремя: {start.strftime('%H:%M')}\n"
        f"Имя: {name}\nЦена: {price}"
    )


def _missing_fields(partial: dict) -> list[str]:
    return [f for f in FIELDS if not (partial.get(f) or "").strip()]


async def _ask_missing(
    db: AsyncSession, tenant: Tenant, client_language: str, partial: dict, message: str
) -> tuple[str, dict, list[str]]:
    """ИИ-сборщик: заполняет известное, спрашивает следующее недостающее."""
    data = await collect_booking(db, tenant, client_language, partial, message)
    booking = data.get("booking") or {}
    merged = {
        "service": booking.get("service_name") or partial.get("service", ""),
        "date": booking.get("date") or partial.get("date", ""),
        "time": booking.get("time") or partial.get("time", ""),
        "name": booking.get("client_name") or partial.get("name", ""),
    }
    raw_missing = data.get("missing") or []
    valid_missing = [f for f in raw_missing if f in FIELDS]
    missing = _missing_fields(merged)
    if not valid_missing:
        valid_missing = missing
    reply = (data.get("reply_text") or "").strip()
    return reply or "", merged, valid_missing


async def _complete_booking(
    db: AsyncSession,
    tenant: Tenant,
    sender_id: str,
    client_phone: str,
    client_language: str,
    partial: dict,
) -> tuple[str, Optional[list[dict]], dict]:
    """Все поля собраны: маппинг услуги, проверка слота, создание записи."""
    service = await bookings_service.find_service_by_name(
        db, tenant.id, partial.get("service")
    )
    if service is None:
        services = (
            (await db.execute(
                select(Service).where(
                    Service.tenant_id == tenant.id, Service.is_active.is_(True)
                )
            )).scalars().all()
        )
        names = "\n".join(
            f"• {s.name_kz if client_language == 'kz' and s.name_kz else s.name_ru} — {s.price} ₸"
            for s in services
        )
        reply = (
            "Я не нашёл такую услугу. Вот что у нас есть:\n" + names
            + "\n\nНапишите, на какую из них записаться."
            if client_language == "ru"
            else "Мұндай қызметті таппадым. Бізде мыналар бар:\n" + names
            + "\n\nҚайсысына жазылғыңыз келетінін жазыңыз."
        )
        return reply, None, {**partial, "service": ""}

    try:
        d = date.fromisoformat(partial["date"])
        start = time.fromisoformat(partial["time"])
    except (ValueError, KeyError):
        reply = (
            "Уточните, пожалуйста, дату и время (например: 25.08 в 15:00)."
            if client_language == "ru"
            else "Күні мен уақытын нақтылаңыз (мысалы: 25.08 сағат 15:00)."
        )
        return reply, None, partial

    free = await bookings_service.is_slot_free(
        db, tenant.id, service, d, start, service.duration_min
    )
    if not free:
        slots = await bookings_service.compute_free_slots(db, tenant, service, d)
        if slots:
            reply = (
                f"К сожалению, {d.isoformat()} в {start.strftime('%H:%M')} занято. "
                f"Свободно в этот день: {', '.join(slots)}. Какое время подойдёт?"
                if client_language == "ru"
                else f"Өкінішке қарай, {d.isoformat()} {start.strftime('%H:%M')} бос емес. "
                f"Осы күні бос: {', '.join(slots)}. Қай уақыт қолайлы?"
            )
        else:
            reply = (
                f"К сожалению, на {d.isoformat()} нет свободных слотов. "
                "Выберите другой день."
                if client_language == "ru"
                else f"Өкінішке қарай, {d.isoformat()} күні бос слот жоқ. Басқа күнді таңдаңыз."
            )
        return reply, None, {**partial, "time": "", "date": ""}

    booking = await bookings_service.create_booking(
        db,
        tenant,
        service,
        client_name=partial.get("name") or "Клиент",
        client_phone=client_phone,
        d=d,
        start=start,
        wa_sender_id=sender_id,
    )
    summary = _booking_summary(tenant, service, booking.client_name, d, start)
    reply = t("booking_created", client_language, summary=summary)
    buttons = [
        {"id": f"bk:confirm:{booking.id}", "title": "✅ Подтвердить" if client_language == "ru" else "✅ Растау"},
        {"id": f"bk:cancel:{booking.id}", "title": "❌ Отменить" if client_language == "ru" else "❌ Болдыру"},
    ]
    return reply, buttons, {}


async def handle_inbound(
    db: AsyncSession,
    tenant: Tenant,
    sender_id: str,
    client_phone: str,
    client_language: str,
    message: str,
    decision_booking: dict,
    decision_reply: str,
) -> tuple[str, Optional[list[dict]]]:
    """Основная точка входа при intent=booking (новая попытка или продолжение)."""
    state = await get_bf_state(str(tenant.id), sender_id)
    if state:
        reply, merged, missing = await _ask_missing(
            db, tenant, client_language, state.get("booking") or {}, message
        )
    else:
        merged = {
            "service": decision_booking.get("service_name") or "",
            "date": decision_booking.get("date") or "",
            "time": decision_booking.get("time") or "",
            "name": decision_booking.get("client_name") or "",
        }
        missing = _missing_fields(merged)
        reply = decision_reply or ""

    if missing:
        if not reply:
            question = FIELD_QUESTIONS_KZ.get(missing[0]) if client_language == "kz" else FIELD_QUESTIONS_RU.get(missing[0])
            reply = question or "Уточните, пожалуйста, детали записи."
        await set_bf_state(
            str(tenant.id), sender_id, {"booking": merged, "step": missing[0]}
        )
        return reply, None

    await clear_bf_state(str(tenant.id), sender_id)
    reply, buttons, kept = await _complete_booking(
        db, tenant, sender_id, client_phone, client_language, merged
    )
    if kept:
        # слот занят / услуга не найдена — сохраняем накопленное для продолжения
        await set_bf_state(
            str(tenant.id), sender_id, {"booking": kept, "step": "time"}
        )
    return reply, buttons


async def handle_cancel_button(
    db: AsyncSession, tenant: Tenant, booking_id: str
) -> str:
    try:
        bid = uuid.UUID(booking_id)
    except ValueError:
        return "Запись не найдена."
    booking = await db.get(Booking, bid)
    if booking is None or booking.tenant_id != tenant.id:
        return "Запись не найдена."
    booking.status = "cancelled"
    await db.commit()
    return "✅ Запись отменена."


async def handle_confirm_button(
    db: AsyncSession, tenant: Tenant, booking_id: str
) -> str:
    try:
        bid = uuid.UUID(booking_id)
    except ValueError:
        return "Запись не найдена."
    booking = await db.get(Booking, bid)
    if booking is None or booking.tenant_id != tenant.id:
        return "Запись не найдена."
    if booking.status != "confirmed":
        booking.status = "confirmed"
        await db.commit()
    return "✅ Ваша запись подтверждена! Ждём вас."
