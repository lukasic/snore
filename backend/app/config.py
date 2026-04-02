from pydantic import BaseModel
from typing import Optional
import yaml

_CONFIG_PATH = "config.yaml"


class NotificationConfig(BaseModel):
    type: str  # slack_webhook, pagerduty, pushover
    # slack_webhook
    url: Optional[str] = None
    # pagerduty
    integration_key: Optional[str] = None
    # pushover
    user_key: Optional[str] = None
    api_token: Optional[str] = None


class RoutingRule(BaseModel):
    match_host: Optional[str] = None
    match_service: Optional[str] = None
    match_source: Optional[str] = None


class QueueConfig(BaseModel):
    name: str
    flush_after_minutes: int = 5
    routing_rules: list[RoutingRule] = []


class UserConfig(BaseModel):
    username: str
    password_hash: str
    queues: list[str] = []
    notifications: list[NotificationConfig] = []


class GlobalNotifications(BaseModel):
    slack_webhook: Optional[str] = None


class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379"


class AppConfig(BaseModel):
    secret_key: str
    redis: RedisConfig = RedisConfig()
    users: list[UserConfig] = []
    queues: list[QueueConfig] = []
    notifications: GlobalNotifications = GlobalNotifications()


_config: Optional[AppConfig] = None


def load_config(path: str = _CONFIG_PATH) -> AppConfig:
    global _config
    with open(path) as f:
        data = yaml.safe_load(f)
    _config = AppConfig(**data)
    return _config


def get_config() -> AppConfig:
    if _config is None:
        raise RuntimeError("Config not loaded")
    return _config


def get_user(username: str) -> Optional[UserConfig]:
    return next((u for u in get_config().users if u.username == username), None)


def get_queue_config(name: str) -> Optional[QueueConfig]:
    return next((q for q in get_config().queues if q.name == name), None)


def resolve_queue(source: str, host: Optional[str], service: Optional[str]) -> str:
    """Determine which queue an incident belongs to based on routing rules."""
    import fnmatch

    for queue in get_config().queues:
        for rule in queue.routing_rules:
            source_match = bool(rule.match_source and fnmatch.fnmatch(source, rule.match_source))
            host_match = bool(rule.match_host and host and fnmatch.fnmatch(host, rule.match_host))
            service_match = bool(rule.match_service and service and fnmatch.fnmatch(service, rule.match_service))

            if rule.match_source and not source_match:
                continue
            if rule.match_host and not host_match:
                continue
            if rule.match_service and not service_match:
                continue
            if source_match or host_match or service_match:
                return queue.name

    return "general"
