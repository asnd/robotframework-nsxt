"""Typed exception hierarchy for the nsxt_robot NSX-T API client."""

from __future__ import annotations

from typing import Any


class NsxtError(Exception):
    """Base class for every error raised by the nsxt_robot HTTP client."""


class NsxtConnectionError(NsxtError):
    """A connection to the NSX Manager could not be established."""


class NsxtTimeoutError(NsxtError):
    """A request did not complete before its timeout, after retries."""


class NsxtAuthError(NsxtError):
    """Authentication failed, or a session could not be re-established."""


def _parse_nsx_error(body: Any) -> tuple[Any, Any]:
    """Extract ``(error_code, error_message)`` from an NSX error body, if present."""
    if not isinstance(body, dict):
        return None, None
    code = body.get("error_code")
    message = body.get("error_message")
    if message is None:
        related = body.get("related_errors") or []
        if related and isinstance(related[0], dict):
            message = related[0].get("error_message")
    return code, message


class NsxtApiError(NsxtError):
    """A non-2xx response from the NSX API, after retries are exhausted."""

    def __init__(self, method: str, path: str, status: int, body: Any = None) -> None:
        self.method = method
        self.path = path
        self.status = status
        self.body = body
        self.error_code, self.error_message = _parse_nsx_error(body)
        super().__init__(str(self))

    def __str__(self) -> str:
        if self.error_message:
            detail = f" (error_code {self.error_code}): {self.error_message}"
        else:
            detail = ""
        return f"{self.method} {self.path} -> {self.status}{detail}"


class NsxtNotFoundError(NsxtApiError):
    """404 Not Found."""


class NsxtConflictError(NsxtApiError):
    """409/412 Conflict — typically a stale ``_revision`` on PATCH."""


class NsxtRateLimitError(NsxtApiError):
    """429 Too Many Requests, after retries were exhausted."""


class NsxtRealizationError(NsxtError):
    """A Policy API intent path did not reach ``SUCCESS`` realization in time."""

    def __init__(self, intent_path: str, last_status: Any, cause: Exception | None = None) -> None:
        self.intent_path = intent_path
        self.last_status = last_status
        detail = f": {cause}" if cause else ""
        super().__init__(
            f"Realization of '{intent_path}' did not reach SUCCESS in time{detail}"
        )
