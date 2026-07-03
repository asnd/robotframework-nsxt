"""Secrets must never appear in logs or exception text, in any code path."""

from __future__ import annotations

import logging

import pytest

from nsxt_robot.client import NsxtSession
from nsxt_robot.exceptions import NsxtApiError

SECRET = "sup3r-s3cr3t-hunter2"


def test_password_not_logged_during_session_auth(fake_session_factory, caplog):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            assert SECRET in (request.body or "")  # sent over the wire, as expected
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 200, {}, {"ok": True}

    session, _ = fake_session_factory(handler)
    with caplog.at_level(logging.DEBUG, logger="nsxt_robot"):
        conn = NsxtSession("nsx.example", password=SECRET, session=session)
        conn.get("/api/v1/cluster/status")

    assert SECRET not in caplog.text


def test_basic_auth_header_value_not_logged(fake_session_factory, caplog):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 404, {}, None
        return 200, {}, {"ok": True}

    session, _ = fake_session_factory(handler)
    with caplog.at_level(logging.DEBUG, logger="nsxt_robot"):
        conn = NsxtSession("nsx.example", password=SECRET, session=session)
        conn.get("/api/v1/cluster/status")

    assert SECRET not in caplog.text
    assert "Basic " not in caplog.text  # header value itself is never logged


def test_password_field_in_error_body_is_redacted_in_exception(fake_session_factory):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 400, {}, {"error_message": "bad body", "password": SECRET}

    session, _ = fake_session_factory(handler)
    conn = NsxtSession("nsx.example", password=SECRET, session=session)
    with pytest.raises(NsxtApiError) as excinfo:
        conn.patch("/policy/api/v1/infra/x", {"a": 1})
    assert SECRET not in str(excinfo.value)
    assert SECRET not in repr(excinfo.value.body)


def test_outgoing_password_field_is_redacted_in_debug_log(fake_session_factory, caplog):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 200, {}, {"ok": True}

    session, _ = fake_session_factory(handler)
    with caplog.at_level(logging.DEBUG, logger="nsxt_robot"):
        conn = NsxtSession("nsx.example", password=SECRET, session=session)
        conn.patch("/policy/api/v1/infra/x", {"password": SECRET, "id": "x"})

    assert SECRET not in caplog.text


def test_verify_false_logs_exactly_one_warning(fake_session_factory, caplog):
    def handler(request):
        if request.path_url.startswith("/api/session/create"):
            return 200, {"X-XSRF-TOKEN": "tok"}, None
        return 200, {}, {"ok": True}

    session, _ = fake_session_factory(handler)
    with caplog.at_level(logging.WARNING, logger="nsxt_robot"):
        NsxtSession("nsx.example", password="x", verify=False, session=session)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "TLS verification is disabled" in warnings[0].message
