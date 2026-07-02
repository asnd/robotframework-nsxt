# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- `uv.lock` is now committed for reproducible builds; CI installs with
  `uv sync --locked`.
- Package version is now single-sourced from `src/nsxt_robot/__init__.py`
  via `[tool.hatch.version]`; `NsxtApi.ROBOT_LIBRARY_VERSION` now reflects
  the package version instead of a hardcoded, drifted value.

### Fixed

- `scripts/gen_docs.sh` now generates libdoc output for
  `failure_keywords.robot` (previously omitted).
- `env.example.yaml` bbprobe path comment corrected to match the actual
  default in `bbprobe_keywords.robot`.

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
