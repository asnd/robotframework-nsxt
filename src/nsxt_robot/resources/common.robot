*** Settings ***
Documentation    Common setup, teardown, and utility keywords shared across all test suites.
Library          Collections
Library          OperatingSystem
Library          String
Library          nsxt_robot.NsxtLibrary
Library          nsxt_robot.NsxtApi


*** Variables ***
${NSX_PORT}         ${443}
${POLICY_BASE}      /policy/api/v1
${MGMT_BASE}        /api/v1
# Shared topology paths (previously redefined in every suite). Resolved from env.yaml.
${T0_PATH}          /infra/tier-0s/${T0_GATEWAY_ID}
${OVERLAY_TZ_PATH}  /infra/sites/default/enforcement-points/default/transport-zones/${OVERLAY_TZ_ID}


*** Keywords ***
Initialize REST Session
    [Documentation]    Open the shared NSX connection (alias 'default') used by every
    ...                `NSX REST *` and realization keyword. The password comes from the
    ...                ${NSX_PASSWORD} variable (env.yaml) but the NSX_PASSWORD environment
    ...                variable, when set, wins — so CI can inject a secret without a creds
    ...                file on disk. Credential resolution runs with logging suppressed so
    ...                the password never reaches the log.
    ${previous_level}=    Set Log Level    NONE
    ${password}=    Set Variable    ${NSX_PASSWORD}
    ${env_password}=    Get Environment Variable    NSX_PASSWORD    ${EMPTY}
    IF    '${env_password}' != '${EMPTY}'
        ${password}=    Set Variable    ${env_password}
    END
    Open Nsx Connection    ${NSX_MANAGER}    ${NSX_USER}    ${password}
    ...    alias=default    port=${NSX_PORT}    verify=${VERIFY_SSL}
    Set Log Level    ${previous_level}
    Log    NSX connection opened for ${NSX_MANAGER}:${NSX_PORT}

Standard Suite Teardown
    [Documentation]    Safe-delete a list of Policy API paths — replaces the per-suite
    ...                teardown blocks. Deletes in the given order (children first).
    [Arguments]    @{paths}
    FOR    ${path}    IN    @{paths}
        Safe Delete Policy Object    ${path}
    END

Safe Delete Policy Object
    [Documentation]    Delete a Policy API object, suppressing errors for teardown safety.
    [Arguments]    ${path}
    NSX REST DELETE Ignore Error    ${path}
