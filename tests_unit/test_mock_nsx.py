"""Unit tests for mock_nsx: the store, auth, realization simulator, and the
FastAPI app end-to-end via TestClient (in-process, no real network/sockets).
"""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from mock_nsx.app import app
from mock_nsx.auth import AuthState
from mock_nsx.realization import RealizationSimulator
from mock_nsx.store import NsxApiError, PolicyStore

# ── PolicyStore ──────────────────────────────────────────────────────────────


def test_upsert_synthesizes_id_path_display_name():
    store = PolicyStore()
    obj = store.upsert("/infra/tier-1s/t1-a", {"foo": "bar"})
    assert obj == {"foo": "bar", "id": "t1-a", "path": "/infra/tier-1s/t1-a", "display_name": "t1-a", "_revision": 1}


def test_upsert_merges_with_existing():
    store = PolicyStore()
    store.upsert("/infra/tier-1s/t1-a", {"foo": "bar"})
    updated = store.upsert("/infra/tier-1s/t1-a", {"baz": "qux"})
    assert updated["foo"] == "bar"
    assert updated["baz"] == "qux"
    assert updated["_revision"] == 2


def test_get_missing_returns_none():
    store = PolicyStore()
    assert store.get("/infra/tier-1s/missing") is None


def test_get_or_404_raises_nsx_api_error():
    store = PolicyStore()
    with pytest.raises(NsxApiError) as excinfo:
        store.get_or_404("/infra/tier-1s/missing")
    assert excinfo.value.status == 404
    assert excinfo.value.body["httpStatus"] == "NOT_FOUND"


def test_children_returns_only_direct_children():
    store = PolicyStore()
    store.upsert("/infra/tier-1s/t1/static-routes/r1", {})
    store.upsert("/infra/tier-1s/t1/static-routes/r2", {})
    store.upsert("/infra/tier-1s/t1", {})  # parent itself, not a child
    children = store.children("/infra/tier-1s/t1/static-routes")
    assert {c["id"] for c in children} == {"r1", "r2"}


def test_list_response_shape():
    store = PolicyStore()
    store.upsert("/infra/tier-1s/t1/static-routes/r1", {})
    resp = store.list_response("/infra/tier-1s/t1/static-routes")
    assert resp["result_count"] == 1
    assert resp["results"][0]["id"] == "r1"


def test_delete_subtree_removes_path_and_children():
    store = PolicyStore()
    store.upsert("/infra/tier-1s/t1", {})
    store.upsert("/infra/tier-1s/t1/static-routes/r1", {})
    assert store.delete_subtree("/infra/tier-1s/t1") is True
    assert store.get("/infra/tier-1s/t1") is None
    assert store.get("/infra/tier-1s/t1/static-routes/r1") is None


def test_delete_subtree_missing_returns_false():
    store = PolicyStore()
    assert store.delete_subtree("/infra/tier-1s/missing") is False


def test_set_raw_stores_body_verbatim_no_synthesis():
    store = PolicyStore()
    store.set_raw("/cluster/status", {"mgmt_cluster_status": {"status": "STABLE"}})
    assert store.get("/cluster/status") == {"mgmt_cluster_status": {"status": "STABLE"}}


def test_reset_clears_all_objects():
    store = PolicyStore()
    store.upsert("/infra/tier-1s/t1", {})
    store.reset()
    assert store.get("/infra/tier-1s/t1") is None


# ── AuthState ─────────────────────────────────────────────────────────────


def test_create_session_valid_credentials_returns_token():
    auth = AuthState(username="admin", password="secret")
    token = auth.create_session("admin", "secret")
    assert token is not None
    assert auth.check_token(token) is True


def test_create_session_invalid_credentials_returns_none():
    auth = AuthState(username="admin", password="secret")
    assert auth.create_session("admin", "wrong") is None


def test_check_basic_valid_header():
    auth = AuthState(username="admin", password="secret")
    header = "Basic " + base64.b64encode(b"admin:secret").decode()
    assert auth.check_basic(header) is True


def test_check_basic_invalid_header():
    auth = AuthState(username="admin", password="secret")
    assert auth.check_basic("Basic bm90LXZhbGlk") is False
    assert auth.check_basic(None) is False
    assert auth.check_basic("Bearer xyz") is False


def test_invalidate_removes_token():
    auth = AuthState()
    token = auth.create_session(auth.username, auth.password)
    auth.invalidate(token)
    assert auth.check_token(token) is False


def test_reset_clears_tokens():
    auth = AuthState()
    token = auth.create_session(auth.username, auth.password)
    auth.reset()
    assert auth.check_token(token) is False


# ── RealizationSimulator ──────────────────────────────────────────────────


def test_realization_default_is_immediate_success():
    sim = RealizationSimulator()
    status = sim.status_for("/infra/tier-1s/t1")
    assert status["consolidated_status"]["consolidated_status"] == "SUCCESS"


def test_realization_polls_before_success():
    sim = RealizationSimulator(polls_before_success=2)
    first = sim.status_for("/infra/tier-1s/t1")
    second = sim.status_for("/infra/tier-1s/t1")
    third = sim.status_for("/infra/tier-1s/t1")
    assert first["consolidated_status"]["consolidated_status"] == "IN_PROGRESS"
    assert second["consolidated_status"]["consolidated_status"] == "IN_PROGRESS"
    assert third["consolidated_status"]["consolidated_status"] == "SUCCESS"


def test_realization_tracks_paths_independently():
    sim = RealizationSimulator(polls_before_success=1)
    a = sim.status_for("/infra/tier-1s/a")
    b = sim.status_for("/infra/tier-1s/b")
    assert a["consolidated_status"]["consolidated_status"] == "IN_PROGRESS"
    assert b["consolidated_status"]["consolidated_status"] == "IN_PROGRESS"


def test_realization_reset_clears_poll_counts():
    sim = RealizationSimulator(polls_before_success=1)
    sim.status_for("/infra/tier-1s/t1")
    sim.reset()
    assert sim.status_for("/infra/tier-1s/t1")["consolidated_status"]["consolidated_status"] == "IN_PROGRESS"


# ── FastAPI app, end-to-end via TestClient ────────────────────────────────


@pytest.fixture
def client():
    c = TestClient(app)
    c.post("/mock/reset")
    yield c
    c.post("/mock/reset")


def _authed_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/session/create", data={"j_username": "admin", "j_password": "VMware1!VMware1!"}
    )
    token = resp.headers["x-xsrf-token"]
    return {"X-XSRF-TOKEN": token}


def test_health_requires_no_auth(client):
    assert client.get("/mock/health").status_code == 200


def test_protected_route_without_auth_is_401(client):
    assert client.get("/api/v1/cluster/status").status_code == 401


def test_session_create_wrong_password_is_403(client):
    resp = client.post("/api/session/create", data={"j_username": "admin", "j_password": "wrong"})
    assert resp.status_code == 403


def test_session_create_then_protected_route_succeeds(client):
    headers = _authed_headers(client)
    resp = client.get("/api/v1/cluster/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["mgmt_cluster_status"]["status"] == "STABLE"


def test_basic_auth_also_works(client):
    header = "Basic " + base64.b64encode(b"admin:VMware1!VMware1!").decode()
    resp = client.get("/api/v1/cluster/status", headers={"Authorization": header})
    assert resp.status_code == 200


def test_generic_crud_roundtrip(client):
    headers = _authed_headers(client)
    patch = client.patch(
        "/policy/api/v1/infra/tier-1s/t1-test", json={"display_name": "t1-test"}, headers=headers
    )
    assert patch.status_code == 200
    get = client.get("/policy/api/v1/infra/tier-1s/t1-test", headers=headers)
    assert get.json()["display_name"] == "t1-test"
    delete = client.delete("/policy/api/v1/infra/tier-1s/t1-test", headers=headers)
    assert delete.status_code == 200
    assert client.get("/policy/api/v1/infra/tier-1s/t1-test", headers=headers).status_code == 404


def test_realized_state_status_endpoint(client):
    headers = _authed_headers(client)
    resp = client.get(
        "/policy/api/v1/infra/realized-state/status",
        params={"intent_path": "/infra/tier-1s/t1-test"},
        headers=headers,
    )
    assert resp.json()["consolidated_status"]["consolidated_status"] == "SUCCESS"


def test_bgp_neighbor_status_reflects_enabled_flag(client):
    headers = _authed_headers(client)
    client.patch(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp",
        json={"enabled": True},
        headers=headers,
    )
    client.patch(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp/neighbors/n1",
        json={"neighbor_address": "10.0.0.1", "remote_as_num": 65000},
        headers=headers,
    )
    status = client.get(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp/neighbors/n1/status",
        headers=headers,
    ).json()
    assert status["connection_state"] == "ESTABLISHED"

    client.patch(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp",
        json={"enabled": False},
        headers=headers,
    )
    status = client.get(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp/neighbors/n1/status",
        headers=headers,
    ).json()
    assert status["connection_state"] != "ESTABLISHED"


def test_bgp_neighbor_routes_empty_when_not_established(client):
    headers = _authed_headers(client)
    client.patch(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp",
        json={"enabled": False},
        headers=headers,
    )
    client.patch(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp/neighbors/n1",
        json={"neighbor_address": "10.0.0.1"},
        headers=headers,
    )
    routes = client.get(
        "/policy/api/v1/infra/tier-0s/t0-gw/locale-services/default/bgp/neighbors/n1/routes",
        headers=headers,
    ).json()
    assert routes == {"results": [], "result_count": 0}


def test_lb_pool_status_all_members_up(client):
    headers = _authed_headers(client)
    client.patch(
        "/policy/api/v1/infra/lb-pools/pool1",
        json={"members": [{"ip_address": "172.16.1.10"}]},
        headers=headers,
    )
    status = client.get(
        "/policy/api/v1/infra/lb-services/svc1/lb-pools/pool1/status", headers=headers
    ).json()
    assert status["members"] == [{"ip_address": "172.16.1.10", "status": "UP"}]


def test_group_members_from_ip_expression(client):
    headers = _authed_headers(client)
    client.patch(
        "/policy/api/v1/infra/domains/default/groups/g1",
        json={"expression": [{"resource_type": "IPAddressExpression", "ip_addresses": ["172.16.2.10"]}]},
        headers=headers,
    )
    members = client.get(
        "/policy/api/v1/infra/domains/default/groups/g1/members/virtual-machines", headers=headers
    ).json()
    assert members["results"] == [{"display_name": "172.16.2.10", "ip_addresses": ["172.16.2.10"]}]


def test_transport_node_maintenance_mode_toggle(client):
    headers = _authed_headers(client)
    node_before = client.get("/api/v1/transport-nodes/edge-node-1", headers=headers).json()
    assert node_before["maintenance_mode"] == "DISABLED"

    client.post(
        "/api/v1/transport-nodes/edge-node-1",
        params={"action": "enter_maintenance_mode"},
        headers=headers,
    )
    node_after = client.get("/api/v1/transport-nodes/edge-node-1", headers=headers).json()
    assert node_after["maintenance_mode"] == "ENABLED"

    client.post(
        "/api/v1/transport-nodes/edge-node-1",
        params={"action": "exit_maintenance_mode"},
        headers=headers,
    )
    node_final = client.get("/api/v1/transport-nodes/edge-node-1", headers=headers).json()
    assert node_final["maintenance_mode"] == "DISABLED"


def test_compute_manager_status_unknown_id_is_404(client):
    headers = _authed_headers(client)
    resp = client.get("/api/v1/fabric/compute-managers/does-not-exist/status", headers=headers)
    assert resp.status_code == 404


def test_mock_reset_reseeds_fixtures(client):
    headers = _authed_headers(client)
    client.patch("/policy/api/v1/infra/tier-1s/scratch", json={}, headers=headers)
    client.post("/mock/reset")
    # a fresh session is required post-reset since tokens are cleared too
    headers = _authed_headers(client)
    assert client.get("/policy/api/v1/infra/tier-1s/scratch", headers=headers).status_code == 404
    assert client.get("/api/v1/cluster/status", headers=headers).status_code == 200
