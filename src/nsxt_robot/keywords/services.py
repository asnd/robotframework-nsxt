"""Service keywords: NAT, load balancer (NSX LB), and HA VIP."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from robot.api.deco import keyword

from ..connections import NsxtConnectionManager
from .paths import INFRA_BASE, POLICY_BASE


class ServiceKeywords:
    """Mixin providing NAT/LB/HA-VIP keywords.

    Requires ``self._connections`` and ``nsx_rest_delete_ignore_error`` from
    :class:`~nsxt_robot.keywords.rest.RestKeywords` (composed by ``NsxtLibrary``).
    """

    _connections: NsxtConnectionManager
    nsx_rest_delete_ignore_error: Callable[[str], None]

    # ── NAT ──────────────────────────────────────────────────────────────

    @keyword("Create SNAT Rule On T1")
    def create_snat_rule_on_t1(self, t1_id: str, rule_id: str, translated_ip: str, source_network: str) -> None:
        """Create an SNAT rule on a Tier-1 gateway."""
        body = {
            "display_name": rule_id,
            "action": "SNAT",
            "translated_network": translated_ip,
            "source_network": source_network,
            "enabled": True,
            "logging": False,
        }
        self._connections.current.patch(f"{INFRA_BASE}/tier-1s/{t1_id}/nat/USER/nat-rules/{rule_id}", body)

    @keyword("Create DNAT Rule On T1")
    def create_dnat_rule_on_t1(
        self,
        t1_id: str,
        rule_id: str,
        destination_ip: str,
        translated_ip: str,
        translated_port: str = "",
    ) -> None:
        """Create a DNAT rule on a Tier-1 gateway.

        Inbound traffic to ``destination_ip`` is translated to the internal
        ``translated_ip``. An optional ``translated_port`` restricts the
        rule to a single service port.
        """
        body: dict[str, Any] = {
            "display_name": rule_id,
            "action": "DNAT",
            "destination_network": destination_ip,
            "translated_network": translated_ip,
            "enabled": True,
            "logging": False,
        }
        if translated_port:
            body["translated_ports"] = translated_port
        self._connections.current.patch(f"{INFRA_BASE}/tier-1s/{t1_id}/nat/USER/nat-rules/{rule_id}", body)

    @keyword("Delete NAT Rule On T1")
    def delete_nat_rule_on_t1(self, t1_id: str, rule_id: str) -> None:
        """Delete a NAT rule from a Tier-1 gateway."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/tier-1s/{t1_id}/nat/USER/nat-rules/{rule_id}")

    @keyword("Get NAT Rules On T1")
    def get_nat_rules_on_t1(self, t1_id: str) -> Any:
        """List all NAT rules on a Tier-1 gateway."""
        return self._connections.current.get(f"{INFRA_BASE}/tier-1s/{t1_id}/nat/USER/nat-rules")

    @keyword("Get NAT Statistics On T1")
    def get_nat_statistics_on_t1(self, t1_id: str) -> Any:
        """Retrieve NAT statistics for a Tier-1 gateway."""
        return self._connections.current.get(
            f"{POLICY_BASE}/infra/tier-1s/{t1_id}/nat/USER/nat-rules?action=statistics"
        )

    # ── Load Balancer (Basic NSX LB) ─────────────────────────────────────

    @keyword("Create LB Service")
    def create_lb_service(self, id: str, t1_path: str, size: str = "SMALL") -> None:
        """Create an NSX LB service attached to a T1 gateway."""
        body = {"display_name": id, "connectivity_path": t1_path, "size": size}
        self._connections.current.patch(f"{INFRA_BASE}/lb-services/{id}", body)

    @keyword("Create LB Pool")
    def create_lb_pool(self, id: str, members: list[str], port: str, monitor_path: str = "") -> None:
        """Create an NSX LB server pool with members.

        When ``monitor_path`` is provided the pool is bound to that active
        health monitor.
        """
        member_list = [{"display_name": ip, "ip_address": ip, "port": port} for ip in members]
        body: dict[str, Any] = {"display_name": id, "members": member_list}
        if monitor_path:
            body["active_monitor_paths"] = [monitor_path]
        self._connections.current.patch(f"{INFRA_BASE}/lb-pools/{id}", body)

    @keyword("Create LB HTTP Monitor")
    def create_lb_http_monitor(
        self,
        id: str,
        monitor_port: str,
        request_url: str = "/",
        response_codes: list[int] | None = None,
    ) -> None:
        """Create an active HTTP health monitor profile.

        The pool that binds it marks members UP only when they answer
        ``request_url`` with one of ``response_codes``.
        """
        body = {
            "resource_type": "LBHttpMonitorProfile",
            "display_name": id,
            "monitor_port": int(monitor_port),
            "request_url": request_url,
            "request_method": "GET",
            "response_status_codes": response_codes if response_codes is not None else [200],
        }
        self._connections.current.patch(f"{INFRA_BASE}/lb-monitor-profiles/{id}", body)

    @keyword("Delete LB Monitor")
    def delete_lb_monitor(self, id: str) -> None:
        """Delete an LB monitor profile."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/lb-monitor-profiles/{id}")

    @keyword("Create LB Virtual Server")
    def create_lb_virtual_server(self, id: str, pool_path: str, vip: str, port: str, lb_service_path: str) -> None:
        """Create an NSX LB virtual server (TCP/L4)."""
        body = {
            "display_name": id,
            "ip_address": vip,
            "ports": [port],
            "pool_path": pool_path,
            "lb_service_path": lb_service_path,
            "application_profile_path": "/infra/lb-app-profiles/default-tcp-lb-app-profile",
        }
        self._connections.current.patch(f"{INFRA_BASE}/lb-virtual-servers/{id}", body)

    @keyword("Create LB HTTP Virtual Server")
    def create_lb_http_virtual_server(
        self, id: str, pool_path: str, vip: str, port: str, lb_service_path: str
    ) -> None:
        """Create an NSX L7 HTTP virtual server.

        Uses the default HTTP application profile, so the LB terminates
        and proxies HTTP rather than forwarding raw TCP.
        """
        body = {
            "display_name": id,
            "ip_address": vip,
            "ports": [port],
            "pool_path": pool_path,
            "lb_service_path": lb_service_path,
            "application_profile_path": "/infra/lb-app-profiles/default-http-lb-app-profile",
        }
        self._connections.current.patch(f"{INFRA_BASE}/lb-virtual-servers/{id}", body)

    @keyword("Get LB Pool Status")
    def get_lb_pool_status(self, id: str, lb_service_id: str) -> Any:
        """Retrieve operational status of an LB pool."""
        return self._connections.current.get(
            f"{POLICY_BASE}/infra/lb-services/{lb_service_id}/lb-pools/{id}/status"
        )

    @keyword("Delete LB Virtual Server")
    def delete_lb_virtual_server(self, id: str) -> None:
        """Delete an LB virtual server."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/lb-virtual-servers/{id}")

    @keyword("Delete LB Pool")
    def delete_lb_pool(self, id: str) -> None:
        """Delete an LB pool."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/lb-pools/{id}")

    @keyword("Delete LB Service")
    def delete_lb_service(self, id: str) -> None:
        """Delete an LB service."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/lb-services/{id}")

    # ── HA VIP ───────────────────────────────────────────────────────────

    @keyword("Create HA VIP Config On T0")
    def create_ha_vip_config_on_t0(
        self, t0_id: str, locale_service_id: str, vip_ip: str, edge_path_1: str, edge_path_2: str
    ) -> None:
        """Configure an HA VIP on a T0 locale service."""
        address, prefix_len = vip_ip.split("/")
        vip_config = {
            "enabled": True,
            "vip_subnets": [{"prefix_len": prefix_len, "ip_addresses": [address]}],
            "external_interface_paths": [edge_path_1, edge_path_2],
        }
        body = {"ha_vip_configs": [vip_config]}
        self._connections.current.patch(f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{locale_service_id}", body)

    @keyword("Remove HA VIP Config On T0")
    def remove_ha_vip_config_on_t0(self, t0_id: str, locale_service_id: str) -> None:
        """Remove HA VIP configuration from a T0 locale service."""
        self._connections.current.patch(
            f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{locale_service_id}", {"ha_vip_configs": []}
        )

    @keyword("Get T0 Locale Service")
    def get_t0_locale_service(self, t0_id: str, locale_service_id: str) -> Any:
        """Retrieve the locale service config for a T0 gateway."""
        return self._connections.current.get(f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{locale_service_id}")
