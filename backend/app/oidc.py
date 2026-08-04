"""OIDC id_token verification against a Keycloak (or any OIDC-compliant) issuer.

No server-side session state is kept — PKCE and the authorization-code
exchange happen entirely in the browser. The backend only verifies the
signature/claims of the id_token it receives and maps it to a config.yaml
user. JWKS keys are cached in-process (not in Redis) since re-fetching on
a cold start is cheap and the container must stay stateless.
"""
import time
from typing import Any

import httpx
from jose import jwt

from app.config import OidcConfig

_JWKS_CACHE_TTL_SECONDS = 600
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}


class OidcError(Exception):
    pass


async def _get_jwks(issuer: str) -> dict[str, Any]:
    cached = _jwks_cache.get(issuer)
    if cached and (time.monotonic() - cached[0]) < _JWKS_CACHE_TTL_SECONDS:
        return cached[1]

    async with httpx.AsyncClient(timeout=5.0) as client:
        discovery = await client.get(f"{issuer.rstrip('/')}/.well-known/openid-configuration")
        discovery.raise_for_status()
        jwks_uri = discovery.json()["jwks_uri"]

        jwks_resp = await client.get(jwks_uri)
        jwks_resp.raise_for_status()
        jwks = jwks_resp.json()

    _jwks_cache[issuer] = (time.monotonic(), jwks)
    return jwks


async def verify_id_token(id_token: str, oidc: OidcConfig) -> dict[str, Any]:
    """Verify signature/claims of an id_token and return its payload.

    Raises OidcError on any validation failure.
    """
    if not oidc.enabled or not oidc.issuer or not oidc.client_id:
        raise OidcError("SSO is not configured")

    try:
        jwks = await _get_jwks(oidc.issuer)
        payload = jwt.decode(
            id_token,
            jwks,
            algorithms=["RS256"],
            audience=oidc.client_id,
            issuer=oidc.issuer,
        )
    except httpx.HTTPError as exc:
        raise OidcError(f"Failed to fetch JWKS from issuer: {exc}") from exc
    except jwt.JWTError as exc:
        raise OidcError(f"Invalid id_token: {exc}") from exc

    return payload
