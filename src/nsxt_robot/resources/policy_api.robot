*** Settings ***
Documentation    Shim: every keyword that used to live here (T1/T0/VRF gateways, segments,
...              static routes, BFD, BGP, HA VIP, NAT, LB, tags, groups, DFW, EVPN,
...              infra/fabric management) is now implemented in Python on
...              nsxt_robot.NsxtLibrary (see keywords/gateways.py, routing.py,
...              services.py, security.py, fabric.py) and is available under the exact
...              same names once that library is imported (common.robot already does).
...              This file only keeps ${INFRA_BASE}, still used by failure_keywords.robot.
Resource         common.robot


*** Variables ***
${INFRA_BASE}    ${POLICY_BASE}/infra
