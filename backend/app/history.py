"""Redis-backed history log."""
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel

from app.redis_client import get_redis

HISTORY_KEY = "snore:history"
HISTORY_ENTRY_KEY = "snore:history:{id}"
MAX_HISTORY = 500

HistoryAction = Literal["sent", "flushed", "auto_sent", "acknowledged", "muted_skip"]


class HistoryNotification(BaseModel):
    username: str  # "global" for the global Slack webhook
    notifier_type: str  # slack_webhook | pushover | pagerduty


class HistoryIncident(BaseModel):
    id: str
    title: str
    source: str
    host: str | None
    service: str | None
    received_at: datetime


class HistoryEntry(BaseModel):
    id: str
    queue: str
    action: HistoryAction
    incidents: list[HistoryIncident]
    notifications: list[HistoryNotification]
    takeover_user: str | None
    triggered_by: str | None  # username for manual actions, None for scheduler
    created_at: datetime


async def log_history(
    queue: str,
    action: HistoryAction,
    incidents: list,
    notifications: list[HistoryNotification],
    takeover_user: str | None,
    triggered_by: str | None,
) -> None:
    from app.models import Incident

    redis = await get_redis()
    entry_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    history_incidents = [
        HistoryIncident(
            id=inc.id,
            title=inc.title,
            source=inc.source,
            host=inc.host,
            service=inc.service,
            received_at=inc.received_at,
        )
        for inc in incidents
        if isinstance(inc, Incident)
    ]

    entry = HistoryEntry(
        id=entry_id,
        queue=queue,
        action=action,
        incidents=history_incidents,
        notifications=notifications,
        takeover_user=takeover_user,
        triggered_by=triggered_by,
        created_at=created_at,
    )

    await redis.set(HISTORY_ENTRY_KEY.format(id=entry_id), entry.model_dump_json())
    await redis.zadd(HISTORY_KEY, {entry_id: created_at.timestamp()})

    # Trim to MAX_HISTORY
    count = await redis.zcard(HISTORY_KEY)
    if count > MAX_HISTORY:
        oldest = await redis.zrange(HISTORY_KEY, 0, count - MAX_HISTORY - 1)
        if oldest:
            await redis.zrem(HISTORY_KEY, *oldest)
            for old_id in oldest:
                await redis.delete(HISTORY_ENTRY_KEY.format(id=old_id))


async def get_history(limit: int = 100, offset: int = 0) -> list[HistoryEntry]:
    redis = await get_redis()
    ids = await redis.zrevrange(HISTORY_KEY, offset, offset + limit - 1)
    entries: list[HistoryEntry] = []
    for entry_id in ids:
        raw = await redis.get(HISTORY_ENTRY_KEY.format(id=entry_id))
        if raw:
            entries.append(HistoryEntry.model_validate_json(raw))
    return entries
