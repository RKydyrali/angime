"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_admin_users_username", "admin_users", ["username"], unique=True)

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("contact_phone", sa.String(50), nullable=False, server_default=""),
        sa.Column("login_email", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("language", sa.String(10), nullable=False, server_default="ru"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Almaty"),
        sa.Column("business_hours", sa.JSON(), nullable=True),
        sa.Column("knowledge_ru", sa.Text(), nullable=False, server_default=""),
        sa.Column("knowledge_kz", sa.Text(), nullable=False, server_default=""),
        sa.Column("greeting_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reminder_hours_before", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("meta_phone_number_id", sa.String(100), nullable=False, server_default=""),
        sa.Column("meta_access_token", sa.String(512), nullable=False, server_default=""),
        sa.Column("meta_app_secret", sa.String(200), nullable=False, server_default=""),
        sa.Column("meta_verify_token", sa.String(200), nullable=False, server_default=""),
        sa.Column("whatsapp_connected", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("whatsapp_business_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("subscription_plan", sa.String(50), nullable=False, server_default="monthly"),
        sa.Column("subscription_price", sa.Integer(), nullable=False, server_default="20000"),
        sa.Column("paid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subscription_status", sa.String(20), nullable=False, server_default="trial"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)
    op.create_index("ix_tenants_login_email", "tenants", ["login_email"], unique=True)

    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name_ru", sa.String(200), nullable=False),
        sa.Column("name_kz", sa.String(200), nullable=False, server_default=""),
        sa.Column("description_ru", sa.Text(), nullable=False, server_default=""),
        sa.Column("description_kz", sa.Text(), nullable=False, server_default=""),
        sa.Column("price", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_min", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_services_tenant_id", "services", ["tenant_id"])

    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="SET NULL"), nullable=True),
        sa.Column("client_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("client_phone", sa.String(50), nullable=False, server_default=""),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time", sa.Time(), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("status", sa.String(20), nullable=False, server_default="confirmed"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("source", sa.String(20), nullable=False, server_default="whatsapp"),
        sa.Column("wa_sender_id", sa.String(100), nullable=False, server_default=""),
        sa.Column("last_client_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reminder_skipped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bookings_tenant_id", "bookings", ["tenant_id"])
    op.create_index("ix_bookings_date", "bookings", ["date"])
    op.create_index("ix_bookings_time", "bookings", ["time"])
    op.create_index("ix_bookings_status", "bookings", ["status"])
    op.create_index("ix_bookings_wa_sender_id", "bookings", ["wa_sender_id"])

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("wa_sender_id", sa.String(100), nullable=False),
        sa.Column("language", sa.String(10), nullable=False, server_default="ru"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("greeted_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "wa_sender_id", name="uq_conv_tenant_sender"),
    )
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])
    op.create_index("ix_conversations_wa_sender_id", "conversations", ["wa_sender_id"])
    op.create_index("ix_conversations_last_seen_at", "conversations", ["last_seen_at"])

    op.create_table(
        "question_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(200), nullable=False, server_default=""),
        sa.Column("question", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_question_log_tenant_id", "question_log", ["tenant_id"])

    op.create_table(
        "tenant_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tg_chat_id", sa.String(100), nullable=False, server_default=""),
        sa.Column("tg_username", sa.String(200), nullable=False, server_default=""),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tenant_notifications_tenant_id", "tenant_notifications", ["tenant_id"], unique=True)


def downgrade() -> None:
    op.drop_table("tenant_notifications")
    op.drop_table("question_log")
    op.drop_table("conversations")
    op.drop_table("bookings")
    op.drop_table("services")
    op.drop_table("tenants")
    op.drop_table("admin_users")
