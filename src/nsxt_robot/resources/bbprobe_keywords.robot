*** Settings ***
Documentation    Structured data-plane validation using the `bbprobe` binary over SSH.
...              Replaces string-scraping ping/curl/nc with JSON-parseable probes that
...              carry success, per-attempt results, and latency. Also deploys the binary
...              to the test VMs via SCP (SSHLibrary Put File).
Library          Collections
Library          String
Library          SSHLibrary
Resource         common.robot
Resource         ssh_keywords.robot


*** Variables ***
${BBPROBE_LOCAL_PATH}     ${EMPTY}
${BBPROBE_REMOTE_PATH}    /usr/local/bin/bbprobe
${BBPROBE_SSH_TIMEOUT}    30s
${PROBE_MAX_LATENCY}      2.0
# Test VMs to deploy bbprobe onto. Defaults to the two-VM pair from env.yaml, but a
# consuming suite can override @{TEST_VM_IPS} to cover any number of hosts.
@{TEST_VM_IPS}            ${VM1_IP}    ${VM2_IP}


*** Keywords ***
# ──────────────────────────────────────────────
# Deployment
# ──────────────────────────────────────────────

Deploy bbprobe To VM
    [Documentation]    SCP the bbprobe binary to a VM, make it executable, verify it runs,
    ...                and grant unprivileged ICMP (setcap, else ping_group_range).
    [Arguments]    ${vm_ip}
    Ensure SSH To VM    ${vm_ip}
    Put File    ${BBPROBE_LOCAL_PATH}    ${BBPROBE_REMOTE_PATH}    mode=0755
    ${out}    ${rc}=    Execute Command    ${BBPROBE_REMOTE_PATH} --version    return_rc=True
    Should Be Equal As Integers    ${rc}    0    msg=bbprobe --version failed on ${vm_ip}: ${out}
    ${cap_out}    ${cap_rc}=    Execute Command
    ...    setcap cap_net_raw+ep ${BBPROBE_REMOTE_PATH} 2>/dev/null || sysctl -w net.ipv4.ping_group_range="0 2147483647"
    ...    return_rc=True
    Log    Deployed bbprobe to ${vm_ip}: ${out} (icmp-setup rc=${cap_rc})

Deploy bbprobe To All Test VMs
    [Documentation]    Deploy bbprobe to every VM in @{TEST_VM_IPS} (default: VM1_IP, VM2_IP).
    FOR    ${vm_ip}    IN    @{TEST_VM_IPS}
        Deploy bbprobe To VM    ${vm_ip}
    END

# ──────────────────────────────────────────────
# Probe execution
# ──────────────────────────────────────────────

Run bbprobe
    [Documentation]    Run bbprobe on a VM and return the parsed JSON result dict and exit code.
    ...                Reuses a persistent SSH connection per host (see Ensure SSH To VM).
    [Arguments]    ${vm_ip}    ${module}    ${target}    ${extra_args}=${EMPTY}
    Ensure SSH To VM    ${vm_ip}
    ${cmd}=    Set Variable
    ...    ${BBPROBE_REMOTE_PATH} --module ${module} --target ${target} --format json ${extra_args}
    ${stdout}    ${stderr}    ${rc}=    Execute Command    ${cmd}    return_stderr=True    return_rc=True
    ${result}=    Evaluate    json.loads($stdout)    modules=json
    Log    bbprobe ${module} → ${target} (rc=${rc}): ${result['summary']}
    RETURN    ${result}    ${rc}

Get Probe Result
    [Documentation]    Return the parsed bbprobe result dict for custom assertions.
    [Arguments]    ${vm_ip}    ${module}    ${target}    ${extra_args}=${EMPTY}
    ${result}    ${rc}=    Run bbprobe    ${vm_ip}    ${module}    ${target}    ${extra_args}
    RETURN    ${result}

# ──────────────────────────────────────────────
# Assertions
# ──────────────────────────────────────────────

Probe Should Succeed
    [Documentation]    Assert bbprobe exits 0 and summary.probe_success == 1.
    [Arguments]    ${vm_ip}    ${module}    ${target}    ${extra_args}=${EMPTY}
    ${result}    ${rc}=    Run bbprobe    ${vm_ip}    ${module}    ${target}    ${extra_args}
    Should Be Equal As Integers    ${rc}    0    msg=bbprobe rc=${rc} for ${module} → ${target}
    Should Be Equal As Integers    ${result['summary']['probe_success']}    1
    ...    msg=probe_success != 1 for ${module} → ${target}
    Log    Probe ${module} → ${target} from ${vm_ip}: SUCCESS

Probe Should Fail
    [Documentation]    Assert the probe fails (summary.probe_success == 0). For deny/DFW tests.
    ...                Bounded with --deadline/--timeout so failure returns quickly.
    [Arguments]    ${vm_ip}    ${module}    ${target}    ${extra_args}=--deadline 6s --timeout 2s
    ${result}    ${rc}=    Run bbprobe    ${vm_ip}    ${module}    ${target}    ${extra_args}
    Should Be Equal As Integers    ${result['summary']['probe_success']}    0
    ...    msg=expected probe failure but it succeeded for ${module} → ${target}
    Log    Probe ${module} → ${target} from ${vm_ip}: FAILED as expected

Probe Latency Should Be Below
    [Documentation]    Assert the max probe latency is below max_seconds (seconds, float).
    [Arguments]    ${vm_ip}    ${module}    ${target}    ${max_seconds}=${PROBE_MAX_LATENCY}
    ${result}    ${rc}=    Run bbprobe    ${vm_ip}    ${module}    ${target}
    Should Be Equal As Integers    ${rc}    0    msg=bbprobe rc=${rc} for ${module} → ${target}
    ${latency}=    Set Variable    ${result['summary']['latency_seconds']['max']}
    Should Be True    ${latency} < ${max_seconds}
    ...    msg=latency ${latency}s exceeded threshold ${max_seconds}s for ${module} → ${target}
    Log    Probe ${module} → ${target} latency ${latency}s < ${max_seconds}s

# ──────────────────────────────────────────────
# Control-plane + data-plane correlation
# ──────────────────────────────────────────────

Service Data Plane Should Be Reachable
    [Documentation]    Wait for realization of the given intent paths, then assert the
    ...                data plane is reachable with a bbprobe from a VM. One keyword that
    ...                ties control-plane realization to data-plane connectivity.
    [Arguments]    ${vm_ip}    ${module}    ${target}    @{intent_paths}
    Wait For Realizations    @{intent_paths}
    Probe Should Succeed    ${vm_ip}    ${module}    ${target}
