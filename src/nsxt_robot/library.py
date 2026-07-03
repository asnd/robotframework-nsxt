"""NsxtLibrary — connection-cache and REST/realization keywords for NSX-T.

Composes the keyword mixins in :mod:`nsxt_robot.keywords` on top of a shared
:class:`~nsxt_robot.connections.NsxtConnectionManager`, following the same
``ConnectionCache``-backed pattern as SSHLibrary and other flagship Robot
Framework libraries: open one or more connections, operate on the current
one, switch or close as needed.

Typical usage from a consuming suite::

    *** Settings ***
    Library     nsxt_robot.NsxtLibrary
    Resource    nsxt_robot/resources/policy_api.robot

    *** Test Cases ***
    Example
        Open Nsx Connection    ${NSX_MANAGER}    ${NSX_USER}    ${NSX_PASSWORD}
        ${status}=    NSX REST GET    /api/v1/cluster/status
        [Teardown]    Close All Nsx Connections
"""

from __future__ import annotations

from robot.api.deco import library

from . import __version__
from .connections import NsxtConnectionManager
from .keywords.connection import ConnectionKeywords
from .keywords.realization import RealizationKeywords
from .keywords.rest import RestKeywords


@library(scope="GLOBAL", auto_keywords=False)
class NsxtLibrary(ConnectionKeywords, RestKeywords, RealizationKeywords):
    """Connection, REST-verb, and realization-polling keywords for NSX-T."""

    ROBOT_LIBRARY_VERSION = __version__

    def __init__(self) -> None:
        self._connections = NsxtConnectionManager()
