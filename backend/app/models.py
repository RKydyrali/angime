import uuid
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    contact_phone: Mapped[str] = mapped_column(String(50), default="")
    login_email: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # --- Локализация ---
    language: Mapped[str] = mapped_column(String(10), default="ru")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Almaty")

    # --- Часы работы: {"mon": {"open":"09:00","close":"18:00"}, "sun": null} ---
    business_hours: Mapped[dict] = mapped_column(JSON, default=dict)

    # --- Знания бота (свободный текст, менеджер заполняет сам) ---
    knowledge_ru: Mapped[str] = mapped_column(Text, default="")
    knowledge_kz: Mapped[str] = mapped_column(Text, default="")

    # --- Настройки ---
    greeting_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_hours_before: Mapped[int] = mapped_column(Integer, default=1)

    # --- Meta Cloud API (WABA тенанта) ---
    meta_phone_number_id: Mapped[str] = mapped_column(String(100), default="")
    meta_access_token: Mapped[str] = mapped_column(String(512), default="")
    meta_app_secret: Mapped[str] = mapped_column(String(200), default="")
    meta_verify_token: Mapped[str] = mapped_column(String(200), default="")
    whatsapp_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    whatsapp_business_name: Mapped[str] = mapped_column(String(200), default="")

    # --- Подписка ---
    subscription_plan: Mapped[str] = mapped_column(String(50), default="monthly")
    subscription_price: Mapped[int] = mapped_column(Integer, default=20000)
    paid_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # trial | active | expired | suspended
    subscription_status: Mapped[str] = mapped_column(String(20), default="trial")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    services: Mapped[list["Service"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    name_ru: Mapped[str] = mapped_column(String(200))
    name_kz: Mapped[str] = mapped_column(String(200), default="")
    description_ru: Mapped[str] = mapped_column(Text, default="")
    description_kz: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[int] = mapped_column(Integer, default=0)
    duration_min: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    daily_limit: Mapped[int] = mapped_column(Integer, default=0)  # 0 = без лимита
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="services")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="service")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    service_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="SET NULL"), nullable=True
    )
    client_name: Mapped[str] = mapped_column(String(200), default="")
    client_phone: Mapped[str] = mapped_column(String(50), default="")
    date: Mapped[date] = mapped_column(Date, index=True)
    time: Mapped[time] = mapped_column(Time, index=True)
    duration_min: Mapped[int] = mapped_column(Integer, default=60)
    # confirmed | cancelled | completed | no_show
    status: Mapped[str] = mapped_column(String(20), default="confirmed", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(20), default="whatsapp")
    wa_sender_id: Mapped[str] = mapped_column(String(100), default="", index=True)
    last_client_message_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="bookings")
    service: Mapped[Optional["Service"]] = relationship(back_populates="bookings")


class Conversation(Base):
    """WA-клиент внутри тенанта: язык, последняя активность, приветствие."""

    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "wa_sender_id", name="uq_conv_tenant_sender"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    wa_sender_id: Mapped[str] = mapped_column(String(100), index=True)
    language: Mapped[str] = mapped_column(String(10), default="ru")
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    greeted_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="conversations")


class QuestionLog(Base):
    """Вопросы, на которые бот не смог ответить (зона роста)."""

    __tablename__ = "question_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    topic: Mapped[str] = mapped_column(String(200), default="")
    question: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TenantNotification(Base):
    """Привязка Telegram-чата владельца к тенанту (6-значный код)."""

    __tablename__ = "tenant_notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    tg_chat_id: Mapped[str] = mapped_column(String(100), default="")
    tg_username: Mapped[str] = mapped_column(String(200), default="")
    linked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant: Mapped["Tenant"] = relationship()
