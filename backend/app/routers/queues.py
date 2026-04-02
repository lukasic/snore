"""Queue management — dynamic on-call assignments."""
from fastapi import APIRouter, Depends, HTTPException

from app.config import get_config
from app.models import OncallRequest
from app.routers.auth import get_current_user
from app.store import clear_oncall, get_oncall, get_oncall_ttl, set_oncall
from app.ws import manager

router = APIRouter(tags=["queues"])

_NOTIFY = {"type": "incidents_updated"}


@router.put("/{queue}/oncall")
async def set_queue_oncall(
    queue: str,
    request: OncallRequest,
    username: str = Depends(get_current_user),
) -> dict:
    config = get_config()
    if not any(q.name == queue for q in config.queues):
        raise HTTPException(status_code=404, detail=f"Queue '{queue}' not found")
    known_users = {u.username for u in config.users}
    unknown = [u for u in request.usernames if u not in known_users]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown users: {unknown}")
    await set_oncall(queue, request.usernames, request.duration_minutes)
    await manager.broadcast(_NOTIFY)
    return {"ok": True, "queue": queue, "usernames": request.usernames}


@router.get("/{queue}/oncall")
async def get_queue_oncall(
    queue: str,
    username: str = Depends(get_current_user),
) -> dict:
    config = get_config()
    usernames = await get_oncall(queue)
    if usernames is None:
        config_users = [u.username for u in config.users if queue in u.queues]
        return {"queue": queue, "usernames": config_users, "dynamic": False, "ttl_seconds": None}
    ttl = await get_oncall_ttl(queue)
    return {"queue": queue, "usernames": usernames, "dynamic": True, "ttl_seconds": ttl}


@router.delete("/{queue}/oncall")
async def clear_queue_oncall(
    queue: str,
    username: str = Depends(get_current_user),
) -> dict:
    await clear_oncall(queue)
    await manager.broadcast(_NOTIFY)
    return {"ok": True}
