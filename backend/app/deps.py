import uuid
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import COOKIE_NAME, TokenPayload, decode_token
from app.database import get_db
from app.models import Tenant

UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
)
FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _extract_token(request: Request, cookie: Optional[str]) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip()
    if cookie:
        return cookie
    raise UNAUTHORIZED


def require_admin(
    request: Request,
    cookie: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
) -> TokenPayload:
    token = _extract_token(request, cookie)
    try:
        payload = decode_token(token)
    except Exception:
        raise UNAUTHORIZED
    if payload.role != "admin":
        raise FORBIDDEN
    return payload


def require_tenant(
    request: Request,
    cookie: Optional[str] = Cookie(default=None, alias=COOKIE_NAME),
) -> TokenPayload:
    token = _extract_token(request, cookie)
    try:
        payload = decode_token(token)
    except Exception:
        raise UNAUTHORIZED
    if payload.role != "tenant":
        raise FORBIDDEN
    if not payload.tenant_id:
        raise FORBIDDEN
    return payload


async def get_tenant_or_404(
    tenant_id: str, db: AsyncSession
) -> Tenant:
    try:
        tid = uuid.UUID(tenant_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant = await db.get(Tenant, tid)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant
