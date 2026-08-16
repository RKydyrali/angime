"""Планировщик: напоминания о записях (1 ч до, только в окне 24ч), ежедневные
сводки, предупреждения о подписках."""

import asyncio
import structlog
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Booking, Service, Tenant, TenantNotification
from app.redis_service import within_24h
from app.translations import t
from app.whatsapp import meta_service

logger = structlog.get_logger("angime.scheduler")

_scheduler: BackgroundScheduler | None = None
_main_loop: asyncio.AbstractEventLoop | None = None


async def _check_reminders() -> None:
    """Каждые REMINDER_CHECK_SECONDS: записи, до которых <= reminder_hours_before,
    reminder ещё не отправлен, и момент отправки попадает в 24ч окно."""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Booking).where(
                Booking.status == "confirmed",
                Booking.reminder_sent.is_(False),
            )
        )
        bookings = list(result.scalars().all())
        for booking in bookings:
            tenant = await db.get(Tenant, booking.tenant_id)
            if tenant is None or not tenant.reminder_enabled:
                continue
            try:
                tz = ZoneInfo(tenant.timezone)
            except Exception:
                tz = ZoneInfo("Asia/Almaty")
            booking_dt = datetime.combine(
                booking.date, booking.time, tzinfo=tz
            )
            remind_at = booking_dt - timedelta(
                hours=tenant.reminder_hours_before
            )
            remind_at_utc = remind_at.astimezone(timezone.utc)
            if remind_at_utc > now:
                continue  # ещё не время
            # правило: только если момент отправки в 24ч после последнего сообщения клиента
            if not within_24h(booking.last_client_message_at, now):
                booking.reminder_sent = True
                booking.reminder_skipped = True
                await db.commit()
                logger.info(
                    "Reminder skipped (outside 24h window): booking=%s", booking.id
                )
                continue
            if now - remind_at_utc > timedelta(hours=1):
                # окно отправки ушло (прошло >1ч после момента напоминания)
                booking.reminder_sent = True
                booking.reminder_skipped = True
                await db.commit()
                continue
            service_name = ""
            if booking.service_id:
                svc = await db.get(Service, booking.service_id)
                if svc:
                    service_name = svc.name_ru if tenant.language == "ru" else (svc.name_kz or svc.name_ru)
            if not booking.client_phone:
                booking.reminder_sent = True
                await db.commit()
                continue
            text = t(
                "booking_reminder",
                "ru",
                service=service_name or "запись",
                time=booking.time.strftime("%H:%M"),
                business=tenant.name,
            )
            ok = await meta_service.send_text(tenant, booking.client_phone, text)
            if ok:
                booking.reminder_sent = True
                await db.commit()
                from app.notifications import events

                await events.notify_reminder_sent(db, tenant, booking, service_name)
                logger.info("Reminder sent: booking=%s", booking.id)
            else:
                # временная ошибка — не помечаем, попробуем в след. цикле
                pass


async def _send_daily_summaries() -> None:
    today = date.today()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Booking).where(
                Booking.date == today,
                Booking.status == "confirmed",
            )
        )
        bookings = list(result.scalars().all())
        by_tenant: dict = {}
        for b in bookings:
            by_tenant.setdefault(b.tenant_id, []).append(b)
        for tenant_id, items in by_tenant.items():
            tenant = await db.get(Tenant, tenant_id)
            if tenant is None:
                continue
            from app.notifications import events

            await events.send_daily_summary(db, tenant, items)


async def _check_subscriptions() -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant))
        tenants = list(result.scalars().all())
        for tenant in tenants:
            if tenant.paid_until is None:
                continue
            days_left = (tenant.paid_until - now).days
            if days_left in (7, 3, 1):
                await _notify_subscription(
                    db, tenant, f"Подписка «{tenant.name}» истекает через {days_left} дн."
                )
            elif days_left < 0 and tenant.subscription_status == "active":
                tenant.subscription_status = "expired"
                await db.commit()
                await _notify_subscription(
                    db, tenant, f"Подписка «{tenant.name}» истекла. Продлите в админ-панели."
                )


async def _notify_subscription(db, tenant: Tenant, text: str) -> None:
    from app.config import config

    if config.TELEGRAM_ADMIN_CHAT_ID:
        from app.notifications.telegram import safe_send

        await safe_send(config.TELEGRAM_ADMIN_CHAT_ID, text)


def _run(coro) -> None:
    """Запускает корутину в главном event loop из потока APScheduler."""
    global _main_loop
    if _main_loop is None or not _main_loop.is_running():
        logger.warning("Scheduler main loop not running; task dropped")
        return
    try:
        future = asyncio.run_coroutine_threadsafe(coro, _main_loop)

        def _on_done(f):
            if f.cancelled():
                return
            exc = f.exception()
            if exc:
                logger.error("Scheduler task error: %s", exc)

        future.add_done_callback(_on_done)
    except Exception:
        logger.exception("Scheduler task failed")


def start_scheduler() -> None:
    global _scheduler, _main_loop
    if _scheduler is not None:
        return
    try:
        _main_loop = asyncio.get_running_loop()
    except RuntimeError:
        _main_loop = None
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        lambda: _run(_check_reminders()),
        "interval",
        seconds=config_reminder_interval(),
        id="reminders",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        lambda: _run(_send_daily_summaries()),
        "cron",
        hour=0,
        minute=30,
        timezone="Asia/Almaty",
        id="daily_summary",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        lambda: _run(_check_subscriptions()),
        "interval",
        hours=6,
        id="subscriptions",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Scheduler started")


def config_reminder_interval() -> int:
    from app.config import config

    return config.REMINDER_CHECK_SECONDS


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
