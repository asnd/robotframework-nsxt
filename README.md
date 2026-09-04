# robotframework-nsxt

A reusable **Robot Framework library for testing VMware NSX-T 4.x**, plus an
acceptance-test suite that uses it. The library drives the **control plane** via the
NSX Policy/Management REST API (`nsxt_robot.NsxtLibrary`, a `requests`-based client with
session-token auth, retries, and connection management) and validates the **data plane**
from test VMs using [`bbprobe`](https://github.com/asnd/bbprobe) — a single-shot,
agentless network probe that emits parseable JSON over SSH.

- **Distribution:** `robotframework-nsxt` · **import name:** `nsxt_robot`
- Ships two Python keyword libraries (`nsxt_robot.NsxtLibrary` for connections/REST/
  Policy-Mgmt-API operations/realization, `nsxt_robot.NsxtApi` for JSON extraction/
  assertions) and six `.robot` resource files under `nsxt_robot/resources/`, importable
  from any suite once installed.
- **Full keyword reference:** generated libdoc HTML publishes to GitHub Pages on every
  push to `main` (see [Keyword docs](#keyword-docs)); this README covers architecture,
  setup, and the parts worth explaining in prose.

## Quick start

```sh
uv sync --locked --group dev
cp env.example.yaml env.yaml    # then fill in your NSX Manager + test VMs
uv run robot -d results -V env.yaml tests/
```

Or against the mock NSX Manager, no lab required:

```sh
uv run --group mock python -m mock_nsx --port 8443 &
uv run robot -d results -V env.mock.yaml -e dataplane -e destructive -e ha -e evpn tests/
```

A suite of your own needs three lines to start driving NSX:

```robotframework
*** Settings ***
Library    nsxt_robot.NsxtLibrary
Library    nsxt_robot.NsxtApi

*** Test Cases ***
Example
    Open Nsx Connection    ${NSX_MANAGER}    ${NSX_USER}    ${NSX_PASSWORD}
    ${status}=    NSX REST GET    /api/v1/cluster/status
    Manager Cluster Should Be Stable    ${status}
    [Teardown]    Close All Nsx Connections
```

## Architecture

```
┌─────────────────────────────┐     ┌──────────────────────────────────────┐
│ nsxt_robot.NsxtLibrary       │     │ nsxt_robot.NsxtApi                    │
│  keywords/connection.py      │     │  keywords/assertions.py               │
│   Open/Switch/Close Nsx      │     │   Get Value / Find In List / Get Ids  │
│   Connection, Set Nsx Timeout│     │   *Should Be* typed assertions        │
│  keywords/rest.py             │     └──────────────────────────────────────┘
│   NSX REST GET/PATCH/POST/    │                       ▲
│   DELETE(+ Ignore Error)      │                       │ operates on bodies
│  keywords/realization.py      │                       │ NsxtLibrary returns
│   Verify Realized,            │───────────────────────┘
│   Wait For Realization(s)     │
│  keywords/{gateways,routing,  │
│   services,security,fabric}.py│   ← every Policy/Mgmt API keyword
│   T1/T0/VRF, NAT, LB, DFW, …  │
└──────────────┬────────────────┘
               │ requests.Session
               ▼
      ┌─────────────────┐        ┌──────────────────────────────┐
      │ NsxtSession       │◄──── │ real NSX-T Manager, or        │
      │ (client.py)       │      │ mock_nsx/ (FastAPI, dev-only) │
      │ session/basic auth,│      └──────────────────────────────┘
      │ retry, redaction   │
      └─────────────────┘

      ssh_keywords.robot / traffic_keywords.robot / bbprobe_keywords.robot
      (SSHLibrary-based; unrelated to the HTTP client above — the data-plane
       side of the library, driving test VMs directly over SSH)
```

Everything under `nsxt_robot.NsxtLibrary` is plain Python (auth, retries, connection
cache, all ~100 Policy/Mgmt API keywords); `common.robot`/`policy_api.robot` are now thin
shims kept only for backward compatibility and shared variables (`${T0_PATH}` etc.) —
see [Migration notes](#migration-notes-for-01x-users) if you're upgrading from `0.1.x`.

### Layout

```
robotframework-nsxt/
├── pyproject.toml               # packaging (hatchling), deps, ruff/mypy/robocop config
├── env.example.yaml             # copy to env.yaml and edit (env.yaml is gitignored)
├── env.mock.yaml                # variables for running against mock_nsx/ instead of a lab
├── Containerfile.mock           # Podman image for mock_nsx/
├── src/nsxt_robot/
│   ├── __init__.py              # exports NsxtLibrary, NsxtApi, __version__
│   ├── library.py               # NsxtLibrary: composes every keyword mixin below
│   ├── client.py                # NsxtSession: auth, retries, redaction (requests-based)
│   ├── connections.py           # ConnectionCache wrapper (Open/Switch/Close Nsx Connection)
│   ├── exceptions.py            # typed exception hierarchy
│   ├── models.py                # permissive TypedDicts for the fields the library reads
│   ├── keywords/                # connection, rest, realization, fabric, gateways, routing,
│   │                            #   services, security mixins + assertions.py (NsxtApi)
│   ├── api.py                   # back-compat shim re-exporting NsxtApi from keywords/assertions.py
│   └── resources/
│       ├── common.robot         # Initialize REST Session shim, shared vars, teardown
│       ├── policy_api.robot     # shim: keywords now live on NsxtLibrary (keywords/*.py)
│       ├── ssh_keywords.robot   # pooled SSH connection management (reused per host)
│       ├── traffic_keywords.robot  # SSH traffic keywords (reachability delegates to bbprobe)
│       ├── bbprobe_keywords.robot  # deploy + run bbprobe; structured probe assertions
│       └── failure_keywords.robot  # fault injection: segment/BGP/edge-node + convergence asserts
├── mock_nsx/                    # FastAPI mock NSX Manager (dev-only, `mock` dependency group)
├── tests_unit/                  # pytest unit tests for the library and the mock
├── scripts/gen_docs.sh          # generate libdoc keyword docs into docs/
└── tests/                       # Robot acceptance suites (consume the library)
    ├── 00_provision/            # deploy bbprobe to the VMs (runs first)
    ├── 01_infra/  02_t1_connectivity/  03_static_routing/
    ├── 04_bgp_bfd/  05_ha_vip/  06_snat/  (SNAT + DNAT)  07_alb_l4/
    ├── 08_dfw/                  # distributed firewall micro-segmentation (groups, tags, allow/deny)
    ├── 09_alb_l7/               # L7 HTTP load balancer + active health monitor
    ├── 10_t0_vrf/               # T0-VRF gateway: uplink interface, static routing, BFD, BGP, EVPN
    └── 11_failover/             # fault injection: segment/BGP/edge-node failures + recovery SLA
```

Service coverage: infra health, T1 connectivity, static routing, BGP/BFD, HA VIP,
NAT (SNAT + DNAT), L4 + L7 load balancing with health monitors, distributed
firewall micro-segmentation (IP + dynamic tag groups, allow/deny enforcement),
Tier-0 VRF gateways (VRF-lite and EVPN: external interfaces, VRF static routing with
BFD-protected next hops, VRF BGP, RD/RT/transit-VNI), and fault injection with
recovery-SLA assertions (segment/BGP/edge-node failures). Data-plane assertions include
reachability, latency SLA, deny-path verification, and overlay MTU.

## Install

```sh
uv sync --locked --group dev                # this repo (editable, with dev tools, from the committed lockfile)
# or, as a dependency of your own test project:
uv pip install robotframework-nsxt          # (once published) or: uv pip install <path-or-git-url>
```

## Connection management

`NsxtLibrary` follows the same `ConnectionCache`-backed pattern as SSHLibrary: open one
or more connections, operate on the current one, switch or close as needed. Useful for
multi-manager testing (e.g. federation, or a manager plus a witness).

| Keyword | Purpose |
|---|---|
| `Open Nsx Connection  host  [username]  [password]  [alias]  [port]  [auth]  [verify]  [ca_bundle]  [timeout]  [connect_timeout]  [retries]  [backoff]` | Authenticate and register a connection; returns its index |
| `Switch Nsx Connection  alias_or_index` | Make another open connection current; returns the *previous* index |
| `Close Nsx Connection` | Close the current connection (logs out if session-authenticated) |
| `Close All Nsx Connections` | Close every open connection; suite-teardown idiom |
| `Get Nsx Connection  [index_or_alias]` | Connection info (host/port/auth mode), secrets masked |
| `Set Nsx Timeout  timeout` | Change the current connection's read timeout; returns the previous value |

`common.robot`'s `Initialize REST Session` keyword is a thin wrapper: `Open Nsx
Connection  ${NSX_MANAGER}  ${NSX_USER}  ${NSX_PASSWORD}  alias=default  port=${NSX_PORT}
verify=${VERIFY_SSL}`. Existing suites that call it need no changes.

## Auth & TLS

`Open Nsx Connection`'s `auth` argument is `auto` (default), `session`, or `basic`:

- **`auto`** tries NSX session-token auth first (`POST /api/session/create`, then an
  `X-XSRF-TOKEN` header on every request) and falls back to Basic auth if that endpoint
  is unavailable (older NSX releases, some VMC deployments). A single re-authentication
  is attempted automatically if a request comes back `401` (session expired).
- **`password`** defaults to the `NSX_PASSWORD` environment variable when not given, so
  CI can inject a secret without a credentials file on disk.
- **`verify`** accepts `${True}`/`${False}` or a CA bundle path (`ca_bundle` is an alias
  for the same option); `verify=${False}` logs one prominent warning per connection —
  don't use it outside a lab.
- Credentials and tokens are **never logged**: request/response logging redacts
  `Authorization`, `Cookie`, `X-XSRF-TOKEN`, and any `password`/`j_password` body field,
  and this is unit-tested (`tests_unit/test_redaction.py`).
- Retries use exponential backoff with jitter and honor a `Retry-After` header on `429`;
  GET/PUT/PATCH/DELETE retry on connection errors and `429/502/503/504`, POST only on
  `429` (it isn't safe to blindly retry a non-idempotent action).

## Configure

```sh
cp env.example.yaml env.yaml    # then edit (env.yaml is gitignored)
```

- Fill in your NSX Manager, test-VM IPs, and per-service values (all `10.x.x.x` / `xxx`
  placeholders). **Credentials:** `NSX_PASSWORD` / `VM_PASSWORD` in `env.yaml` are used by
  default, but the `NSX_PASSWORD` / `VM_PASSWORD` **environment variables win when set**, so
  CI can inject secrets without a creds file on disk. Passwords are never logged.
- Two Linux test VMs reachable over SSH (`VM1_IP`, `VM2_IP`); override `VM_SSH_PORT`
  (default `22`) and `@{TEST_VM_IPS}` to change the port or the set of probed hosts.
- The **bbprobe binary** for the VM architecture (usually `linux/amd64`). Build it from
  the sibling `blackbox-ssh` repo (`make linux-amd64` → `dist/bbprobe-linux-amd64`); the
  default `BBPROBE_LOCAL_PATH` resolves to it relative to this repo. To use a different
  build (e.g. a downloaded `v0.9.0` release asset), set an absolute `BBPROBE_LOCAL_PATH`.

## Running against a live lab

```sh
# everything, with the environment file
robot -d results -V env.yaml tests/

# a single service area by tag
robot -d results -V env.yaml -i t1 tests/
robot -d results -V env.yaml -i bgp tests/

# structure check without touching the lab (no keywords execute)
robot --dryrun -V env.example.yaml tests/
```

The `00_provision` suite deploys bbprobe and must run before the traffic-dependent
suites (it is ordered first by the `00_` prefix, so a full `tests/` run is correct).

Exclusion tags for fabrics that can't support everything:

| Tag | Meaning | Exclude with |
|---|---|---|
| `dataplane` | SSHes to a VM or runs bbprobe — needs real VMs (not satisfied by `mock_nsx`) | `-e dataplane` |
| `destructive` | Real SSH restart/reboot of an edge node; also gated on `${EDGE_PASSWORD}` being set | `-e destructive` |
| `ha` | Needs ≥2 edges in `${EDGE_CLUSTER_ID}` (edge maintenance-mode failover) | `-e ha` |
| `evpn` | Mutates the **parent** T0's EVPN config (persists after teardown) | `-e evpn` |

## Mock NSX Manager (`mock_nsx/`)

A small FastAPI stand-in for an NSX-T Manager, used to run the control-plane suites
for real in CI (and locally) without a live lab — it validates the keyword/client
plumbing (auth handshake, retries, realization polling), not NSX semantics: the
generic Policy API store accepts and echoes back whatever you PATCH to it.

```sh
# start it (self-signed TLS by default — NsxtSession only speaks https://)
uv run --group mock python -m mock_nsx --port 8443 &

# run the control-plane suites against it (dataplane/destructive/ha/evpn tests
# need real VMs or a real edge, so they stay excluded)
uv run robot -d results -V env.mock.yaml -e dataplane -e destructive -e ha -e evpn tests/

# or in Podman (HEALTHCHECK needs the Docker image format)
podman build --format docker -f Containerfile.mock -t mock-nsx .
podman run --rm -p 8443:8443 mock-nsx
```

On a host behind a corporate proxy, see the troubleshooting note at the top of
`Containerfile.mock` if the container's HEALTHCHECK reports unhealthy.

## bbprobe deployment (data plane)

`tests/00_provision/deploy_bbprobe.robot` copies the binary to every VM before any
traffic test runs. It uses the keywords in `nsxt_robot/resources/bbprobe_keywords.robot`:

- **`Deploy bbprobe To VM  ${vm_ip}`** — SCPs `${BBPROBE_LOCAL_PATH}` to
  `${BBPROBE_REMOTE_PATH}` (`/usr/local/bin/bbprobe`) via SSHLibrary `Put File`
  (`mode=0755`), runs `bbprobe --version` to confirm it works, and grants
  unprivileged ICMP.
- **`Deploy bbprobe To All Test VMs`** — loops every host in `@{TEST_VM_IPS}`
  (default `VM1_IP`, `VM2_IP`; override to cover any number of VMs).

### ICMP without root

The ICMP probe needs raw-socket capability. The deploy keyword applies one of
these on the VM automatically (VM_USER is root); if you provision the VMs
yourself, set one of:

```sh
setcap cap_net_raw+ep /usr/local/bin/bbprobe                 # per-binary
# or
sysctl -w net.ipv4.ping_group_range="0 2147483647"           # system-wide
```

`bbprobe` modules used: `icmp`, `tcp_connect` (target `host:port`), `http_2xx`. Core
keywords: `Probe Should Succeed`/`Probe Should Fail`, `Probe Latency Should Be Below`,
`Service Data Plane Should Be Reachable` (waits for realization, then probes). The
reachability keywords in `traffic_keywords.robot` (`Ping From VM`, `TCP Connect From
VM`, …) delegate to these; three checks stay on shell tools because bbprobe cannot
express them: `Verify Source IP From VM`/`Verify HTTP Response From VM` assert on the
HTTP response **body** (curl), and `Verify Overlay MTU From VM` sends a full-size
**DF-bit** ICMP packet to validate the overlay carries a 1500-byte inner frame without
fragmenting. Full keyword reference: [Keyword docs](#keyword-docs).

## T0-VRF and EVPN (`nsxt_robot.NsxtLibrary` + `tests/10_t0_vrf`)

A T0-VRF is itself a tier-0 object, so every `... On T0` keyword (BGP, static routes,
interfaces, locale services) works against a VRF's ID unchanged. On top of that:

- `Create VRF Gateway On T0` — VRF-lite by default; optional `route_distinguisher`,
  `import_rts`/`export_rts` (L2VPN_EVPN route targets), and `evpn_transit_vni` for EVPN.
- `Create T0 Locale Service` / `Create T0 External Interface` — uplinks on VLAN segments
  (`Create VLAN Segment`), pinned to an edge node via `Get Edge Nodes In Cluster`.
- `Create Static Route On T0` + `Create BFD Profile` + `Create Static Route BFD Peer On T0`
  — VRF static routing with BFD-withdrawn next hops.
- `Enable BGP On T0 Locale Service` — for VRFs, which inherit the parent's ASN
  (use `Configure BGP On T0` only on the parent/standalone T0).
- `Create VNI Pool` / `Configure EVPN On T0` / `Create EVPN Tunnel Endpoint On T0` —
  EVPN INLINE / ROUTE_SERVER enablement on the parent T0.

The `tests/10_t0_vrf` suite runs the full lifecycle; its `evpn`-tagged tests mutate the
**parent** T0 (EVPN mode persists after teardown) — exclude them with `-e evpn` on
fabrics without EVPN. EVPN field names follow the NSX 4.x schemas and are the most
version-sensitive part of the Policy API; verify against your release's API reference
on the first live run.

## Failure simulation (`failure_keywords.robot` + `tests/11_failover`)

Resilience testing needs to *inject* failures, not just verify positive-path config. Every
injection keyword has a paired restore keyword, and convergence is measured from the data
plane with the existing bbprobe keywords via `Data Plane Should Recover Within` /
`Data Plane Should Be Down Within`.

| Failure | Keyword(s) | Restore |
|---|---|---|
| Segment (or T0/T0-VRF uplink — its backing VLAN segment) | `Fail Segment` | `Restore Segment` |
| BGP session (T0 or T0-VRF) | `Disable BGP On T0 Locale Service` | `Enable BGP On T0 Locale Service` |
| BGP neighbor | `Delete BGP Neighbor On T0` | `Create BGP Neighbor On T0` |
| Edge node drain/failover | `Enter Edge Maintenance Mode` | `Exit Edge Maintenance Mode` |
| Edge node hard failure (**destructive**) | `Restart Edge Dataplane`, `Reboot Edge Node` | recovers on its own; assert with `Data Plane Should Recover Within` |

`Restart Edge Dataplane` and `Reboot Edge Node` SSH into the edge CLI and cause a real
outage — they run only when `${EDGE_PASSWORD}` is set (empty by default, unlike
`NSX_PASSWORD`/`VM_PASSWORD`, so they're opt-in) and are tagged `destructive` for
wholesale exclusion with `-e destructive`. The edge maintenance-mode failover test is
tagged `ha` and needs ≥2 edges in `${EDGE_CLUSTER_ID}` (exclude with `-e ha` on a
single-edge lab). There is no API-level "power off a T0/T0-VRF" — its failure is
represented by its uplink path (segment admin-down) and by the edge node carrying it,
which is also what fails in production.

## NsxtApi assertion keywords

Used alongside `nsxt_robot.NsxtLibrary` — its getter keywords (`Get T1 Gateway`,
`Get Group Members`, ...) return bodies; `NsxtApi` parses and asserts on them,
replacing `Get From Dictionary` chains and `Evaluate next(...)`: `Get Value`
(dotted/indexed lookup), `Find In List`, `Get Ids`, and typed assertions
(`Realized State Should Be Success`, `Manager Cluster Should Be Stable`,
`BGP Neighbor Should Be Established`, `BFD Should Be Healthy`, `Pool Member Should Be
Up`, `NAT Rule Should Exist`, `DFW Rule Should Have Action`, `Group Should Have
Member`, `VRF Should Be Linked To Parent`, `Compute Manager Should Be Registered`).
Full signatures: [Keyword docs](#keyword-docs).

## Migration notes for 0.1.x users

`0.1.0` built keywords on RESTinstance directly in `.robot` resources; `1.0.0` moves all
of that to Python on `NsxtLibrary` while keeping every keyword name and argument order
unchanged — **no suite needs to change**. What's different if you're upgrading:

- `Initialize REST Session` still works, but now opens a session-token connection (with
  Basic-auth fallback) instead of building a Basic header on a RESTinstance session; TLS
  `verify` now defaults to `${True}` (was implicitly permissive) — set `VERIFY_SSL:
  false` explicitly in your `env.yaml` if your lab uses a self-signed cert without a CA
  bundle.
- `RESTinstance` is no longer a dependency; if you imported it directly (rather than
  through this library), add it to your own project.
- New capability, not required: `Open Nsx Connection`/`Switch Nsx Connection`/`Close
  Nsx Connection` for multi-manager suites (see [Connection management](#connection-management)).

## NSX version compatibility

There is no VMware/Broadcom "NSX 5.x" — the version line went 4.0 → 4.1 → 4.2.x,
then jumped straight to NSX 9.0; the 4.0 rename from "NSX-T Data Center" to "NSX"
was cosmetic and introduced no API break. Compatibility notes for this library
against that timeline:

- Nearly every keyword (`routing.py`, `gateways.py`, `security.py`, `services.py`,
  `realization.py`, `assertions.py`) targets the Policy API (`/policy/api/v1/infra/*`),
  which is VMware's actively-recommended, forward-compatible surface.
- Session-cookie auth (`/api/session/create`, `X-XSRF-TOKEN`) is unaffected by any
  of the above changes and remains the current mechanism for both Manager and
  Policy API calls.
- `fabric.py`'s 6 read-only fabric/health GETs (cluster status, transport-zones,
  transport-node status, compute-managers) are the only calls on the Management API
  (`/api/v1/*`), which has carried a standing deprecation notice since NSX-T 3.2 with
  no fixed removal date yet (as of NSX 4.2.4). This is the one module to revisit first
  if a future NSX major removes Manager API support.
- The `07_alb_l4`/`09_alb_l7` suites exercise NSX's native Policy-managed load
  balancer (`/infra/lb-*`), not the separate NSX Advanced Load Balancer (Avi)
  integration that Broadcom has deprecated — the suite names predate that
  distinction and shouldn't be read as using the deprecated surface.

## Keyword docs

Full keyword reference (all `NsxtLibrary`/`NsxtApi` keywords and `.robot` resources)
publishes to GitHub Pages on every push to `main`. Generate it locally:

```sh
scripts/gen_docs.sh          # writes docs/*.html (gitignored)
```

## Development checks

The same gates run in CI (`.github/workflows/ci.yml`, matrix over Python 3.11–3.13):

```sh
uv sync --locked --group dev                 # install from the committed lockfile
uv run ruff check .                          # lint Python
uv run mypy src/ mock_nsx/                   # type-check the library and the mock
uv run pytest -q --cov=nsxt_robot --cov=mock_nsx --cov-report=term  # unit tests + coverage
uv run robocop check src/ tests/             # lint the Robot code
uv run robot --dryrun -V env.example.yaml tests/   # all keywords/imports resolve
uv run --group mock python -m mock_nsx --port 8443 &        # then:
uv run robot -V env.mock.yaml -e dataplane -e destructive -e ha -e evpn tests/
uv build                                     # wheel + sdist in dist/
```

Versioning follows [semver](https://semver.org/): a keyword scheduled for removal is
deprecated (documented + a runtime warning) for at least one minor release before it's
dropped. See `CHANGELOG.md` for what changed release to release.
