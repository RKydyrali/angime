"""Доменная логика записей: доступность слотов, создание, отмена, свободные окна."""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Booking, Service, Tenant

WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def weekday_key(d: date) -> str:
    return WEEKDAY_KEYS[d.weekday()]


def business_hours_for_day(tenant: Tenant, d: date) -> Optional[tuple[time, time]]:
    hours = tenant.business_hours or {}
    day = hours.get(weekday_key(d))
    if not day or not day.get("open") or not day.get("close"):
        return None
    try:
        open_t = time.fromisoformat(day["open"])
        close_t = time.fromisoformat(day["close"])
    except ValueError:
        return None
    return open_t, close_t


def _overlaps(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:
    return a_start < b_end and b_start < a_end


async def find_service_by_name(
    db: AsyncSession, tenant_id: uuid.UUID, name: Optional[str]
) -> Optional[Service]:
    if not name:
        return None
    needle = name.strip().lower()
    services = (
        await db.execute(
            select(Service).where(
                Service.tenant_id == tenant_id, Service.is_active.is_(True)
            )
        )
    ).scalars().all()
    exact = [s for s in services if needle == s.name_ru.lower() or needle == s.name_kz.lower()]
    if len(exact) == 1:
        return exact[0]
    partial = [s for s in services if needle in s.name_ru.lower() or needle in s.name_kz.lower()]
    if len(partial) == 1:
        return partial[0]
    return None


async def _confirmed_in_window(
    db: AsyncSession, tenant_id: uuid.UUID, d: date
) -> list[Booking]:
    result = await db.execute(
        select(Booking).where(
            Booking.tenant_id == tenant_id,
            Booking.status == "confirmed",
            Booking.date == d,
        )
    )
    return list(result.scalars().all())


async def count_service_bookings_on_day(
    db: AsyncSession, tenant_id: uuid.UUID, service_id: Optional[uuid.UUID], d: date
) -> int:
    result = await db.execute(
        select(func.count()).select_from(Booking).where(
            Booking.tenant_id == tenant_id,
            Booking.service_id == service_id,
            Booking.date == d,
            Booking.status.in_(["confirmed", "completed"]),
        )
    )
    return int(result.scalar() or 0)


async def is_slot_free(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    service: Optional[Service],
    d: date,
    start: time,
    duration_min: int,
    exclude_booking_id: Optional[uuid.UUID] = None,
) -> bool:
    """Слот свободен, если нет пересекающихся подтверждённых записей и не превышен
    дневной лимит услуги."""
    start_dt = datetime.combine(d, start)
    end_dt = start_dt + timedelta(minutes=duration_min)
    end = end_dt.time()
    if end_dt.date() != d:
        return False  # не пересекаем полночь

    for b in await _confirmed_in_window(db, tenant_id, d):
        if exclude_booking_id and b.id == exclude_booking_id:
            continue
        b_start = datetime.combine(d, b.time)
        b_end = b_start + timedelta(minutes=b.duration_min)
        if _overlaps(start, end, b.time, b_end.time()):
            return False

    if service and service.daily_limit > 0:
        count = await count_service_bookings_on_day(db, tenant_id, service.id, d)
        if count >= service.daily_limit:
            return False
    return True


async def compute_free_slots(
    db: AsyncSession,
    tenant: Tenant,
    service: Optional[Service],
    d: date,
    step_min: int = 30,
    limit: int = 8,
) -> list[str]:
    """Свободные слоты в день d с учётом часов работы и занятости."""
    hours = business_hours_for_day(tenant, d)
    if not hours:
        return []
    open_t, close_t = hours
    duration = service.duration_min if service else 60
    free: list[str] = []
    cursor = datetime.combine(d, open_t)
    close_dt = datetime.combine(d, close_t)
    while cursor + timedelta(minutes=duration) <= close_dt and len(free) < limit:
        if await is_slot_free(db, tenant.id, service, d, cursor.time(), duration):
            free.append(cursor.strftime("%H:%M"))
        cursor += timedelta(minutes=step_min)
    return free


async def create_booking(
    db: AsyncSession,
    tenant: Tenant,
    service: Optional[Service],
    client_name: str,
    client_phone: str,
    d: date,
    start: time,
    wa_sender_id: str = "",
    source: str = "whatsapp",
    notes: str = "",
) -> Booking:
    booking = Booking(
        tenant_id=tenant.id,
        service_id=service.id if service else None,
        client_name=client_name,
        client_phone=client_phone,
        date=d,
        time=start,
        duration_min=service.duration_min if service else 60,
        status="confirmed",
        source=source,
        wa_sender_id=wa_sender_id,
        notes=notes,
        last_client_message_at=datetime.now(timezone.utc),
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return booking
