from abc import ABC, abstractmethod
from app.models import Incident


class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, incidents: list[Incident], queue: str) -> None:
        pass


def format_incidents_text(incidents: list[Incident], queue: str) -> str:
    lines = [f"SNORE alert — queue: {queue} ({len(incidents)} incident(s))\n"]
    for inc in incidents:
        lines.append(f"• [{inc.source.upper()}] {inc.title}")
        if inc.description:
            lines.append(f"  {inc.description}")
        if inc.host:
            lines.append(f"  Host: {inc.host}")
        lines.append(f"  Received: {inc.received_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")
    return "\n".join(lines)
