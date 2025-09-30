from __future__ import annotations

from typing import Iterable

from nicegui import ui

from ..stubs import DASHBOARD_SUMMARY


def _render_summary_cards(cards: Iterable[dict[str, str]]) -> None:
    with ui.grid(columns=3).classes("gap-4"):
        for card in cards:
            with ui.card().classes("p-4 shadow bg-white flex flex-col gap-2"):
                ui.label(card["title"]).classes("text-lg font-semibold")
                ui.label(card["value"]).classes("text-3xl font-bold text-slate-900")
                ui.label(card["updated"]).classes("text-xs uppercase text-gray-500")


def render_dashboard() -> None:
    with ui.column().classes("gap-6"):
        ui.label("Global overview").classes("text-2xl font-semibold")
        _render_summary_cards(DASHBOARD_SUMMARY)
