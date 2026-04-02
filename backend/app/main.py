import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_config
from app.redis_client import close_redis
from app.routers import auth, history, incidents, version, webhook
from app.routers import queues
from app.routers.auth import ALGORITHM
from app.scheduler import start_scheduler, stop_scheduler
from app.ws import manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
    load_config(os.environ.get("SNORE_CONFIG", "config.yaml"))
    start_scheduler()
    yield
    await close_redis()
    stop_scheduler()


app = FastAPI(title="SNORE — Service Notification Override & Response Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(version.router, prefix="/api/version")
app.include_router(auth.router, prefix="/api/auth")
app.include_router(incidents.router, prefix="/api/incidents")
app.include_router(history.router, prefix="/api/history")
app.include_router(webhook.router, prefix="/api/webhook")
app.include_router(queues.router, prefix="/api/queues")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)) -> None:
    from jose import JWTError, jwt
    from app.config import get_config

    try:
        config = get_config()
        payload = jwt.decode(token, config.secret_key, algorithms=[ALGORITHM])
        if not payload.get("sub"):
            await websocket.close(code=4001)
            return
    except JWTError:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client may send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
