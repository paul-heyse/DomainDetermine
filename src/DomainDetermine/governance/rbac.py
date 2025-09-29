"""Role-based access, tenancy, and licensing enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import MutableMapping, Optional, Sequence

from DomainDetermine.governance.models import Role, TenantPolicy


@dataclass(frozen=True)
class LicensePolicy:
    """Describes licensing enforcement rules."""

    license_tag: str
    export_policy: str  # e.g. "ids_only", "labels_allowed", "no_export"

    def allows_export(self, export_type: str) -> bool:
        if self.export_policy == "no_export":
            return False
        if self.export_policy == "ids_only" and export_type != "ids_only":
            return False
        return True


@dataclass
class AccessDecision:
    """Result of an access check."""

    allowed: bool
    reason: Optional[str] = None


class AccessManager:
    """Manages RBAC roles, tenancy isolation, and licensing enforcement."""

    def __init__(self) -> None:
        self._user_roles: MutableMapping[str, set[Role]] = {}
        self._tenant_policies: MutableMapping[str, TenantPolicy] = {}
        self._license_policies: MutableMapping[str, LicensePolicy] = {}

    def assign_role(self, user: str, role: Role) -> None:
        self._user_roles.setdefault(user, set()).add(role)

    def set_tenant_policy(self, artifact_id: str, policy: TenantPolicy) -> None:
        self._tenant_policies[artifact_id] = policy

    def set_license_policy(self, artifact_id: str, policy: LicensePolicy) -> None:
        self._license_policies[artifact_id] = policy

    def check_access(
        self,
        *,
        user: str,
        tenant_id: str,
        required_roles: Sequence[Role],
        artifact_id: Optional[str] = None,
        export_type: Optional[str] = None,
    ) -> AccessDecision:
        user_roles = self._user_roles.get(user, set())
        if not set(required_roles).issubset(user_roles):
            return AccessDecision(False, reason="role_missing")
        if artifact_id:
            policy = self._tenant_policies.get(artifact_id)
            if policy and not policy.allows(tenant_id):
                return AccessDecision(False, reason="tenant_denied")
            license_policy = self._license_policies.get(artifact_id)
            if export_type and license_policy and not license_policy.allows_export(export_type):
                return AccessDecision(False, reason="license_denied")
        return AccessDecision(True)

    def users_with_role(self, role: Role) -> Sequence[str]:
        return [user for user, roles in self._user_roles.items() if role in roles]


__all__ = ["AccessDecision", "AccessManager", "LicensePolicy"]
