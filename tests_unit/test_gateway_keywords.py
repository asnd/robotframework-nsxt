"""Unit tests for GatewayKeywords (T1/T0/VRF gateways, segments, interfaces)."""

from __future__ import annotations

from nsxt_robot.keywords.gateways import GatewayKeywords
from nsxt_robot.keywords.rest import RestKeywords


class _Lib(GatewayKeywords, RestKeywords):
    def __init__(self, connections):
        self._connections = connections


def test_create_t1_gateway_default_advertisement(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_t1_gateway("t1-a", "T1-A", "/infra/tier-0s/t0-gw")
    method, path, body = spy_session.last
    assert (method, path) == ("PATCH", "/policy/api/v1/infra/tier-1s/t1-a")
    assert body == {
        "display_name": "T1-A",
        "tier0_path": "/infra/tier-0s/t0-gw",
        "route_advertisement_types": ["TIER1_CONNECTED"],
    }


def test_create_t1_gateway_explicit_advertisement_types(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_t1_gateway("t1-a", "T1-A", "/infra/tier-0s/t0-gw", "TIER1_STATIC_ROUTES")
    _, _, body = spy_session.last
    assert body["route_advertisement_types"] == ["TIER1_STATIC_ROUTES"]


def test_delete_t1_gateway(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_t1_gateway("t1-a")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/tier-1s/t1-a")


def test_get_t1_gateway(spy_connections, spy_session):
    spy_session.when("/policy/api/v1/infra/tier-1s/t1-a", {"id": "t1-a"})
    lib = _Lib(spy_connections)
    assert lib.get_t1_gateway("t1-a") == {"id": "t1-a"}


def test_create_overlay_segment(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_overlay_segment("seg-a", "/infra/tier-1s/t1-a", "/infra/.../overlay-tz", "172.16.1.1/24")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/segments/seg-a"
    assert body["subnets"] == [{"gateway_address": "172.16.1.1/24"}]
    assert body["connectivity_path"] == "/infra/tier-1s/t1-a"


def test_create_vlan_segment_multiple_vlans(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_vlan_segment("seg-vlan", "/infra/.../vlan-tz", "100", "200")
    _, _, body = spy_session.last
    assert body["vlan_ids"] == ["100", "200"]


def test_delete_segment(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_segment("seg-a")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/segments/seg-a")


def test_get_segment(spy_connections, spy_session):
    spy_session.when("/policy/api/v1/infra/segments/seg-a", {"id": "seg-a"})
    lib = _Lib(spy_connections)
    assert lib.get_segment("seg-a") == {"id": "seg-a"}


def test_get_t0_gateway(spy_connections, spy_session):
    spy_session.when("/policy/api/v1/infra/tier-0s/t0-gw", {"id": "t0-gw"})
    lib = _Lib(spy_connections)
    assert lib.get_t0_gateway("t0-gw") == {"id": "t0-gw"}


def test_create_vrf_gateway_plain_vrf_lite(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_vrf_gateway_on_t0("vrf-red", "VRF-Red", "/infra/tier-0s/t0-gw")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-0s/vrf-red"
    assert body == {"display_name": "VRF-Red", "vrf_config": {"tier0_path": "/infra/tier-0s/t0-gw"}}


def test_create_vrf_gateway_with_evpn_fields(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_vrf_gateway_on_t0(
        "vrf-red",
        "VRF-Red",
        "/infra/tier-0s/t0-gw",
        route_distinguisher="65001:100",
        evpn_transit_vni="75001",
        import_rts=["65001:100"],
        export_rts=["65001:100"],
    )
    _, _, body = spy_session.last
    vrf_config = body["vrf_config"]
    assert vrf_config["route_distinguisher"] == "65001:100"
    assert vrf_config["evpn_transit_vni"] == 75001
    assert vrf_config["route_targets"] == [
        {
            "address_family": "L2VPN_EVPN",
            "import_route_targets": ["65001:100"],
            "export_route_targets": ["65001:100"],
        }
    ]


def test_delete_vrf_gateway(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_vrf_gateway("vrf-red")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/tier-0s/vrf-red")


def test_create_t0_locale_service_without_edge_cluster(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_t0_locale_service("vrf-red")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-0s/vrf-red/locale-services/default"
    assert body == {"display_name": "default"}


def test_create_t0_locale_service_with_edge_cluster(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_t0_locale_service("t0-gw", edge_cluster_path="/infra/.../edge-cluster-1")
    _, _, body = spy_session.last
    assert body["edge_cluster_path"] == "/infra/.../edge-cluster-1"


def test_delete_t0_locale_service(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_t0_locale_service("t0-gw", "default")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default")


def test_create_t0_external_interface_minimal(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_t0_external_interface("t0-gw", "default", "if-1", "/infra/segments/vlan-seg", "10.0.0.1", "24")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/interfaces/if-1"
    assert body["type"] == "EXTERNAL"
    assert body["subnets"] == [{"ip_addresses": ["10.0.0.1"], "prefix_len": 24}]
    assert "edge_path" not in body
    assert "mtu" not in body


def test_create_t0_external_interface_with_edge_path_and_mtu(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_t0_external_interface(
        "t0-gw", "default", "if-1", "/infra/segments/vlan-seg", "10.0.0.1", "24",
        edge_path="/infra/.../edge-node-1", mtu="9000",
    )
    _, _, body = spy_session.last
    assert body["edge_path"] == "/infra/.../edge-node-1"
    assert body["mtu"] == 9000


def test_get_t0_interfaces(spy_connections, spy_session):
    spy_session.when(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/interfaces",
        {"results": [{"id": "if-1"}]},
    )
    lib = _Lib(spy_connections)
    assert lib.get_t0_interfaces("t0-gw") == {"results": [{"id": "if-1"}]}


def test_delete_t0_interface(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_t0_interface("t0-gw", "default", "if-1")
    assert spy_session.last[:2] == (
        "DELETE",
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/interfaces/if-1",
    )
