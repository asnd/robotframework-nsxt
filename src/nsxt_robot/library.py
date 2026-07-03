"""NsxtLibrary — connection, REST/realization, and NSX-T Policy/Mgmt API keywords.

Composes the keyword mixins in :mod:`nsxt_robot.keywords` on top of a shared
:class:`~nsxt_robot.connections.NsxtConnectionManager`, following the same
``ConnectionCache``-backed pattern as SSHLibrary and other flagship Robot
Framework libraries: open one or more connections, operate on the current
one, switch or close as needed.

Typical usage from a consuming suite::

    *** Settings ***
    Library     nsxt_robot.NsxtLibrary

    *** Test Cases ***
    Example
        Open Nsx Connection    ${NSX_MANAGER}    ${NSX_USER}    ${NSX_PASSWORD}
        Create T1 Gateway    t1-a    T1-A    ${T0_PATH}
        [Teardown]    Close All Nsx Connections
"""

from __future__ import annotations

from robot.api.deco import library

from . import __version__
from .connections import NsxtConnectionManager
from .keywords.connection import ConnectionKeywords
from .keywords.fabric import FabricKeywords
from .keywords.gateways import GatewayKeywords
from .keywords.realization import RealizationKeywords
from .keywords.rest import RestKeywords
from .keywords.routing import RoutingKeywords
from .keywords.security import SecurityKeywords
from .keywords.services import ServiceKeywords


@library(scope="GLOBAL", auto_keywords=False)
class NsxtLibrary(
    ConnectionKeywords,
    RestKeywords,
    RealizationKeywords,
    FabricKeywords,
    GatewayKeywords,
    RoutingKeywords,
    ServiceKeywords,
    SecurityKeywords,
):
    """Connection, REST-verb, realization, and NSX-T Policy/Mgmt API keywords."""

    ROBOT_LIBRARY_VERSION = __version__

    def __init__(self) -> None:
        self._connections = NsxtConnectionManager()
