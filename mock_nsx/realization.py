"""Realization-state simulator: a path reports IN_PROGRESS for N polls, then SUCCESS.

Defaults to zero extra polls (immediate SUCCESS) so a full suite run stays
fast — the point is exercising the real GET/parse/assert round trip through
``NsxtLibrary``, not spending wall-clock on an artificial delay. Set
``polls_before_success`` above zero (see the ``/mock/control`` endpoints) to
verify the ``Wait For Realization`` polling loop itself.
"""

from __future__ import annotations


class RealizationSimulator:
    def __init__(self, polls_before_success: int = 0) -> None:
        self.polls_before_success = polls_before_success
        self._poll_counts: dict[str, int] = {}

    def status_for(self, intent_path: str) -> dict[str, dict[str, str]]:
        count = self._poll_counts.get(intent_path, 0)
        self._poll_counts[intent_path] = count + 1
        state = "SUCCESS" if count >= self.polls_before_success else "IN_PROGRESS"
        return {"consolidated_status": {"consolidated_status": state}}

    def reset(self) -> None:
        self._poll_counts.clear()
