"""mock_nsx — an in-memory NSX-T Manager stand-in for hermetic CI test runs.

Not shipped in the published wheel: a dev-only fixture (see the ``mock``
dependency group) that lets the Robot suites in ``tests/`` actually execute
their keyword and client plumbing — auth handshake, retries, realization
polling — without a live NSX-T lab. It validates that plumbing, not NSX
semantics: the generic policy-path store accepts any body you PATCH to it.
"""

from __future__ import annotations
