"""Session-token and Basic auth for the mock NSX Manager.

Mirrors just enough of the real handshake to exercise ``NsxtSession``'s auth
code paths: ``POST /api/session/create`` accepts ``j_username``/``j_password``
form fields, sets a ``JSESSIONID`` cookie, and returns an ``X-XSRF-TOKEN``
header that must be echoed back on every mutating request.
"""

from __future__ import annotations

import base64
import secrets


class AuthState:
    def __init__(self, username: str = "admin", password: str = "VMware1!VMware1!") -> None:
        self.username = username
        self.password = password
        self._tokens: set[str] = set()

    def create_session(self, username: str, password: str) -> str | None:
        """Return a new XSRF token if the credentials are valid, else None."""
        if username != self.username or password != self.password:
            return None
        token = secrets.token_hex(16)
        self._tokens.add(token)
        return token

    def check_basic(self, header_value: str | None) -> bool:
        if not header_value or not header_value.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header_value.removeprefix("Basic ")).decode()
        except (ValueError, UnicodeDecodeError):
            return False
        username, _, password = decoded.partition(":")
        return username == self.username and password == self.password

    def check_token(self, token: str | None) -> bool:
        return token is not None and token in self._tokens

    def invalidate(self, token: str | None) -> None:
        if token is not None:
            self._tokens.discard(token)

    def is_authenticated(self, xsrf_token: str | None, authorization: str | None) -> bool:
        return self.check_token(xsrf_token) or self.check_basic(authorization)

    def reset(self) -> None:
        self._tokens.clear()
