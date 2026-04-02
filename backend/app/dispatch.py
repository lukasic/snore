"""Dispatch notifications to all relevant notifiers for a queue."""
import logging
from typing import Literal

from app.config import get_config
from app.history import HistoryNotification, log_history
from app.models import Incident
from app.notifiers.base import BaseNotifier
from app.notifiers.slack import SlackNotifier
from app.notifiers.pagerduty import PagerDutyNotifier
from app.notifiers.pushover import PushoverNotifier

logger = logging.getLogger(__name__)


def _notifier_type(notifier: BaseNotifier) -> str:
    if isinstance(notifier, SlackNotifier):
        return "slack_webhook"
    if isinstance(notifier, PagerDutyNotifier):
        return "pagerduty"
    if isinstance(notifier, PushoverNotifier):
        return "pushover"
    return "unknown"


def _notifiers_for_user(username: str) -> list[tuple[BaseNotifier, str]]:
    """Returns list of (notifier, username) pairs for the given user."""
    config = get_config()
    result: list[tuple[BaseNotifier, str]] = []
    user = next((u for u in config.users if u.username == username), None)
    if not user:
        return result
    for notif in user.notifications:
        if notif.type == "pushover" and notif.user_key and notif.api_token:
            result.append((PushoverNotifier(notif.user_key, notif.api_token), username))
        elif notif.type == "pagerduty" and notif.integration_key:
            result.append((PagerDutyNotifier(notif.integration_key), username))
        elif notif.type == "slack_webhook" and notif.url:
            result.append((SlackNotifier(notif.url), username))
    return result


async def _build_notifiers(queue_name: str) -> tuple[list[tuple[BaseNotifier, str]], str | None]:
    """Returns ([(notifier, username)], takeover_user | None)."""
    from app.store import get_oncall, get_takeover
    config = get_config()
    pairs: list[tuple[BaseNotifier, str]] = []

    takeover = await get_takeover(queue_name)
    if takeover:
        logger.info("Queue '%s' has active takeover by '%s'", queue_name, takeover.username)
        return _notifiers_for_user(takeover.username), takeover.username

    # Global Slack webhook — attributed to "global"
    if config.notifications.slack_webhook:
        pairs.append((SlackNotifier(config.notifications.slack_webhook), "global"))

    oncall = await get_oncall(queue_name)
    if oncall is not None:
        logger.info("Queue '%s' using dynamic on-call list: %s", queue_name, oncall)
        for uname in oncall:
            pairs.extend(_notifiers_for_user(uname))
    else:
        for user in config.users:
            if queue_name not in user.queues:
                continue
            pairs.extend(_notifiers_for_user(user.username))

    return pairs, None


async def dispatch(
    incidents: list[Incident],
    queue_name: str,
    action: Literal["sent", "auto_sent"] = "sent",
    triggered_by: str | None = None,
) -> None:
    if not incidents:
        return

    pairs, takeover_user = await _build_notifiers(queue_name)

    sent_notifications: list[HistoryNotification] = []
    for notifier, username in pairs:
        try:
            await notifier.send(incidents, queue_name)
            sent_notifications.append(
                HistoryNotification(username=username, notifier_type=_notifier_type(notifier))
            )
        except Exception:
            logger.exception("Notifier %s failed for queue %s", type(notifier).__name__, queue_name)

    await log_history(
        queue=queue_name,
        action=action,
        incidents=incidents,
        notifications=sent_notifications,
        takeover_user=takeover_user,
        triggered_by=triggered_by,
    )
