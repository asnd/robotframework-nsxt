"""Unit tests for ConnectionKeywords (Open/Switch/Close/Get Nsx Connection)."""

from __future__ import annotations

import pytest

from nsxt_robot.connections import NsxtConnectionManager
from nsxt_robot.keywords import connection as connection_module
from nsxt_robot.keywords.connection import ConnectionKeywords


class _FakeSession:
    def __init__(self, host, **kwargs):
        self.host = host
        self.port = kwargs.get("port", 443)
        self.username = kwargs.get("username", "admin")
        self.active_auth = "session"
        self.verify = kwargs.get("verify", True)
        self.timeout = kwargs.get("timeout", 30)
        self.closed = False

    def close(self):
        self.closed = True


class _Lib(ConnectionKeywords):
    def __init__(self):
        self._connections = NsxtConnectionManager()


@pytest.fixture
def lib(monkeypatch):
    monkeypatch.setattr(connection_module, "NsxtSession", _FakeSession)
    return _Lib()


def test_open_nsx_connection_returns_index(lib):
    index = lib.open_nsx_connection("nsx.example", username="admin", password="secret")
    assert index == 1
    assert lib._connections.current.host == "nsx.example"


def test_open_nsx_connection_ca_bundle_overrides_verify(lib, monkeypatch):
    captured = {}
    real_init = _FakeSession.__init__

    def capturing_init(self, host, **kwargs):
        captured.update(kwargs)
        real_init(self, host, **kwargs)

    monkeypatch.setattr(_FakeSession, "__init__", capturing_init)
    lib.open_nsx_connection("nsx.example", ca_bundle="/etc/ssl/ca.pem", verify=False)
    assert captured["verify"] == "/etc/ssl/ca.pem"


def test_switch_nsx_connection_returns_previous_index(lib):
    lib.open_nsx_connection("a.example", alias="a")
    lib.open_nsx_connection("b.example", alias="b")
    previous = lib.switch_nsx_connection("a")
    assert previous == 2
    assert lib._connections.current.host == "a.example"


def test_close_nsx_connection_closes_current(lib):
    lib.open_nsx_connection("a.example")
    session = lib._connections.current
    lib.close_nsx_connection()
    assert session.closed is True
    with pytest.raises(RuntimeError):
        _ = lib._connections.current


def test_close_all_nsx_connections_closes_every_session(lib):
    lib.open_nsx_connection("a.example")
    lib.open_nsx_connection("b.example")
    sessions = list(lib._connections._cache)
    lib.close_all_nsx_connections()
    assert all(s.closed for s in sessions)


def test_get_nsx_connection_masks_no_secrets_and_reports_fields(lib):
    lib.open_nsx_connection("a.example", username="admin", port=8443)
    info = lib.get_nsx_connection()
    assert info == {"host": "a.example", "port": 8443, "username": "admin", "auth": "session", "verify": True}


def test_set_nsx_timeout_returns_previous_value(lib):
    lib.open_nsx_connection("a.example", timeout=30)
    previous = lib.set_nsx_timeout(60)
    assert previous == 30
    assert lib._connections.current.timeout == 60
