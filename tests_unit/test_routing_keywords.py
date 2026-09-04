"""Unit tests for RoutingKeywords (static routes, BFD, BGP, EVPN)."""

from __future__ import annotations

from nsxt_robot.keywords.rest import RestKeywords
from nsxt_robot.keywords.routing import RoutingKeywords


class _Lib(RoutingKeywords, RestKeywords):
    def __init__(self, connections):
        self._connections = connections


def test_create_static_route_on_t1(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_static_route_on_t1("t1-a", "route-1", "10.99.0.0/24", "172.16.1.1")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-1s/t1-a/static-routes/route-1"
    assert body == {
        "display_name": "route-1",
        "network": "10.99.0.0/24",
        "next_hops": [{"ip_address": "172.16.1.1"}],
    }


def test_delete_static_route_on_t1(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_static_route_on_t1("t1-a", "route-1")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/tier-1s/t1-a/static-routes/route-1")


def test_get_static_routes_on_t1(spy_connections, spy_session):
    spy_session.when("/policy/api/v1/infra/tier-1s/t1-a/static-routes", {"results": []})
    lib = _Lib(spy_connections)
    assert lib.get_static_routes_on_t1("t1-a") == {"results": []}


def test_create_static_route_on_t0(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_static_route_on_t0("t0-gw", "route-1", "10.99.0.0/24", "192.168.100.1")
    _, path, _ = spy_session.last
    assert path == "/policy/api/v1/infra/tier-0s/t0-gw/static-routes/route-1"


def test_delete_static_route_on_t0(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_static_route_on_t0("t0-gw", "route-1")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/tier-0s/t0-gw/static-routes/route-1")


def test_get_static_routes_on_t0(spy_connections, spy_session):
    spy_session.when("/policy/api/v1/infra/tier-0s/t0-gw/static-routes", {"results": []})
    lib = _Lib(spy_connections)
    assert lib.get_static_routes_on_t0("t0-gw") == {"results": []}


def test_create_bfd_profile_default_interval(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_bfd_profile("bfd-1")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/bfd-profiles/bfd-1"
    assert body == {"display_name": "bfd-1", "interval": 500, "multiple": 3}


def test_create_bfd_profile_custom_interval(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_bfd_profile("bfd-1", interval="1000", multiple="5")
    _, _, body = spy_session.last
    assert body["interval"] == 1000
    assert body["multiple"] == 5


def test_delete_bfd_profile(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_bfd_profile("bfd-1")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/bfd-profiles/bfd-1")


def test_create_static_route_bfd_peer_without_profile(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_static_route_bfd_peer_on_t0("t0-gw", "peer-1", "192.168.100.1")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-0s/t0-gw/static-routes/bfd-peers/peer-1"
    assert body == {"display_name": "peer-1", "peer_address": "192.168.100.1", "enabled": True}


def test_create_static_route_bfd_peer_with_profile(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_static_route_bfd_peer_on_t0(
        "t0-gw", "peer-1", "192.168.100.1", bfd_profile_path="/infra/bfd-profiles/bfd-1"
    )
    _, _, body = spy_session.last
    assert body["bfd_profile_path"] == "/infra/bfd-profiles/bfd-1"


def test_delete_static_route_bfd_peer_on_t0(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_static_route_bfd_peer_on_t0("t0-gw", "peer-1")
    assert spy_session.last[:2] == (
        "DELETE",
        "/policy/api/v1/infra/tier-0s/t0-gw/static-routes/bfd-peers/peer-1",
    )


def test_enable_bgp_on_t0_locale_service(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.enable_bgp_on_t0_locale_service("vrf-red")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-0s/vrf-red/locale-services/default/bgp"
    assert body == {"enabled": True}
    assert "local_as_num" not in body


def test_configure_bgp_on_t0_sets_asn(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.configure_bgp_on_t0("t0-gw", "default", "65001")
    _, _, body = spy_session.last
    assert body == {"local_as_num": "65001", "enabled": True}


def test_create_bgp_neighbor_on_t0(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_bgp_neighbor_on_t0("t0-gw", "default", "neighbor-1", "192.0.2.1", "65000")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp/neighbors/neighbor-1"
    assert body["neighbor_address"] == "192.0.2.1"
    assert body["remote_as_num"] == "65000"
    assert body["bfd_config"] == {"enabled": True, "interval": "500", "multiple": "3"}


def test_get_bgp_neighbor_status(spy_connections, spy_session):
    spy_session.when(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp/neighbors/n1/status",
        {"connection_state": "ESTABLISHED"},
    )
    lib = _Lib(spy_connections)
    assert lib.get_bgp_neighbor_status("t0-gw", "default", "n1") == {"connection_state": "ESTABLISHED"}


def test_delete_bgp_neighbor_on_t0(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_bgp_neighbor_on_t0("t0-gw", "default", "n1")
    assert spy_session.last[:2] == (
        "DELETE",
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp/neighbors/n1",
    )


def test_get_bgp_routes_on_t0(spy_connections, spy_session):
    spy_session.when(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp/neighbors/n1/routes",
        {"results": []},
    )
    lib = _Lib(spy_connections)
    assert lib.get_bgp_routes_on_t0("t0-gw", "default", "n1") == {"results": []}


def test_create_vni_pool(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_vni_pool("vni-1", "75001", "75100")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/vni-pools/vni-1"
    assert body == {"display_name": "vni-1", "start": 75001, "end": 75100}


def test_delete_vni_pool(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_vni_pool("vni-1")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/vni-pools/vni-1")


def test_configure_evpn_on_t0_inline_mode(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.configure_evpn_on_t0("t0-gw", vni_pool_path="/infra/vni-pools/vni-1")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-0s/t0-gw/evpn"
    assert body == {
        "mode": "INLINE",
        "encapsulation_method": {"encapsulation_type": "VXLAN", "vni_pool_path": "/infra/vni-pools/vni-1"},
    }


def test_configure_evpn_on_t0_without_vni_pool(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.configure_evpn_on_t0("t0-gw")
    _, _, body = spy_session.last
    assert body == {"mode": "INLINE"}


def test_get_evpn_config_on_t0(spy_connections, spy_session):
    spy_session.when("/policy/api/v1/infra/tier-0s/t0-gw/evpn", {"mode": "INLINE"})
    lib = _Lib(spy_connections)
    assert lib.get_evpn_config_on_t0("t0-gw") == {"mode": "INLINE"}


def test_create_evpn_tunnel_endpoint_on_t0(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_evpn_tunnel_endpoint_on_t0("t0-gw", "default", "te-1", "/infra/.../edge-node-1", "10.10.10.1")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/evpn-tunnel-endpoints/te-1"
    assert body["local_addresses"] == ["10.10.10.1"]
    assert "mtu" not in body


def test_delete_evpn_tunnel_endpoint_on_t0(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_evpn_tunnel_endpoint_on_t0("t0-gw", "default", "te-1")
    assert spy_session.last[:2] == (
        "DELETE",
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/evpn-tunnel-endpoints/te-1",
    )
