import httpx
from app.models import Incident
from app.notifiers.base import BaseNotifier, format_incidents_text

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"


class PushoverNotifier(BaseNotifier):
    def __init__(self, user_key: str, api_token: str) -> None:
        self.user_key = user_key
        self.api_token = api_token

    async def send(self, incidents: list[Incident], queue: str) -> None:
        message = format_incidents_text(incidents, queue)
        payload = {
            "token": self.api_token,
            "user": self.user_key,
            "title": f"SNORE: {len(incidents)} incident(s) in '{queue}'",
            "message": message[:1024],  # Pushover limit
            "priority": 1,
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(PUSHOVER_API_URL, data=payload)
            response.raise_for_status()
