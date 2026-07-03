# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- The remaining ~70 `policy_api.robot` keywords (T1/T0/VRF gateways,
  segments, static routes, BFD, BGP, EVPN, NAT, LB, HA VIP, tags, groups,
  DFW, plus fabric/infra lookups) are now implemented in Python on
  `NsxtLibrary` (`keywords/{gateways,routing,services,security,fabric}.py`),
  under their exact legacy names and argument signatures. `policy_api.robot`
  is now a shim (keeps `${INFRA_BASE}` for `failure_keywords.robot`); no
  consuming suite needed any changes.
- `NsxtApi`'s assertions moved to `keywords/assertions.py`; `api.py` is now a
  backward-compatible re-export so `from nsxt_robot.api import NsxtApi`
  keeps working.
- The `RESTinstance` dependency is dropped entirely — nothing in the library
  used it after the REST-verb migration in the prior release.
- 85 new unit tests for the migrated keyword modules (gateways/routing/
  services/security/fabric), using a lightweight call-recording fake
  connection rather than the mock server, for fast, precise coverage of
  each keyword's request shape.

- `NsxtLibrary`: a stateful `requests`-based client (`NsxtSession`) with
  session-token auth (falling back to Basic), automatic re-authentication on
  an expired session, retry with backoff honoring `Retry-After`, and
  redaction of credentials from logs/exceptions. Provides connection-cache
  keywords (`Open`/`Switch`/`Close`/`Close All`/`Get Nsx Connection`,
  `Set Nsx Timeout`) in the same style as SSHLibrary.
- `NSX REST GET/PATCH/POST/DELETE(+ Ignore Error)` and `Verify Realized` /
  `Wait For Realization(s)` are now implemented in Python under their exact
  legacy names; `common.robot` opens a connection via `Open Nsx Connection`
  instead of building a Basic-auth header on a RESTinstance session.
  Existing suites and resource files needed no changes.
- Typed exception hierarchy (`NsxtApiError` and its Not Found/Conflict/
  RateLimit subclasses, `NsxtAuthError`, `NsxtConnectionError`,
  `NsxtTimeoutError`, `NsxtRealizationError`) surfacing NSX's own
  `error_code`/`error_message` instead of a bare HTTP status.
- `mock_nsx/`: a FastAPI mock NSX Manager (dev-only, `mock` dependency
  group) so the control-plane suites execute for real in CI instead of only
  `robot --dryrun` — session/Basic auth, a generic Policy API CRUD store,
  a realization simulator, and derived operational state for BGP neighbor
  status/routes, LB pool member status, group effective membership, and
  transport-node maintenance mode. `env.mock.yaml` and `Containerfile.mock`
  (Podman) support running against it locally or in CI. It validates
  keyword/client plumbing, not NSX semantics — live-lab suites remain the
  semantic gate.
- `dataplane` tag added to every test case that SSHes to a VM or runs
  bbprobe, so a mock-backed run can exclude them with `-e dataplane`.
- Test coverage reporting (`pytest-cov`, `fail_under = 90`) across
  `nsxt_robot` and `mock_nsx`.

### Changed

- `uv.lock` is now committed for reproducible builds; CI installs with
  `uv sync --locked`.
- Package version is now single-sourced from `src/nsxt_robot/__init__.py`
  via `[tool.hatch.version]`; `NsxtApi.ROBOT_LIBRARY_VERSION` now reflects
  the package version instead of a hardcoded, drifted value.
- Dev dependencies moved from `[project.optional-dependencies]` to PEP 735
  `[dependency-groups]` (`dev`, `mock`); `PyYAML` promoted to a base runtime
  dependency (Robot's `-V env.yaml` support needs it for any consumer, not
  just this project's own dev loop).
- CI now runs a Python 3.11/3.12/3.13 matrix, uploads a coverage artifact,
  and adds a `robot-mock` job that executes (not just dry-runs) the
  control-plane suites against `mock_nsx`; keyword docs publish to GitHub
  Pages on push to `main`.

### Fixed

- `scripts/gen_docs.sh` now generates libdoc output for `failure_keywords.robot`
  and the new `NsxtLibrary` (previously only `NsxtApi` was documented).
- `env.example.yaml` bbprobe path comment corrected to match the actual
  default in `bbprobe_keywords.robot`.
- Two latent bugs in `tests/08_dfw/dfw.robot` and `tests/10_t0_vrf/t0_vrf.robot`:
  `${{["$VAR"]}}` evaluated to the literal string `"$VAR"` instead of the
  substituted value (RF's bare `$VAR` form isn't substituted inside a quoted
  string in an evaluate expression; `${VAR}` is) — caught only because these
  suites now actually execute against `mock_nsx` instead of only dry-running.

## [0.1.0] - Initial release

- Policy/Management API keyword coverage: T1/T0/VRF gateways, segments,
  static routes, BFD, BGP, HA VIP, NAT, LB, tags, groups, DFW, EVPN,
  infra/fabric management.
- `NsxtApi` extraction and typed-assertion keywords.
- SSH-pooled traffic keywords and `bbprobe`-based structured data-plane
  probing.
- Fault-injection keywords for segment/BGP/edge-node failures.
- CI: ruff, mypy, pytest, robocop, `robot --dryrun`, wheel/sdist build.
- PyPI trusted publishing on `v*` tags.
