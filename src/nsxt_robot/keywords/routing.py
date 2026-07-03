"""Routing keywords: static routes (T1/T0), BFD, BGP, and EVPN."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from robot.api.deco import keyword

from ..connections import NsxtConnectionManager
from .paths import INFRA_BASE, POLICY_BASE


class RoutingKeywords:
    """Mixin providing static-route/BFD/BGP/EVPN keywords.

    Requires ``self._connections`` and ``nsx_rest_delete_ignore_error`` from
    :class:`~nsxt_robot.keywords.rest.RestKeywords` (composed by ``NsxtLibrary``).
    """

    _connections: NsxtConnectionManager
    nsx_rest_delete_ignore_error: Callable[[str], None]

    # ── Static Routes: T1 ────────────────────────────────────────────────

    @keyword("Create Static Route On T1")
    def create_static_route_on_t1(self, t1_id: str, route_id: str, network: str, next_hop: str) -> None:
        """Add a static route to a Tier-1 gateway."""
        body = {
            "display_name": route_id,
            "network": network,
            "next_hops": [{"ip_address": next_hop}],
        }
        self._connections.current.patch(f"{INFRA_BASE}/tier-1s/{t1_id}/static-routes/{route_id}", body)

    @keyword("Delete Static Route On T1")
    def delete_static_route_on_t1(self, t1_id: str, route_id: str) -> None:
        """Delete a static route from a Tier-1 gateway."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/tier-1s/{t1_id}/static-routes/{route_id}")

    @keyword("Get Static Routes On T1")
    def get_static_routes_on_t1(self, t1_id: str) -> Any:
        """List all static routes on a Tier-1 gateway."""
        return self._connections.current.get(f"{INFRA_BASE}/tier-1s/{t1_id}/static-routes")

    # ── Static Routes: T0 ────────────────────────────────────────────────

    @keyword("Create Static Route On T0")
    def create_static_route_on_t0(self, t0_id: str, route_id: str, network: str, next_hop: str) -> None:
        """Add a static route to a T0 or T0-VRF gateway."""
        body = {
            "display_name": route_id,
            "network": network,
            "next_hops": [{"ip_address": next_hop}],
        }
        self._connections.current.patch(f"{INFRA_BASE}/tier-0s/{t0_id}/static-routes/{route_id}", body)

    @keyword("Delete Static Route On T0")
    def delete_static_route_on_t0(self, t0_id: str, route_id: str) -> None:
        """Delete a static route from a T0 or T0-VRF gateway."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/tier-0s/{t0_id}/static-routes/{route_id}")

    @keyword("Get Static Routes On T0")
    def get_static_routes_on_t0(self, t0_id: str) -> Any:
        """List all static routes on a T0 or T0-VRF gateway."""
        return self._connections.current.get(f"{INFRA_BASE}/tier-0s/{t0_id}/static-routes")

    # ── BFD ──────────────────────────────────────────────────────────────

    @keyword("Create BFD Profile")
    def create_bfd_profile(self, id: str, interval: str = "500", multiple: str = "3") -> None:
        """Create a reusable BFD profile (``/infra/bfd-profiles``).

        ``interval`` is the transmit/receive interval in milliseconds;
        ``multiple`` the declare-dead multiplier.
        """
        body = {"display_name": id, "interval": int(interval), "multiple": int(multiple)}
        self._connections.current.patch(f"{INFRA_BASE}/bfd-profiles/{id}", body)

    @keyword("Delete BFD Profile")
    def delete_bfd_profile(self, id: str) -> None:
        """Delete a BFD profile."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/bfd-profiles/{id}")

    @keyword("Create Static Route BFD Peer On T0")
    def create_static_route_bfd_peer_on_t0(
        self, t0_id: str, peer_id: str, peer_ip: str, bfd_profile_path: str = ""
    ) -> None:
        """Create a BFD peer for static routes on a T0 or T0-VRF gateway.

        Static routes via ``peer_ip`` are withdrawn when the BFD session
        goes down.
        """
        body: dict[str, Any] = {"display_name": peer_id, "peer_address": peer_ip, "enabled": True}
        if bfd_profile_path:
            body["bfd_profile_path"] = bfd_profile_path
        self._connections.current.patch(
            f"{INFRA_BASE}/tier-0s/{t0_id}/static-routes/bfd-peers/{peer_id}", body
        )

    @keyword("Delete Static Route BFD Peer On T0")
    def delete_static_route_bfd_peer_on_t0(self, t0_id: str, peer_id: str) -> None:
        """Delete a static-route BFD peer from a T0 or T0-VRF gateway."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/tier-0s/{t0_id}/static-routes/bfd-peers/{peer_id}")

    # ── BGP ──────────────────────────────────────────────────────────────

    @keyword("Enable BGP On T0 Locale Service")
    def enable_bgp_on_t0_locale_service(self, t0_id: str, locale_service_id: str = "default") -> None:
        """Enable BGP on a T0/T0-VRF locale service without setting an ASN.

        Use this for VRF gateways, which inherit the local ASN from the
        parent T0 (setting ``local_as_num`` on a VRF is rejected); use
        ``Configure BGP On T0`` for a parent/standalone T0 where the ASN
        must be set.
        """
        self._connections.current.patch(
            f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{locale_service_id}/bgp", {"enabled": True}
        )

    @keyword("Configure BGP On T0")
    def configure_bgp_on_t0(self, t0_id: str, locale_service_id: str, local_asn: str) -> None:
        """Enable BGP and set local ASN on a T0 gateway locale service."""
        body = {"local_as_num": local_asn, "enabled": True}
        self._connections.current.patch(
            f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{locale_service_id}/bgp", body
        )

    @keyword("Create BGP Neighbor On T0")
    def create_bgp_neighbor_on_t0(
        self,
        t0_id: str,
        locale_service_id: str,
        neighbor_id: str,
        peer_ip: str,
        remote_asn: str,
        bfd_enabled: bool = True,
        bfd_interval: str = "500",
        bfd_multiplier: str = "3",
    ) -> None:
        """Create a BGP neighbor entry on a T0 gateway with optional BFD."""
        body = {
            "display_name": neighbor_id,
            "neighbor_address": peer_ip,
            "remote_as_num": remote_asn,
            "bfd_config": {
                "enabled": bfd_enabled,
                "interval": bfd_interval,
                "multiple": bfd_multiplier,
            },
        }
        self._connections.current.patch(
            f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{locale_service_id}/bgp/neighbors/{neighbor_id}",
            body,
        )

    @keyword("Get BGP Neighbor Status")
    def get_bgp_neighbor_status(self, t0_id: str, locale_service_id: str, neighbor_id: str) -> Any:
        """Retrieve BGP neighbor operational status."""
        return self._connections.current.get(
            f"{POLICY_BASE}/infra/tier-0s/{t0_id}/locale-services/{locale_service_id}"
            f"/bgp/neighbors/{neighbor_id}/status"
        )

    @keyword("Delete BGP Neighbor On T0")
    def delete_bgp_neighbor_on_t0(self, t0_id: str, locale_service_id: str, neighbor_id: str) -> None:
        """Delete a BGP neighbor from a T0 gateway."""
        self.nsx_rest_delete_ignore_error(
            f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{locale_service_id}/bgp/neighbors/{neighbor_id}"
        )

    @keyword("Get BGP Routes On T0")
    def get_bgp_routes_on_t0(self, t0_id: str, locale_service_id: str, neighbor_id: str) -> Any:
        """Retrieve BGP routes learned from a specific neighbor on the T0 gateway.

        Routes are reported per neighbor, not for the gateway as a whole.
        """
        return self._connections.current.get(
            f"{POLICY_BASE}/infra/tier-0s/{t0_id}/locale-services/{locale_service_id}"
            f"/bgp/neighbors/{neighbor_id}/routes"
        )

    # ── EVPN (NSX 3.1+ / 4.x) ────────────────────────────────────────────
    # Field names follow the NSX 4.x EvpnConfig/VniPoolConfig schemas. EVPN
    # endpoints are the most version-sensitive part of the Policy API —
    # verify against your release's API reference before the first live run.

    @keyword("Create VNI Pool")
    def create_vni_pool(self, id: str, start: str, end: str) -> None:
        """Create a VNI pool (``/infra/vni-pools``) for EVPN VXLAN encapsulation.

        VRF ``evpn_transit_vni`` values must fall inside ``[start, end]``.
        """
        body = {"display_name": id, "start": int(start), "end": int(end)}
        self._connections.current.patch(f"{INFRA_BASE}/vni-pools/{id}", body)

    @keyword("Delete VNI Pool")
    def delete_vni_pool(self, id: str) -> None:
        """Delete a VNI pool."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/vni-pools/{id}")

    @keyword("Configure EVPN On T0")
    def configure_evpn_on_t0(self, t0_id: str, mode: str = "INLINE", vni_pool_path: str = "") -> None:
        """Enable EVPN on a parent T0 gateway.

        ``mode`` is ``INLINE`` or ``ROUTE_SERVER``; ``vni_pool_path``
        selects the VXLAN VNI pool used for the per-VRF transit VNIs
        (required for INLINE mode).
        """
        body: dict[str, Any] = {"mode": mode}
        if vni_pool_path:
            body["encapsulation_method"] = {
                "encapsulation_type": "VXLAN",
                "vni_pool_path": vni_pool_path,
            }
        self._connections.current.patch(f"{INFRA_BASE}/tier-0s/{t0_id}/evpn", body)

    @keyword("Get EVPN Config On T0")
    def get_evpn_config_on_t0(self, t0_id: str) -> Any:
        """Retrieve the EVPN configuration of a T0 gateway."""
        return self._connections.current.get(f"{INFRA_BASE}/tier-0s/{t0_id}/evpn")

    @keyword("Create EVPN Tunnel Endpoint On T0")
    def create_evpn_tunnel_endpoint_on_t0(
        self, t0_id: str, ls_id: str, te_id: str, edge_path: str, local_address: str, mtu: str = ""
    ) -> None:
        """Create an EVPN (VXLAN) tunnel endpoint on a T0 locale service.

        Pinned to an edge node. ``local_address`` is the VTEP loopback IP
        advertised to the DC gateways.
        """
        body: dict[str, Any] = {
            "display_name": te_id,
            "edge_path": edge_path,
            "local_addresses": [local_address],
        }
        if mtu:
            body["mtu"] = int(mtu)
        self._connections.current.patch(
            f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{ls_id}/evpn-tunnel-endpoints/{te_id}", body
        )

    @keyword("Delete EVPN Tunnel Endpoint On T0")
    def delete_evpn_tunnel_endpoint_on_t0(self, t0_id: str, ls_id: str, te_id: str) -> None:
        """Delete an EVPN tunnel endpoint from a T0 locale service."""
        self.nsx_rest_delete_ignore_error(
            f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{ls_id}/evpn-tunnel-endpoints/{te_id}"
        )
