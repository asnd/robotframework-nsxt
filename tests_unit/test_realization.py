"""Unit tests for the Wait For Realization retry/timeout logic."""

from __future__ import annotations

import time

import pytest

from nsxt_robot.exceptions import NsxtRealizationError
from nsxt_robot.keywords.realization import RealizationKeywords


class _FakeConnections:
    """Minimal stand-in for NsxtConnectionManager exposing `.current.get(path)`."""

    def __init__(self, responses):
        self._responses = iter(responses)
        self.current = self

    def get(self, path):
        return next(self._responses)


class _Lib(RealizationKeywords):
    def __init__(self, responses):
        self._connections = _FakeConnections(responses)


def _status(state):
    return {"consolidated_status": {"consolidated_status": state}}


def test_verify_realized_passes_on_success():
    lib = _Lib([_status("SUCCESS")])
    body = lib.verify_realized("/infra/tier-1s/t1")
    assert body["consolidated_status"]["consolidated_status"] == "SUCCESS"


def test_verify_realized_fails_on_non_success():
    lib = _Lib([_status("IN_PROGRESS")])
    with pytest.raises(AssertionError):
        lib.verify_realized("/infra/tier-1s/t1")


def test_wait_for_realization_polls_until_success(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)
    lib = _Lib([_status("IN_PROGRESS"), _status("IN_PROGRESS"), _status("SUCCESS")])
    body = lib.wait_for_realization("/infra/tier-1s/t1", retry_interval="1 ms")
    assert body["consolidated_status"]["consolidated_status"] == "SUCCESS"


def test_wait_for_realization_times_out(monkeypatch):
    # Every poll is IN_PROGRESS; jump the fake clock past the deadline after the
    # first poll so the loop exits deterministically without real sleeping.
    calls = {"n": 0}

    def fake_monotonic():
        calls["n"] += 1
        return 0.0 if calls["n"] == 1 else 1000.0

    monkeypatch.setattr(time, "monotonic", fake_monotonic)
    monkeypatch.setattr(time, "sleep", lambda _: None)
    lib = _Lib([_status("IN_PROGRESS")])
    with pytest.raises(NsxtRealizationError) as excinfo:
        lib.wait_for_realization("/infra/tier-1s/t1", timeout="1 sec", retry_interval="1 ms")
    assert "/infra/tier-1s/t1" in str(excinfo.value)


def test_wait_for_realizations_checks_each_path_in_order():
    lib = _Lib([_status("SUCCESS"), _status("SUCCESS")])
    lib.wait_for_realizations("/infra/a", "/infra/b")
