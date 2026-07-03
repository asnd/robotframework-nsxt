"""Connection-cache keywords: Open/Switch/Close Nsx Connection, in the style
of SSHLibrary and other flagship Robot Framework libraries.
"""

from __future__ import annotations

from typing import Any

from robot.api import logger as robot_logger
from robot.api.deco import keyword

from ..client import NsxtSession
from ..connections import NsxtConnectionManager


class ConnectionKeywords:
    """Mixin providing NSX connection-cache keywords. Requires ``self._connections``."""

    _connections: NsxtConnectionManager

    @keyword("Open Nsx Connection")
    def open_nsx_connection(
        self,
        host: str,
        username: str = "admin",
        password: str | None = None,
        alias: str | None = None,
        port: int = 443,
        auth: str = "auto",
        verify: bool = True,
        ca_bundle: str | None = None,
        timeout: float = 30,
        connect_timeout: float = 10,
        retries: int = 3,
        backoff: float = 0.5,
    ) -> int:
        """Open and authenticate a connection to an NSX-T Manager, returning its index.

        ``password`` defaults to the ``NSX_PASSWORD`` environment variable when not
        given, so CI can inject a secret without a credentials file on disk. ``auth``
        is one of ``auto`` (session-token, falling back to Basic), ``session``, or
        ``basic``. ``verify`` accepts ``${True}``/``${False}`` or a CA bundle path;
        ``ca_bundle`` is an alias for the same option, for readability. ``alias``
        registers a name so a later suite can ``Switch Nsx Connection`` to it.

        Example: ``Open Nsx Connection    ${NSX_MANAGER}    ${NSX_USER}    ${NSX_PASSWORD}``
        """
        verify_option: bool | str = ca_bundle if ca_bundle else verify
        session = NsxtSession(
            host,
            username=username,
            password=password,
            port=port,
            auth=auth,
            verify=verify_option,
            timeout=timeout,
            connect_timeout=connect_timeout,
            retries=retries,
            backoff=backoff,
        )
        index = self._connections.open(session, alias)
        robot_logger.info(
            f"Opened NSX connection {index} to {host}:{port} (auth={session.active_auth})"
        )
        return index

    @keyword("Switch Nsx Connection")
    def switch_nsx_connection(self, alias_or_index: Any) -> int | None:
        """Switch the active NSX connection; returns the *previous* connection's index."""
        return self._connections.switch(alias_or_index)

    @keyword("Close Nsx Connection")
    def close_nsx_connection(self) -> None:
        """Close the current NSX connection, logging out if session-authenticated."""
        self._connections.close_current()

    @keyword("Close All Nsx Connections")
    def close_all_nsx_connections(self) -> None:
        """Close every open NSX connection and reset the connection cache."""
        self._connections.close_all()

    @keyword("Get Nsx Connection")
    def get_nsx_connection(self, index_or_alias: Any = None) -> dict[str, Any]:
        """Return info about a connection (host, port, auth mode) with secrets masked.

        Defaults to the current connection when ``index_or_alias`` is not given.
        """
        session = self._connections.get(index_or_alias)
        return {
            "host": session.host,
            "port": session.port,
            "username": session.username,
            "auth": session.active_auth,
            "verify": session.verify,
        }

    @keyword("Set Nsx Timeout")
    def set_nsx_timeout(self, timeout: float) -> float:
        """Set the current connection's default read timeout (seconds).

        Returns the previous value.
        """
        session = self._connections.current
        previous = session.timeout
        session.timeout = timeout
        return previous
