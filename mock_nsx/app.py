"""FastAPI application implementing the mock NSX-T Manager.

Route order matters: FastAPI/Starlette matches in registration order, so
every specific-path (derived-state, mgmt fixture, control) route is declared
before the generic Policy API catch-all that handles plain CRUD.
"""

from __future__ import annotations

from urllib.parse import parse_qs

from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse

from . import fixtures
from .auth import AuthState
from .realization import RealizationSimulator
from .store import NsxApiError, PolicyStore

app = FastAPI(title="mock-nsx", docs_url=None, redoc_url=None)

policy_store = PolicyStore()
mgmt_store = PolicyStore()
auth_state = AuthState()
realization = RealizationSimulator()


def _reset_state() -> None:
    policy_store.reset()
    mgmt_store.reset()
    auth_state.reset()
    realization.reset()
    fixtures.seed_policy(policy_store)
    fixtures.seed_mgmt(mgmt_store)


_reset_state()


@app.exception_handler(NsxApiError)
def _handle_nsx_api_error(request: Request, exc: NsxApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content=exc.body)


@app.middleware("http")
async def _enforce_auth(request: Request, call_next):
    if request.url.path.startswith("/mock/") or request.url.path == "/api/session/create":
        return await call_next(request)
    authenticated = auth_state.is_authenticated(
        request.headers.get("X-XSRF-TOKEN"), request.headers.get("Authorization")
    )
    if not authenticated:
        return JSONResponse(status_code=401, content={"error_message": "Unauthorized"})
    return await call_next(request)


# ── auth ──────────────────────────────────────────────────────────────────


@app.post("/api/session/create")
async def session_create(request: Request) -> Response:
    # Parsed by hand (rather than Starlette's request.form()) to avoid taking a
    # python-multipart dependency just for a urlencoded j_username/j_password body.
    form = parse_qs((await request.body()).decode())
    username = form.get("j_username", [""])[0]
    password = form.get("j_password", [""])[0]
    token = auth_state.create_session(username, password)
    if token is None:
        return JSONResponse(status_code=403, content={"error_message": "Invalid credentials"})
    response = Response(status_code=200)
    response.set_cookie("JSESSIONID", token)
    response.headers["X-XSRF-TOKEN"] = token
    return response


@app.delete("/api/session")
def session_delete(request: Request) -> Response:
    auth_state.invalidate(request.headers.get("X-XSRF-TOKEN"))
    return Response(status_code=200)


# ── realization ───────────────────────────────────────────────────────────


@app.get("/policy/api/v1/infra/realized-state/status")
def realized_state_status(intent_path: str) -> dict:
    return realization.status_for(intent_path)


# ── derived operational state: BGP ────────────────────────────────────────


def _bgp_neighbor_status(t0_id: str, ls_id: str, neighbor_id: str) -> dict:
    neighbor_path = f"/infra/tier-0s/{t0_id}/locale-services/{ls_id}/bgp/neighbors/{neighbor_id}"
    neighbor = policy_store.get_or_404(neighbor_path)
    bgp_config = policy_store.get(f"/infra/tier-0s/{t0_id}/locale-services/{ls_id}/bgp") or {}
    established = bool(bgp_config.get("enabled", True))
    return {
        "connection_state": "ESTABLISHED" if established else "IDLE",
        "bfd_diagnostic_code": 0 if established else 1,
        "neighbor_address": neighbor.get("neighbor_address"),
        "remote_as_num": neighbor.get("remote_as_num"),
    }


@app.get("/policy/api/v1/infra/tier-0s/{t0_id}/locale-services/{ls_id}/bgp/neighbors/{neighbor_id}/status")
def bgp_neighbor_status(t0_id: str, ls_id: str, neighbor_id: str) -> dict:
    return _bgp_neighbor_status(t0_id, ls_id, neighbor_id)


@app.get("/policy/api/v1/infra/tier-0s/{t0_id}/locale-services/{ls_id}/bgp/neighbors/{neighbor_id}/routes")
def bgp_neighbor_routes(t0_id: str, ls_id: str, neighbor_id: str) -> dict:
    status = _bgp_neighbor_status(t0_id, ls_id, neighbor_id)
    if status["connection_state"] != "ESTABLISHED":
        return {"results": [], "result_count": 0}
    return {
        "results": [{"network": "10.99.0.0/24", "next_hop": status["neighbor_address"]}],
        "result_count": 1,
    }


# ── derived operational state: LB pool ────────────────────────────────────


@app.get("/policy/api/v1/infra/lb-services/{lb_service_id}/lb-pools/{pool_id}/status")
def lb_pool_status(lb_service_id: str, pool_id: str) -> dict:
    pool = policy_store.get_or_404(f"/infra/lb-pools/{pool_id}")
    members = pool.get("members", [])
    return {"members": [{"ip_address": m.get("ip_address"), "status": "UP"} for m in members]}


# ── derived operational state: group effective membership ────────────────


@app.get("/policy/api/v1/infra/domains/{domain}/groups/{group_id}/members/virtual-machines")
def group_members(domain: str, group_id: str) -> dict:
    group = policy_store.get_or_404(f"/infra/domains/{domain}/groups/{group_id}")
    expressions = group.get("expression") or []
    ip_addresses: list[str] = []
    for expr in expressions:
        if expr.get("resource_type") == "IPAddressExpression":
            ip_addresses.extend(expr.get("ip_addresses", []))
    results = [{"display_name": ip, "ip_addresses": [ip]} for ip in ip_addresses]
    return {"results": results, "result_count": len(results)}


# ── management API fixtures ───────────────────────────────────────────────


@app.get("/api/v1/cluster/status")
def mgmt_cluster_status() -> dict:
    return mgmt_store.get_or_404("/cluster/status")


@app.get("/api/v1/transport-zones")
def mgmt_transport_zones() -> dict:
    return mgmt_store.get_or_404("/transport-zones")


@app.get("/api/v1/transport-nodes/status")
def mgmt_transport_node_statuses() -> dict:
    return mgmt_store.get_or_404("/transport-nodes/status")


@app.get("/api/v1/transport-nodes/{node_id}")
def mgmt_transport_node(node_id: str) -> dict:
    return mgmt_store.get_or_404(f"/transport-nodes/{node_id}")


@app.get("/api/v1/transport-nodes")
def mgmt_transport_nodes() -> dict:
    return mgmt_store.get_or_404("/transport-nodes")


@app.post("/api/v1/transport-nodes/{node_id}")
def mgmt_transport_node_action(node_id: str, action: str = Query(...)) -> Response:
    node = mgmt_store.get_or_404(f"/transport-nodes/{node_id}")
    if action == "enter_maintenance_mode":
        node["maintenance_mode"] = "ENABLED"
    elif action == "exit_maintenance_mode":
        node["maintenance_mode"] = "DISABLED"
    else:
        raise NsxApiError(400, 1, f"Unsupported action '{action}'")
    mgmt_store.upsert(f"/transport-nodes/{node_id}", node)
    return Response(status_code=200)


@app.get("/api/v1/fabric/compute-managers")
def mgmt_compute_managers() -> dict:
    return mgmt_store.get_or_404("/fabric/compute-managers")


@app.get("/api/v1/fabric/compute-managers/{cm_id}/status")
def mgmt_compute_manager_status(cm_id: str) -> dict:
    managers = mgmt_store.get_or_404("/fabric/compute-managers")["results"]
    if not any(m["id"] == cm_id for m in managers):
        raise NsxApiError(404, 202, f"Compute manager '{cm_id}' not found")
    return {"registration_status": "REGISTERED"}


# ── control API (test harness only, never touched by suites) ─────────────


@app.get("/mock/health")
def mock_health() -> dict:
    return {"status": "ok"}


@app.post("/mock/reset")
def mock_reset() -> dict:
    _reset_state()
    return {"status": "reset"}


@app.post("/mock/control/realize-after")
def mock_set_realize_after(polls: int = Query(...)) -> dict:
    realization.polls_before_success = polls
    return {"polls_before_success": polls}


# ── generic Policy API CRUD (must be registered last) ─────────────────────


@app.patch("/policy/api/v1/{path:path}")
async def policy_patch(path: str, request: Request) -> dict:
    body = await request.json()
    return policy_store.upsert(f"/{path}", body)


@app.get("/policy/api/v1/{path:path}")
def policy_get(path: str) -> dict:
    intent_path = f"/{path}"
    obj = policy_store.get(intent_path)
    if obj is not None:
        return obj
    children = policy_store.children(intent_path)
    if children:
        return policy_store.list_response(intent_path)
    raise NsxApiError(404, 202, f"The object at '{intent_path}' was not found")


@app.delete("/policy/api/v1/{path:path}")
def policy_delete(path: str) -> Response:
    intent_path = f"/{path}"
    if not policy_store.delete_subtree(intent_path):
        raise NsxApiError(404, 202, f"The object at '{intent_path}' was not found")
    return Response(status_code=200)
