"""Shared fixtures: a fake requests transport so client tests never touch a real socket."""

from __future__ import annotations

import json

import pytest
import requests
from requests.adapters import BaseAdapter


class FakeAdapter(BaseAdapter):
    """A requests transport adapter serving canned responses from a handler queue.

    ``handler(request) -> (status, headers, body)`` is called for every request;
    ``body`` is JSON-encoded automatically (or left empty if ``None``).
    """

    def __init__(self, handler):
        super().__init__()
        self.handler = handler
        self.calls: list[requests.PreparedRequest] = []

    def send(self, request, **kwargs):
        self.calls.append(request)
        status, headers, body = self.handler(request)
        resp = requests.Response()
        resp.status_code = status
        resp.headers.update(headers or {})
        resp._content = json.dumps(body).encode() if body is not None else b""
        resp.request = request
        resp.url = request.url
        return resp

    def close(self) -> None:
        pass


def make_fake_session(handler) -> tuple[requests.Session, FakeAdapter]:
    """Build a requests.Session with the fake adapter mounted for https://."""
    session = requests.Session()
    adapter = FakeAdapter(handler)
    session.mount("https://", adapter)
    return session, adapter


@pytest.fixture
def fake_session_factory():
    return make_fake_session
