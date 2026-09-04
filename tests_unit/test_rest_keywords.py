"""Unit tests for RestKeywords (`NSX REST *` keywords)."""

from __future__ import annotations

import pytest

from nsxt_robot.keywords.rest import RestKeywords


class _FakeSession:
    def __init__(self):
        self.calls = []
        self.fail_next = False

    def get(self, path):
        self.calls.append(("GET", path))
        return {"path": path}

    def patch(self, path, body):
        self.calls.append(("PATCH", path, body))
        return {"path": path, **body}

    def post(self, path, body=None):
        self.calls.append(("POST", path, body))
        return {"path": path}

    def delete(self, path):
        self.calls.append(("DELETE", path))
        if self.fail_next:
            raise RuntimeError(f"boom deleting {path}")
        return None


class _FakeConnections:
    def __init__(self, session):
        self.current = session


class _Lib(RestKeywords):
    def __init__(self, session):
        self._connections = _FakeConnections(session)


@pytest.fixture
def session():
    return _FakeSession()


@pytest.fixture
def lib(session):
    return _Lib(session)


def test_nsx_rest_get(lib, session):
    result = lib.nsx_rest_get("/policy/api/v1/infra/tier-1s/t1")
    assert result == {"path": "/policy/api/v1/infra/tier-1s/t1"}
    assert session.calls == [("GET", "/policy/api/v1/infra/tier-1s/t1")]


def test_nsx_rest_patch(lib, session):
    result = lib.nsx_rest_patch("/infra/tier-1s/t1", {"display_name": "t1"})
    assert result["display_name"] == "t1"
    assert session.calls == [("PATCH", "/infra/tier-1s/t1", {"display_name": "t1"})]


def test_nsx_rest_post_with_body(lib, session):
    lib.nsx_rest_post("/infra/x?action=y", {"a": 1})
    assert session.calls == [("POST", "/infra/x?action=y", {"a": 1})]


def test_nsx_rest_post_without_body(lib, session):
    lib.nsx_rest_post("/infra/x?action=y")
    assert session.calls == [("POST", "/infra/x?action=y", None)]


def test_nsx_rest_delete(lib, session):
    result = lib.nsx_rest_delete("/infra/tier-1s/t1")
    assert result is None
    assert session.calls == [("DELETE", "/infra/tier-1s/t1")]


def test_nsx_rest_delete_ignore_error_swallows_exception(lib, session):
    session.fail_next = True
    lib.nsx_rest_delete_ignore_error("/infra/tier-1s/missing")  # must not raise
    assert session.calls == [("DELETE", "/infra/tier-1s/missing")]


def test_nsx_rest_delete_ignore_error_passes_through_on_success(lib, session):
    lib.nsx_rest_delete_ignore_error("/infra/tier-1s/t1")
    assert session.calls == [("DELETE", "/infra/tier-1s/t1")]
