"""Custom exceptions for the overlay module."""

from __future__ import annotations


class OverlayError(Exception):
    """Base exception for overlay related failures."""


class IdentifierCollisionError(OverlayError):
    """Raised when an overlay identifier collides with an existing record."""


class InvalidStateTransitionError(OverlayError):
    """Raised when attempting an illegal lifecycle state transition."""


class QualityGateError(OverlayError):
    """Raised when automated quality checks fail."""


class EvidenceValidationError(OverlayError):
    """Raised when evidence metadata cannot be verified."""


class PolicyViolationError(OverlayError):
    """Raised when proposals violate policy or licensing restrictions."""

