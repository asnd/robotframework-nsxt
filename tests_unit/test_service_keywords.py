"""Unit tests for ServiceKeywords (NAT, LB, HA VIP)."""

from __future__ import annotations

from nsxt_robot.keywords.rest import RestKeywords
from nsxt_robot.keywords.services import ServiceKeywords


class _Lib(ServiceKeywords, RestKeywords):
    def __init__(self, connections):
        self._connections = connections


def test_create_snat_rule_on_t1(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_snat_rule_on_t1("t1-a", "snat-1", "192.0.2.50", "172.16.1.0/24")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-1s/t1-a/nat/USER/nat-rules/snat-1"
    assert body["action"] == "SNAT"
    assert body["translated_network"] == "192.0.2.50"
    assert body["source_network"] == "172.16.1.0/24"


def test_create_dnat_rule_on_t1_without_port(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_dnat_rule_on_t1("t1-a", "dnat-1", "192.0.2.51", "172.16.1.10")
    _, _, body = spy_session.last
    assert body["action"] == "DNAT"
    assert body["destination_network"] == "192.0.2.51"
    assert body["translated_network"] == "172.16.1.10"
    assert "translated_ports" not in body


def test_create_dnat_rule_on_t1_with_port(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_dnat_rule_on_t1("t1-a", "dnat-1", "192.0.2.51", "172.16.1.10", translated_port="8080")
    _, _, body = spy_session.last
    assert body["translated_ports"] == "8080"


def test_delete_nat_rule_on_t1(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_nat_rule_on_t1("t1-a", "snat-1")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/tier-1s/t1-a/nat/USER/nat-rules/snat-1")


def test_get_nat_rules_on_t1(spy_connections, spy_session):
    spy_session.when("/policy/api/v1/infra/tier-1s/t1-a/nat/USER/nat-rules", {"results": []})
    lib = _Lib(spy_connections)
    assert lib.get_nat_rules_on_t1("t1-a") == {"results": []}


def test_get_nat_statistics_on_t1(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.get_nat_statistics_on_t1("t1-a")
    method, path, _ = spy_session.last
    assert method == "GET"
    assert path == "/policy/api/v1/infra/tier-1s/t1-a/nat/USER/nat-rules?action=statistics"


def test_create_lb_service(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_lb_service("lb-1", "/infra/tier-1s/t1-a")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/lb-services/lb-1"
    assert body == {"display_name": "lb-1", "connectivity_path": "/infra/tier-1s/t1-a", "size": "SMALL"}


def test_create_lb_pool_with_monitor(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_lb_pool("pool-1", ["172.16.1.10"], "8080", monitor_path="/infra/lb-monitor-profiles/mon-1")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/lb-pools/pool-1"
    assert body["members"] == [{"display_name": "172.16.1.10", "ip_address": "172.16.1.10", "port": "8080"}]
    assert body["active_monitor_paths"] == ["/infra/lb-monitor-profiles/mon-1"]


def test_create_lb_pool_without_monitor(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_lb_pool("pool-1", ["172.16.1.10"], "8080")
    _, _, body = spy_session.last
    assert "active_monitor_paths" not in body


def test_create_lb_http_monitor_defaults(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_lb_http_monitor("mon-1", "8080")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/lb-monitor-profiles/mon-1"
    assert body["resource_type"] == "LBHttpMonitorProfile"
    assert body["monitor_port"] == 8080
    assert body["request_url"] == "/"
    assert body["response_status_codes"] == [200]


def test_delete_lb_monitor(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_lb_monitor("mon-1")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/lb-monitor-profiles/mon-1")


def test_create_lb_virtual_server_tcp_profile(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_lb_virtual_server("vs-1", "/infra/lb-pools/pool-1", "192.0.2.60", "80", "/infra/lb-services/lb-1")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/lb-virtual-servers/vs-1"
    assert body["application_profile_path"] == "/infra/lb-app-profiles/default-tcp-lb-app-profile"
    assert body["ports"] == ["80"]


def test_create_lb_http_virtual_server_http_profile(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_lb_http_virtual_server(
        "vs-1", "/infra/lb-pools/pool-1", "192.0.2.61", "80", "/infra/lb-services/lb-1"
    )
    _, _, body = spy_session.last
    assert body["application_profile_path"] == "/infra/lb-app-profiles/default-http-lb-app-profile"


def test_get_lb_pool_status(spy_connections, spy_session):
    spy_session.when(
        "/policy/api/v1/infra/lb-services/lb-1/lb-pools/pool-1/status",
        {"members": [{"ip_address": "172.16.1.10", "status": "UP"}]},
    )
    lib = _Lib(spy_connections)
    status = lib.get_lb_pool_status("pool-1", "lb-1")
    assert status["members"][0]["status"] == "UP"


def test_delete_lb_virtual_server(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_lb_virtual_server("vs-1")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/lb-virtual-servers/vs-1")


def test_delete_lb_pool(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_lb_pool("pool-1")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/lb-pools/pool-1")


def test_delete_lb_service(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_lb_service("lb-1")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/lb-services/lb-1")


def test_create_ha_vip_config_on_t0(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_ha_vip_config_on_t0(
        "t0-gw", "default", "192.0.2.100/24", "/infra/.../edge-1", "/infra/.../edge-2"
    )
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default"
    vip_config = body["ha_vip_configs"][0]
    assert vip_config["vip_subnets"] == [{"prefix_len": "24", "ip_addresses": ["192.0.2.100"]}]
    assert vip_config["external_interface_paths"] == ["/infra/.../edge-1", "/infra/.../edge-2"]


def test_remove_ha_vip_config_on_t0(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.remove_ha_vip_config_on_t0("t0-gw", "default")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default"
    assert body == {"ha_vip_configs": []}


def test_get_t0_locale_service(spy_connections, spy_session):
    spy_session.when(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default", {"display_name": "default"}
    )
    lib = _Lib(spy_connections)
    assert lib.get_t0_locale_service("t0-gw", "default") == {"display_name": "default"}
