"""Value-add reports for Ramp Connector -- spend overview and card
utilization, same "aggregate raw records into one glance" shape as
every other connector's handlers_reports.py this session.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import ramp_client as rc
from app import chat
from handlers_connection import resolve_or_error
from schemas import (
    GetSpendOverviewParams, SpendOverviewReport,
    GetCardUtilizationReportParams, CardUtilizationReport,
)


@chat.function(
    "get_spend_overview_report",
    "Value-add report: summarize recent Ramp transaction spend by category -- total spend and transaction count.",
    action_type="read", chain_callable=True, data_model=SpendOverviewReport,
)
async def get_spend_overview_report(ctx, params: GetSpendOverviewParams) -> ActionResult:
    """Scan recent transactions and bucket spend by category."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    data = await rc.request(
        ctx, conn, "GET", "/transactions", params={"page_size": params.limit}, action="list transactions for spend overview"
    )
    rows = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    total = 0.0
    by_category: dict[str, float] = {}
    for r in rows:
        amt = r.get("amount", {})
        value = (amt.get("amount", 0) or 0) / 100 if isinstance(amt, dict) else float(r.get("amount", 0) or 0)
        total += value
        cat = (r.get("sk_category_name") or r.get("category") or "Uncategorized")
        by_category[cat] = by_category.get(cat, 0.0) + value
    return ActionResult.ok(SpendOverviewReport(transaction_count=len(rows), total_spend=round(total, 2), by_category={k: round(v, 2) for k, v in by_category.items()}))


@chat.function(
    "get_card_utilization_report",
    "Value-add report: scan Ramp cards and flag active/suspended counts plus any cards near their spend limit.",
    action_type="read", chain_callable=True, data_model=CardUtilizationReport,
)
async def get_card_utilization_report(ctx, params: GetCardUtilizationReportParams) -> ActionResult:
    """Scan cards and summarize utilization/status."""
    conn, err = await resolve_or_error(ctx, params.connection_id)
    if not conn:
        return err
    data = await rc.request(
        ctx, conn, "GET", "/cards", params={"page_size": params.limit}, action="list cards for utilization report"
    )
    rows = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    active = sum(1 for r in rows if (r.get("state") or "").upper() == "ACTIVE")
    suspended = sum(1 for r in rows if (r.get("state") or "").upper() == "SUSPENDED")
    near_limit: list[dict] = []
    for r in rows:
        spend_limit = r.get("spending_restrictions", {}).get("amount", 0) if isinstance(r.get("spending_restrictions"), dict) else 0
        available = r.get("spending_restrictions", {}).get("interval_spending_limit", 0) if isinstance(r.get("spending_restrictions"), dict) else 0
        if spend_limit and available and available <= spend_limit * 0.1:
            near_limit.append({"card_id": r.get("id", ""), "display_name": r.get("display_name", "")})
    return ActionResult.ok(CardUtilizationReport(
        total_cards=len(rows), active_cards=active, suspended_cards=suspended, cards_near_limit=near_limit,
    ))
