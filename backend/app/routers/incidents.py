from fastapi import APIRouter, Depends, HTTPException

from app.config import get_config
from app.dispatch import dispatch
from app.scheduler import get_next_run_time
from app.history import log_history
from app.models import AcknowledgeRequest, FlushRequest, MuteRequest, TakeoverRequest
from app.routers.auth import get_current_user
from app.store import (
    acknowledge_incident,
    clear_takeover,
    flush_queue,
    get_all_incidents,
    get_mute_ttl,
    get_oncall,
    get_oncall_ttl,
    get_takeover,
    get_takeover_ttl,
    is_muted,
    set_mute,
    set_takeover,
    unmute_queue,
)
from app.ws import manager

router = APIRouter(tags=["incidents"])

_NOTIFY = {"type": "incidents_updated"}


@router.get("/")
async def list_incidents(username: str = Depends(get_current_user)) -> dict:
    all_incidents = await get_all_incidents()
    config = get_config()

    mute_info: dict[str, int] = {}
    subscribers: dict[str, list[str]] = {}
    takeovers: dict[str, dict] = {}
    oncall_info: dict[str, dict] = {}

    flush_after: dict[str, int] = {q.name: q.flush_after_minutes for q in config.queues}

    for queue_name in all_incidents:
        mute_info[queue_name] = await get_mute_ttl(queue_name)
        oncall = await get_oncall(queue_name)
        if oncall is not None:
            subscribers[queue_name] = oncall
            ttl = await get_oncall_ttl(queue_name)
            oncall_info[queue_name] = {"usernames": oncall, "ttl_seconds": ttl}
        else:
            subscribers[queue_name] = [u.username for u in config.users if queue_name in u.queues]
        takeover = await get_takeover(queue_name)
        if takeover:
            takeovers[queue_name] = {
                "username": takeover.username,
                "expires_at": takeover.expires_at.isoformat(),
                "ttl_seconds": await get_takeover_ttl(queue_name),
            }

    return {
        "incidents": {q: [i.model_dump() for i in incidents] for q, incidents in all_incidents.items()},
        "mutes": mute_info,
        "subscribers": subscribers,
        "takeovers": takeovers,
        "oncall": oncall_info,
        "flush_after": flush_after,
        "next_scheduler_run": get_next_run_time(),
    }


@router.post("/acknowledge")
async def acknowledge(request: AcknowledgeRequest, username: str = Depends(get_current_user)) -> dict:
    incident = await acknowledge_incident(request.incident_id, request.queue)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    await log_history(
        queue=request.queue,
        action="acknowledged",
        incidents=[incident],
        notifications=[],
        takeover_user=None,
        triggered_by=username,
    )
    await manager.broadcast(_NOTIFY)
    return {"ok": True}


@router.post("/flush")
async def flush(request: FlushRequest, username: str = Depends(get_current_user)) -> dict:
    """Acknowledge all — remove all incidents from queue without sending notifications."""
    incidents = await flush_queue(request.queue)
    if incidents:
        await log_history(
            queue=request.queue,
            action="flushed",
            incidents=incidents,
            notifications=[],
            takeover_user=None,
            triggered_by=username,
        )
    await manager.broadcast(_NOTIFY)
    return {"ok": True, "flushed": len(incidents)}


@router.post("/send")
async def send(request: FlushRequest, username: str = Depends(get_current_user)) -> dict:
    """Send all incidents to notification backends, then remove from queue."""
    if await is_muted(request.queue):
        raise HTTPException(status_code=400, detail="Queue is muted — unmute first or wait for expiry")
    incidents = await flush_queue(request.queue)
    await dispatch(incidents, request.queue, action="sent", triggered_by=username)
    await manager.broadcast(_NOTIFY)
    return {"ok": True, "sent": len(incidents)}


@router.post("/mute")
async def mute(request: MuteRequest, username: str = Depends(get_current_user)) -> dict:
    await set_mute(request.queue, request.duration_minutes)
    await manager.broadcast(_NOTIFY)
    return {"ok": True, "muted_minutes": request.duration_minutes}


@router.post("/unmute")
async def unmute(request: FlushRequest, username: str = Depends(get_current_user)) -> dict:
    await unmute_queue(request.queue)
    await manager.broadcast(_NOTIFY)
    return {"ok": True}


@router.post("/takeover")
async def takeover(request: TakeoverRequest, username: str = Depends(get_current_user)) -> dict:
    """Temporarily take over a queue — notifications go only to the calling user."""
    result = await set_takeover(request.queue, username, request.duration_minutes)
    await manager.broadcast(_NOTIFY)
    return {"ok": True, "username": result.username, "expires_at": result.expires_at.isoformat()}


@router.post("/takeover/clear")
async def takeover_clear(request: FlushRequest, username: str = Depends(get_current_user)) -> dict:
    await clear_takeover(request.queue)
    await manager.broadcast(_NOTIFY)
    return {"ok": True}
