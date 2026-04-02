import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.config import load_config
import os


@pytest.fixture(autouse=True)
def load_test_config():
    config_path = os.path.join(os.path.dirname(__file__), "test_config.yaml")
    load_config(config_path)


@pytest.mark.asyncio
async def test_webhook_generic():
    with patch("app.routers.webhook.add_incident", new_callable=AsyncMock) as mock_add:
        from app.models import Incident
        from datetime import datetime

        mock_add.return_value = Incident(
            id="test-id",
            source="manual",
            title="Test incident",
            description="Something broke",
            queue="general",
            received_at=datetime.utcnow(),
            raw_payload={},
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/webhook/manual",
                json={"title": "Test incident", "description": "Something broke"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["queue"] == "general"


@pytest.mark.asyncio
async def test_webhook_icinga2_normalization():
    with patch("app.routers.webhook.add_incident", new_callable=AsyncMock) as mock_add:
        from app.models import Incident
        from datetime import datetime

        mock_add.return_value = Incident(
            id="test-id",
            source="icinga2",
            title="CRITICAL: web-01/HTTP",
            description="Socket timeout",
            queue="general",
            received_at=datetime.utcnow(),
            raw_payload={},
        )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/webhook/icinga2",
                json={
                    "host": "web-01",
                    "service": "HTTP",
                    "state": "CRITICAL",
                    "output": "Socket timeout",
                },
            )

        assert response.status_code == 200
        call_args = mock_add.call_args[0][0]
        assert call_args.title == "CRITICAL: web-01/HTTP"
        assert call_args.host == "web-01"
        assert call_args.service == "HTTP"
