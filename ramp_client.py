"""Thin HTTP client for Ramp Developer API.

OAuth2 Client Credentials grant -- confirmed via docs.ramp.com/developer-api/
v1/authorization (2026-08-29): token endpoint uses HTTP Basic Auth with
client_id/client_secret, no refresh_token concept, connector re-exchanges
on expiry. Same "fail()-dict + ClientFail exception" shape as every other
connector this session's *_client.py.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

API_BASE = "https://api.ramp.com/developer/v1"
TOKEN_URL = "https://api.ramp.com/developer/v1/token"

DEFAULT_SCOPE = (
    "cards:read transactions:read users:read users:write departments:read "
    "locations:read reimbursements:read reimbursements:write limits:read "
    "receipts:read cards:write"
)

RAMP_NOT_CONNECTED = "RAMP_NOT_CONNECTED"
RAMP_UNAUTHORIZED = "RAMP_UNAUTHORIZED"
RAMP_FORBIDDEN_SCOPE = "RAMP_FORBIDDEN_SCOPE"
RAMP_NOT_FOUND = "RAMP_NOT_FOUND"
RAMP_RATE_LIMITED = "RAMP_RATE_LIMITED"
RAMP_BACKEND_ERROR = "RAMP_BACKEND_ERROR"
RAMP_VALIDATION_FAILED = "RAMP_VALIDATION_FAILED"

_MESSAGES = {
    RAMP_NOT_CONNECTED: "No Ramp connection found. Connect Ramp first.",
    RAMP_UNAUTHORIZED: "Ramp rejected the Client ID/Secret pair as invalid.",
    RAMP_FORBIDDEN_SCOPE: "Ramp rejected this request -- the connected developer app is missing the required scope.",
    RAMP_NOT_FOUND: "That Ramp record was not found.",
    RAMP_RATE_LIMITED: "Ramp rate-limited this request. Try again shortly.",
    RAMP_BACKEND_ERROR: "Ramp's API returned an error.",
    RAMP_VALIDATION_FAILED: "Ramp rejected the request as invalid.",
}


class ClientFail(Exception):
    def __init__(self, payload: dict):
        self.payload = payload
        super().__init__(payload.get("message", "Ramp request failed"))


def fail(code: str, detail: str = "") -> dict:
    msg = _MESSAGES.get(code, "Ramp request failed.")
    if detail:
        msg = f"{msg} ({detail})"
    return {"ok": False, "code": code, "message": msg}


async def exchange_client_credentials(client_id: str, client_secret: str, scope: str = DEFAULT_SCOPE) -> dict:
    """Exchange client_id/client_secret for a short-lived access token via HTTP Basic Auth."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.post(
                TOKEN_URL,
                auth=(client_id, client_secret),
                data={"grant_type": "client_credentials", "scope": scope},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except httpx.RequestError as e:
            return fail(RAMP_BACKEND_ERROR, str(e))
    if resp.status_code in (401, 403):
        return fail(RAMP_UNAUTHORIZED, f"HTTP {resp.status_code}")
    if resp.status_code >= 400:
        return fail(RAMP_BACKEND_ERROR, f"HTTP {resp.status_code}")
    try:
        data = resp.json()
    except ValueError:
        return fail(RAMP_BACKEND_ERROR, "non-JSON token response")
    access_token = data.get("access_token", "")
    if not access_token:
        return fail(RAMP_UNAUTHORIZED, "no access_token in response")
    expires_in = int(data.get("expires_in", 3600) or 3600)
    return {"ok": True, "access_token": access_token, "expires_at": time.time() + expires_in - 30}


async def ensure_fresh_token(conn: dict) -> dict:
    """Re-exchange the token if expired or missing. Returns updated conn dict fields (access_token/expires_at) or a fail() dict."""
    if conn.get("access_token") and conn.get("expires_at", 0) > time.time():
        return {"ok": True, "access_token": conn["access_token"], "expires_at": conn["expires_at"]}
    result = await exchange_client_credentials(conn.get("client_id", ""), conn.get("client_secret", ""))
    return result


def _check_status(resp: httpx.Response, action: str) -> Any:
    if resp.status_code == 401:
        raise ClientFail(fail(RAMP_UNAUTHORIZED, action))
    if resp.status_code == 403:
        raise ClientFail(fail(RAMP_FORBIDDEN_SCOPE, action))
    if resp.status_code == 404:
        raise ClientFail(fail(RAMP_NOT_FOUND, action))
    if resp.status_code == 429:
        raise ClientFail(fail(RAMP_RATE_LIMITED, action))
    if resp.status_code >= 400:
        raise ClientFail(fail(RAMP_BACKEND_ERROR, f"HTTP {resp.status_code} on {action}"))
    if not resp.content:
        return {}
    try:
        return resp.json()
    except ValueError:
        raise ClientFail(fail(RAMP_BACKEND_ERROR, f"non-JSON response on {action}"))


async def request(ctx, conn: dict, method: str, path: str, *, params: dict | None = None,
                   json_body: dict | None = None, action: str = "call Ramp") -> Any:
    token_result = await ensure_fresh_token(conn)
    if not token_result.get("ok"):
        raise ClientFail(token_result)
    headers = {"Authorization": f"Bearer {token_result['access_token']}"}
    url = f"{API_BASE}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.request(method, url, headers=headers, params=params, json=json_body)
        except httpx.RequestError as e:
            raise ClientFail(fail(RAMP_BACKEND_ERROR, str(e)))
    return _check_status(resp, action)


def known_entities() -> list[str]:
    return ["cards", "transactions", "users", "departments", "locations", "reimbursements", "limits", "receipts"]


def entity_path(entity: str, record_id: str = "") -> str:
    mapping = {
        "cards": "/cards",
        "transactions": "/transactions",
        "users": "/users",
        "departments": "/departments",
        "locations": "/locations",
        "reimbursements": "/reimbursements",
        "limits": "/limits",
        "receipts": "/receipts",
    }
    base = mapping.get(entity, f"/{entity}")
    return f"{base}/{record_id}" if record_id else base
