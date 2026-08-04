/**
 * Minimal OIDC Authorization Code + PKCE flow for a public SPA client.
 * The code exchange happens directly against the issuer's token endpoint
 * (no client_secret) — the backend never talks to Keycloak, it only
 * verifies the resulting id_token's signature.
 */
import api from '@/api/client'

const STORAGE_VERIFIER = 'snore_oidc_verifier'
const STORAGE_STATE = 'snore_oidc_state'

interface SsoConfig {
  enabled: boolean
  issuer: string | null
  client_id: string | null
}

function base64UrlEncode(bytes: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
}

function randomString(length = 64): string {
  const bytes = new Uint8Array(length)
  crypto.getRandomValues(bytes)
  return base64UrlEncode(bytes.buffer)
}

async function sha256(value: string): Promise<ArrayBuffer> {
  const data = new TextEncoder().encode(value)
  return crypto.subtle.digest('SHA-256', data)
}

export async function fetchSsoConfig(): Promise<SsoConfig> {
  const res = await api.get<SsoConfig>('/auth/sso/config')
  return res.data
}

export async function redirectToKeycloak(config: SsoConfig): Promise<void> {
  if (!config.enabled || !config.issuer || !config.client_id) {
    throw new Error('SSO is not configured')
  }

  const discoveryRes = await fetch(`${config.issuer.replace(/\/$/, '')}/.well-known/openid-configuration`)
  const discovery = await discoveryRes.json()

  const verifier = randomString()
  const state = randomString(32)
  sessionStorage.setItem(STORAGE_VERIFIER, verifier)
  sessionStorage.setItem(STORAGE_STATE, state)

  const challenge = base64UrlEncode(await sha256(verifier))
  const redirectUri = `${window.location.origin}/auth/callback`

  const params = new URLSearchParams({
    client_id: config.client_id,
    response_type: 'code',
    scope: 'openid profile',
    redirect_uri: redirectUri,
    state,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  })

  window.location.href = `${discovery.authorization_endpoint}?${params.toString()}`
}

export async function handleKeycloakCallback(): Promise<string> {
  const query = new URLSearchParams(window.location.search)
  const code = query.get('code')
  const state = query.get('state')
  const error = query.get('error')

  const expectedState = sessionStorage.getItem(STORAGE_STATE)
  const verifier = sessionStorage.getItem(STORAGE_VERIFIER)
  sessionStorage.removeItem(STORAGE_STATE)
  sessionStorage.removeItem(STORAGE_VERIFIER)

  if (error) {
    throw new Error(`SSO login failed: ${error}`)
  }
  if (!code || !state || !expectedState || state !== expectedState || !verifier) {
    throw new Error('Invalid or expired SSO callback state')
  }

  const config = await fetchSsoConfig()
  if (!config.enabled || !config.issuer || !config.client_id) {
    throw new Error('SSO is not configured')
  }

  const discoveryRes = await fetch(`${config.issuer.replace(/\/$/, '')}/.well-known/openid-configuration`)
  const discovery = await discoveryRes.json()
  const redirectUri = `${window.location.origin}/auth/callback`

  const tokenRes = await fetch(discovery.token_endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: redirectUri,
      client_id: config.client_id,
      code_verifier: verifier,
    }),
  })

  if (!tokenRes.ok) {
    throw new Error('Failed to exchange authorization code for tokens')
  }

  const tokens = await tokenRes.json()
  if (!tokens.id_token) {
    throw new Error('Keycloak response did not include an id_token')
  }
  return tokens.id_token as string
}
