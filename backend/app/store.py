"""Redis-backed incident store."""
import uuid
from datetime import datetime, timezone

from app.models import Incident, IncidentCreate, Takeover
from app.redis_client import get_redis

INCIDENT_KEY = "snore:incident:{id}"
QUEUE_KEY = "snore:queue:{name}"
MUTE_KEY = "snore:mute:{name}"
TAKEOVER_KEY = "snore:takeover:{name}"
ONCALL_KEY = "snore:oncall:{name}"


async def add_incident(data: IncidentCreate) -> Incident:
    redis = await get_redis()
    incident_id = str(uuid.uuid4())
    received_at = datetime.now(timezone.utc)

    incident = Incident(
        id=incident_id,
        source=data.source,
        title=data.title,
        description=data.description,
        queue=data.queue,
        host=data.host,
        service=data.service,
        received_at=received_at,
        raw_payload=data.raw_payload,
    )

    await redis.set(
        INCIDENT_KEY.format(id=incident_id),
        incident.model_dump_json(),
    )
    await redis.zadd(
        QUEUE_KEY.format(name=data.queue),
        {incident_id: received_at.timestamp()},
    )

    return incident


async def get_queue_incidents(queue: str) -> list[Incident]:
    redis = await get_redis()
    ids = await redis.zrange(QUEUE_KEY.format(name=queue), 0, -1)
    incidents: list[Incident] = []
    for incident_id in ids:
        raw = await redis.get(INCIDENT_KEY.format(id=incident_id))
        if raw:
            incidents.append(Incident.model_validate_json(raw))
    return incidents


async def get_all_incidents() -> dict[str, list[Incident]]:
    """Return incidents grouped by queue."""
    from app.config import get_config
    result: dict[str, list[Incident]] = {}
    for queue in get_config().queues:
        result[queue.name] = await get_queue_incidents(queue.name)
    return result


async def acknowledge_incident(incident_id: str, queue: str) -> "Incident | None":
    """Remove incident from queue and return it (None if not found)."""
    redis = await get_redis()
    raw = await redis.get(INCIDENT_KEY.format(id=incident_id))
    if not raw:
        return None
    removed = await redis.zrem(QUEUE_KEY.format(name=queue), incident_id)
    if not removed:
        return None
    await redis.delete(INCIDENT_KEY.format(id=incident_id))
    return Incident.model_validate_json(raw)


async def flush_queue(queue: str) -> list[Incident]:
    """Remove all incidents from queue and return them for notification."""
    redis = await get_redis()
    incidents = await get_queue_incidents(queue)
    if incidents:
        ids = [i.id for i in incidents]
        await redis.zrem(QUEUE_KEY.format(name=queue), *ids)
        for incident_id in ids:
            await redis.delete(INCIDENT_KEY.format(id=incident_id))
    return incidents


async def set_mute(queue: str, duration_minutes: int) -> None:
    redis = await get_redis()
    await redis.setex(MUTE_KEY.format(name=queue), duration_minutes * 60, "1")


async def is_muted(queue: str) -> bool:
    redis = await get_redis()
    return bool(await redis.exists(MUTE_KEY.format(name=queue)))


async def get_mute_ttl(queue: str) -> int:
    """Returns remaining mute seconds, or 0 if not muted."""
    redis = await get_redis()
    ttl = await redis.ttl(MUTE_KEY.format(name=queue))
    return max(0, ttl)


async def unmute_queue(queue: str) -> None:
    redis = await get_redis()
    await redis.delete(MUTE_KEY.format(name=queue))


async def get_oldest_incident_timestamp(queue: str) -> float | None:
    redis = await get_redis()
    result = await redis.zrange(QUEUE_KEY.format(name=queue), 0, 0, withscores=True)
    if result:
        return result[0][1]
    return None


async def set_takeover(queue: str, username: str, duration_minutes: int) -> Takeover:
    redis = await get_redis()
    expires_at = datetime.now(timezone.utc).replace(microsecond=0)
    from datetime import timedelta
    expires_at = expires_at + timedelta(minutes=duration_minutes)
    takeover = Takeover(username=username, expires_at=expires_at)
    await redis.setex(TAKEOVER_KEY.format(name=queue), duration_minutes * 60, takeover.model_dump_json())
    return takeover


async def get_takeover(queue: str) -> Takeover | None:
    redis = await get_redis()
    raw = await redis.get(TAKEOVER_KEY.format(name=queue))
    if raw:
        return Takeover.model_validate_json(raw)
    return None


async def get_takeover_ttl(queue: str) -> int:
    redis = await get_redis()
    ttl = await redis.ttl(TAKEOVER_KEY.format(name=queue))
    return max(0, ttl)


async def clear_takeover(queue: str) -> None:
    redis = await get_redis()
    await redis.delete(TAKEOVER_KEY.format(name=queue))


async def set_oncall(queue: str, usernames: list[str], duration_minutes: int | None) -> None:
    import json
    redis = await get_redis()
    data = json.dumps(usernames)
    if duration_minutes is not None:
        await redis.setex(ONCALL_KEY.format(name=queue), duration_minutes * 60, data)
    else:
        await redis.set(ONCALL_KEY.format(name=queue), data)


async def get_oncall(queue: str) -> list[str] | None:
    import json
    redis = await get_redis()
    raw = await redis.get(ONCALL_KEY.format(name=queue))
    if raw:
        return json.loads(raw)
    return None


async def get_oncall_ttl(queue: str) -> int | None:
    """Returns remaining seconds, or None if key has no TTL (permanent), or -2 if key missing."""
    redis = await get_redis()
    ttl = await redis.ttl(ONCALL_KEY.format(name=queue))
    if ttl == -1:
        return None  # key exists, no expiry
    if ttl < 0:
        return -2    # key missing
    return ttl


async def clear_oncall(queue: str) -> None:
    redis = await get_redis()
    await redis.delete(ONCALL_KEY.format(name=queue))
