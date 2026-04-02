from pydantic import BaseModel
from datetime import datetime
from typing import Any


class Incident(BaseModel):
    id: str
    source: str
    title: str
    description: str
    queue: str
    host: str | None = None
    service: str | None = None
    received_at: datetime
    raw_payload: dict[str, Any]


class IncidentCreate(BaseModel):
    source: str
    title: str
    description: str
    queue: str = "general"
    host: str | None = None
    service: str | None = None
    raw_payload: dict[str, Any] = {}


class FlushRequest(BaseModel):
    queue: str


class MuteRequest(BaseModel):
    queue: str
    duration_minutes: int = 60


class TakeoverRequest(BaseModel):
    queue: str
    duration_minutes: int = 60


class Takeover(BaseModel):
    username: str
    expires_at: datetime


class AcknowledgeRequest(BaseModel):
    incident_id: str
    queue: str


class OncallRequest(BaseModel):
    usernames: list[str]
    duration_minutes: int | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
