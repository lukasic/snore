"""Webhook receiver — normalizes payloads from various monitoring sources."""
import json
import logging
from typing import Any

from fastapi import APIRouter, Query, Request

logger = logging.getLogger(__name__)

from app.config import resolve_queue
from app.models import IncidentCreate
from app.store import add_incident
from app.ws import manager

router = APIRouter(tags=["webhook"])


def _normalize_icinga2(payload: dict[str, Any]) -> dict[str, Any]:
    host = payload.get("host", payload.get("hostname", ""))
    service = payload.get("service", payload.get("servicedesc", ""))
    state = payload.get("state", payload.get("servicestate", "UNKNOWN"))
    output = payload.get("output", payload.get("serviceoutput", ""))
    title = f"{state}: {host}/{service}" if service else f"{state}: {host}"
    return {"title": title, "description": output, "host": host, "service": service}


def _normalize_uptime_kuma(payload: dict[str, Any]) -> dict[str, Any]:
    monitor = payload.get("monitor", {})
    heartbeat = payload.get("heartbeat", {})
    name = monitor.get("name", "unknown")
    msg = heartbeat.get("msg", "")
    url = monitor.get("url", "")
    title = f"DOWN: {name}"
    description = msg or f"Monitor down: {url}"
    return {"title": title, "description": description, "host": url, "service": name}


def _normalize_nodeping(payload: dict[str, Any]) -> dict[str, Any]:
    # Expected NodePing webhook template (configure in NodePing notification settings):
    # {
    #   "label":   "{label}",
    #   "event":   "{event}",
    #   "type":    "{t}",
    #   "target":  "{tg}",
    #   "success": "{su}",
    #   "message": "{m}",
    #   "checkid": "{_id}"
    # }
    label = payload.get("label") or payload.get("checkid", "unknown")
    event = str(payload.get("event", "down")).lower()
    check_type = payload.get("type", "")
    target = payload.get("target") or None
    message = payload.get("message", "")
    success = str(payload.get("success", "false")).lower() in ("true", "1")

    state = "UP" if success or event == "up" else "DOWN"
    type_suffix = f" [{check_type}]" if check_type else ""
    title = f"{state}: {label}{type_suffix}"

    return {
        "title": title,
        "description": message,
        "host": target or label,
        "service": check_type or None,
    }


def _normalize_generic(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": payload.get("title", "Incident"),
        "description": payload.get("description", ""),
        "host": payload.get("host"),
        "service": payload.get("service"),
    }


# Maps source prefix → normalizer function.
# A source matches if it equals the prefix exactly or starts with "<prefix>.".
# Example: "icinga2.master-cz" → _normalize_icinga2
_NORMALIZER_PREFIXES: list[tuple[str, Any]] = [
    ("icinga2", _normalize_icinga2),
    ("uptime_kuma", _normalize_uptime_kuma),
    ("nodeping", _normalize_nodeping),
    ("manual", _normalize_generic),
]


def _get_normalizer(source: str) -> Any:
    for prefix, fn in _NORMALIZER_PREFIXES:
        if source == prefix or source.startswith(prefix + "."):
            return fn
    return _normalize_generic


async def _parse_payload(request: Request) -> dict[str, Any]:
    """Accept JSON body, form-urlencoded body, or URL query params."""
    body = await request.body()
    logger.debug("webhook raw body (%d bytes): %r", len(body), body[:512])
    logger.debug("webhook query_params: %s", dict(request.query_params))
    logger.debug("webhook headers: %s", dict(request.headers))
    if body:
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass
        try:
            from urllib.parse import parse_qsl
            parsed = dict(parse_qsl(body.decode()))
            if parsed:
                return parsed
        except Exception:
            pass
    return dict(request.query_params)


@router.api_route("/{source}", methods=["GET", "POST"])
async def receive_webhook(
    source: str,
    request: Request,
    queue: str | None = Query(default=None, description="Override target queue"),
) -> dict:
    payload = await _parse_payload(request)
    normalizer = _get_normalizer(source)
    normalized = normalizer(payload)

    target_queue = queue or resolve_queue(source, normalized.get("host"), normalized.get("service"))

    incident_data = IncidentCreate(
        source=source,
        title=normalized["title"],
        description=normalized.get("description", ""),
        host=normalized.get("host"),
        service=normalized.get("service"),
        queue=target_queue,
        raw_payload=payload,
    )

    incident = await add_incident(incident_data)
    await manager.broadcast({"type": "incidents_updated"})
    return {"ok": True, "incident_id": incident.id, "queue": incident.queue}
