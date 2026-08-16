"""Панель тенанта: услуги, записи, настройки, статистика, Telegram-код."""

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenPayload
from app.database import get_db
from app.deps import require_tenant
from app.models import Booking, Conversation, Service, Tenant, TenantNotification
from app.redis_service import create_tg_code
from app.schemas import (
    BookingCreateIn,
    BookingOut,
    BookingQuery,
    BookingUpdateIn,
    DashboardStats,
    NotificationsStatusOut,
    ServiceIn,
    ServiceOut,
    SettingsIn,
    SettingsOut,
    TgCodeOut,
)
from app.whatsapp import meta_service

router = APIRouter(prefix="/api/tenant", tags=["tenant"], dependencies=[Depends(require_tenant)])


async def _tenant(db: AsyncSession, payload: TokenPayload) -> Tenant:
    tenant = await db.get(Tenant, uuid.UUID(payload.tenant_id))
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _booking_out(b: Booking, svc: Service | None = None) -> BookingOut:
    out = BookingOut.model_validate(b)
    if svc:
        out.service_name_ru = svc.name_ru
        out.service_name_kz = svc.name_kz
    return out


async def _bookings_with_services(
    db: AsyncSession, tenant_id: uuid.UUID, from_date: date, to_date: date
) -> list[BookingOut]:
    result = await db.execute(
        select(Booking)
        .where(
            Booking.tenant_id == tenant_id,
            Booking.date >= from_date,
            Booking.date <= to_date,
        )
        .order_by(Booking.date, Booking.time)
    )
    bookings = list(result.scalars().all())
    service_ids = {b.service_id for b in bookings if b.service_id}
    services: dict = {}
    if service_ids:
        sresult = await db.execute(select(Service).where(Service.id.in_(service_ids)))
        services = {s.id: s for s in sresult.scalars().all()}
    return [_booking_out(b, services.get(b.service_id)) for b in bookings]


@router.get("/me", response_model=SettingsOut)
async def me(payload: TokenPayload = Depends(require_tenant), db: AsyncSession = Depends(get_db)):
    return await _tenant(db, payload)


# ---------- Услуги ----------
@router.get("/services", response_model=list[ServiceOut])
async def list_services(
    payload: TokenPayload = Depends(require_tenant), db: AsyncSession = Depends(get_db)
):
    tenant = await _tenant(db, payload)
    result = await db.execute(
        select(Service)
        .where(Service.tenant_id == tenant.id)
        .order_by(Service.sort, Service.created_at)
    )
    return list(result.scalars().all())


@router.post("/services", response_model=ServiceOut)
async def create_service(
    data: ServiceIn,
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    service = Service(tenant_id=tenant.id, **data.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@router.patch("/services/{service_id}", response_model=ServiceOut)
async def update_service(
    service_id: str,
    data: ServiceIn,
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    service = await _get_service(db, tenant.id, service_id)
    for field, value in data.model_dump().items():
        setattr(service, field, value)
    await db.commit()
    await db.refresh(service)
    return service


@router.delete("/services/{service_id}")
async def delete_service(
    service_id: str,
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    service = await _get_service(db, tenant.id, service_id)
    await db.delete(service)
    await db.commit()
    return {"ok": True}


# ---------- Записи ----------
@router.get("/bookings", response_model=list[BookingOut])
async def list_bookings(
    from_date: date,
    to_date: date,
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    return await _bookings_with_services(db, tenant.id, from_date, to_date)


@router.post("/bookings", response_model=BookingOut)
async def create_manual_booking(
    data: BookingCreateIn,
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    svc = None
    if data.service_id:
        svc = await db.get(Service, data.service_id)
        if svc is None or svc.tenant_id != tenant.id:
            raise HTTPException(status_code=404, detail="Service not found")
    from app.bookings.service import create_booking

    booking = await create_booking(
        db,
        tenant,
        svc,
        client_name=data.client_name,
        client_phone=data.client_phone,
        d=data.date,
        start=data.time,
        source="dashboard",
        notes=data.notes,
    )
    return _booking_out(booking, svc)


@router.patch("/bookings/{booking_id}", response_model=BookingOut)
async def update_booking(
    booking_id: str,
    data: BookingUpdateIn,
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    booking = await _get_booking(db, tenant.id, booking_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(booking, field, value)
    await db.commit()
    await db.refresh(booking)
    svc = None
    if booking.service_id:
        svc = await db.get(Service, booking.service_id)
    return _booking_out(booking, svc)


@router.delete("/bookings/{booking_id}")
async def delete_booking(
    booking_id: str,
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    booking = await _get_booking(db, tenant.id, booking_id)
    await db.delete(booking)
    await db.commit()
    return {"ok": True}


# ---------- Статистика ----------
@router.get("/stats/dashboard", response_model=DashboardStats)
async def dashboard_stats(
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    bookings_today = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Booking)
                .where(Booking.tenant_id == tenant.id, Booking.date == today)
            )
        ).scalar()
        or 0
    )
    week_bookings_result = await db.execute(
        select(Booking).where(
            Booking.tenant_id == tenant.id,
            Booking.date >= week_start,
            Booking.date <= week_end,
        )
    )
    week_bookings = list(week_bookings_result.scalars().all())

    revenue = 0
    for b in week_bookings:
        if b.service_id:
            svc = await db.get(Service, b.service_id)
            if svc:
                revenue += svc.price

    new_convs = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Conversation)
                .where(
                    Conversation.tenant_id == tenant.id,
                    Conversation.created_at >= datetime.now(timezone.utc) - timedelta(days=7),
                )
            )
        ).scalar()
        or 0
    )

    upcoming = await _bookings_with_services(
        db, tenant.id, today, today + timedelta(days=7)
    )
    upcoming = [b for b in upcoming if b.status == "confirmed"]

    chart = []
    for i in range(7):
        d = today - timedelta(days=6 - i)
        count = int(
            (
                await db.execute(
                    select(func.count())
                    .select_from(Booking)
                    .where(Booking.tenant_id == tenant.id, Booking.date == d)
                )
            ).scalar()
            or 0
        )
        chart.append({"date": d.isoformat(), "count": count})

    return DashboardStats(
        bookings_today=bookings_today,
        bookings_week=len(week_bookings),
        new_conversations_7d=new_convs,
        revenue_estimate_week=revenue,
        upcoming=upcoming,
        week_chart=chart,
        subscription_status=tenant.subscription_status,
        paid_until=tenant.paid_until,
    )


# ---------- Настройки ----------
@router.patch("/settings", response_model=SettingsOut)
async def update_settings(
    data: SettingsIn,
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return tenant


# ---------- ИИ-ассистент владельца (панель) ----------
class AiChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@router.post("/ai-chat")
async def ai_chat(
    data: AiChatIn,
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    from app.ai import business
    from app.ai.context import build_tenant_context

    ctx = await build_tenant_context(db, tenant, language=tenant.language)
    try:
        reply = await business.generate_business_response(
            question=data.question, data_context=ctx, language=tenant.language
        )
    except Exception:
        raise HTTPException(status_code=502, detail="AI temporarily unavailable")
    return {"reply": reply}


# ---------- Telegram-подключение ----------
@router.get("/notifications", response_model=NotificationsStatusOut)
async def notifications_status(
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    result = await db.execute(
        select(TenantNotification).where(TenantNotification.tenant_id == tenant.id)
    )
    link = result.scalar_one_or_none()
    if link is None:
        return NotificationsStatusOut(linked=False, tg_chat_id="", tg_username="", linked_at=None)
    return NotificationsStatusOut(
        linked=bool(link.tg_chat_id),
        tg_chat_id=link.tg_chat_id,
        tg_username=link.tg_username,
        linked_at=link.linked_at,
    )


@router.post("/notifications/code", response_model=TgCodeOut)
async def get_tg_code(
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    code = await create_tg_code(str(tenant.id), ttl=300)
    return TgCodeOut(code=code, ttl_seconds=300)


@router.post("/notifications/test", response_model=dict)
async def test_notification(
    payload: TokenPayload = Depends(require_tenant),
    db: AsyncSession = Depends(get_db),
):
    tenant = await _tenant(db, payload)
    result = await db.execute(
        select(TenantNotification).where(TenantNotification.tenant_id == tenant.id)
    )
    link = result.scalar_one_or_none()
    if link is None or not link.tg_chat_id:
        raise HTTPException(status_code=400, detail="Telegram not linked yet")
    from app.notifications.telegram import safe_send

    await safe_send(link.tg_chat_id, "🔔 Тестовое уведомление из панели Angime!")
    return {"ok": True}


# ---------- Хелперы ----------
async def _get_service(db: AsyncSession, tenant_id: uuid.UUID, service_id: str) -> Service:
    try:
        sid = uuid.UUID(service_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Service not found")
    service = await db.get(Service, sid)
    if service is None or service.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


async def _get_booking(db: AsyncSession, tenant_id: uuid.UUID, booking_id: str) -> Booking:
    try:
        bid = uuid.UUID(booking_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking = await db.get(Booking, bid)
    if booking is None or booking.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking
