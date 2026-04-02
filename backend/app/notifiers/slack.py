import httpx
from app.models import Incident
from app.notifiers.base import BaseNotifier, format_incidents_text


class SlackNotifier(BaseNotifier):
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    async def send(self, incidents: list[Incident], queue: str) -> None:
        text = format_incidents_text(incidents, queue)
        async with httpx.AsyncClient() as client:
            response = await client.post(self.webhook_url, json={"text": text})
            response.raise_for_status()
