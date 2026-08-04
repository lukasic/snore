"""Tests for OIDC/SSO login and the notifications-required checks on takeover/on-call."""
import os
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.config import load_config, user_has_notifications
from app.main import app
from app.oidc import OidcError
from app.routers.auth import get_current_user


@pytest.fixture(autouse=True)
def load_test_config():
    config_path = os.path.join(os.path.dirname(__file__), "test_config.yaml")
    load_config(config_path)


@contextmanager
def _mock_auth(username: str):
    app.dependency_overrides[get_current_user] = lambda: username
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_user_has_notifications_true():
    assert user_has_notifications("testuser") is True


def test_user_has_notifications_false_when_empty():
    assert user_has_notifications("nonotify") is False


def test_user_has_notifications_false_when_unknown():
    assert user_has_notifications("ghost") is False


@pytest.mark.asyncio
async def test_sso_config_disabled_by_default():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/auth/sso/config")
    assert resp.status_code == 200
    assert resp.json() == {"enabled": False, "issuer": None, "client_id": None}


@pytest.mark.asyncio
async def test_sso_login_maps_known_user():
    with patch("app.routers.auth.verify_id_token", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"preferred_username": "testuser"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/auth/sso/login", json={"id_token": "fake"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_sso_login_unknown_user_still_issues_token():
    """A Keycloak user with no matching config.yaml entry can still log in."""
    with patch("app.routers.auth.verify_id_token", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"preferred_username": "someone-else"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/auth/sso/login", json={"id_token": "fake"})
            assert resp.status_code == 200
            token = resp.json()["access_token"]

            me_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json() == {"username": "someone-else", "queues": [], "has_notifications": False}


@pytest.mark.asyncio
async def test_sso_login_invalid_token_rejected():
    with patch("app.routers.auth.verify_id_token", new_callable=AsyncMock) as mock_verify:
        mock_verify.side_effect = OidcError("bad signature")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/auth/sso/login", json={"id_token": "fake"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_reports_has_notifications_for_configured_user():
    with _mock_auth("testuser"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["has_notifications"] is True


@pytest.mark.asyncio
async def test_takeover_rejected_without_notifications():
    with _mock_auth("nonotify"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/incidents/takeover", json={"queue": "general", "duration_minutes": 60})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_takeover_allowed_with_notifications():
    with _mock_auth("testuser"), \
         patch("app.routers.incidents.set_takeover", new_callable=AsyncMock) as mock_set, \
         patch("app.routers.incidents.manager") as mock_ws:
        from app.models import Takeover
        from datetime import datetime, timezone

        mock_set.return_value = Takeover(username="testuser", expires_at=datetime.now(timezone.utc))
        mock_ws.broadcast = AsyncMock()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/incidents/takeover", json={"queue": "general", "duration_minutes": 60})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_set_oncall_rejected_without_notifications():
    with _mock_auth("nonotify"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put("/api/queues/general/oncall", json={"usernames": ["nonotify"]})
    assert resp.status_code == 403
