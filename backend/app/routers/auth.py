import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import get_config, get_user, user_has_notifications
from app.models import LoginRequest, SsoConfigResponse, SsoLoginRequest, TokenResponse
from app.oidc import OidcError, verify_id_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])
security = HTTPBearer()

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def create_token(username: str) -> str:
    config = get_config()
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, config.secret_key, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    config = get_config()
    try:
        payload = jwt.decode(credentials.credentials, config.secret_key, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    user = get_user(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not bcrypt.checkpw(request.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_token(request.username))


@router.get("/me")
async def me(username: str = Depends(get_current_user)) -> dict:
    user = get_user(username)
    if not user:
        return {"username": username, "queues": [], "has_notifications": False}
    return {
        "username": user.username,
        "queues": user.queues,
        "has_notifications": user_has_notifications(username),
    }


@router.get("/sso/config", response_model=SsoConfigResponse)
async def sso_config() -> SsoConfigResponse:
    config = get_config()
    if not config.oidc.enabled:
        return SsoConfigResponse(enabled=False)
    return SsoConfigResponse(
        enabled=True,
        issuer=config.oidc.issuer,
        client_id=config.oidc.client_id,
    )


@router.post("/sso/login", response_model=TokenResponse)
async def sso_login(request: SsoLoginRequest) -> TokenResponse:
    config = get_config()
    try:
        payload = await verify_id_token(request.id_token, config.oidc)
    except OidcError as exc:
        logger.warning("SSO login rejected: %s", exc)
        raise HTTPException(status_code=401, detail=str(exc))

    username = payload.get(config.oidc.username_claim)
    if not username:
        raise HTTPException(
            status_code=401,
            detail=f"id_token missing claim '{config.oidc.username_claim}'",
        )
    return TokenResponse(access_token=create_token(username))
