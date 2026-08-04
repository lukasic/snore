# SSO (OIDC) login via Keycloak

SNORE supports logging in through an external OIDC provider (Keycloak) as an
**optional alternative** to the built-in password login. The password login
always remains available.

## How it works

1. The frontend redirects the browser to Keycloak's authorization endpoint
   using the **Authorization Code + PKCE** flow. Keycloak client is a
   **public client** (no client secret) — the code/token exchange happens
   directly between the browser and Keycloak.
2. Keycloak redirects back to `/auth/callback` on the SNORE frontend with an
   authorization code.
3. The frontend exchanges the code for tokens directly against Keycloak's
   token endpoint and receives an `id_token`.
4. The frontend sends the `id_token` to the SNORE backend
   (`POST /api/auth/sso/login`).
5. The backend verifies the `id_token` signature against Keycloak's JWKS
   (fetched via the issuer's `.well-known/openid-configuration`, cached
   in-process for 10 minutes) and extracts the username from the configured
   claim (default: `preferred_username`).
6. The backend maps that username to an entry in `config.yaml`'s `users`
   list and issues its own `snore_token` (JWT, HS256, 24h) — identical to
   what the password login produces. From this point on, SSO and password
   sessions are indistinguishable to the rest of SNORE.

No server-side session state, PKCE verifier/state, or Keycloak tokens are
ever stored — the SNORE container stays fully stateless. The only cache is
an in-process JWKS cache that is safely rebuilt on restart.

## User mapping

- A user authenticated via Keycloak is matched to `config.yaml` **by
  username** (the `preferred_username` claim by default — configurable via
  `oidc.username_claim`).
- If no matching user exists in `config.yaml`, the login still succeeds, but
  the user has no `queues` and no `notifications`. The frontend shows a
  banner informing them that no notifications are configured, and disables
  the *Takeover* / *On-call* actions. The backend also rejects
  `POST /api/incidents/takeover` and `PUT /api/queues/{queue}/oncall` with
  `403` for any user (SSO or password) with an empty `notifications` list —
  this check is not SSO-specific, it applies to every login method.

## config.yaml

```yaml
oidc:
  enabled: false
  issuer: "https://keycloak.example.com/realms/snore"
  client_id: "snore-frontend"
  username_claim: "preferred_username"  # optional, default shown
```

Nothing else is required in `config.yaml` for SSO — existing `users:`
entries are reused as-is; there is no separate "Keycloak user" concept in
the config.

## Required changes in Keycloak

1. **Create a realm** (or reuse an existing one) — this becomes `oidc.issuer`,
   e.g. `https://keycloak.example.com/realms/snore`.
2. **Create a client**:
   - Client ID: e.g. `snore-frontend` (must match `oidc.client_id`)
   - Client authentication: **Off** (public client — PKCE is used instead of
     a client secret)
   - Standard flow (Authorization Code): **enabled**
   - Direct access grants: not required, can be disabled
   - Valid redirect URIs: `https://<snore-frontend-host>/auth/callback`
   - Web origins: `https://<snore-frontend-host>` (or `+` to reuse redirect
     URIs) — required for the browser to call the token endpoint via CORS
3. **Users**: usernames in Keycloak should match the `username` values used
   in SNORE's `config.yaml` for the mapping in step 6 above to work. If a
   different claim should be used for mapping (e.g. `email`), set
   `oidc.username_claim` accordingly and ensure that claim is included in
   the ID token (Keycloak includes `email` by default when the `email`
   scope is requested; the frontend currently requests `openid profile`).
4. No special client scopes/mappers are required beyond the defaults — the
   backend only needs `iss`, `aud`, `exp`, and the configured username claim
   to be present in the `id_token`.

## Required changes in reverse proxy / deployment

- The SNORE frontend must be reachable at a stable origin matching the
  redirect URI registered in Keycloak.
- No changes needed on the SNORE backend's reverse-proxy config beyond what
  already exists — `/api/auth/sso/config` and `/api/auth/sso/login` are
  regular `/api/*` routes.
- The browser must be able to reach the Keycloak issuer directly (discovery
  document, JWKS via the backend, and the token/authorization endpoints via
  the browser) — if Keycloak is only reachable on an internal network, the
  SNORE frontend's users need network access to it too.

## Logout

Logout is **local only**: SNORE clears its own `snore_token` from
`localStorage`. It does not perform a Keycloak/OIDC end-session redirect, so
an existing Keycloak SSO session in the browser is not terminated — the user
would be transparently re-authenticated if they click "Sign in with SSO"
again without an explicit Keycloak logout.

## Token lifetime

The SNORE token issued after SSO login has the same 24h expiry as the
password-login token. There is no silent refresh against Keycloak; once it
expires, the user logs in again (via either method).
