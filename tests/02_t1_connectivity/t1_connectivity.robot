*** Settings ***
Documentation    T1 gateway lifecycle: create T1-A and T1-B, attach segments, verify realization
...              and connectivity between VMs on different T1s.
Resource         ../../resources/common.robot
Resource         ../../resources/policy_api.robot
Resource         ../../resources/traffic_keywords.robot
Suite Setup      T1 Connectivity Suite Setup
Suite Teardown   T1 Connectivity Suite Teardown
Test Tags        t1    routing


*** Variables ***
${T1A_ID}           test-t1-a
${T1B_ID}           test-t1-b
${SEG_A_ID}         test-seg-a
${SEG_B_ID}         test-seg-b
${T1A_PATH}         /infra/tier-1s/${T1A_ID}
${T1B_PATH}         /infra/tier-1s/${T1B_ID}
${T0_PATH}          /infra/tier-0s/${T0_GATEWAY_ID}
${OVERLAY_TZ_PATH}  /infra/sites/default/enforcement-points/default/transport-zones/${OVERLAY_TZ_ID}


*** Keywords ***
T1 Connectivity Suite Setup
    Initialize REST Session
    Create T1 Gateway    ${T1A_ID}    T1-Gateway-A    ${T0_PATH}    TIER1_CONNECTED    TIER1_STATIC_ROUTES
    Create T1 Gateway    ${T1B_ID}    T1-Gateway-B    ${T0_PATH}    TIER1_CONNECTED    TIER1_STATIC_ROUTES
    Create Overlay Segment    ${SEG_A_ID}    ${T1A_PATH}    ${OVERLAY_TZ_PATH}    ${T1A_SEGMENT_CIDR}
    Create Overlay Segment    ${SEG_B_ID}    ${T1B_PATH}    ${OVERLAY_TZ_PATH}    ${T1B_SEGMENT_CIDR}

T1 Connectivity Suite Teardown
    Safe Delete Policy Object    ${POLICY_BASE}/infra/segments/${SEG_A_ID}
    Safe Delete Policy Object    ${POLICY_BASE}/infra/segments/${SEG_B_ID}
    Safe Delete Policy Object    ${POLICY_BASE}/infra/tier-1s/${T1A_ID}
    Safe Delete Policy Object    ${POLICY_BASE}/infra/tier-1s/${T1B_ID}


*** Test Cases ***
Verify T1-A Gateway Is Realized
    [Documentation]    Poll the realization API until T1-A reports SUCCESS.
    [Tags]    t1    realization
    Wait For Realization    /infra/tier-1s/${T1A_ID}

Verify T1-B Gateway Is Realized
    [Documentation]    Poll the realization API until T1-B reports SUCCESS.
    [Tags]    t1    realization
    Wait For Realization    /infra/tier-1s/${T1B_ID}

Verify Segment-A Is Realized
    [Documentation]    Poll the realization API until Segment-A reports SUCCESS.
    [Tags]    t1    realization
    Wait For Realization    /infra/segments/${SEG_A_ID}

Verify Segment-B Is Realized
    [Documentation]    Poll the realization API until Segment-B reports SUCCESS.
    [Tags]    t1    realization
    Wait For Realization    /infra/segments/${SEG_B_ID}

Verify T1-A Gateway Configuration
    [Documentation]    GET the T1-A gateway and assert it is linked to the T0.
    [Tags]    t1    config
    ${t1}=    Get T1 Gateway    ${T1A_ID}
    Should Be Equal As Strings    ${t1['tier0_path']}    ${T0_PATH}
    Log    T1-A linked to T0: ${t1['tier0_path']}

Verify T1-B Gateway Configuration
    [Documentation]    GET the T1-B gateway and assert it is linked to the T0.
    [Tags]    t1    config
    ${t1}=    Get T1 Gateway    ${T1B_ID}
    Should Be Equal As Strings    ${t1['tier0_path']}    ${T0_PATH}
    Log    T1-B linked to T0: ${t1['tier0_path']}

Verify Inter-T1 Connectivity
    [Documentation]    SSH to VM1 (on Seg-A/T1-A) and ping VM2 (on Seg-B/T1-B).
    ...                Traffic must traverse: VM1 → T1-A → T0 → T1-B → VM2.
    [Tags]    t1    traffic
    Ping From VM    ${VM1_IP}    ${VM2_IP}

Verify T1 To External Connectivity
    [Documentation]    SSH to VM1 and ping an IP outside NSX to verify T0 uplink routing.
    [Tags]    t1    traffic    external
    Ping From VM    ${VM1_IP}    ${EXTERNAL_TEST_IP}
