"""Static seed data for the mock NSX Manager, matching env.mock.yaml's topology.

These IDs are load-bearing: env.mock.yaml's ``T0_GATEWAY_ID``, ``EDGE_CLUSTER_ID``,
``OVERLAY_TZ_ID``, and ``VLAN_TZ_ID`` must match the constants below, or the
suites that assume this topology already exists (05_ha_vip's pre-seeded T0
interfaces, 01_infra's transport-zone lookup, 11_failover's edge-node lookup)
will fail against the mock.
"""

from __future__ import annotations

from .store import PolicyStore

T0_GATEWAY_ID = "t0-gw"
EDGE_CLUSTER_ID = "edge-cluster-1"
OVERLAY_TZ_ID = "overlay-tz"
VLAN_TZ_ID = "vlan-tz"

EDGE_NODE_IDS = ["edge-node-1", "edge-node-2"]


def seed_policy(store: PolicyStore) -> None:
    """Seed Policy API objects the suites assume already exist."""
    store.upsert(f"/infra/tier-0s/{T0_GATEWAY_ID}", {"ha_mode": "ACTIVE_STANDBY"})
    store.upsert(
        f"/infra/tier-0s/{T0_GATEWAY_ID}/locale-services/default",
        {"edge_cluster_path": f"/infra/sites/default/enforcement-points/default/edge-clusters/{EDGE_CLUSTER_ID}"},
    )
    # 05_ha_vip reads back >= 2 pre-existing external interfaces on the default
    # locale service; this suite only PATCHes ha_vip_configs, it never creates them.
    for i, node_id in enumerate(EDGE_NODE_IDS, start=1):
        store.upsert(
            f"/infra/tier-0s/{T0_GATEWAY_ID}/locale-services/default/interfaces/uplink-{i}",
            {"type": "EXTERNAL", "edge_path": f".../edge-nodes/{node_id}"},
        )

    edge_cluster_path = f"/infra/sites/default/enforcement-points/default/edge-clusters/{EDGE_CLUSTER_ID}"
    for node_id in EDGE_NODE_IDS:
        store.upsert(f"{edge_cluster_path}/edge-nodes/{node_id}", {"nsx_id": node_id})


def seed_mgmt(mgmt: PolicyStore) -> None:
    """Seed Management API fixture responses (static reference/fabric data)."""
    mgmt.set_raw(
        "/cluster/status",
        {
            "mgmt_cluster_status": {
                "status": "STABLE",
                "online_nodes": [
                    {"member_ip": "192.0.2.11"},
                    {"member_ip": "192.0.2.12"},
                    {"member_ip": "192.0.2.13"},
                ],
            }
        },
    )
    mgmt.set_raw(
        "/transport-zones",
        {
            "results": [
                {"id": OVERLAY_TZ_ID, "display_name": OVERLAY_TZ_ID, "transport_type": "OVERLAY"},
                {"id": VLAN_TZ_ID, "display_name": VLAN_TZ_ID, "transport_type": "VLAN"},
            ],
            "result_count": 2,
        },
    )
    mgmt.set_raw(
        "/transport-nodes",
        {
            "results": [
                {"id": "tn-host-1", "display_name": "tn-host-1", "tunnel_endpoints": [{"ip": "192.168.10.11"}]},
                {"id": "tn-host-2", "display_name": "tn-host-2", "tunnel_endpoints": [{"ip": "192.168.10.12"}]},
            ],
            "result_count": 2,
        },
    )
    mgmt.set_raw(
        "/transport-nodes/status",
        {
            "results": [
                {"node_id": "tn-host-1", "node_deployment_state": {"state": "success"}},
                {"node_id": "tn-host-2", "node_deployment_state": {"state": "success"}},
            ],
            "result_count": 2,
        },
    )
    mgmt.set_raw(
        "/fabric/compute-managers",
        {"results": [{"id": "cm-1", "display_name": "vcenter-1"}], "result_count": 1},
    )
    # Individual, mutable transport-node objects for the edge nodes (11_failover
    # toggles `maintenance_mode` on these via the enter/exit-maintenance actions).
    for node_id in EDGE_NODE_IDS:
        mgmt.upsert(f"/transport-nodes/{node_id}", {"maintenance_mode": "DISABLED"})
