#!/usr/bin/env python3
"""Icinga2 notification script — forwards PROBLEM alerts to SNORE webhook.

Required environment variables (set via NotificationCommand env {}):
  SNORE_URL     Base URL of SNORE, e.g. https://snore.example.com
  SNORE_SOURCE  Webhook source name (default: icinga2). Use a qualified
                name like icinga2.prod to distinguish multiple instances.

Icinga2 passes the remaining variables automatically via env {} in the
NotificationCommand definition — see snore.conf.
"""
import json
import os
import sys
import urllib.error
import urllib.request


def main() -> None:
    snore_url = os.environ.get("SNORE_URL", "").rstrip("/")
    if not snore_url:
        print("SNORE_URL is not set", file=sys.stderr)
        sys.exit(1)

    notif_type = os.environ.get("ICINGA_NOTIFICATIONTYPE", "PROBLEM")
    if notif_type not in ("PROBLEM", "CUSTOM"):
        # Skip RECOVERY, ACKNOWLEDGEMENT, DOWNTIMESTART, DOWNTIMEEND, etc.
        sys.exit(0)

    source = os.environ.get("SNORE_SOURCE", "icinga2")
    is_service = bool(os.environ.get("ICINGA_SERVICEDESC"))

    payload = {
        "host":    os.environ.get("ICINGA_HOSTNAME", ""),
        "service": os.environ.get("ICINGA_SERVICEDESC", "") if is_service else "",
        "state":   os.environ.get("ICINGA_SERVICESTATE" if is_service else "ICINGA_HOSTSTATE", "UNKNOWN"),
        "output":  os.environ.get("ICINGA_SERVICEOUTPUT" if is_service else "ICINGA_HOSTOUTPUT", ""),
    }

    url = f"{snore_url}/api/webhook/{source}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"SNORE HTTP error {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"SNORE error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
