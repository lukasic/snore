# SNORE — Service Notification Override & Response Engine

## Popis
- Web utilita pre malé tímy sysadminov (do ~10 ľudí) ktorí sa striedajú na pohotovostiach
- Agreguje incidenty zo sledovacích systémov do front predtým, než sú odoslané notifikačnými backendmi
- Admin vidí incidenty v dashboarde a môže ich potvrdiť; ak tak neurobí, SNORE ich po `flush_after_minutes` odošle
- Podporuje dynamické nastavenie on-call cez API (bez reštartu alebo zmeny configu) — integrácia s externým plánovačom rotácií
- Takeover umožňuje prevziať frontu okamžite (napr. admin príde skôr ráno, alebo ide na obed)
- Mute stlmí notifikácie pre frontu na definovanú dobu (napr. pri veľkom výpadku)

## Stack
- **Backend**: Python + FastAPI, port 8000
- **Frontend**: Vue 3 + Vite + TypeScript + Tailwind CSS + Pinia, port 5173
- **Databáza**: Redis (async cez `redis[hiredis]`)
- **Auth**: JWT HS256, 24h, uložený v localStorage ako `snore_token`
- **Python env**: pyenv virtualenv `snore`

## Kľúčové súbory

### Backend
- `backend/app/main.py` — FastAPI app, lifespan spúšťa scheduler; `LOG_LEVEL` env var
- `backend/app/config.py` — YAML config loader + `resolve_queue()` routing (fnmatch pre source/host/service)
- `backend/app/store.py` — Redis CRUD: incidenty, mute, takeover, on-call
- `backend/app/scheduler.py` — APScheduler auto-flush každú 1 min, broadcast `scheduler_tick`
- `backend/app/dispatch.py` — zostavuje notifikátorov (takeover > on-call > config), odosiela
- `backend/app/history.py` — Redis história, max 500 záznamov
- `backend/app/ws.py` — WebSocket ConnectionManager s broadcast
- `backend/app/routers/incidents.py` — CRUD incidentov, mute, takeover
- `backend/app/routers/queues.py` — dynamický on-call (PUT/GET/DELETE `/{queue}/oncall`)
- `backend/app/routers/webhook.py` — prijíma webhooky, normalizuje payload; akceptuje POST aj GET
- `backend/config.yaml` — produkčná konfigurácia (nie v gite), vzor: `config.example.yaml`

### Frontend
- `frontend/src/stores/incidents.ts` — Pinia store: incidents, mutes, subscribers, takeovers, oncall, flushAfter
- `frontend/src/stores/auth.ts` — JWT auth store
- `frontend/src/views/DashboardView.vue` — hlavný dashboard, WebSocket
- `frontend/src/components/QueuePanel.vue` — UI fronty (flush, send, mute, takeover, on-call, ack)
- `frontend/src/composables/useWebSocket.ts` — reconnect s exponential backoff; WS cez nginx (`location.host`)

### Integrácie
- `contrib/icinga2/notify-snore.py` — Icinga2 notify skript (len stdlib)
- `contrib/icinga2/snore.conf` — Icinga2 NotificationCommand + template
- Python client: samostatný repozitár https://github.com/lukasic/snore-client-python

## API endpointy
- `POST /api/auth/login` — JWT token
- `GET  /api/auth/me`
- `GET  /api/incidents/` — incidenty, mutes, subscribers, takeovers, oncall, flush_after, next_scheduler_run
- `POST /api/incidents/acknowledge`
- `POST /api/incidents/flush` — ack all, bez notifikácií
- `POST /api/incidents/send` — notifikuj + vymaž
- `POST /api/incidents/mute` / `unmute`
- `POST /api/incidents/takeover` / `takeover/clear`
- `PUT/GET/DELETE /api/queues/{queue}/oncall`
- `GET  /api/history/?limit=50&offset=0`
- `GET/POST /api/webhook/{source}` — icinga2, icinga2.prod, uptime_kuma, nodeping, manual
- `WS   /ws?token=<jwt>`

## Redis kľúče
- `snore:incident:{id}` — JSON blob
- `snore:queue:{name}` — sorted set (score = received_at timestamp UTC)
- `snore:mute:{name}` — kľúč s TTL
- `snore:takeover:{name}` — JSON blob s TTL
- `snore:oncall:{name}` — JSON zoznam userov, voliteľný TTL
- `snore:history` — sorted set ID záznamov
- `snore:history:{id}` — JSON blob

## WebSocket správy
- `incidents_updated` — po každej mutácii incidentu; frontend volá `fetchIncidents()`
- `scheduler_tick` — po každom behu schedulera; frontend volá `fetchIncidents()`

## Webhook zdroje
Prefix-based matching: `icinga2.prod` použije icinga2 normalizer, uloží celý názov ako source.
`match_source` v routing pravidlách používa fnmatch (napr. `icinga2.*`).

NodePing vyžaduje custom JSON template (pozri README).

## Notifikačné backendy
- Slack webhook — globálny
- PagerDuty — per user, formát: `<source>: check <host> <service>, ...`
- Pushover — per user

## Konvencie
- TypeScript strict mode, žiadny `any`
- Tailwind utility classes
- Pydantic v2 (`model_dump_json()`, `model_validate_json()`)
- Testy v `backend/tests/`, pytest-asyncio; auth cez `app.dependency_overrides`
- Projekt píš v angličtine

## Dev príkazy
```
make install        # pip + npm install
make dev-backend    # uvicorn na :8000
make dev-frontend   # vite na :5173
make test           # pytest
make hash PW=xxx    # bcrypt hash hesla
```

## Dôležité
- Pred každou väčšou zmenou sa opýtaj na plán
- Testy píš pre každú novú funkciu
- Timezone: vždy `datetime.now(timezone.utc)`, nikdy `datetime.utcnow()`
- WebSocket auth: token cez `?token=` query param; close code 4001 = neplatný token
- `dispatch._build_notifiers` je `async` (volá `await get_takeover()`, `await get_oncall()`)
- Po `setOncall`/`clearOncall` volaj `fetchIncidents()` pre okamžitú aktualizáciu UI

## Pasce (hard-learned)
- **FastAPI testy — auth**: `app.dependency_overrides[get_current_user] = lambda: "user"` — nikdy `patch("app.routers.x.get_current_user")`, to nemá na `Depends()` žiadny efekt → 401
- **logging.basicConfig() nefunguje po uvicorne**: uvicorn si nastaví handlery pred `lifespan`, `basicConfig()` je potom no-op; log level nastav cez `logging.getLogger().setLevel(level)` priamo
- **Okamžitá aktualizácia UI po oncall zmenách**: WS broadcast môže prísť neskoro; store akcie `setOncall`/`clearOncall` musia volať `fetchIncidents()` explicitne
- **Webhook Content-Type**: externé systémy (napr. NodePing) nemusia posielať `Content-Type: application/json`; `_parse_payload` preto číta raw body a skúša JSON aj form-urlencoded, fallback na query params
