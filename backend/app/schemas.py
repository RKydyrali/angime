import uuid
from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Auth ----------
class AdminLoginIn(BaseModel):
    username: str
    password: str


class TenantLoginIn(BaseModel):
    email: str
    password: str


class LoginOut(BaseModel):
    token: str
    role: str
    name: str
    tenant_id: Optional[str] = None


# ---------- Tenant (admin view) ----------
class TenantIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    contact_phone: str = ""
    login_email: Optional[str] = None
    password: Optional[str] = None
    subscription_price: int = 20000
    subscription_plan: str = "monthly"
    months_paid: int = Field(default=1, ge=0)
    language: str = "ru"
    timezone: str = "Asia/Almaty"


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    contact_phone: str
    login_email: Optional[str]
    language: str
    timezone: str
    whatsapp_connected: bool
    whatsapp_business_name: str
    subscription_plan: str
    subscription_price: int
    paid_until: Optional[datetime]
    subscription_status: str
    created_at: datetime


class TenantDetailOut(TenantOut):
    meta_phone_number_id: str
    has_meta_access_token: bool = False
    has_meta_app_secret: bool = False
    has_meta_verify_token: bool = False
    meta_verify_token: str = ""
    reminder_enabled: bool
    reminder_hours_before: int
    business_hours: dict


class TenantUpdateIn(BaseModel):
    name: Optional[str] = None
    contact_phone: Optional[str] = None
    login_email: Optional[str] = None
    password: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None


class MetaCredsIn(BaseModel):
    phone_number_id: str
    access_token: str
    app_secret: str
    verify_token: str
    business_name: str = ""


class SubscriptionIn(BaseModel):
    months: int = Field(ge=0, le=120)
    set_paid_until: Optional[datetime] = None
    status: Optional[str] = None  # active | suspended | trial


class TestMessageIn(BaseModel):
    wa_id: str = Field(min_length=5)


# ---------- Services ----------
class ServiceIn(BaseModel):
    name_ru: str = Field(min_length=1, max_length=200)
    name_kz: str = ""
    description_ru: str = ""
    description_kz: str = ""
    price: int = Field(ge=0)
    duration_min: int = Field(ge=5, le=1440, default=60)
    is_active: bool = True
    sort: int = 0
    daily_limit: int = Field(default=0, ge=0)


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name_ru: str
    name_kz: str
    description_ru: str
    description_kz: str
    price: int
    duration_min: int
    is_active: bool
    sort: int
    daily_limit: int


# ---------- Bookings ----------
class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    service_id: Optional[uuid.UUID]
    client_name: str
    client_phone: str
    date: date
    time: time
    duration_min: int
    status: str
    notes: str
    source: str
    created_at: datetime
    service_name_ru: Optional[str] = None
    service_name_kz: Optional[str] = None


class BookingCreateIn(BaseModel):
    service_id: Optional[uuid.UUID] = None
    client_name: str = Field(min_length=1, max_length=200)
    client_phone: str = ""
    date: date
    time: time
    duration_min: int = 60
    notes: str = ""


class BookingUpdateIn(BaseModel):
    status: Optional[str] = None
    client_name: Optional[str] = None
    date: Optional[date] = None
    time: Optional[time] = None
    service_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class BookingQuery(BaseModel):
    from_date: date
    to_date: date


# ---------- Settings ----------
class SettingsIn(BaseModel):
    business_hours: Optional[dict] = None
    knowledge_ru: Optional[str] = None
    knowledge_kz: Optional[str] = None
    greeting_enabled: Optional[bool] = None
    reminder_enabled: Optional[bool] = None
    reminder_hours_before: Optional[int] = Field(default=None, ge=1, le=72)


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    language: str
    timezone: str
    business_hours: dict
    knowledge_ru: str
    knowledge_kz: str
    greeting_enabled: bool
    reminder_enabled: bool
    reminder_hours_before: int
    whatsapp_connected: bool
    subscription_status: str
    paid_until: Optional[datetime]
    subscription_price: int


# ---------- Stats ----------
class DashboardStats(BaseModel):
    bookings_today: int
    bookings_week: int
    new_conversations_7d: int
    revenue_estimate_week: int
    upcoming: list[BookingOut]
    week_chart: list[dict]
    subscription_status: str
    paid_until: Optional[datetime]


class AdminStats(BaseModel):
    tenants_total: int
    tenants_active: int
    tenants_expiring_soon: list[TenantOut]
    bookings_30d: int


# ---------- Telegram ----------
class TgCodeOut(BaseModel):
    code: str
    ttl_seconds: int


class NotificationsStatusOut(BaseModel):
    linked: bool
    tg_chat_id: str
    tg_username: str
    linked_at: Optional[datetime]
