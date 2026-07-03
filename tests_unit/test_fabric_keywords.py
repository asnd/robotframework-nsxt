"""Unit tests for FabricKeywords (edge clusters, manager cluster, transport zones/nodes)."""

from __future__ import annotations

from nsxt_robot.keywords.fabric import FabricKeywords


class _Lib(FabricKeywords):
    def __init__(self, connections):
        self._connections = connections


def test_get_edge_nodes_in_cluster(spy_connections, spy_session):
    spy_session.when(
        "/policy/api/v1/infra/sites/default/enforcement-points/default/edge-clusters/ec-1/edge-nodes",
        {"results": [{"nsx_id": "edge-node-1"}]},
    )
    lib = _Lib(spy_connections)
    result = lib.get_edge_nodes_in_cluster("ec-1")
    assert result["results"][0]["nsx_id"] == "edge-node-1"


def test_get_manager_cluster_status(spy_connections, spy_session):
    spy_session.when("/api/v1/cluster/status", {"mgmt_cluster_status": {"status": "STABLE"}})
    lib = _Lib(spy_connections)
    assert lib.get_manager_cluster_status()["mgmt_cluster_status"]["status"] == "STABLE"


def test_get_transport_zones(spy_connections, spy_session):
    spy_session.when("/api/v1/transport-zones", {"results": []})
    lib = _Lib(spy_connections)
    assert lib.get_transport_zones() == {"results": []}


def test_get_transport_node_status(spy_connections, spy_session):
    spy_session.when("/api/v1/transport-nodes/tn-1/status", {"state": "success"})
    lib = _Lib(spy_connections)
    assert lib.get_transport_node_status("tn-1") == {"state": "success"}


def test_get_all_transport_node_statuses(spy_connections, spy_session):
    spy_session.when("/api/v1/transport-nodes/status", {"results": []})
    lib = _Lib(spy_connections)
    assert lib.get_all_transport_node_statuses() == {"results": []}


def test_get_compute_managers(spy_connections, spy_session):
    spy_session.when("/api/v1/fabric/compute-managers", {"results": [{"id": "cm-1"}]})
    lib = _Lib(spy_connections)
    assert lib.get_compute_managers()["results"][0]["id"] == "cm-1"


def test_get_compute_manager_status(spy_connections, spy_session):
    spy_session.when("/api/v1/fabric/compute-managers/cm-1/status", {"registration_status": "REGISTERED"})
    lib = _Lib(spy_connections)
    assert lib.get_compute_manager_status("cm-1")["registration_status"] == "REGISTERED"
