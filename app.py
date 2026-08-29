"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK, same reasoning as every other connector here -- the user's own
Ramp company's card/transaction/spend data lives inside THEIR OWN Ramp
account.

WHY OAUTH2 CLIENT CREDENTIALS (confirmed against docs.ramp.com/developer-api/v1/
authorization + apis.io/security/ramp, 2026-08-29): Ramp's Developer API
issues short-lived access tokens from a token endpoint
(api.ramp.com/developer/v1/token) using HTTP Basic Auth with the
developer app's Client ID/Secret plus a requested scope string. No
browser redirect, no refresh_token concept -- on expiry the connector
just re-exchanges from the stored client_id/client_secret, same pattern
as Paychex Flex Connector.

WHY BILL PAY IS OUT OF SCOPE THIS RELEASE. Ramp Bill Pay (AP automation,
vendor invoices) is a separate product surface with its own scope grants
not universally enabled on every Ramp account -- flagged as an explicit
v2 follow-up in PREPARATION.md rather than silently omitted.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "ramp-connector",
    version="0.1.0",
    display_name="Ramp",
    icon="icon.svg",
    capabilities=["ramp:read", "ramp:write"],
    description=(
        "Connect your own Ramp account (OAuth2 Client Credentials -- bring your own developer app Client ID/"
        "Secret from the Ramp Developer Console) to read cards, transactions, users, departments, locations, "
        "reimbursements, limits, and receipts, plus value-add spend and card-utilization reports. Reimbursement "
        "creation, user department/role updates, and card suspend/unsuspend are supported. Bill Pay (AP invoices) "
        "is out of scope this release."
    ),
)

chat = ChatExtension(ext)
