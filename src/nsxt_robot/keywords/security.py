"""Security keywords: segment tags, groups (static IP / dynamic tag), and DFW."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from robot.api.deco import keyword

from ..connections import NsxtConnectionManager
from .paths import INFRA_BASE


class SecurityKeywords:
    """Mixin providing tag/group/DFW keywords.

    Requires ``self._connections`` and ``nsx_rest_delete_ignore_error`` from
    :class:`~nsxt_robot.keywords.rest.RestKeywords` (composed by ``NsxtLibrary``).
    """

    _connections: NsxtConnectionManager
    nsx_rest_delete_ignore_error: Callable[[str], None]

    # ── Tags ─────────────────────────────────────────────────────────────

    @keyword("Set Tags On Segment")
    def set_tags_on_segment(self, segment_id: str, *tags: str) -> None:
        """Replace the tag set on a segment.

        ``tags`` is a list of ``scope|value`` strings, e.g.
        ``app|web``, ``tier|frontend``.
        """
        tag_list = []
        for entry in tags:
            scope, _, value = entry.partition("|")
            tag_list.append({"scope": scope, "tag": value})
        self._connections.current.patch(f"{INFRA_BASE}/segments/{segment_id}", {"tags": tag_list})

    # ── Groups (NSGroups) ────────────────────────────────────────────────

    @keyword("Create IP Group")
    def create_ip_group(self, group_id: str, ip_addresses: list[str], domain: str = "default") -> None:
        """Create a group whose membership is a static set of IP addresses/CIDRs."""
        body = {
            "display_name": group_id,
            "expression": [{"resource_type": "IPAddressExpression", "ip_addresses": ip_addresses}],
        }
        self._connections.current.patch(f"{INFRA_BASE}/domains/{domain}/groups/{group_id}", body)

    @keyword("Create Tag Group")
    def create_tag_group(self, group_id: str, scope_value: str, domain: str = "default") -> None:
        """Create a group with dynamic membership.

        VMs carrying the tag ``scope_value`` (a ``scope|value`` string, e.g.
        ``app|web``) join the group.
        """
        body = {
            "display_name": group_id,
            "expression": [
                {
                    "resource_type": "Condition",
                    "member_type": "VirtualMachine",
                    "key": "Tag",
                    "operator": "EQUALS",
                    "value": scope_value,
                }
            ],
        }
        self._connections.current.patch(f"{INFRA_BASE}/domains/{domain}/groups/{group_id}", body)

    @keyword("Get Group")
    def get_group(self, group_id: str, domain: str = "default") -> Any:
        """Retrieve a group definition by ID."""
        return self._connections.current.get(f"{INFRA_BASE}/domains/{domain}/groups/{group_id}")

    @keyword("Get Group Members")
    def get_group_members(self, group_id: str, domain: str = "default") -> Any:
        """Retrieve the effective (realized) VM members of a group."""
        return self._connections.current.get(
            f"{INFRA_BASE}/domains/{domain}/groups/{group_id}/members/virtual-machines"
        )

    @keyword("Delete Group")
    def delete_group(self, group_id: str, domain: str = "default") -> None:
        """Delete a group by ID."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/domains/{domain}/groups/{group_id}")

    # ── Distributed Firewall (DFW) ───────────────────────────────────────

    @keyword("Create Security Policy")
    def create_security_policy(
        self, policy_id: str, sequence_number: str = "10", category: str = "Application", domain: str = "default"
    ) -> None:
        """Create (or update) an empty DFW security policy in a domain.

        Lower ``sequence_number`` values are evaluated first relative to
        other policies.
        """
        body = {"display_name": policy_id, "category": category, "sequence_number": sequence_number}
        self._connections.current.patch(f"{INFRA_BASE}/domains/{domain}/security-policies/{policy_id}", body)

    @keyword("Create DFW Rule")
    def create_dfw_rule(
        self,
        policy_id: str,
        rule_id: str,
        source_groups: list[str],
        destination_groups: list[str],
        action: str = "ALLOW",
        services: list[str] | None = None,
        sequence_number: str = "10",
        domain: str = "default",
    ) -> None:
        """Create a distributed firewall rule inside a security policy.

        ``action`` is ALLOW, DROP, or REJECT. ``source_groups``/
        ``destination_groups``/``services`` are lists of Policy paths (or
        ``["ANY"]``).
        """
        body = {
            "display_name": rule_id,
            "source_groups": source_groups,
            "destination_groups": destination_groups,
            "services": services if services is not None else ["ANY"],
            "action": action,
            "direction": "IN_OUT",
            "ip_protocol": "IPV4_IPV6",
            "sequence_number": sequence_number,
        }
        self._connections.current.patch(
            f"{INFRA_BASE}/domains/{domain}/security-policies/{policy_id}/rules/{rule_id}", body
        )

    @keyword("Get DFW Rules")
    def get_dfw_rules(self, policy_id: str, domain: str = "default") -> Any:
        """List the rules of a security policy."""
        return self._connections.current.get(f"{INFRA_BASE}/domains/{domain}/security-policies/{policy_id}/rules")

    @keyword("Delete DFW Rule")
    def delete_dfw_rule(self, policy_id: str, rule_id: str, domain: str = "default") -> None:
        """Delete a single DFW rule from a security policy."""
        self.nsx_rest_delete_ignore_error(
            f"{INFRA_BASE}/domains/{domain}/security-policies/{policy_id}/rules/{rule_id}"
        )

    @keyword("Delete Security Policy")
    def delete_security_policy(self, policy_id: str, domain: str = "default") -> None:
        """Delete a security policy (and all its rules) by ID."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/domains/{domain}/security-policies/{policy_id}")
