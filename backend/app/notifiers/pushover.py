from typing import Optional

import httpx
from app.models import Incident
from app.notifiers.base import BaseNotifier, format_incidents_text

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"

# Pushover emergency priority (2) defaults, used when not overridden in config.
EMERGENCY_RETRY_SECONDS = 60
EMERGENCY_EXPIRE_SECONDS = 1800


class PushoverNotifier(BaseNotifier):
    def __init__(
        self,
        user_key: str,
        api_token: str,
        priority: int = 1,
        sound: str = "pushover",
        retry: Optional[int] = None,
        expire: Optional[int] = None,
    ) -> None:
        self.user_key = user_key
        self.api_token = api_token
        self.priority = priority
        self.sound = sound
        self.retry = retry
        self.expire = expire

    async def send(self, incidents: list[Incident], queue: str) -> None:
        message = format_incidents_text(incidents, queue)
        payload = {
            "token": self.api_token,
            "user": self.user_key,
            "title": f"SNORE: {len(incidents)} incident(s) in '{queue}'",
            "message": message[:1024],  # Pushover limit
            "priority": self.priority,
            "sound": self.sound,
        }
        if self.priority == 2:
            # Emergency priority requires retry/expire per Pushover API.
            payload["retry"] = self.retry or EMERGENCY_RETRY_SECONDS
            payload["expire"] = self.expire or EMERGENCY_EXPIRE_SECONDS
        async with httpx.AsyncClient() as client:
            response = await client.post(PUSHOVER_API_URL, data=payload)
            response.raise_for_status()
