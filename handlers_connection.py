"""Connection management for Ramp Connector: connect/disconnect/list.

OAuth2 Client Credentials -- verified synchronously against a harmless
token exchange at connect time, then re-exchanged transparently on every
call when the cached token has expired (ensure_fresh_token).
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import ramp_client as rc
from app import chat
from schemas import (
    NoParams,
    ConnectRampParams,
    ProviderConnection, ProviderConnectionList,
    DisconnectRampParams, DeleteResult,
)

_SECRET_NAME = "ramp_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


async def resolve_connection(ctx, connection_id: str = "") -> dict | None:
    connections = await _load_connections(ctx)
    if not connections:
        return None
    if connection_id:
        for c in connections:
            if c.get("id") == connection_id:
                return c
        return None
    return connections[0]


async def resolve_or_error(ctx, connection_id: str = ""):
    conn = await resolve_connection(ctx, connection_id)
    if not conn:
        return None, ActionResult.error(
            "No Ramp connection found. Connect Ramp first.",
            code="RAMP_NOT_CONNECTED",
        )
    return conn, None


async def _persist_token(ctx, conn: dict, token_result: dict) -> None:
    """Write back a refreshed access_token/expires_at into the stored connection."""
    connections = await _load_connections(ctx)
    for c in connections:
        if c.get("id") == conn.get("id"):
            c["access_token"] = token_result.get("access_token", "")
            c["expires_at"] = token_result.get("expires_at", 0)
            conn["access_token"] = c["access_token"]
            conn["expires_at"] = c["expires_at"]
            break
    await _save_connections(ctx, connections)


@chat.function(
    "connect_ramp",
    "Connect your own Ramp account by saving your developer app's Client ID/Secret (from the Ramp Developer "
    "Console), after checking they actually work via OAuth2 Client Credentials.",
    action_type="write", chain_callable=True, data_model=ProviderConnection,
    event="ramp-connector.connect_ramp", effects=["create:connection"],
)
async def connect_ramp(ctx, params: ConnectRampParams) -> ActionResult:
    """Verify the Client ID/Secret pair via token exchange and save the connection."""
    if not params.client_id or not params.client_secret:
        return ActionResult.error(
            "client_id and client_secret are both required.",
            code="RAMP_VALIDATION_FAILED",
        )
    token_result = await rc.exchange_client_credentials(params.client_id, params.client_secret)
    if not token_result.get("ok"):
        return ActionResult.error(token_result.get("message", "Could not verify Ramp credentials."),
                                   code=token_result.get("code", "RAMP_UNAUTHORIZED"))
    connections = await _load_connections(ctx)
    conn_id = str(uuid.uuid4())
    connections.append({
        "id": conn_id,
        "label": params.label or "Ramp",
        "client_id": params.client_id,
        "client_secret": params.client_secret,
        "access_token": token_result["access_token"],
        "expires_at": token_result["expires_at"],
    })
    await _save_connections(ctx, connections)
    return ActionResult.ok(ProviderConnection(id=conn_id, label=params.label or "Ramp"))


@chat.function(
    "list_connections",
    "List the connected Ramp accounts.",
    action_type="read", chain_callable=True, data_model=ProviderConnectionList,
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List the connected Ramp accounts."""
    connections = await _load_connections(ctx)
    items = [ProviderConnection(id=c.get("id", ""), label=c.get("label", "")) for c in connections]
    return ActionResult.ok(ProviderConnectionList(connections=items))


@chat.function(
    "disconnect_ramp",
    "Disconnect a Ramp account: deletes the saved Client ID/Secret pair. Nothing in Ramp itself is changed.",
    action_type="write", chain_callable=True, data_model=DeleteResult,
    event="ramp-connector.disconnect_ramp", effects=["delete:connection"],
)
async def disconnect_ramp(ctx, params: DisconnectRampParams) -> ActionResult:
    """Disconnect a Ramp account: deletes the saved connection."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error("Connection not found.", code="RAMP_NOT_CONNECTED")
    await _save_connections(ctx, remaining)
    return ActionResult.ok(DeleteResult(deleted=True, id=params.connection_id))
