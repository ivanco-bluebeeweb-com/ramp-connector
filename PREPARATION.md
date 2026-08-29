# Ramp Connector -- Preparation (v0.1)

## API surface
Ramp Developer API (api.ramp.com/developer/v1) -- standard REST/JSON,
resources: cards, transactions, users, departments, locations, reimbursements,
bills (Ramp Bill Pay), limits, receipts. Confirmed via docs.ramp.com/developer-api
(2026-08-29).

## Auth model
OAuth2 **Client Credentials** grant (server-to-server, no browser redirect) --
confirmed via docs.ramp.com/developer-api/v1/authorization + apis.io/security/ramp.
Token endpoint: `https://api.ramp.com/developer/v1/token`, client_id/client_secret
sent via HTTP Basic Auth in the token request body (`grant_type=client_credentials`
+ `scope=...`). Returned access_token is short-lived (typically 1h) -- connector
re-exchanges from the stored client_id/client_secret on expiry, same shape as
Paychex Flex's token refresh (no refresh_token concept, just re-exchange).

## Why BYOK
Same reasoning as every other connector here -- the user's own Ramp company's
card/transaction/spend data lives inside THEIR OWN Ramp account. The developer
app (Client ID + Secret) is created per Ramp account from the Ramp Developer
Console (admin access required), not a shared Imperal-wide credential.

## Scope for v1
Read-heavy: cards, transactions, users, departments, locations, reimbursements,
limits, receipts. Write: create reimbursement, update user (department/role),
suspend/unsuspend card. Bill Pay (AP automation, vendor invoices) is a separate
Ramp product surface with its own scope grants -- flagged as v2 follow-up rather
than silently omitted, since it isn't universally enabled on every Ramp account.

## Rate limits / known constraints
Ramp enforces per-scope rate limits (documented as generous for read scopes,
tighter for write). Token requires the specific scope for each resource
(e.g. `transactions:read`, `users:read`, `cards:write`) -- granted at developer
app creation time in the Ramp Developer Console. If a scope wasn't granted,
Ramp returns 403 -- the client surfaces this as a clear "missing scope" error
rather than a generic auth failure.
