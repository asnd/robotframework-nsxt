"""Shared fixtures: a fake requests transport so client tests never touch a real socket."""

from __future__ import annotations

import json
from typing import Any

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


class SpySession:
    """Records every GET/PATCH/POST/DELETE call for keyword-level unit tests.

    GET responses are canned per-path via ``responses``; PATCH/POST echo the
    body back merged with ``{"path": path}`` (mirroring mock_nsx's own
    upsert semantics) unless a canned response is registered for that path.
    """

    def __init__(self):
        self.calls: list[tuple[str, str, Any]] = []
        self.responses: dict[str, Any] = {}

    def when(self, path: str, response: Any) -> None:
        self.responses[path] = response

    def get(self, path):
        self.calls.append(("GET", path, None))
        return self.responses.get(path)

    def patch(self, path, body):
        self.calls.append(("PATCH", path, body))
        return self.responses.get(path, {"path": path, **(body or {})})

    def post(self, path, body=None):
        self.calls.append(("POST", path, body))
        return self.responses.get(path, {"path": path})

    def delete(self, path):
        self.calls.append(("DELETE", path, None))
        return self.responses.get(path)

    @property
    def last(self) -> tuple[str, str, Any]:
        return self.calls[-1]


class SpyConnections:
    def __init__(self, session: SpySession):
        self.current = session


@pytest.fixture
def spy_session():
    return SpySession()


@pytest.fixture
def spy_connections(spy_session):
    return SpyConnections(spy_session)
