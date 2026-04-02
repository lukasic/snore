from fastapi import APIRouter, Depends, Query
from app.history import get_history
from app.routers.auth import get_current_user

router = APIRouter(tags=["history"])


@router.get("/")
async def list_history(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    username: str = Depends(get_current_user),
) -> dict:
    entries = await get_history(limit=limit, offset=offset)
    return {"entries": [e.model_dump() for e in entries]}
