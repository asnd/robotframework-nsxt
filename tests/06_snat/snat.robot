*** Settings ***
Documentation    SNAT end-to-end: create T1 and segment, configure SNAT rule, verify rule config
...              and realization, then confirm traffic exits using the translated source IP.
Resource         ../../resources/common.robot
Resource         ../../resources/policy_api.robot
Resource         ../../resources/traffic_keywords.robot
Suite Setup      SNAT Suite Setup
Suite Teardown   SNAT Suite Teardown
Test Tags        nat    snat


*** Variables ***
${T1A_ID}               test-t1-snat
${SEG_A_ID}             test-seg-snat
${SNAT_RULE_ID}         test-snat-rule-1
${T1A_PATH}             /infra/tier-1s/${T1A_ID}
${T0_PATH}              /infra/tier-0s/${T0_GATEWAY_ID}
${OVERLAY_TZ_PATH}      /infra/sites/default/enforcement-points/default/transport-zones/${OVERLAY_TZ_ID}
${SOURCE_NETWORK}       172.16.1.0/24


*** Keywords ***
SNAT Suite Setup
    Initialize REST Session
    Create T1 Gateway    ${T1A_ID}    T1-SNAT    ${T0_PATH}    TIER1_CONNECTED    TIER1_STATIC_ROUTES    TIER1_NAT
    Create Overlay Segment    ${SEG_A_ID}    ${T1A_PATH}    ${OVERLAY_TZ_PATH}    ${T1A_SEGMENT_CIDR}

SNAT Suite Teardown
    Safe Delete Policy Object
    ...    ${POLICY_BASE}/infra/tier-1s/${T1A_ID}/nat/USER/nat-rules/${SNAT_RULE_ID}
    Safe Delete Policy Object    ${POLICY_BASE}/infra/segments/${SEG_A_ID}
    Safe Delete Policy Object    ${POLICY_BASE}/infra/tier-1s/${T1A_ID}

Verify SNAT Realized
    [Documentation]    Check realization for the SNAT NAT rule.
    Verify Realized    /infra/tier-1s/${T1A_ID}/nat/USER/nat-rules/${SNAT_RULE_ID}


*** Test Cases ***
Verify T1 Gateway Is Realized
    [Documentation]    Wait until the T1 for SNAT tests reaches realized state SUCCESS.
    [Tags]    nat    realization
    Wait For Realization    /infra/tier-1s/${T1A_ID}

Verify Segment Is Realized
    [Documentation]    Wait until the segment for SNAT tests reaches realized state SUCCESS.
    [Tags]    nat    realization
    Wait For Realization    /infra/segments/${SEG_A_ID}

Create SNAT Rule On T1
    [Documentation]    Create an SNAT rule translating traffic from ${SOURCE_NETWORK} to ${SNAT_TRANSLATED_IP}.
    [Tags]    nat    snat    config
    Create SNAT Rule On T1
    ...    ${T1A_ID}
    ...    ${SNAT_RULE_ID}
    ...    ${SNAT_TRANSLATED_IP}
    ...    ${SOURCE_NETWORK}

Verify SNAT Rule Exists
    [Documentation]    GET NAT rules on T1 and assert the SNAT rule is present with correct action.
    [Tags]    nat    snat    config
    ${rules}=    Get NAT Rules On T1    ${T1A_ID}
    ${rule_list}=    Get From Dictionary    ${rules}    results
    ${rule_ids}=    Evaluate    [r.get('id', '') for r in ${rule_list}]
    Should Contain    ${rule_ids}    ${SNAT_RULE_ID}
    ${test_rule}=    Evaluate
    ...    next(r for r in ${rule_list} if r.get('id') == '${SNAT_RULE_ID}')
    Should Be Equal As Strings    ${test_rule['action']}    SNAT
    Should Be Equal As Strings    ${test_rule['translated_network']}    ${SNAT_TRANSLATED_IP}
    Log    SNAT rule verified: ${SOURCE_NETWORK} → ${SNAT_TRANSLATED_IP}

Verify SNAT Rule Is Realized
    [Documentation]    Poll realization state for the SNAT rule until SUCCESS.
    [Tags]    nat    snat    realization
    Wait Until Keyword Succeeds    2 min    10 sec    Verify SNAT Realized

Verify Traffic Uses Translated Source IP
    [Documentation]    From VM1, make an HTTP request to an external reflector service and verify
    ...                the response contains the SNAT translated IP as the client address.
    ...                Requires an HTTP reflector (e.g., httpbin /ip) running at EXTERNAL_TEST_IP.
    [Tags]    nat    snat    traffic    end-to-end
    Verify Source IP From VM
    ...    ${VM1_IP}
    ...    ${EXTERNAL_TEST_IP}
    ...    ${SNAT_TRANSLATED_IP}
