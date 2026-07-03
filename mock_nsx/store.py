"""A generic policy-path key/value store simulating NSX Policy API CRUD.

One handler covers every intent object the test suites create (T1/T0
gateways, segments, static routes, NAT rules, LB objects, DFW groups/
policies/rules, VNI pools, ...): PATCH upserts by full path, GET returns the
object or its direct children as a ``results`` list, DELETE removes the path
and any nested children. The store never validates body contents — it just
echoes back whatever was PATCHed, which is exactly what these suites assert
on (they read back the fields they themselves set).
"""

from __future__ import annotations

from typing import Any


class NsxApiError(Exception):
    """Raised by store/derived-state lookups; carries an NSX-shaped error body."""

    def __init__(self, status: int, error_code: int, message: str) -> None:
        self.status = status
        self.body = {
            "httpStatus": "NOT_FOUND" if status == 404 else "ERROR",
            "error_code": error_code,
            "error_message": message,
        }
        super().__init__(message)


class PolicyStore:
    """Path-keyed object store with upsert/get/children/delete-subtree semantics."""

    def __init__(self) -> None:
        self._objects: dict[str, dict[str, Any]] = {}
        self._revision = 0

    def upsert(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        existing = self._objects.get(path, {})
        merged = {**existing, **body}
        merged.setdefault("id", path.rstrip("/").rsplit("/", 1)[-1])
        merged.setdefault("path", path)
        merged.setdefault("display_name", merged["id"])
        self._revision += 1
        merged["_revision"] = self._revision
        self._objects[path] = merged
        return merged

    def set_raw(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Store ``body`` verbatim — for static fixture blobs, not Policy intent objects."""
        self._objects[path] = body
        return body

    def get(self, path: str) -> dict[str, Any] | None:
        return self._objects.get(path)

    def get_or_404(self, path: str) -> dict[str, Any]:
        obj = self.get(path)
        if obj is None:
            raise NsxApiError(404, 202, f"The object at '{path}' was not found")
        return obj

    def children(self, path: str) -> list[dict[str, Any]]:
        prefix = path.rstrip("/") + "/"
        return [
            obj
            for key, obj in self._objects.items()
            if key.startswith(prefix) and "/" not in key[len(prefix) :]
        ]

    def list_response(self, path: str) -> dict[str, Any]:
        results = self.children(path)
        return {"results": results, "result_count": len(results)}

    def delete_subtree(self, path: str) -> bool:
        keys = [k for k in self._objects if k == path or k.startswith(path + "/")]
        for k in keys:
            del self._objects[k]
        return bool(keys)

    def reset(self) -> None:
        self._objects.clear()
        self._revision = 0
