"""Typed shapes for the NSX-T response fields this library itself inspects.

These are intentionally permissive (``total=False``) TypedDicts, not a strict
schema: NSX field names drift across releases (the EVPN and BFD fields in
particular), and this library must tolerate that drift rather than fail on
benign, unrelated additions or renames. They exist to give mypy coverage of
the handful of fields the keywords in this package read directly — not to
validate arbitrary NSX API responses.
"""

from __future__ import annotations

from typing import Any, TypedDict


class ListResult(TypedDict, total=False):
    results: list[dict[str, Any]]
    result_count: int


class ConsolidatedStatus(TypedDict, total=False):
    consolidated_status: str


class RealizedStatus(TypedDict, total=False):
    consolidated_status: ConsolidatedStatus


class NsxErrorBody(TypedDict, total=False):
    error_code: int
    error_message: str
    related_errors: list[dict[str, Any]]
    httpStatus: str
