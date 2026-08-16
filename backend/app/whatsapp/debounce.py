"""Debounce: быстрые подряд сообщения клиента склеиваются в один ИИ-ответ."""

import asyncio
import structlog
from dataclasses import dataclass, field

from app.config import config

logger = structlog.get_logger("angime.debounce")


@dataclass
class _Pending:
    tenant_id: str
    sender_id: str
    items: list[dict] = field(default_factory=list)
    first_ts: float = 0.0
    timer: asyncio.Task | None = None
    flushed: bool = False


class Debouncer:
    def __init__(self, window: float, max_wait: float, flush_coro):
        self.window = window
        self.max_wait = max_wait
        self.flush_coro = flush_coro
        self._pending: dict[str, _Pending] = {}

    def push(self, tenant_id: str, sender_id: str, item: dict) -> None:
        key = f"{tenant_id}:{sender_id}"
        pending = self._pending.get(key)
        now = asyncio.get_event_loop().time()
        if pending is None:
            pending = _Pending(tenant_id=tenant_id, sender_id=sender_id)
            self._pending[key] = pending
        if not pending.items:
            pending.first_ts = now
        pending.items.append(item)
        if pending.timer is not None and not pending.timer.done():
            pending.timer.cancel()
        if now - pending.first_ts >= self.max_wait:
            self._flush(pending)
            return
        loop = asyncio.get_event_loop()
        pending.timer = loop.create_task(self._schedule(pending))

    async def _schedule(self, pending: _Pending) -> None:
        try:
            await asyncio.sleep(self.window)
        except asyncio.CancelledError:
            return
        if not pending.flushed:
            self._flush(pending)

    def _flush(self, pending: _Pending) -> None:
        if pending.flushed:
            return
        pending.flushed = True
        key = f"{pending.tenant_id}:{pending.sender_id}"
        self._pending.pop(key, None)
        if pending.items:
            items = list(pending.items)
            pending.items.clear()
            asyncio.get_event_loop().create_task(self._run_flush(pending, items))

    async def _run_flush(self, pending: _Pending, items: list[dict]) -> None:
        try:
            await self.flush_coro(pending.tenant_id, pending.sender_id, items)
        except Exception:
            logger.exception("Debounce flush failed")

    async def flush_all(self) -> None:
        for key, pending in list(self._pending.items()):
            if not pending.flushed:
                self._flush(pending)
        for task in asyncio.all_tasks():
            pass
        await asyncio.sleep(0)


debouncer = Debouncer(
    window=config.DEBOUNCE_SECONDS,
    max_wait=config.DEBOUNCE_MAX_SECONDS,
    flush_coro=lambda *a: asyncio.sleep(0),
)
