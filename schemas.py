"""Pydantic params/result models for Ramp Connector.

All params models are module-scope (V17 federal invariant, same rule as
every other connector this session's schemas.py).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


class ConnectionScoped(BaseModel):
    connection_id: str = Field(
        "",
        description="Which connected Ramp account to use (see list_connections). Omit if only one is connected.",
    )


# ──────────────────────────────────────────────────────────────────────────
# Connection -- OAuth2 Client Credentials, no browser redirect
# ──────────────────────────────────────────────────────────────────────────


class ConnectRampParams(BaseModel):
    client_id: str = Field("", description="Your Ramp developer app's Client ID.")
    client_secret: str = Field("", description="Your Ramp developer app's Client Secret.")
    label: str = Field("", description="Optional friendly label for this connection, e.g. 'Acme Inc Ramp'.")


class ProviderConnection(BaseModel):
    id: str = ""
    label: str = ""


class ProviderConnectionList(BaseModel):
    connections: list[ProviderConnection] = Field(default_factory=list)


class DisconnectRampParams(BaseModel):
    connection_id: str = Field(description="Which connection to disconnect (see list_connections).")


class DeleteResult(BaseModel):
    deleted: bool = False
    id: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Generic entity layer
# ──────────────────────────────────────────────────────────────────────────


class ListEntitiesParams(ConnectionScoped):
    entity: str = Field(description="Resource type: cards, transactions, users, departments, locations, reimbursements, limits, receipts.")
    filter_expr: str = Field("", description="Optional query-string filter supported by the resource (e.g. 'department_id=...').")
    limit: int = Field(50, ge=1, le=200, description="Maximum records to return.")


class EntityList(BaseModel):
    entity: str = ""
    count: int = 0
    records: list[dict] = Field(default_factory=list)


class GetEntityParams(ConnectionScoped):
    entity: str = Field(description="Resource type, same values as list_entities.")
    record_id: str = Field(description="The record's Ramp id.")


class EntityDetail(BaseModel):
    entity: str = ""
    record: dict = Field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────────
# Writes
# ──────────────────────────────────────────────────────────────────────────


class CreateReimbursementParams(ConnectionScoped):
    user_id: str = Field(description="The Ramp user id this reimbursement is for.")
    amount: float = Field(description="Reimbursement amount.")
    currency: str = Field("USD", description="Three-letter currency code.")
    memo: str = Field("", description="Optional memo/description for the reimbursement.")


class UpdateUserParams(ConnectionScoped):
    user_id: str = Field(description="The Ramp user id to update.")
    department_id: str = Field("", description="New department id. Leave empty to keep unchanged.")
    role: str = Field("", description="New role, e.g. 'BUSINESS_ADMIN', 'BUSINESS_USER'. Leave empty to keep unchanged.")


class SetCardStatusParams(ConnectionScoped):
    card_id: str = Field(description="The Ramp card id.")
    suspend: bool = Field(description="True to suspend the card, false to unsuspend it.")


class WriteResult(BaseModel):
    ok: bool = False
    record_id: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Value-add reports
# ──────────────────────────────────────────────────────────────────────────


class GetSpendOverviewParams(ConnectionScoped):
    limit: int = Field(100, ge=1, le=200, description="Number of recent transactions to scan for the overview.")


class SpendOverviewReport(BaseModel):
    transaction_count: int = 0
    total_spend: float = 0.0
    by_category: dict[str, float] = Field(default_factory=dict)


class GetCardUtilizationReportParams(ConnectionScoped):
    limit: int = Field(100, ge=1, le=200, description="Number of cards to scan.")


class CardUtilizationReport(BaseModel):
    total_cards: int = 0
    active_cards: int = 0
    suspended_cards: int = 0
    cards_near_limit: list[dict] = Field(default_factory=list)
