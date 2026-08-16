"""Админ-панель: клиенты, подписки, Meta-подключение, статистика."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenPayload, hash_password
from app.bookings.service import create_booking
from app.config import config
from app.database import get_db
from app.deps import require_admin
from app.models import Booking, Tenant
from app.redis_service import create_tg_code
from app.schemas import (
    AdminStats,
    LoginOut,
    MetaCredsIn,
    SubscriptionIn,
    TenantDetailOut,
    TenantIn,
    TenantOut,
    TenantUpdateIn,
    TestMessageIn,
    TgCodeOut,
)
from app.whatsapp import meta_service

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _tenant_out(t: Tenant) -> TenantOut:
    return TenantOut.model_validate(t)


@router.get("/stats", response_model=AdminStats)
async def admin_stats(db: AsyncSession = Depends(get_db)):
    tenants_total = int(
        (await db.execute(select(func.count()).select_from(Tenant))).scalar() or 0
    )
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Tenant).where(
            Tenant.subscription_status == "active", Tenant.paid_until >= now
        )
    )
    active = list(result.scalars().all())
    result = await db.execute(
        select(Tenant).where(Tenant.paid_until.is_not(None))
    )
    all_tenants = list(result.scalars().all())
    expiring = [
        t
        for t in all_tenants
        if t.paid_until and 0 <= (t.paid_until - now).days <= 7
    ]
    bookings_30d = int(
        (
            await db.execute(
                select(func.count())
                .select_from(Booking)
                .where(Booking.created_at >= now - timedelta(days=30))
            )
        ).scalar()
        or 0
    )
    return AdminStats(
        tenants_total=tenants_total,
        tenants_active=len(active),
        tenants_expiring_soon=[_tenant_out(t) for t in expiring],
        bookings_30d=bookings_30d,
    )


@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return [_tenant_out(t) for t in result.scalars().all()]


@router.post("/tenants", response_model=TenantOut)
async def create_tenant(data: TenantIn, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(
        select(Tenant).where(
            (Tenant.slug == data.slug)
            | (
                (Tenant.login_email == (data.login_email or "").strip().lower())
                if data.login_email
                else False
            )
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Slug or email already in use")
    tenant = Tenant(
        name=data.name,
        slug=data.slug,
        contact_phone=data.contact_phone,
        login_email=(data.login_email or "").strip().lower() or None,
        password_hash=hash_password(data.password) if data.password else None,
        language=data.language,
        timezone=data.timezone,
        subscription_plan=data.subscription_plan,
        subscription_price=data.subscription_price,
        subscription_status="trial",
        paid_until=(
            datetime.now(timezone.utc) + timedelta(days=30 * data.months_paid)
            if data.months_paid > 0
            else None
        ),
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return _tenant_out(tenant)


@router.get("/tenants/{tenant_id}", response_model=TenantDetailOut)
async def get_tenant(tenant_id: str, db: AsyncSession = Depends(get_db)):
    tenant = await _get(db, tenant_id)
    out = TenantDetailOut.model_validate(tenant)
    out.has_meta_access_token = bool(tenant.meta_access_token)
    out.has_meta_app_secret = bool(tenant.meta_app_secret)
    out.has_meta_verify_token = bool(tenant.meta_verify_token)
    return out


@router.patch("/tenants/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: str, data: TenantUpdateIn, db: AsyncSession = Depends(get_db)
):
    tenant = await _get(db, tenant_id)
    for field, value in data.model_dump(exclude_none=True).items():
        if field == "password" and value:
            tenant.password_hash = hash_password(value)
            continue
        setattr(tenant, field, value)
    await db.commit()
    await db.refresh(tenant)
    return _tenant_out(tenant)


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str, db: AsyncSession = Depends(get_db)):
    tenant = await _get(db, tenant_id)
    await db.delete(tenant)
    await db.commit()
    return {"ok": True}


@router.post("/tenants/{tenant_id}/meta-creds", response_model=TenantDetailOut)
async def set_meta_creds(
    tenant_id: str, data: MetaCredsIn, db: AsyncSession = Depends(get_db)
):
    tenant = await _get(db, tenant_id)
    tenant.meta_phone_number_id = data.phone_number_id.strip()
    tenant.meta_access_token = data.access_token.strip()
    tenant.meta_app_secret = data.app_secret.strip()
    tenant.meta_verify_token = data.verify_token.strip()
    tenant.whatsapp_business_name = data.business_name.strip()
    tenant.whatsapp_connected = bool(
        tenant.meta_phone_number_id and tenant.meta_access_token
    )
    await db.commit()
    await db.refresh(tenant)
    out = TenantDetailOut.model_validate(tenant)
    out.has_meta_access_token = True
    out.has_meta_app_secret = True
    out.has_meta_verify_token = True
    return out


@router.post("/tenants/{tenant_id}/subscription", response_model=TenantOut)
async def update_subscription(
    tenant_id: str, data: SubscriptionIn, db: AsyncSession = Depends(get_db)
):
    tenant = await _get(db, tenant_id)
    if data.set_paid_until:
        tenant.paid_until = data.set_paid_until
    elif data.months > 0:
        base = tenant.paid_until or datetime.now(timezone.utc)
        tenant.paid_until = base + timedelta(days=30 * data.months)
    if data.status:
        tenant.subscription_status = data.status
    elif tenant.paid_until and tenant.paid_until >= datetime.now(timezone.utc):
        tenant.subscription_status = "active"
    await db.commit()
    await db.refresh(tenant)
    return _tenant_out(tenant)


@router.post("/tenants/{tenant_id}/tg-code", response_model=TgCodeOut)
async def generate_tg_code(tenant_id: str, db: AsyncSession = Depends(get_db)):
    await _get(db, tenant_id)
    code = await create_tg_code(tenant_id, ttl=300)
    return TgCodeOut(code=code, ttl_seconds=300)


@router.post("/tenants/{tenant_id}/test-message", response_model=dict)
async def send_test(
    tenant_id: str, data: TestMessageIn, db: AsyncSession = Depends(get_db)
):
    tenant = await _get(db, tenant_id)
    if not tenant.meta_access_token or not tenant.meta_phone_number_id:
        raise HTTPException(status_code=400, detail="Meta credentials not configured")
    ok = await meta_service.send_test_message(tenant, data.wa_id)
    return {"ok": ok}


@router.post("/tenants/{tenant_id}/login-link", response_model=LoginOut)
async def tenant_login_link(tenant_id: str, db: AsyncSession = Depends(get_db)):
    """Админ может войти в панель клиента."""
    tenant = await _get(db, tenant_id)
    from app.auth import create_token

    return LoginOut(
        token=create_token(tenant.login_email or str(tenant.id), "tenant", tenant.id),
        role="tenant",
        name=tenant.name,
        tenant_id=str(tenant.id),
    )


async def _get(db: AsyncSession, tenant_id: str) -> Tenant:
    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant = await db.get(Tenant, tid)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
