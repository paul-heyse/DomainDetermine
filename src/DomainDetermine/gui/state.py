from __future__ import annotations

from dataclasses import dataclass, replace

from nicegui import app


@dataclass
class TenantContext:
    tenant_id: str = "dev"
    user_id: str = "demo-operator"


@dataclass
class UserPreferences:
    theme: str = "light"
    default_workspace: str = "dashboard"


def register_global_state() -> None:
    """Ensure shared state objects exist for the NiceGUI application."""

    if "tenant_context" not in app.storage.general:
        app.storage.general["tenant_context"] = TenantContext()


def ensure_user_state() -> None:
    """Initialise per-user storage with default tenant context and preferences."""

    storage = app.storage.user
    if "tenant_context" not in storage:
        storage["tenant_context"] = TenantContext()
    if "preferences" not in storage:
        storage["preferences"] = UserPreferences()


def get_tenant_context() -> TenantContext:
    ensure_user_state()
    return app.storage.user["tenant_context"]


def set_tenant_context(tenant_id: str) -> TenantContext:
    ensure_user_state()
    context: TenantContext = app.storage.user["tenant_context"]
    new_context = replace(context, tenant_id=tenant_id)
    app.storage.user["tenant_context"] = new_context
    return new_context


def get_preferences() -> UserPreferences:
    ensure_user_state()
    return app.storage.user["preferences"]


def set_theme(theme: str) -> UserPreferences:
    ensure_user_state()
    preferences: UserPreferences = app.storage.user["preferences"]
    new_preferences = replace(preferences, theme=theme)
    app.storage.user["preferences"] = new_preferences
    return new_preferences
