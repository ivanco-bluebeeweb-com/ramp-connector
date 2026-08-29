"""Panel UI -- connections list/connect form + the one required "App
settings" entry point, same shape as every other connector this
session's panels.py.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule. Disconnect lives only in the
"App settings" screen (panels_settings.py). The one secondary "App
settings" button is always the LAST element at the bottom of the sidebar.

PER ~/UI_INTERFACE_STANDARD.md (2026-08-21 addendum): every Input carries
its own visible label (a ui.Text wrapping the ui.Input in a Stack -- ui.Input
itself does not accept label=), the placeholder text is always contextually
specific. The "How do I set this up?" instructions live ONLY in the help
overlay below -- never duplicated as static sidebar text.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers_connection as h


def _settings_button() -> ui.UINode:
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__ramp_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("label") or "Ramp connection"
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(label, variant="body"),
        ui.Text("Connected", variant="caption"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Ramp accounts connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _connect_section() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, children=[
        ui.Form(
            action="connect_ramp",
            submit_label="Connect Ramp",
            children=[
                ui.Stack(direction="v", gap=1, children=[
                    ui.Text("Client ID", variant="label"),
                    ui.Input(param_name="client_id", placeholder="Paste your Ramp developer app Client ID"),
                ]),
                ui.Stack(direction="v", gap=1, children=[
                    ui.Text("Client Secret", variant="label"),
                    ui.Password(param_name="client_secret", placeholder="Paste your Ramp developer app Client Secret"),
                ]),
                ui.Stack(direction="v", gap=1, children=[
                    ui.Text("Label (optional)", variant="label"),
                    ui.Input(param_name="label", placeholder="e.g. Acme Inc Ramp"),
                ]),
            ],
        ),
        ui.Button(
            "How do I set this up?", variant="ghost", size="sm", full_width=True,
            on_click=ui.Call("__panel__ramp_connect_help"),
        ),
    ])


@ext.panel("ramp_connect", slot="left", title="Ramp")
async def ramp_connect(ctx, **kwargs) -> object:
    connections = await h._load_connections(ctx)
    return ui.Stack(direction="v", gap=4, children=[
        _connections_section(connections),
        ui.Divider(),
        _connect_section(),
        ui.Spacer(),
        _settings_button(),
    ])


@ext.panel("ramp_connect_help", slot="overlay", title="How do I set this up?")
async def ramp_connect_help(ctx, **kwargs) -> object:
    return ui.Stack(direction="v", gap=3, children=[
        ui.Text(
            "1. Sign in to Ramp as a Business Admin and open the Ramp Developer Console "
            "(ramp.com > Bank & Cards > Developer, or business.ramp.com/settings/developer).",
            variant="body",
        ),
        ui.Text(
            "2. Create a new API application (\"Add App\"). Ramp will show you a Client ID and "
            "Client Secret -- copy the Secret now, it is shown only once.",
            variant="body",
        ),
        ui.Text(
            "3. When creating the app, grant it the scopes it needs: cards, transactions, users, "
            "departments, locations, reimbursements, limits, receipts (read and write where relevant).",
            variant="body",
        ),
        ui.Text(
            "4. Paste the Client ID and Client Secret into the form here and connect -- Webbee "
            "verifies them with a real token exchange before saving anything.",
            variant="body",
        ),
    ])
