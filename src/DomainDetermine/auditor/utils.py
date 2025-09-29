"""Utility helpers for working with plan records."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Sequence


def to_records(data: Any) -> list[Mapping[str, Any]]:
    """Convert supported inputs into a list of mapping records."""

    if hasattr(data, "to_dict"):
        try:
            records = data.to_dict(orient="records")  # type: ignore[call-arg]
        except TypeError:
            records = data.to_dict()  # Fall back for objects exposing mapping-like output
        if isinstance(records, list):
            return [record if isinstance(record, Mapping) else dict(record) for record in records]
    if isinstance(data, Sequence):
        return [record if isinstance(record, Mapping) else dict(record) for record in data]
    msg = f"Unsupported record container: {type(data)}"
    raise TypeError(msg)


def copy_record(record: Mapping[str, Any]) -> MutableMapping[str, Any]:
    """Return a shallow mutable copy of a record."""

    return dict(record)


__all__ = ["copy_record", "to_records"]
