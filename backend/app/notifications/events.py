"""События уведомлений владельцу тенанта и админу."""

import structlog
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, QuestionLog, Service, Tenant, TenantNotification
from app.notifications.telegram import safe_send
from app.translations import t

logger = structlog.get_logger("angime.events")


async def get_owner_chat(db: AsyncSession, tenant_id) -> Optional[str]:
    result = await db.execute(
        select(TenantNotification).where(TenantNotification.tenant_id == tenant_id)
    )
    link = result.scalar_one_or_none()
    return link.tg_chat_id if link and link.tg_chat_id else None


def _fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _fmt_time(t) -> str:
    return t.strftime("%H:%M")


async def notify_booking_created(
    db: AsyncSession, tenant: Tenant, booking: Booking
) -> None:
    chat = await get_owner_chat(db, tenant.id)
    if not chat:
        return
    service_name = ""
    price = "—"
    if booking.service_id:
        svc = await db.get(Service, booking.service_id)
        if svc:
            service_name = svc.name_ru
            price = str(svc.price)
    text = t(
        "owner_new_booking",
        "ru",
        name=booking.client_name,
        phone=booking.client_phone or "—",
        service=service_name or "—",
        date=_fmt_date(booking.date),
        time=_fmt_time(booking.time),
        price=price,
    )
    await safe_send(chat, text)


async def notify_booking_cancelled(
    db: AsyncSession, tenant: Tenant, booking: Booking
) -> None:
    chat = await get_owner_chat(db, tenant.id)
    if not chat:
        return
    service_name = ""
    if booking.service_id:
        svc = await db.get(Service, booking.service_id)
        if svc:
            service_name = svc.name_ru
    text = t(
        "owner_booking_cancelled",
        "ru",
        name=booking.client_name,
        service=service_name or "—",
        date=_fmt_date(booking.date),
        time=_fmt_time(booking.time),
    )
    await safe_send(chat, text)


async def notify_knowledge_gap(
    db: AsyncSession, tenant: Tenant, sender_id: str, question: str, topic: str
) -> None:
    chat = await get_owner_chat(db, tenant.id)
    if not chat:
        return
    await safe_send(chat, t("knowledge_gap_notify", "ru", sender=sender_id, question=question[:2000]))
    log = QuestionLog(
        tenant_id=tenant.id, topic=(topic or "question")[:200], question=question[:2000]
    )
    db.add(log)
    await db.commit()


async def notify_reminder_sent(
    db: AsyncSession, tenant: Tenant, booking: Booking, service_name: str
) -> None:
    chat = await get_owner_chat(db, tenant.id)
    if not chat:
        return
    await safe_send(
        chat,
        t(
            "reminder_nudge_owner",
            "ru",
            name=booking.client_name,
            service=service_name or "—",
            time=_fmt_time(booking.time),
        ),
    )


async def send_daily_summary(db: AsyncSession, tenant: Tenant, bookings: list[Booking]) -> None:
    chat = await get_owner_chat(db, tenant.id)
    if not chat:
        return
    if not bookings:
        return
    lines = []
    for b in sorted(bookings, key=lambda x: x.time):
        service_name = ""
        if b.service_id:
            svc = await db.get(Service, b.service_id)
            if svc:
                service_name = svc.name_ru
        lines.append(f"• {_fmt_time(b.time)} — {service_name or '—'} — {b.client_name}")
    await safe_send(
        chat,
        t(
            "owner_daily_summary",
            "ru",
            date=_fmt_date(bookings[0].date),
            items="\n".join(lines),
            count=len(bookings),
        ),
    )


async def notify_admin(text: str) -> None:
    from app.config import config

    if config.TELEGRAM_ADMIN_CHAT_ID:
        await safe_send(config.TELEGRAM_ADMIN_CHAT_ID, text)
