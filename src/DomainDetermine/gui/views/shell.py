from __future__ import annotations

from typing import Callable

from nicegui import app as nicegui_app
from nicegui import ui

from ..state import TenantContext
from ..stubs import COMMAND_PALETTE_ACTIONS, NOTIFICATION_FEED
from ..workspaces import WORKSPACES


def render_shell(active_slug: str, content: Callable[[], None]) -> None:
    """Render global chrome (header, navigation) and workspace content."""

    tenant_context: TenantContext = nicegui_app.storage.general.get(
        "tenant_context", TenantContext()
    )

    command_dialog = ui.dialog()
    with command_dialog, ui.card().classes("p-4 w-80 space-y-3"):
        ui.label("Command Palette").classes("text-lg font-semibold")
    selection = ui.select(
        options=[action["label"] for action in COMMAND_PALETTE_ACTIONS],
        value=COMMAND_PALETTE_ACTIONS[0]["label"],
    ).classes("w-full")

        def _execute_command() -> None:
        selected_label = selection.value
        for action in COMMAND_PALETTE_ACTIONS:
            if action["label"] == selected_label:
                if action["path"].startswith("/"):
                    ui.navigate.to(action["path"])
                else:
                    ui.notify(f"Action coming soon: {action['label']}")
                break
            command_dialog.close()

        ui.button("Go", on_click=_execute_command).classes("w-full bg-slate-900 text-white")

    with ui.header().classes(
        "items-center justify-between bg-slate-900 text-white px-6 py-4 gap-4"
    ):
        ui.label("DomainDetermine GUI Prototype").classes("text-xl font-bold")

        with ui.row().classes("items-center gap-3"):
            ui.input(
                placeholder="Global search (press Enter)",
                on_key=lambda e: ui.notify(f"Search coming soon: {e.args['value']}")
                if e.args.get("key") == "Enter"
                else None,
            ).props("dense input-class=\"text-slate-900\"")
            ui.button("Command Palette", on_click=command_dialog.open)
            notification_button = ui.button(
                "Notifications",
                on_click=lambda: notification_drawer.toggle(),
            ).props("outline")
            ui.badge(tenant_context.tenant_id.upper()).props("color=primary")

    notification_drawer = ui.drawer(side="right", value=False).classes(
        "w-96 p-4 space-y-3"
    )
    with notification_drawer:
        ui.label("Notification Center").classes("text-lg font-semibold")
        for notification in NOTIFICATION_FEED:
            with ui.card().classes("p-3 bg-white shadow"):
                ui.label(notification["title"]).classes("text-sm font-semibold")
                ui.label(notification["body"]).classes("text-sm text-gray-600")
                ui.label(notification["timestamp"]).classes("text-xs text-gray-400")
                ui.button("Acknowledge", on_click=lambda: ui.notify("Acknowledged"))

    with ui.row().classes("w-full min-h-screen"):
        with ui.column().classes(
            "w-64 bg-slate-100 min-h-screen p-4 space-y-2 border-r border-slate-200"
        ):
            ui.label("Workspaces").classes("text-xs uppercase text-gray-500 tracking-wide")
            for workspace in WORKSPACES:
                def navigate(target: str = workspace.slug) -> None:
                    ui.navigate.to("/" if target == "dashboard" else f"/workspaces/{target}")

                button = ui.button(workspace.title, on_click=navigate).classes("w-full")
                if workspace.slug == active_slug:
                    button.classes("bg-slate-900 text-white")
                else:
                    button.classes("bg-white text-slate-900")

        with ui.column().classes("flex-1 p-6 space-y-4"):
            content()
