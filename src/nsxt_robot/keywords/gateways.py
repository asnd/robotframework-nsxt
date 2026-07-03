"""Gateway topology keywords: T1 gateways, segments, T0/VRF gateways, locale
services, and external interfaces.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from robot.api.deco import keyword

from ..connections import NsxtConnectionManager
from .paths import INFRA_BASE


class GatewayKeywords:
    """Mixin providing T1/T0/VRF/segment keywords.

    Requires ``self._connections`` and the ``nsx_rest_delete_ignore_error``
    keyword from :class:`~nsxt_robot.keywords.rest.RestKeywords` (both are
    provided by the composed ``NsxtLibrary``).
    """

    _connections: NsxtConnectionManager
    nsx_rest_delete_ignore_error: Callable[[str], None]

    # ── T1 Gateways ──────────────────────────────────────────────────────

    @keyword("Create T1 Gateway")
    def create_t1_gateway(
        self, id: str, display_name: str, t0_path: str, *route_adv_types: str
    ) -> None:
        """Create or update a Tier-1 gateway linked to T0.

        ``route_adv_types`` accepts values such as ``TIER1_CONNECTED``,
        ``TIER1_STATIC_ROUTES``.
        """
        body = {
            "display_name": display_name,
            "tier0_path": t0_path,
            "route_advertisement_types": list(route_adv_types) or ["TIER1_CONNECTED"],
        }
        self._connections.current.patch(f"{INFRA_BASE}/tier-1s/{id}", body)

    @keyword("Delete T1 Gateway")
    def delete_t1_gateway(self, id: str) -> None:
        """Delete a Tier-1 gateway."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/tier-1s/{id}")

    @keyword("Get T1 Gateway")
    def get_t1_gateway(self, id: str) -> Any:
        """Retrieve a Tier-1 gateway by ID."""
        return self._connections.current.get(f"{INFRA_BASE}/tier-1s/{id}")

    # ── Segments ─────────────────────────────────────────────────────────

    @keyword("Create Overlay Segment")
    def create_overlay_segment(self, id: str, t1_path: str, tz_path: str, subnet_cidr: str) -> None:
        """Create an overlay segment attached to a T1 gateway."""
        body = {
            "display_name": id,
            "connectivity_path": t1_path,
            "transport_zone_path": tz_path,
            "subnets": [{"gateway_address": subnet_cidr}],
        }
        self._connections.current.patch(f"{INFRA_BASE}/segments/{id}", body)

    @keyword("Create VLAN Segment")
    def create_vlan_segment(self, id: str, tz_path: str, *vlan_ids: str) -> None:
        """Create a VLAN-backed segment on a VLAN transport zone.

        Used for T0/VRF external (uplink) interfaces. ``vlan_ids`` is one or
        more VLAN IDs.
        """
        body = {
            "display_name": id,
            "transport_zone_path": tz_path,
            "vlan_ids": list(vlan_ids),
        }
        self._connections.current.patch(f"{INFRA_BASE}/segments/{id}", body)

    @keyword("Delete Segment")
    def delete_segment(self, id: str) -> None:
        """Delete a segment by ID."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/segments/{id}")

    @keyword("Get Segment")
    def get_segment(self, id: str) -> Any:
        """Retrieve a segment by ID."""
        return self._connections.current.get(f"{INFRA_BASE}/segments/{id}")

    # ── T0 Gateways / VRF ────────────────────────────────────────────────

    @keyword("Get T0 Gateway")
    def get_t0_gateway(self, id: str) -> Any:
        """Retrieve a Tier-0 gateway (or a T0-VRF gateway) by ID."""
        return self._connections.current.get(f"{INFRA_BASE}/tier-0s/{id}")

    @keyword("Create VRF Gateway On T0")
    def create_vrf_gateway_on_t0(
        self,
        vrf_id: str,
        display_name: str,
        parent_t0_path: str,
        route_distinguisher: str = "",
        evpn_transit_vni: str = "",
        import_rts: Any = "",
        export_rts: Any = "",
    ) -> None:
        """Create (or update) a Tier-0 VRF gateway linked to a parent T0.

        A VRF is itself a tier-0 object, so every "... On T0" keyword (BGP,
        static routes, interfaces, locale services) also works against
        ``vrf_id``. The EVPN fields are optional: ``route_distinguisher``
        (e.g. ``65001:100``), ``import_rts``/``export_rts`` (lists of
        ``ASN:nn`` route targets, L2VPN_EVPN address family), and
        ``evpn_transit_vni`` (must belong to the parent's VNI pool). Plain
        VRF-lite needs only ``parent_t0_path``.
        """
        vrf_config: dict[str, Any] = {"tier0_path": parent_t0_path}
        if route_distinguisher:
            vrf_config["route_distinguisher"] = route_distinguisher
        if import_rts or export_rts:
            route_target: dict[str, Any] = {"address_family": "L2VPN_EVPN"}
            if import_rts:
                route_target["import_route_targets"] = import_rts
            if export_rts:
                route_target["export_route_targets"] = export_rts
            vrf_config["route_targets"] = [route_target]
        if evpn_transit_vni:
            vrf_config["evpn_transit_vni"] = int(evpn_transit_vni)
        body = {"display_name": display_name, "vrf_config": vrf_config}
        self._connections.current.patch(f"{INFRA_BASE}/tier-0s/{vrf_id}", body)

    @keyword("Delete VRF Gateway")
    def delete_vrf_gateway(self, vrf_id: str) -> None:
        """Delete a Tier-0 VRF gateway by ID."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/tier-0s/{vrf_id}")

    # ── T0 Locale Services / Interfaces ──────────────────────────────────

    @keyword("Create T0 Locale Service")
    def create_t0_locale_service(
        self, t0_id: str, ls_id: str = "default", edge_cluster_path: str = ""
    ) -> None:
        """Create (or update) a locale service on a T0 or T0-VRF gateway.

        ``edge_cluster_path`` is optional for a VRF (it inherits the
        parent's edge cluster) but required for a standalone T0.
        """
        body: dict[str, Any] = {"display_name": ls_id}
        if edge_cluster_path:
            body["edge_cluster_path"] = edge_cluster_path
        self._connections.current.patch(f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{ls_id}", body)

    @keyword("Delete T0 Locale Service")
    def delete_t0_locale_service(self, t0_id: str, ls_id: str = "default") -> None:
        """Delete a locale service from a T0 or T0-VRF gateway."""
        self.nsx_rest_delete_ignore_error(f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{ls_id}")

    @keyword("Create T0 External Interface")
    def create_t0_external_interface(
        self,
        t0_id: str,
        ls_id: str,
        if_id: str,
        segment_path: str,
        ip_address: str,
        prefix_len: str,
        edge_path: str = "",
        mtu: str = "",
    ) -> None:
        """Create an EXTERNAL (uplink) interface on a T0 or T0-VRF locale service.

        Attached to a VLAN segment. ``edge_path`` pins the interface to a
        specific edge node (required for EXTERNAL interfaces).
        """
        body: dict[str, Any] = {
            "display_name": if_id,
            "type": "EXTERNAL",
            "segment_path": segment_path,
            "subnets": [{"ip_addresses": [ip_address], "prefix_len": int(prefix_len)}],
        }
        if edge_path:
            body["edge_path"] = edge_path
        if mtu:
            body["mtu"] = int(mtu)
        self._connections.current.patch(
            f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{ls_id}/interfaces/{if_id}", body
        )

    @keyword("Get T0 Interfaces")
    def get_t0_interfaces(self, t0_id: str, ls_id: str = "default") -> Any:
        """List the interfaces of a T0 (or T0-VRF) locale service."""
        return self._connections.current.get(
            f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{ls_id}/interfaces"
        )

    @keyword("Delete T0 Interface")
    def delete_t0_interface(self, t0_id: str, ls_id: str, if_id: str) -> None:
        """Delete an interface from a T0 (or T0-VRF) locale service."""
        self.nsx_rest_delete_ignore_error(
            f"{INFRA_BASE}/tier-0s/{t0_id}/locale-services/{ls_id}/interfaces/{if_id}"
        )
