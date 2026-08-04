from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.config import NotificationConfig
from app.models import Incident
from app.notifiers.pushover import PushoverNotifier


@pytest.fixture
def incident() -> Incident:
    return Incident(
        id="1",
        source="icinga2",
        title="disk full",
        description="disk at 95%",
        queue="general",
        host="host1",
        service="disk",
        received_at=datetime.now(timezone.utc),
        raw_payload={},
    )


def test_notification_config_pushover_defaults():
    notif = NotificationConfig(type="pushover", user_key="u", api_token="t")
    assert notif.priority == 1
    assert notif.sound == "pushover"


def test_notification_config_pushover_override():
    notif = NotificationConfig(
        type="pushover", user_key="u", api_token="t", priority=2, sound="siren", retry=30, expire=3600
    )
    assert notif.priority == 2
    assert notif.sound == "siren"
    assert notif.retry == 30
    assert notif.expire == 3600


@pytest.mark.asyncio
async def test_pushover_notifier_sends_default_priority_and_sound(incident: Incident):
    notifier = PushoverNotifier("user-key", "api-token")

    with patch("app.notifiers.pushover.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value.raise_for_status = lambda: None

        await notifier.send([incident], "general")

        _, kwargs = mock_client.post.call_args
        payload = kwargs["data"]
        assert payload["priority"] == 1
        assert payload["sound"] == "pushover"
        assert "retry" not in payload
        assert "expire" not in payload


@pytest.mark.asyncio
async def test_pushover_notifier_sends_custom_priority_and_sound(incident: Incident):
    notifier = PushoverNotifier("user-key", "api-token", priority=2, sound="siren")

    with patch("app.notifiers.pushover.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value.raise_for_status = lambda: None

        await notifier.send([incident], "general")

        _, kwargs = mock_client.post.call_args
        payload = kwargs["data"]
        assert payload["priority"] == 2
        assert payload["sound"] == "siren"
        assert payload["retry"] == 60
        assert payload["expire"] == 1800


@pytest.mark.asyncio
async def test_pushover_notifier_emergency_priority_custom_retry_expire(incident: Incident):
    notifier = PushoverNotifier("user-key", "api-token", priority=2, retry=30, expire=3600)

    with patch("app.notifiers.pushover.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value.raise_for_status = lambda: None

        await notifier.send([incident], "general")

        _, kwargs = mock_client.post.call_args
        payload = kwargs["data"]
        assert payload["retry"] == 30
        assert payload["expire"] == 3600


@pytest.mark.asyncio
async def test_pushover_notifier_non_emergency_ignores_retry_expire(incident: Incident):
    notifier = PushoverNotifier("user-key", "api-token", priority=1, retry=30, expire=3600)

    with patch("app.notifiers.pushover.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value.raise_for_status = lambda: None

        await notifier.send([incident], "general")

        _, kwargs = mock_client.post.call_args
        payload = kwargs["data"]
        assert "retry" not in payload
        assert "expire" not in payload
