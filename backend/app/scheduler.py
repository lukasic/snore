"""APScheduler job that auto-flushes queues after their configured timeout."""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_config
from app.store import flush_queue, get_oldest_incident_timestamp, get_queue_incidents, is_muted
from app.dispatch import dispatch
from app.history import log_history
from app.redis_client import get_redis
from app.ws import manager

logger = logging.getLogger(__name__)
_scheduler = AsyncIOScheduler()

# Redis key: tracks the oldest-incident timestamp we already logged as muted_skip for a queue
MUTED_SKIP_LOGGED_KEY = "snore:muted_skip_logged:{name}"


async def _check_queues() -> None:
    config = get_config()
    now = datetime.now(timezone.utc).timestamp()

    for queue_cfg in config.queues:
        oldest = await get_oldest_incident_timestamp(queue_cfg.name)
        if oldest is None:
            continue

        age_minutes = (now - oldest) / 60
        if age_minutes < queue_cfg.flush_after_minutes:
            continue

        if await is_muted(queue_cfg.name):
            logger.info("Queue '%s' is muted, skipping auto-flush", queue_cfg.name)
            # Log muted_skip only once per unique "oldest incident" timestamp
            redis = await get_redis()
            logged_key = MUTED_SKIP_LOGGED_KEY.format(name=queue_cfg.name)
            already_logged = await redis.get(logged_key)
            if already_logged == str(oldest):
                continue
            held = await get_queue_incidents(queue_cfg.name)
            await log_history(
                queue=queue_cfg.name,
                action="muted_skip",
                incidents=held,
                notifications=[],
                takeover_user=None,
                triggered_by=None,
            )
            # Remember we logged this batch; expire after 2h as safety net
            await redis.setex(logged_key, 7200, str(oldest))
            continue

        # Clear muted_skip tracker when queue is actually flushed
        redis = await get_redis()
        await redis.delete(MUTED_SKIP_LOGGED_KEY.format(name=queue_cfg.name))

        logger.info("Auto-flushing queue '%s' (%d min old)", queue_cfg.name, int(age_minutes))
        incidents = await flush_queue(queue_cfg.name)
        await dispatch(incidents, queue_cfg.name, action="auto_sent", triggered_by=None)

    await manager.broadcast({"type": "scheduler_tick"})


def start_scheduler() -> None:
    _scheduler.add_job(_check_queues, "interval", minutes=1, id="queue_check")
    _scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    _scheduler.shutdown(wait=False)


def get_next_run_time() -> str | None:
    """Return ISO 8601 string of the next scheduled queue check, or None."""
    job = _scheduler.get_job("queue_check")
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None
