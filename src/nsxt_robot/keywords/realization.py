"""Realization-polling keywords: Verify Realized, Wait For Realization(s).

Implemented as a plain Python retry loop rather than RF's
``Wait Until Keyword Succeeds`` so the timeout/interval/failure behavior is
directly unit-testable and reports the actual last-seen status on timeout.
"""

from __future__ import annotations

import time
import urllib.parse
from typing import Any

from robot.api.deco import keyword
from robot.utils import timestr_to_secs

from ..connections import NsxtConnectionManager
from ..exceptions import NsxtRealizationError
from .assertions import NsxtApi
from .paths import POLICY_BASE

_assertions = NsxtApi()


class RealizationKeywords:
    """Mixin providing realization-polling keywords. Requires ``self._connections``."""

    _connections: NsxtConnectionManager

    def _get_realized_status(self, intent_path: str) -> Any:
        encoded = urllib.parse.quote(intent_path, safe="")
        return self._connections.current.get(
            f"{POLICY_BASE}/infra/realized-state/status?intent_path={encoded}"
        )

    @keyword("Verify Realized")
    def verify_realized(self, intent_path: str) -> Any:
        """Assert the realization status for a Policy API intent path is SUCCESS."""
        body = self._get_realized_status(intent_path)
        _assertions.realized_state_should_be_success(body)
        return body

    @keyword("Wait For Realization")
    def wait_for_realization(
        self,
        intent_path: str,
        timeout: str = "2 min",
        retry_interval: str = "10 sec",
    ) -> Any:
        """Poll realization status until SUCCESS, raising ``NsxtRealizationError`` on timeout."""
        timeout_s = timestr_to_secs(timeout)
        interval_s = timestr_to_secs(retry_interval)
        deadline = time.monotonic() + timeout_s
        last_body: Any = None
        last_error: Exception | None = None

        while True:
            try:
                last_body = self._get_realized_status(intent_path)
                _assertions.realized_state_should_be_success(last_body)
                return last_body
            except AssertionError as exc:
                last_error = exc
            if time.monotonic() >= deadline:
                raise NsxtRealizationError(intent_path, last_body, last_error) from last_error
            time.sleep(interval_s)

    @keyword("Wait For Realizations")
    def wait_for_realizations(
        self,
        *intent_paths: str,
        timeout: str = "2 min",
        retry_interval: str = "10 sec",
    ) -> None:
        """Wait for realization of every intent path in the given list."""
        for path in intent_paths:
            self.wait_for_realization(path, timeout=timeout, retry_interval=retry_interval)
