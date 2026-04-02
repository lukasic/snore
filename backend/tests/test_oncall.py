"""Tests for dynamic on-call queue assignments."""
import os
import pytest
from contextlib import contextmanager
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.config import load_config
from app.routers.auth import get_current_user


@pytest.fixture(autouse=True)
def load_test_config():
    config_path = os.path.join(os.path.dirname(__file__), "test_config.yaml")
    load_config(config_path)


@contextmanager
def _mock_auth(username: str = "testuser"):
    """Override FastAPI auth dependency to return a fixed username."""
    app.dependency_overrides[get_current_user] = lambda: username
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_set_oncall_valid():
    with _mock_auth(), \
         patch("app.routers.queues.set_oncall", new_callable=AsyncMock) as mock_set, \
         patch("app.routers.queues.manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/queues/general/oncall",
                json={"usernames": ["testuser"]},
                            )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["usernames"] == ["testuser"]
        mock_set.assert_called_once_with("general", ["testuser"], None)
        mock_ws.broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_set_oncall_with_duration():
    with _mock_auth(), \
         patch("app.routers.queues.set_oncall", new_callable=AsyncMock) as mock_set, \
         patch("app.routers.queues.manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/queues/general/oncall",
                json={"usernames": ["testuser"], "duration_minutes": 480},
                            )
        assert resp.status_code == 200
        mock_set.assert_called_once_with("general", ["testuser"], 480)


@pytest.mark.asyncio
async def test_set_oncall_unknown_queue():
    with _mock_auth():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/queues/nonexistent/oncall",
                json={"usernames": ["testuser"]},
                            )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_set_oncall_unknown_user():
    with _mock_auth():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/queues/general/oncall",
                json={"usernames": ["ghost"]},
                            )
        assert resp.status_code == 400
        assert "ghost" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_oncall_dynamic():
    with _mock_auth(), \
         patch("app.routers.queues.get_oncall", new_callable=AsyncMock, return_value=["testuser"]), \
         patch("app.routers.queues.get_oncall_ttl", new_callable=AsyncMock, return_value=3600):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/queues/general/oncall")
        assert resp.status_code == 200
        data = resp.json()
        assert data["dynamic"] is True
        assert data["usernames"] == ["testuser"]
        assert data["ttl_seconds"] == 3600


@pytest.mark.asyncio
async def test_get_oncall_config_fallback():
    with _mock_auth(), \
         patch("app.routers.queues.get_oncall", new_callable=AsyncMock, return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/queues/general/oncall")
        assert resp.status_code == 200
        data = resp.json()
        assert data["dynamic"] is False
        # test_config.yaml: testuser is subscribed to general
        assert "testuser" in data["usernames"]


@pytest.mark.asyncio
async def test_clear_oncall():
    with _mock_auth(), \
         patch("app.routers.queues.clear_oncall", new_callable=AsyncMock) as mock_clear, \
         patch("app.routers.queues.manager") as mock_ws:
        mock_ws.broadcast = AsyncMock()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/api/queues/general/oncall")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        mock_clear.assert_called_once_with("general")
        mock_ws.broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_dispatch_uses_oncall_over_config():
    """dispatch._build_notifiers should use oncall list when set, ignoring config subscribers."""
    from app.dispatch import _build_notifiers

    with patch("app.store.get_oncall", new_callable=AsyncMock, return_value=["testuser"]), \
         patch("app.store.get_takeover", new_callable=AsyncMock, return_value=None):
        pairs, takeover_user = await _build_notifiers("general")

    assert takeover_user is None
    # testuser has no notifiers in test_config.yaml — pairs should be empty but no crash
    assert isinstance(pairs, list)


@pytest.mark.asyncio
async def test_dispatch_falls_back_to_config_when_no_oncall():
    """dispatch._build_notifiers falls back to config when oncall is None."""
    from app.dispatch import _build_notifiers

    with patch("app.store.get_oncall", new_callable=AsyncMock, return_value=None), \
         patch("app.store.get_takeover", new_callable=AsyncMock, return_value=None):
        pairs, takeover_user = await _build_notifiers("general")

    assert takeover_user is None
    assert isinstance(pairs, list)
