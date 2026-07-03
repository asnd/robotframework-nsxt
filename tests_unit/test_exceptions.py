"""Unit tests for the nsxt_robot exception hierarchy."""

from __future__ import annotations

from nsxt_robot.exceptions import NsxtApiError, NsxtRealizationError


def test_api_error_str_without_nsx_body():
    exc = NsxtApiError("GET", "/policy/api/v1/infra/tier-1s/t1", 500, body=None)
    assert str(exc) == "GET /policy/api/v1/infra/tier-1s/t1 -> 500"


def test_api_error_str_includes_nsx_error_message():
    exc = NsxtApiError(
        "PATCH",
        "/policy/api/v1/infra/tier-0s/t0",
        400,
        body={"error_code": 500045, "error_message": "invalid ASN"},
    )
    assert str(exc) == "PATCH /policy/api/v1/infra/tier-0s/t0 -> 400 (error_code 500045): invalid ASN"


def test_api_error_falls_back_to_related_errors_message():
    exc = NsxtApiError(
        "POST",
        "/policy/api/v1/infra/x",
        400,
        body={"related_errors": [{"error_message": "nested failure"}]},
    )
    assert "nested failure" in str(exc)


def test_api_error_exposes_status_and_body():
    exc = NsxtApiError("GET", "/x", 404, body={"error_code": 202})
    assert exc.status == 404
    assert exc.method == "GET"
    assert exc.path == "/x"
    assert exc.error_code == 202


def test_realization_error_message_includes_intent_path():
    exc = NsxtRealizationError("/infra/tier-1s/t1", last_status={"consolidated_status": {}})
    assert "/infra/tier-1s/t1" in str(exc)
