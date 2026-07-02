# robotframework-nsxt

A reusable **Robot Framework library for testing VMware NSX-T 4.x**, plus an
acceptance-test suite that uses it. The library drives the **control plane** via the
NSX Policy/Management REST API (RESTinstance) and validates the **data plane** from test
VMs using [`bbprobe`](https://github.com/asnd/bbprobe) — a single-shot, agentless network
probe that emits parseable JSON over SSH.

- **Distribution:** `robotframework-nsxt` · **import name:** `nsxt_robot`
- Ships a Python keyword library (`nsxt_robot.NsxtApi`) and six `.robot` resource files
  under `nsxt_robot/resources/`, importable from any suite once installed.

## Layout

```
nsxt-robot/
├── pyproject.toml               # packaging (hatchling), deps, ruff/mypy/robocop config
├── env.example.yaml             # copy to env.yaml and edit (env.yaml is gitignored)
├── src/nsxt_robot/
│   ├── __init__.py              # exports NsxtApi, __version__
│   ├── api.py                   # NsxtApi: JSON extraction + typed status assertions
│   └── resources/
│       ├── common.robot         # REST session, realization polling, shared vars, teardown
│       ├── policy_api.robot     # NSX Policy/Mgmt API operations (T1/segment/BGP/NAT/LB/DFW/…)
│       ├── ssh_keywords.robot   # pooled SSH connection management (reused per host)
│       ├── traffic_keywords.robot  # SSH traffic keywords (reachability delegates to bbprobe)
│       ├── bbprobe_keywords.robot  # deploy + run bbprobe; structured probe assertions
│       └── failure_keywords.robot  # fault injection: segment/BGP/edge-node + convergence asserts
├── tests_unit/                  # pytest unit tests for NsxtApi (pure Python)
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
uv sync --locked --extra dev                # this repo (editable, with dev tools, from the committed lockfile)
# or, as a dependency of your own test project:
uv pip install robotframework-nsxt          # (once published) or: uv pip install <path-or-git-url>
```

Then import the keywords from any suite:

```robotframework
*** Settings ***
Library     nsxt_robot.NsxtApi
Resource    nsxt_robot/resources/common.robot
Resource    nsxt_robot/resources/policy_api.robot
Resource    nsxt_robot/resources/traffic_keywords.robot
```

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

## Running

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

## Probe keywords (`nsxt_robot/resources/bbprobe_keywords.robot`)

| Keyword | Purpose |
|---------|---------|
| `Run bbprobe  vm  module  target  [extra_args]` | Run a probe, return the parsed JSON dict + exit code |
| `Probe Should Succeed  vm  module  target` | Assert exit 0 and `summary.probe_success == 1` |
| `Probe Should Fail  vm  module  target` | Assert failure (for deny/DFW tests); bounded by `--deadline`/`--timeout` |
| `Probe Latency Should Be Below  vm  module  target  [max_s]` | Assert `summary.latency_seconds.max < max_s` |
| `Get Probe Result  vm  module  target` | Return the dict for custom assertions |
| `Service Data Plane Should Be Reachable  vm  module  target  @paths` | Wait for realization of `paths`, then probe |

`bbprobe` modules used: `icmp`, `tcp_connect` (target `host:port`), `http_2xx`.
The reachability keywords in `traffic_keywords.robot` (`Ping From VM`,
`TCP Connect From VM`, …) delegate to these. Three checks stay on shell tools because
bbprobe cannot express them: `Verify Source IP From VM` / `Verify HTTP Response From VM`
assert on the HTTP response **body** (curl), and `Verify Overlay MTU From VM` sends a
full-size **DF-bit** ICMP packet (`ping -M do -s`) to validate the overlay carries a
1500-byte inner frame without fragmenting.

## NSX-T API keywords (`nsxt_robot.NsxtApi`)

Used alongside RESTinstance — the `policy_api.robot` getters return bodies; these
keywords parse and assert on them, replacing `Get From Dictionary` chains and
`Evaluate next(...)`.

| Keyword | Purpose |
|---------|---------|
| `Get Value  data  path` | Dotted/indexed lookup, e.g. `members.0.status` |
| `Find In List  items  key  value` | First dict where `item[key] == value` (accepts a `results` body) |
| `Get Ids  list_body` | List of `id`/`display_name` for every item |
| `Realized State Should Be Success  body` | Assert realization consolidated status is SUCCESS |
| `Manager Cluster Should Be Stable  status` | Assert cluster status STABLE |
| `Compute Manager Should Be Registered  cm_status` | Assert REGISTERED |
| `BGP Neighbor Should Be Established  status` | Assert BGP connection_state ESTABLISHED |
| `BFD Should Be Healthy  status` | Assert BFD diagnostic code 0 |
| `Pool Member Should Be Up  pool_status` | Assert every LB pool member is UP |
| `NAT Rule Should Exist  rules  rule_id  [action]  [translated]` | Assert a NAT rule (SNAT/DNAT) exists with the expected fields |
| `DFW Rule Should Have Action  rules  rule_id  action` | Assert a DFW rule exists with ALLOW/DROP/REJECT |
| `Group Should Have Member  members  ip_or_name` | Assert a group's effective members include a VM by IP or name |

## T0-VRF and EVPN (`policy_api.robot` + `tests/10_t0_vrf`)

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
| BGP session (T0 or T0-VRF) | `Disable BGP On T0 Locale Service` | `Enable BGP On T0 Locale Service` (policy_api.robot) |
| BGP neighbor | `Delete BGP Neighbor On T0` (policy_api.robot) | `Create BGP Neighbor On T0` |
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

## Keyword docs

Generate browsable HTML keyword docs (libdoc) for `NsxtApi` and each resource file:

```sh
scripts/gen_docs.sh          # writes docs/*.html (gitignored)
```

## Development checks

The same gates run in CI (`.github/workflows/ci.yml`):

```sh
uv run ruff check .                          # lint Python
uv run mypy src/                             # type-check the library
uv run pytest -q                             # NsxtApi unit tests (tests_unit/)
uv run robocop check src/ tests/             # lint the Robot code
uv run robot --dryrun -V env.example.yaml tests/   # all keywords/imports resolve
uv build                                     # wheel + sdist in dist/
```
