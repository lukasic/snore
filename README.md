# 😴 S.N.O.R.E.

**Service Notification Override & Response Engine**

> A smart alert aggregation layer for small sysadmin teams who share on-call duties.
> SNORE sits between your monitoring systems and notification backends — collecting alerts into queues, letting you acknowledge or suppress them via a dashboard, and dispatching aggregated notifications if they go unattended.

---

## 💡 Why SNORE exists

**🔁 On-call handover without friction.**
When one admin holds the overnight shift and another arrives early, the early arrival can take over the queue immediately — one click, no config edits, no restarts.

**⛈️ Alert storms.**
When a switch goes down and 15 monitoring systems fire their own alerts, your phone should not ring 15 times. SNORE aggregates everything into one queue. A single **Mute** suppresses all further notifications for a defined period.

**🔔 Per-user notification preferences.**
One admin prefers a PagerDuty call at 3 AM, another wants Pushover, a third uses SMS. SNORE dispatches to each subscriber using their own configured backend.

**📅 API-driven on-call assignment.**
SNORE doesn't manage rotation schedules — that's your scheduling system's job (PagerDuty, OpsGenie, a shared calendar). SNORE just needs to know who is on-call *right now*, and exposes an API endpoint to set that at shift boundaries.

### What SNORE is not

- ❌ **Not a rotation planner** — monthly schedules and swap management belong in a dedicated tool
- ❌ **Not a monitoring system** — SNORE manages the notification flow; source resolution is your monitor's job

---

## ⚙️ How it works

```
[Icinga2 / Uptime Kuma / NodePing]
           │  webhook
           ▼
        🟡 SNORE queue
           │
    ┌──────┴──────┐
    │  Admin ACKs │  → done, no notification sent
    └──────┬──────┘
           │ nobody ACKed within flush_after_minutes
           ▼
  📣 Dispatch to Slack / PagerDuty / Pushover
```

---

## ✨ Features

| | Feature | Description |
|---|---|---|
| 🪝 | **Webhook ingestion** | Icinga2, Uptime Kuma, NodePing, manual; named instances (`icinga2.prod`, `icinga2.staging`) |
| 🗂️ | **Queue routing** | Route by source, host glob, or service glob |
| 📊 | **Real-time dashboard** | WebSocket-driven UI, all queues at a glance |
| ✅ | **Acknowledge / Flush / Send** | Full manual control over every queue |
| 🔇 | **Mute** | Suppress notifications for a defined period |
| 🔀 | **Takeover** | Redirect all queue notifications to yourself instantly |
| 👤 | **Dynamic on-call** | Override queue subscribers at runtime via API — no restart needed |
| 📜 | **History** | Audit log of all dispatched and flushed incidents |
| 📣 | **Notification backends** | Global Slack webhook, per-user PagerDuty and Pushover |
| 🐍 | **Python client** | [snore-client-python](https://github.com/lukasic/snore-client-python) for scripting and automation |

---

## 🏗️ Stack

| Layer | Technology |
|---|---|
| 🐍 Backend | Python 3.11+, FastAPI, APScheduler |
| ⚡ Frontend | Vue 3, Vite, TypeScript, Tailwind CSS, Pinia |
| 🗄️ Database | Redis |
| 🔐 Auth | JWT (HS256) |

---

## 🚀 Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis

### Setup

```bash
# Clone
git clone https://github.com/lukasic/snore.git
cd snore

# Install dependencies
make install

# Create config
cp backend/config.example.yaml backend/config.yaml
# Edit backend/config.yaml — set secret_key, Redis URL, users, queues

# Generate a bcrypt password hash
make hash PW=yourpassword
```

### Development

```bash
make dev-backend    # FastAPI on :8000
make dev-frontend   # Vite on :5173
```

Open `http://localhost:5173` and log in with credentials from your `config.yaml`.

### Production (Docker) 🐳

```bash
docker build -f backend/Dockerfile -t snore-backend backend/
docker build -f frontend/Dockerfile -t snore-frontend frontend/
```

The frontend image includes nginx that proxies `/api` and `/ws` to the backend.

```bash
docker run -e SNORE_CONFIG=/config/config.yaml -v /path/to/config:/config snore-backend
```

---

## 🛠️ Configuration

See [`backend/config.example.yaml`](backend/config.example.yaml) for a fully annotated example.

```yaml
secret_key: "long-random-string"   # JWT signing key

redis:
  url: "redis://localhost:6379"

users:
  - username: alice
    password_hash: "..."            # make hash PW=yourpassword
    queues: [general]
    notifications:
      - type: pushover
        user_key: "..."
        api_token: "..."

queues:
  - name: general
    flush_after_minutes: 5
    routing_rules: []

notifications:
  slack_webhook: "https://hooks.slack.com/..."
```

---

## 🪝 Webhook sources

All webhooks accept `POST` (JSON or form-encoded) and `GET` (query params).

| Source | URL | Notes |
|---|---|---|
| Icinga2 | `POST /api/webhook/icinga2` | See [`contrib/icinga2/`](contrib/icinga2/) |
| Uptime Kuma | `POST /api/webhook/uptime_kuma` | |
| NodePing | `POST /api/webhook/nodeping` | See payload template below |
| Manual | `POST /api/webhook/manual` | `{"title": "...", "description": "..."}` |

Named instances (multiple Icinga2 nodes etc.):
```
POST /api/webhook/icinga2.prod
POST /api/webhook/icinga2.staging
```

**NodePing webhook body template:**
```json
{
  "label": "{label}", "event": "{event}", "type": "{t}",
  "target": "{tg}", "success": "{su}", "message": "{m}", "checkid": "{_id}"
}
```

---

## 👤 Dynamic on-call

Override queue subscribers at runtime without restarting or editing config:

```bash
# Set on-call for 8 hours
curl -X PUT https://snore.example.com/api/queues/general/oncall \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"usernames": ["alice", "bob"], "duration_minutes": 480}'

# Clear (revert to config)
curl -X DELETE https://snore.example.com/api/queues/general/oncall \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔗 Icinga2 integration

See [`contrib/icinga2/`](contrib/icinga2/) for a ready-to-use notification script and Icinga2 config template.

---

## 🐍 Python client

A Python client library is available as a separate package:
**[github.com/lukasic/snore-client-python](https://github.com/lukasic/snore-client-python)**

```python
from snore_client import SnoreClient

client = SnoreClient("https://snore.example.com")
client.login("admin", "password")

client.send_webhook("manual", {"title": "Disk full", "description": "/var at 99%"})
client.set_oncall("general", ["alice"], duration_minutes=480)
```

---

## 🌍 Environment variables

| Variable | Default | Description |
|---|---|---|
| `SNORE_CONFIG` | `config.yaml` | Path to config file |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## 📄 License

Apache License 2.0 — see [LICENSE](LICENSE).

---

*This project was largely written with the assistance of [Claude](https://claude.ai) (Anthropic).*
