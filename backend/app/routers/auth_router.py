from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_token, hash_password, verify_password
from app.config import config
from app.database import get_db
from app.models import AdminUser, Tenant
from app.schemas import AdminLoginIn, LoginOut, TenantLoginIn

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/admin/login", response_model=LoginOut)
async def admin_login(data: AdminLoginIn, db: AsyncSession = Depends(get_db)):
    if data.username == config.ADMIN_USERNAME and verify_password(
        data.password, config.ADMIN_PASSWORD
    ):
        return LoginOut(
            token=create_token("admin", "admin"),
            role="admin",
            name=config.ADMIN_USERNAME,
        )
    result = await db.execute(
        select(AdminUser).where(AdminUser.username == data.username)
    )
    admin = result.scalar_one_or_none()
    if admin and verify_password(data.password, admin.password_hash):
        return LoginOut(
            token=create_token(admin.username, "admin"),
            role="admin",
            name=admin.username,
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")


@router.post("/tenant/login", response_model=LoginOut)
async def tenant_login(data: TenantLoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Tenant).where(Tenant.login_email == data.email.strip().lower())
    )
    tenant = result.scalar_one_or_none()
    if tenant and tenant.password_hash and verify_password(
        data.password, tenant.password_hash
    ):
        subject = tenant.login_email or str(tenant.id)
        return LoginOut(
            token=create_token(subject, "tenant", tenant.id),
            role="tenant",
            name=tenant.name,
            tenant_id=str(tenant.id),
        )
    raise HTTPException(status_code=401, detail="Invalid credentials")
