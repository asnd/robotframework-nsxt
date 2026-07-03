"""Fabric/infra keywords: edge clusters, manager cluster, transport zones/nodes,
compute managers — read-only Policy and Management API lookups.
"""

from __future__ import annotations

from typing import Any

from robot.api.deco import keyword

from ..connections import NsxtConnectionManager
from .paths import MGMT_BASE, POLICY_BASE


class FabricKeywords:
    """Mixin providing fabric/infra lookup keywords. Requires ``self._connections``."""

    _connections: NsxtConnectionManager

    @keyword("Get Edge Nodes In Cluster")
    def get_edge_nodes_in_cluster(self, edge_cluster_id: str) -> Any:
        """List the edge nodes of a Policy edge cluster.

        Each result carries a ``path`` usable as ``edge_path`` for external
        interfaces and EVPN endpoints.
        """
        return self._connections.current.get(
            f"{POLICY_BASE}/infra/sites/default/enforcement-points/default/"
            f"edge-clusters/{edge_cluster_id}/edge-nodes"
        )

    @keyword("Get Manager Cluster Status")
    def get_manager_cluster_status(self) -> Any:
        """Retrieve NSX Manager cluster status via the management API."""
        return self._connections.current.get(f"{MGMT_BASE}/cluster/status")

    @keyword("Get Transport Zones")
    def get_transport_zones(self) -> Any:
        """List all transport zones."""
        return self._connections.current.get(f"{MGMT_BASE}/transport-zones")

    @keyword("Get Transport Node Status")
    def get_transport_node_status(self, tn_id: str) -> Any:
        """Retrieve status for a specific transport node."""
        return self._connections.current.get(f"{MGMT_BASE}/transport-nodes/{tn_id}/status")

    @keyword("Get All Transport Node Statuses")
    def get_all_transport_node_statuses(self) -> Any:
        """List the status of all transport nodes."""
        return self._connections.current.get(f"{MGMT_BASE}/transport-nodes/status")

    @keyword("Get Compute Managers")
    def get_compute_managers(self) -> Any:
        """List all registered compute managers (vCenter)."""
        return self._connections.current.get(f"{MGMT_BASE}/fabric/compute-managers")

    @keyword("Get Compute Manager Status")
    def get_compute_manager_status(self, cm_id: str) -> Any:
        """Retrieve the registration and connectivity status of a compute manager."""
        return self._connections.current.get(f"{MGMT_BASE}/fabric/compute-managers/{cm_id}/status")
