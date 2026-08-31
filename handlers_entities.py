"""Generic entity layer + explicit writes for Ramp Connector.

list_entities/get_entity cover the bulk read surface (cards, transactions,
users, departments, locations, reimbursements, limits, receipts).
Writes are explicit, narrow chat functions (not generic create/update)
because Ramp's write surface is intentionally small and each write has
distinct real-world consequences (money movement, access changes).
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import ramp_client as rc
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    ListEntitiesParams, EntityList,
    GetEntityParams, EntityDetail,
    CreateReimbursementParams, UpdateUserParams, SetCardStatusParams, WriteResult,
)


@chat.function(
    "list_entities",
    "List Ramp records of any resource type (cards, transactions, users, departments, locations, "
    "reimbursements, limits, receipts) in the connected Ramp account.",
    action_type="read", chain_callable=True, data_model=EntityList,
)
async def list_entities(ctx, params: ListEntitiesParams) -> ActionResult:
    """List Ramp records of any resource type."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    if params.entity not in rc.known_entities():
        return ActionResult.error(
            f"Unknown entity '{params.entity}'. Known: {', '.join(rc.known_entities())}",
            code="RAMP_VALIDATION_FAILED",
        )
    query = {"page_size": params.limit}
    if params.filter_expr:
        for pair in params.filter_expr.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                query[k] = v
    data = await rc.request(ctx, conn, "GET", rc.entity_path(params.entity), params=query, action=f"list {params.entity}")
    records = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    return ActionResult.success(EntityList(entity=params.entity, count=len(records), records=records)), summary="Entities listed."


@chat.function(
    "get_entity",
    "Read one Ramp record of any resource type in full by its id.",
    action_type="read", chain_callable=True, data_model=EntityDetail,
)
async def get_entity(ctx, params: GetEntityParams) -> ActionResult:
    """Read one Ramp record in full."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    if params.entity not in rc.known_entities():
        return ActionResult.error(
            f"Unknown entity '{params.entity}'. Known: {', '.join(rc.known_entities())}",
            code="RAMP_VALIDATION_FAILED",
        )
    data = await rc.request(
        ctx, conn, "GET", rc.entity_path(params.entity, params.record_id), action=f"get {params.entity}"
    )
    return ActionResult.success(EntityDetail(entity=params.entity, record=data if isinstance(data, dict) else {})), summary="Entity retrieved."


@chat.function(
    "create_reimbursement",
    "Create a new reimbursement request for a Ramp user -- an out-of-pocket expense to be repaid.",
    action_type="write", chain_callable=True, data_model=WriteResult,
    event="ramp-connector.create_reimbursement", effects=["create:reimbursement"],
)
async def create_reimbursement(ctx, params: CreateReimbursementParams) -> ActionResult:
    """Create a reimbursement request."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    body = {
        "user_id": params.user_id,
        "amount": {"amount": round(params.amount * 100), "currency_code": params.currency},
        "merchant": params.memo or "Reimbursement",
    }
    data = await rc.request(ctx, conn, "POST", "/reimbursements", json_body=body, action="create reimbursement")
    rec_id = data.get("id", "") if isinstance(data, dict) else ""
    return ActionResult.success(WriteResult(ok=True, record_id=rec_id)), summary="Reimbursement created."


@chat.function(
    "update_user",
    "Update an existing Ramp user's department and/or role. Only given fields change.",
    action_type="write", chain_callable=True, data_model=WriteResult,
    event="ramp-connector.update_user", effects=["update:user"],
)
async def update_user(ctx, params: UpdateUserParams) -> ActionResult:
    """Update a Ramp user's department/role."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    body: dict = {}
    if params.department_id:
        body["department_id"] = params.department_id
    if params.role:
        body["role"] = params.role
    if not body:
        return ActionResult.error("Provide department_id and/or role to update.", code="RAMP_VALIDATION_FAILED")
    await rc.request(ctx, conn, "PATCH", f"/users/{params.user_id}", json_body=body, action="update user")
    return ActionResult.success(WriteResult(ok=True, record_id=params.user_id)), summary="User updated."


@chat.function(
    "set_card_status",
    "Suspend or unsuspend a Ramp card -- blocks/restores its ability to make new purchases.",
    action_type="write", chain_callable=True, data_model=WriteResult,
    event="ramp-connector.set_card_status", effects=["update:card"],
)
async def set_card_status(ctx, params: SetCardStatusParams) -> ActionResult:
    """Suspend or unsuspend a card."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    path = f"/cards/{params.card_id}/{'suspend' if params.suspend else 'unsuspend'}"
    await rc.request(ctx, conn, "POST", path, action="set card status")
    return ActionResult.success(WriteResult(ok=True, record_id=params.card_id)), summary="Card status updated."
