"""Unit tests for NsxtConnectionManager (the ConnectionCache wrapper)."""

from __future__ import annotations

import pytest

from nsxt_robot.connections import NsxtConnectionManager


class _FakeSession:
    def __init__(self, name):
        self.name = name
        self.closed = False

    def close(self):
        self.closed = True


def test_open_returns_incrementing_index():
    mgr = NsxtConnectionManager()
    idx1 = mgr.open(_FakeSession("a"))
    idx2 = mgr.open(_FakeSession("b"))
    assert idx1 == 1
    assert idx2 == 2
    assert mgr.current.name == "b"


def test_open_with_alias_and_switch_by_alias():
    mgr = NsxtConnectionManager()
    mgr.open(_FakeSession("a"), alias="mgr-a")
    mgr.open(_FakeSession("b"), alias="mgr-b")
    previous = mgr.switch("mgr-a")
    assert mgr.current.name == "a"
    assert previous == 2


def test_switch_by_index():
    mgr = NsxtConnectionManager()
    mgr.open(_FakeSession("a"))
    mgr.open(_FakeSession("b"))
    mgr.switch(1)
    assert mgr.current.name == "a"


def test_current_raises_when_no_connection_open():
    mgr = NsxtConnectionManager()
    with pytest.raises(RuntimeError):
        _ = mgr.current


def test_close_current_closes_session_and_clears_current():
    mgr = NsxtConnectionManager()
    session_a = _FakeSession("a")
    mgr.open(session_a)
    mgr.close_current()
    assert session_a.closed is True
    with pytest.raises(RuntimeError):
        _ = mgr.current


def test_close_all_closes_every_session_and_resets_indices():
    mgr = NsxtConnectionManager()
    session_a = _FakeSession("a")
    session_b = _FakeSession("b")
    mgr.open(session_a)
    mgr.open(session_b)
    mgr.close_all()
    assert session_a.closed is True
    assert session_b.closed is True
    new_index = mgr.open(_FakeSession("c"))
    assert new_index == 1  # cache reset, indices restart


def test_get_returns_specific_connection_without_switching_current():
    mgr = NsxtConnectionManager()
    mgr.open(_FakeSession("a"), alias="a")
    mgr.open(_FakeSession("b"), alias="b")
    fetched = mgr.get("a")
    assert fetched.name == "a"
    assert mgr.current.name == "b"  # unchanged
