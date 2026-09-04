"""Unit tests for nsxt_robot.client.NsxtSession — no real network (fake adapter)."""

from __future__ import annotations

import time

import pytest
import requests
from requests.adapters import BaseAdapter

from nsxt_robot.client import NsxtSession, _coerce_body, _parse_retry_after, _redact_body
from nsxt_robot.exceptions import (
    NsxtApiError,
    NsxtAuthError,
    NsxtConflictError,
    NsxtConnectionError,
    NsxtNotFoundError,
    NsxtRateLimitError,
)


def _session_create_ok(token="tok-123"):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": token}, None
        return 200, {}, {"ok": True}

    return handler


# ── authentication ──────────────────────────────────────────────────────────


def test_open_prefers_session_auth(fake_session_factory):
    session, adapter = fake_session_factory(_session_create_ok())
    conn = NsxtSession("nsx.example", username="admin", password="secret", session=session)
    assert conn.active_auth == "session"
    assert adapter.calls[0].path_url.startswith("/api/session/create")


def test_session_auth_sends_xsrf_token(fake_session_factory):
    session, adapter = fake_session_factory(_session_create_ok(token="abc"))
    conn = NsxtSession("nsx.example", password="secret", session=session)
    conn.get("/api/v1/cluster/status")
    last = adapter.calls[-1]
    assert last.headers["X-XSRF-TOKEN"] == "abc"
    assert "Authorization" not in last.headers


def test_falls_back_to_basic_when_session_auth_unavailable(fake_session_factory):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 404, {}, None
        return 200, {}, {"ok": True}

    session, adapter = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", username="admin", password="secret", session=session)
    assert conn.active_auth == "basic"
    conn.get("/api/v1/cluster/status")
    assert adapter.calls[-1].headers["Authorization"].startswith("Basic ")


def test_auth_basic_skips_session_create_entirely(fake_session_factory):
    def handler(request):
        return 200, {}, {"ok": True}

    session, adapter = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", auth="basic", session=session)
    assert conn.active_auth == "basic"
    assert adapter.calls == []  # Basic mode never makes an eager request


def test_auth_session_explicit_raises_when_unavailable(fake_session_factory):
    def handler(request):
        return 404, {}, None

    session, _ = fake_session_factory(handler)
    with pytest.raises(NsxtAuthError):
        NsxtSession("nsx.example", password="secret", auth="session", session=session)


def test_wrong_credentials_raise_auth_error_on_open(fake_session_factory):
    def handler(request):
        return 403, {}, None

    session, _ = fake_session_factory(handler)
    with pytest.raises(NsxtAuthError):
        NsxtSession("nsx.example", password="wrong", session=session)


def test_reauthenticates_once_on_expired_session(fake_session_factory):
    calls = {"session_create": 0}

    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            calls["session_create"] += 1
            return 200, {"X-XSRF-TOKEN": f"tok-{calls['session_create']}"}, None
        if request.headers.get("X-XSRF-TOKEN") == "tok-1":
            return 401, {}, None  # first token has "expired"
        return 200, {}, {"ok": True}

    session, _ = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", session=session)
    body = conn.get("/api/v1/cluster/status")
    assert body == {"ok": True}
    assert calls["session_create"] == 2  # initial auth + one re-auth


def test_reauth_failure_raises_auth_error(fake_session_factory):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 401, {}, None  # every real request stays unauthorized

    session, _ = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", session=session)
    with pytest.raises(NsxtAuthError):
        conn.get("/api/v1/cluster/status")


def test_connection_error_wrapped():
    class RaisingAdapter(BaseAdapter):
        def send(self, request, **kwargs):
            raise requests.exceptions.ConnectionError("refused")

        def close(self):
            pass

    session = requests.Session()
    session.mount("https://", RaisingAdapter())
    with pytest.raises(NsxtConnectionError):
        NsxtSession("nsx.example", password="secret", session=session)


# ── retries ──────────────────────────────────────────────────────────────────


def test_retries_get_on_503_then_succeeds(fake_session_factory, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)
    attempts = {"n": 0}

    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        attempts["n"] += 1
        if attempts["n"] < 2:
            return 503, {}, None
        return 200, {}, {"ok": True}

    session, _ = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", session=session)
    assert conn.get("/api/v1/cluster/status") == {"ok": True}
    assert attempts["n"] == 2


def test_retries_exhausted_raises_api_error(fake_session_factory, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)

    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 503, {}, None

    session, adapter = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", retries=2, session=session)
    with pytest.raises(NsxtApiError) as excinfo:
        conn.get("/api/v1/cluster/status")
    assert excinfo.value.status == 503
    # 1 session-create + (1 initial GET + 2 retries) = 4 calls total
    assert len(adapter.calls) == 4


def test_post_does_not_retry_on_503(fake_session_factory, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)

    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 503, {}, None

    session, adapter = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", retries=3, session=session)
    with pytest.raises(NsxtApiError):
        conn.post("/policy/api/v1/infra/tier-1s/t1", {"id": "t1"})
    assert len(adapter.calls) == 2  # session-create + exactly one POST attempt


def test_post_retries_on_429(fake_session_factory, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)
    attempts = {"n": 0}

    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        attempts["n"] += 1
        if attempts["n"] < 2:
            return 429, {}, None
        return 200, {}, {"ok": True}

    session, _ = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", session=session)
    assert conn.post("/policy/api/v1/infra/tier-1s/t1", {"id": "t1"}) == {"ok": True}
    assert attempts["n"] == 2


def test_429_retry_after_header_honored_then_exhausted(fake_session_factory, monkeypatch):
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", slept.append)

    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 429, {"Retry-After": "2"}, None

    session, _ = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", retries=1, session=session)
    with pytest.raises(NsxtRateLimitError):
        conn.get("/policy/api/v1/infra/tier-1s/t1")
    assert 2.0 in slept


# ── status-to-exception mapping ───────────────────────────────────────────────


def test_404_raises_not_found(fake_session_factory):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 404, {}, {"httpStatus": "NOT_FOUND", "error_code": 202, "error_message": "not found"}

    session, _ = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", session=session)
    with pytest.raises(NsxtNotFoundError):
        conn.get("/policy/api/v1/infra/tier-1s/missing")


def test_409_raises_conflict(fake_session_factory):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 409, {}, {"error_code": 500, "error_message": "stale revision"}

    session, _ = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", session=session)
    with pytest.raises(NsxtConflictError):
        conn.patch("/policy/api/v1/infra/tier-1s/t1", {"_revision": 0})


def test_delete_accepts_204_with_no_body(fake_session_factory):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 204, {}, None

    session, _ = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", session=session)
    assert conn.delete("/policy/api/v1/infra/tier-1s/t1") is None


def test_error_message_from_nsx_body_in_exception_string(fake_session_factory):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 400, {}, {"error_code": 500045, "error_message": "Bad request: invalid ASN"}

    session, _ = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password="secret", session=session)
    with pytest.raises(NsxtApiError) as excinfo:
        conn.patch("/policy/api/v1/infra/tier-0s/t0", {"asn": -1})
    assert "500045" in str(excinfo.value)
    assert "invalid ASN" in str(excinfo.value)


# ── pure helper functions ─────────────────────────────────────────────────────


def test_coerce_body_none_and_empty():
    assert _coerce_body(None) is None
    assert _coerce_body("") is None


def test_coerce_body_json_string():
    assert _coerce_body('{"a": 1}') == {"a": 1}


def test_coerce_body_dict_is_copied_not_aliased():
    body = {"a": 1}
    coerced = _coerce_body(body)
    assert coerced == body
    assert coerced is not body


def test_redact_body_masks_password_keys():
    redacted = _redact_body({"j_password": "hunter2", "other": "keep"})
    assert redacted["j_password"] == "***"
    assert redacted["other"] == "keep"


def test_redact_body_recurses_into_nested_structures():
    redacted = _redact_body({"outer": {"password": "hunter2"}, "list": [{"password": "x"}]})
    assert redacted["outer"]["password"] == "***"
    assert redacted["list"][0]["password"] == "***"


def test_parse_retry_after_numeric():
    assert _parse_retry_after("5") == 5.0


def test_parse_retry_after_http_date_returns_none():
    assert _parse_retry_after("Wed, 21 Oct 2026 07:28:00 GMT") is None


def test_parse_retry_after_none_value():
    assert _parse_retry_after(None) is None
