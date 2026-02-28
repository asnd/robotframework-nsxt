*** Settings ***
Documentation    SSH-based traffic validation keywords using SSHLibrary.
Library          SSHLibrary
Library          String
Library          Collections


*** Variables ***
${SSH_TIMEOUT}      30s
${SSH_PROMPT}       $


*** Keywords ***
Open SSH To VM
    [Documentation]    Open an SSH connection to a test VM.
    [Arguments]    ${vm_ip}
    Open Connection    ${vm_ip}    timeout=${SSH_TIMEOUT}    prompt=${SSH_PROMPT}
    Login    ${VM_USER}    ${VM_PASSWORD}
    Log    SSH connected to ${vm_ip}

Close SSH From VM
    [Documentation]    Close the active SSH connection.
    Close Connection

Run Command On VM
    [Documentation]    Execute a shell command on a VM via SSH and return stdout.
    [Arguments]    ${vm_ip}    ${command}
    Open SSH To VM    ${vm_ip}
    ${stdout}    ${stderr}    ${rc}=    Execute Command    ${command}    return_stderr=True    return_rc=True
    Close SSH From VM
    Log    CMD: ${command} | RC: ${rc} | OUT: ${stdout} | ERR: ${stderr}
    RETURN    ${stdout}    ${stderr}    ${rc}

Ping From VM
    [Documentation]    SSH to a VM and ping a destination. Assert 0% packet loss.
    [Arguments]    ${vm_ip}    ${dest_ip}    ${count}=3
    ${stdout}    ${stderr}    ${rc}=    Run Command On VM
    ...    ${vm_ip}    ping -c ${count} -W 2 ${dest_ip}
    Should Be Equal As Integers    ${rc}    0
    Should Not Contain    ${stdout}    100% packet loss
    Log    Ping from ${vm_ip} to ${dest_ip}: SUCCESS

Ping Should Fail From VM
    [Documentation]    Assert that ping from a VM to a destination fails.
    [Arguments]    ${vm_ip}    ${dest_ip}    ${count}=3
    ${stdout}    ${stderr}    ${rc}=    Run Command On VM
    ...    ${vm_ip}    ping -c ${count} -W 2 ${dest_ip}
    Should Not Be Equal As Integers    ${rc}    0
    Log    Ping from ${vm_ip} to ${dest_ip}: FAILED as expected

Curl From VM
    [Documentation]    SSH to a VM and perform an HTTP request. Assert expected HTTP status code.
    [Arguments]    ${vm_ip}    ${url}    ${expected_code}=200    ${extra_args}=${EMPTY}
    ${stdout}    ${stderr}    ${rc}=    Run Command On VM
    ...    ${vm_ip}    curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 15 ${extra_args} ${url}
    Should Be Equal As Strings    ${stdout.strip()}    ${expected_code}
    Log    Curl from ${vm_ip} to ${url}: HTTP ${stdout.strip()}

TCP Connect From VM
    [Documentation]    SSH to a VM and verify TCP connectivity to a host:port using nc.
    [Arguments]    ${vm_ip}    ${dest_ip}    ${port}    ${timeout}=5
    ${stdout}    ${stderr}    ${rc}=    Run Command On VM
    ...    ${vm_ip}    nc -zv -w ${timeout} ${dest_ip} ${port} 2>&1 || true
    Should Contain Any    ${stdout}    succeeded    open    Connected
    Log    TCP connect from ${vm_ip} to ${dest_ip}:${port}: SUCCESS

Verify Source IP From VM
    [Documentation]    Verify that traffic from a VM to dest_ip uses expected_src_ip as source.
    ...    Requires an HTTP reflector at dest_ip that echoes the client's IP (e.g., httpbin /ip).
    [Arguments]    ${vm_ip}    ${dest_ip}    ${expected_src_ip}    ${port}=80    ${path}=/ip
    ${stdout}    ${stderr}    ${rc}=    Run Command On VM
    ...    ${vm_ip}    curl -s --connect-timeout 10 --max-time 15 http://${dest_ip}:${port}${path}
    Should Contain    ${stdout}    ${expected_src_ip}
    Log    Source IP verification: expected ${expected_src_ip} found in response from ${dest_ip}

Verify HTTP Response From VM
    [Documentation]    Perform a full HTTP GET from a VM and assert the response body contains expected text.
    [Arguments]    ${vm_ip}    ${url}    ${expected_text}
    ${stdout}    ${stderr}    ${rc}=    Run Command On VM
    ...    ${vm_ip}    curl -s --connect-timeout 10 --max-time 15 ${url}
    Should Contain    ${stdout}    ${expected_text}
    Log    HTTP response from ${url} contains expected text: ${expected_text}
