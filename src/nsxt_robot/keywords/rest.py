"""`NSX REST *` verb keywords, operating on the current NsxtLibrary connection.

Keep the exact legacy keyword names from ``common.robot``'s RESTinstance-based
implementation: existing suites and resource files call these by name and must
keep working unchanged as the transport moves from RESTinstance to the
built-in ``NsxtSession`` client.
"""

from __future__ import annotations

from typing import Any

from robot.api import logger as robot_logger
from robot.api.deco import keyword

from ..connections import NsxtConnectionManager


class RestKeywords:
    """Mixin providing the `NSX REST *` keywords. Requires ``self._connections``."""

    _connections: NsxtConnectionManager

    @keyword("NSX REST GET")
    def nsx_rest_get(self, path: str) -> Any:
        """Perform a GET request against the NSX API and return the parsed body."""
        return self._connections.current.get(path)

    @keyword("NSX REST PATCH")
    def nsx_rest_patch(self, path: str, body: Any) -> Any:
        """Perform a PATCH request and return the parsed response body."""
        return self._connections.current.patch(path, body)

    @keyword("NSX REST POST")
    def nsx_rest_post(self, path: str, body: Any = None) -> Any:
        """Perform a POST request (e.g. an action endpoint); accepts 200 or 202."""
        return self._connections.current.post(path, body)

    @keyword("NSX REST DELETE")
    def nsx_rest_delete(self, path: str) -> Any:
        """Perform a DELETE request; accepts 200 or 204 and returns the parsed body."""
        return self._connections.current.delete(path)

    @keyword("NSX REST DELETE Ignore Error")
    def nsx_rest_delete_ignore_error(self, path: str) -> None:
        """DELETE that logs a warning but never fails — for use in teardowns."""
        try:
            self.nsx_rest_delete(path)
        except Exception as exc:  # noqa: BLE001 — deliberately broad for teardown safety
            robot_logger.warn(f"DELETE {path} failed (ignored): {exc}")
