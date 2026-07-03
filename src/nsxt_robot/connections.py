"""Connection-cache management for NsxtLibrary, mirroring SSHLibrary's model.

Multiple ``NsxtSession`` connections can be open at once (e.g. two NSX
Managers under federation, or a manager plus a witness); keywords always
operate on the *current* one, selected via alias or index.
"""

from __future__ import annotations

from robot.utils import ConnectionCache

from .client import NsxtSession


class NsxtConnectionManager:
    """Owns the cache of open ``NsxtSession`` connections."""

    def __init__(self) -> None:
        self._cache: ConnectionCache[NsxtSession] = ConnectionCache(
            "No NSX connection is open. Call `Open Nsx Connection` first."
        )

    @property
    def current(self) -> NsxtSession:
        return self._cache.get_connection()  # raises RuntimeError if none is open

    @property
    def current_index(self) -> int | None:
        return self._cache.current_index

    def open(self, session: NsxtSession, alias: str | None = None) -> int:
        return self._cache.register(session, alias)

    def switch(self, alias_or_index: int | str) -> int | None:
        """Switch the current connection, returning the *previous* index."""
        previous = self._cache.current_index
        self._cache.switch(alias_or_index)
        return previous

    def get(self, alias_or_index: int | str | None = None) -> NsxtSession:
        return self._cache.get_connection(alias_or_index)

    def close_current(self) -> None:
        """Close and detach the current connection; it remains at its index."""
        current = self._cache.current
        if current:  # NoConnection.__bool__ is False when nothing is open
            current.close()
        # ConnectionCache has no public "detach one" API; resetting `current`
        # to its own no-connection sentinel is the same trick SSHLibrary uses.
        self._cache.current = self._cache._no_current  # type: ignore[attr-defined]

    def close_all(self) -> None:
        self._cache.close_all()
