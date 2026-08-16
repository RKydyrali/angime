import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.config import config

ALGORITHM = "HS256"
TOKEN_TTL_HOURS = 24 * 7
COOKIE_NAME = "angime_token"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


def create_token(
    subject: str, role: str, tenant_id: Optional[uuid.UUID] = None
) -> str:
    payload = {
        "sub": subject,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    if tenant_id is not None:
        payload["tenant_id"] = str(tenant_id)
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITHM)


class TokenPayload:
    def __init__(self, sub: str, role: str, tenant_id: Optional[str] = None):
        self.sub = sub
        self.role = role
        self.tenant_id = tenant_id


def decode_token(token: str) -> TokenPayload:
    data = jwt.decode(token, config.JWT_SECRET, algorithms=[ALGORITHM])
    return TokenPayload(
        sub=data["sub"],
        role=data["role"],
        tenant_id=data.get("tenant_id"),
    )
