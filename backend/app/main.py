"""Angime — FastAPI: webhook-шлюз Meta (мультитенантный), API панели, планировщик,
Telegram-бот уведомлений."""

import asyncio
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select, text

import app.database as database
from app.ai import openrouter
from app.config import config
from app.notifications.bot import start_telegram_bot, stop_telegram_bot
from app.notifications.telegram import close_client as close_tg_client
from app.routers import admin_router, auth_router, tenant_router
from app.scheduler import shutdown_scheduler, start_scheduler
from app.whatsapp import meta_service
from app.whatsapp.webhook_service import (
    flush_debouncer,
    process_webhook_payload,
    verify_signature,
    verify_webhook_get,
)

logger = structlog.get_logger("angime.main")


def setup_logging() -> None:
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    for noisy in ("httpx", "apscheduler", "aiosqlite"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


setup_logging()


async def bootstrap_admin() -> None:
    from app.auth import hash_password
    from app.models import AdminUser

    async with database.AsyncSessionLocal() as db:
        result = await db.execute(select(AdminUser).limit(1))
        if result.scalar_one_or_none() is None:
            db.add(
                AdminUser(
                    username=config.ADMIN_USERNAME,
                    password_hash=hash_password(config.ADMIN_PASSWORD),
                )
            )
            await db.commit()
            logger.info("Bootstrap admin created: %s", config.ADMIN_USERNAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Angime")
    await bootstrap_admin()
    start_scheduler()
    start_telegram_bot()
    yield
    await flush_debouncer()
    await stop_telegram_bot()
    shutdown_scheduler()
    await database.redis_client.aclose()
    await database.engine.dispose()
    await openrouter.close_client()
    await meta_service.close_client()
    await close_tg_client()
    logger.info("Angime stopped")


app = FastAPI(title="Angime API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://danyshpan.xyz",
        "https://www.danyshpan.xyz",
        "https://server.danyshpan.xyz",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(tenant_router.router)


@app.get("/health")
async def health() -> JSONResponse:
    checks: dict[str, str] = {}
    try:
        await asyncio.wait_for(database.redis_client.ping(), timeout=2.0)
        checks["redis"] = "ok"
    except Exception as exc:
        logger.exception("health redis check failed: %s", exc)
        checks["redis"] = "error"
    try:
        async with database.AsyncSessionLocal() as session:
            await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=3.0)
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "error"
    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "degraded", **checks},
    )


@app.get("/webhook")
async def webhook_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):
    return await verify_webhook_get(hub_mode, hub_verify_token, hub_challenge)


@app.post("/webhook")
async def webhook_receive(request: Request):
    body = await request.body()
    await verify_signature(request, body)
    payload = await request.json()
    asyncio.get_running_loop().create_task(process_webhook_payload(payload))
    return {"status": "ok"}
