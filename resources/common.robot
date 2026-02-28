*** Settings ***
Documentation    Common setup, teardown, and utility keywords shared across all test suites.
Library          REST    https://${NSX_MANAGER}    ssl_verify=${VERIFY_SSL}
Library          Collections
Library          String
Library          OperatingSystem


*** Variables ***
${POLICY_BASE}    /policy/api/v1
${MGMT_BASE}      /api/v1


*** Keywords ***
Initialize REST Session
    [Documentation]    Configure authentication headers on the shared RESTinstance session.
    ${raw}=    Set Variable    ${NSX_USER}:${NSX_PASSWORD}
    ${auth}=    Evaluate    __import__('base64').b64encode($raw.encode()).decode()
    Set Headers    {"Authorization": "Basic ${auth}", "Content-Type": "application/json", "Accept": "application/json"}
    Log    REST auth headers configured for ${NSX_MANAGER}

NSX REST GET
    [Documentation]    Perform a GET request against the NSX API and return the parsed body.
    [Arguments]    ${path}
    GET    ${path}
    Integer    response status    200
    ${body}=    Output    response body
    RETURN    ${body}

NSX REST PATCH
    [Documentation]    Perform a PATCH request and return the parsed response body.
    [Arguments]    ${path}    ${body}
    PATCH    ${path}    ${body}
    Integer    response status    200
    ${resp_body}=    Output    response body
    RETURN    ${resp_body}

NSX REST DELETE
    [Documentation]    Perform a DELETE request. Accepts 200 or 204 responses.
    [Arguments]    ${path}
    DELETE    ${path}
    ${status}=    Output    response status
    Should Be True    ${status} in [200, 204]    msg=DELETE ${path} returned unexpected status: ${status}
    RETURN    ${status}

NSX REST DELETE Ignore Error
    [Documentation]    DELETE that logs warnings but does not fail — for use in teardowns.
    [Arguments]    ${path}
    ${result}    ${value}=    Run Keyword And Ignore Error    NSX REST DELETE    ${path}
    Run Keyword If    '${result}' == 'FAIL'    Log    DELETE ${path} failed (ignored): ${value}    WARN

Verify Realized
    [Documentation]    Assert the realization status for a Policy API intent path is SUCCESS.
    [Arguments]    ${intent_path}
    ${encoded}=    Evaluate
    ...    __import__('urllib.parse', fromlist=['quote']).quote($intent_path, safe='')
    ${body}=    NSX REST GET    ${POLICY_BASE}/infra/realized-state/status?intent_path=${encoded}
    ${status}=    Get From Dictionary    ${body['consolidated_status']}    consolidated_status
    Should Be Equal As Strings    ${status}    SUCCESS

Wait For Realization
    [Documentation]    Poll realization status up to 2 minutes until SUCCESS.
    [Arguments]    ${intent_path}
    Wait Until Keyword Succeeds    2 min    10 sec    Verify Realized    ${intent_path}

Safe Delete Policy Object
    [Documentation]    Delete a Policy API object, suppressing errors for teardown safety.
    [Arguments]    ${path}
    NSX REST DELETE Ignore Error    ${path}
