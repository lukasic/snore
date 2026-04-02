import httpx
from app.models import Incident
from app.notifiers.base import BaseNotifier, format_incidents_text

PAGERDUTY_EVENTS_URL = "https://events.pagerduty.com/v2/enqueue"


def _build_summary(incidents: list[Incident]) -> str:
    """Build a compact human-readable summary line.

    Format: "<source>: check <host1> <service1>, <host2> <service2>, ..."
    Mirrors the format used in other internal monitoring tooling.
    """
    sources = sorted({inc.source for inc in incidents})
    monitoring_source = ", ".join(sources)

    parts: list[str] = []
    for inc in incidents:
        host_short = inc.host.split(".")[0] if inc.host else None
        svc_clean = (
            inc.service.replace("check_", "").replace("_", " ")
            if inc.service
            else None
        )
        if host_short and svc_clean:
            parts.append(f"{host_short} {svc_clean}")
        elif host_short:
            parts.append(host_short)
        elif svc_clean:
            parts.append(svc_clean)
        else:
            parts.append(inc.title)

    return f"{monitoring_source}: check {', '.join(parts)}"


class PagerDutyNotifier(BaseNotifier):
    def __init__(self, integration_key: str) -> None:
        self.integration_key = integration_key

    async def send(self, incidents: list[Incident], queue: str) -> None:
        summary = _build_summary(incidents)
        details = format_incidents_text(incidents, queue)
        payload = {
            "routing_key": self.integration_key,
            "event_action": "trigger",
            "payload": {
                "summary": summary,
                "severity": "critical",
                "source": "snore",
                "custom_details": {"incidents": details},
            },
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(PAGERDUTY_EVENTS_URL, json=payload)
            response.raise_for_status()
