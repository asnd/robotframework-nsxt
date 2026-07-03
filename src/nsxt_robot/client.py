"""NsxtSession — a stateful HTTP client for a single NSX-T Manager connection.

Handles session-token authentication (with Basic-auth fallback), automatic
re-authentication on an expired session, retries with backoff on transient
failures, and redaction of credentials from logs and exception messages.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import random
import time
from typing import Any

import requests
import urllib3

from .exceptions import (
    NsxtApiError,
    NsxtAuthError,
    NsxtConflictError,
    NsxtConnectionError,
    NsxtNotFoundError,
    NsxtRateLimitError,
    NsxtTimeoutError,
)

logger = logging.getLogger("nsxt_robot")

# urllib3 debug logging can dump raw headers (including Authorization/Cookie);
# pin it above DEBUG so enabling this package's logger can never leak secrets.
logging.getLogger("urllib3").setLevel(logging.WARNING)

_REDACT_HEADERS = {"authorization", "cookie", "x-xsrf-token"}
_REDACT_BODY_KEYS = {"password", "j_password"}
_RETRY_STATUSES = {429, 502, 503, 504}
_IDEMPOTENT_METHODS = {"GET", "PUT", "PATCH", "DELETE"}
_MAX_BACKOFF_SECONDS = 30.0


def _redact_body(value: Any) -> Any:
    """Recursively mask known secret keys so bodies are safe to log."""
    if isinstance(value, dict):
        return {
            k: ("***" if k.lower() in _REDACT_BODY_KEYS else _redact_body(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact_body(v) for v in value]
    return value


def _coerce_body(body: Any) -> Any:
    """Normalize a keyword-supplied body (dict, RF DotDict, or JSON string) to plain data."""
    if body is None or body == "":
        return None
    if isinstance(body, str):
        return json.loads(body)
    if isinstance(body, dict):
        return dict(body)
    return body


def _safe_json(resp: requests.Response) -> Any:
    if not resp.content:
        return None
    try:
        return resp.json()
    except ValueError:
        return resp.text


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None  # HTTP-date form: fall back to exponential backoff


def _error_class(status: int) -> type[NsxtApiError]:
    return {
        404: NsxtNotFoundError,
        409: NsxtConflictError,
        412: NsxtConflictError,
        429: NsxtRateLimitError,
    }.get(status, NsxtApiError)


class NsxtSession:
    """An authenticated connection to one NSX-T Manager.

    ``auth='auto'`` (the default) tries session-token authentication first
    (``POST /api/session/create``) and falls back to HTTP Basic if that
    endpoint is unavailable (older NSX releases, some VMC deployments).
    """

    def __init__(
        self,
        host: str,
        username: str = "admin",
        password: str | None = None,
        port: int = 443,
        auth: str = "auto",
        verify: bool | str = True,
        timeout: float = 30,
        connect_timeout: float = 10,
        retries: int = 3,
        backoff: float = 0.5,
        session: requests.Session | None = None,
    ) -> None:
        """``session`` allows injecting a preconfigured ``requests.Session``

        (e.g. with a fake transport adapter mounted) for testing without a
        real network call; production callers should leave it unset.
        """
        if auth not in ("auto", "session", "basic"):
            raise ValueError(f"auth must be 'auto', 'session', or 'basic', got {auth!r}")
        self.host = host
        self.port = port
        self.username = username
        self._password = password if password is not None else os.environ.get("NSX_PASSWORD", "")
        self.verify = verify
        self.timeout = timeout
        self.connect_timeout = connect_timeout
        self.retries = retries
        self.backoff = backoff
        self.base_url = f"https://{host}:{port}"
        self._auth_mode = auth
        self.active_auth: str | None = None
        self._xsrf_token: str | None = None
        self._session = session if session is not None else requests.Session()

        if verify is False:
            logger.warning(
                "TLS verification is disabled for %s — do not use outside a lab", host
            )
            # Suppress urllib3's per-request InsecureRequestWarning: the single
            # WARN above already says this once, per connection, more clearly.
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self._authenticate()

    # ── authentication ──────────────────────────────────────────────────

    def _basic_header(self) -> str:
        raw = f"{self.username}:{self._password}".encode()
        return "Basic " + base64.b64encode(raw).decode()

    def _authenticate(self) -> None:
        if self._auth_mode in ("auto", "session"):
            if self._try_session_auth():
                self.active_auth = "session"
                return
            if self._auth_mode == "session":
                raise NsxtAuthError(
                    f"Session-based auth is unavailable on {self.host} and "
                    "auth='session' was explicitly requested"
                )
            logger.info("Session auth unavailable on %s, falling back to Basic", self.host)
        self.active_auth = "basic"

    def _try_session_auth(self) -> bool:
        url = f"{self.base_url}/api/session/create"
        try:
            resp = self._session.post(
                url,
                data={"j_username": self.username, "j_password": self._password},
                timeout=(self.connect_timeout, self.timeout),
                verify=self.verify,
            )
        except requests.exceptions.RequestException as exc:
            raise NsxtConnectionError(f"Could not reach {self.host}: {exc}") from exc

        if resp.status_code in (404, 405, 400):
            return False
        if resp.status_code in (401, 403):
            raise NsxtAuthError(f"Authentication failed for {self.username}@{self.host}")
        if resp.status_code != 200:
            raise NsxtApiError("POST", "/api/session/create", resp.status_code, _redact_body(_safe_json(resp)))

        token = resp.headers.get("X-XSRF-TOKEN")
        if not token:
            return False
        self._xsrf_token = token
        return True

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.active_auth == "session" and self._xsrf_token:
            headers["X-XSRF-TOKEN"] = self._xsrf_token
        else:
            headers["Authorization"] = self._basic_header()
        return headers

    def close(self) -> None:
        """Log out of the NSX session (if any) and release the connection pool."""
        if self.active_auth == "session":
            try:
                self._session.delete(
                    f"{self.base_url}/api/session",
                    headers=self._headers(),
                    timeout=(self.connect_timeout, self.timeout),
                    verify=self.verify,
                )
            except requests.exceptions.RequestException:
                pass  # best-effort logout; the manager will expire it anyway
        self._session.close()

    # ── requests ────────────────────────────────────────────────────────

    def get(self, path: str, timeout: float | None = None) -> Any:
        return self.request("GET", path, expected_status=(200,), timeout=timeout)

    def patch(self, path: str, body: Any, timeout: float | None = None) -> Any:
        return self.request("PATCH", path, body=body, expected_status=(200,), timeout=timeout)

    def put(self, path: str, body: Any, timeout: float | None = None) -> Any:
        return self.request("PUT", path, body=body, expected_status=(200,), timeout=timeout)

    def post(self, path: str, body: Any = None, timeout: float | None = None) -> Any:
        return self.request("POST", path, body=body, expected_status=(200, 202), timeout=timeout)

    def delete(self, path: str, timeout: float | None = None) -> Any:
        return self.request("DELETE", path, expected_status=(200, 204), timeout=timeout)

    def request(
        self,
        method: str,
        path: str,
        body: Any = None,
        expected_status: tuple[int, ...] = (200,),
        timeout: float | None = None,
        _reauthed: bool = False,
    ) -> Any:
        url = f"{self.base_url}{path}"
        json_body = _coerce_body(body)
        req_timeout = (self.connect_timeout, timeout if timeout is not None else self.timeout)
        logger.debug("%s %s body=%s", method, path, _redact_body(json_body))

        attempt = 0
        while True:
            start = time.monotonic()
            try:
                resp = self._session.request(
                    method,
                    url,
                    json=json_body,
                    headers=self._headers(),
                    timeout=req_timeout,
                    verify=self.verify,
                )
            except requests.exceptions.Timeout as exc:
                if attempt < self.retries:
                    self._sleep_backoff(attempt)
                    attempt += 1
                    continue
                raise NsxtTimeoutError(
                    f"{method} {path} timed out after {attempt + 1} attempt(s)"
                ) from exc
            except requests.exceptions.RequestException as exc:
                if attempt < self.retries:
                    self._sleep_backoff(attempt)
                    attempt += 1
                    continue
                raise NsxtConnectionError(f"{method} {path} failed: {exc}") from exc

            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.info("%s %s -> %s (%dms)", method, path, resp.status_code, elapsed_ms)

            if resp.status_code == 401 and not _reauthed and self.active_auth == "session":
                logger.info("Session expired for %s, re-authenticating", self.host)
                if self._try_session_auth():
                    return self.request(
                        method, path, body=body, expected_status=expected_status,
                        timeout=timeout, _reauthed=True,
                    )
                raise NsxtAuthError(f"Re-authentication failed for {self.host}")

            if resp.status_code in (401, 403):
                raise NsxtAuthError(f"{method} {path} -> {resp.status_code}")

            retryable = resp.status_code in _RETRY_STATUSES and (
                method in _IDEMPOTENT_METHODS or resp.status_code == 429
            )
            if retryable and attempt < self.retries:
                retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
                self._sleep_backoff(attempt, retry_after)
                attempt += 1
                continue

            if resp.status_code not in expected_status:
                exc_cls = _error_class(resp.status_code)
                raise exc_cls(method, path, resp.status_code, _redact_body(_safe_json(resp)))

            return _safe_json(resp)

    def _sleep_backoff(self, attempt: int, retry_after: float | None = None) -> None:
        if retry_after is not None:
            delay = retry_after
        else:
            ceiling = min(_MAX_BACKOFF_SECONDS, self.backoff * (2**attempt))
            delay = random.uniform(0, ceiling)
        time.sleep(delay)
