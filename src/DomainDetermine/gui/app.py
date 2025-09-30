from __future__ import annotations

from fastapi import FastAPI
from nicegui import app as nicegui_app
from nicegui import ui

from .state import register_global_state
from .views.dashboard import render_dashboard
from .views.shell import render_shell
from .workspaces import WORKSPACES, render_workspace


def create_app() -> FastAPI:
    """Return a FastAPI application with NiceGUI mounted."""

    nicegui_app.config.title = "DomainDetermine GUI"

    @nicegui_app.on_startup
    async def _on_startup() -> None:  # noqa: D401 - startup hook
        register_global_state()

    @ui.page("/")
    def _root() -> None:
        render_shell("dashboard", render_dashboard)

    for workspace in WORKSPACES:
        @ui.page(f"/workspaces/{workspace.slug}")
        def _workspace_page(workspace=workspace) -> None:  # noqa: B902
            render_shell(workspace.slug, lambda w=workspace: render_workspace(w))

    return ui.app  # NiceGUI exposes the FastAPI app as ui.app
