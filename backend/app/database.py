from collections.abc import AsyncGenerator

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import config

engine = create_async_engine(config.POSTGRES_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

redis_client: Redis = Redis.from_url(
    config.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5.0,
    socket_timeout=5.0,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
