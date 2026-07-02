*** Settings ***
Documentation    Reusable keywords wrapping NSX-T Policy API operations.
Resource         common.robot


*** Variables ***
${INFRA_BASE}    ${POLICY_BASE}/infra


*** Keywords ***
# ──────────────────────────────────────────────
# T1 Gateways
# ──────────────────────────────────────────────

Create T1 Gateway
    [Documentation]    Create or update a Tier-1 gateway linked to T0.
    ...    route_adv_types accepts a list such as: TIER1_CONNECTED  TIER1_STATIC_ROUTES
    [Arguments]    ${id}    ${display_name}    ${t0_path}    @{route_adv_types}
    IF    len($route_adv_types) > 0
        ${adv}=    Set Variable    ${route_adv_types}
    ELSE
        ${adv}=    Create List    TIER1_CONNECTED
    END
    ${body}=    Create Dictionary
    ...    display_name=${display_name}
    ...    tier0_path=${t0_path}
    ...    route_advertisement_types=${adv}
    NSX REST PATCH    ${INFRA_BASE}/tier-1s/${id}    ${body}
    Log    Created T1 gateway: ${id}

Delete T1 Gateway
    [Documentation]    Delete a Tier-1 gateway.
    [Arguments]    ${id}
    Safe Delete Policy Object    ${INFRA_BASE}/tier-1s/${id}

Get T1 Gateway
    [Documentation]    Retrieve a Tier-1 gateway by ID.
    [Arguments]    ${id}
    ${body}=    NSX REST GET    ${INFRA_BASE}/tier-1s/${id}
    RETURN    ${body}

# ──────────────────────────────────────────────
# Segments
# ──────────────────────────────────────────────

Create Overlay Segment
    [Documentation]    Create an overlay segment attached to a T1 gateway.
    [Arguments]    ${id}    ${t1_path}    ${tz_path}    ${subnet_cidr}
    ${subnet}=    Create Dictionary    gateway_address=${subnet_cidr}
    ${subnets}=    Create List    ${subnet}
    ${body}=    Create Dictionary
    ...    display_name=${id}
    ...    connectivity_path=${t1_path}
    ...    transport_zone_path=${tz_path}
    ...    subnets=${subnets}
    NSX REST PATCH    ${INFRA_BASE}/segments/${id}    ${body}
    Log    Created overlay segment: ${id}

Delete Segment
    [Documentation]    Delete a segment by ID.
    [Arguments]    ${id}
    Safe Delete Policy Object    ${INFRA_BASE}/segments/${id}

Get Segment
    [Documentation]    Retrieve a segment by ID.
    [Arguments]    ${id}
    ${body}=    NSX REST GET    ${INFRA_BASE}/segments/${id}
    RETURN    ${body}

# ──────────────────────────────────────────────
# Static Routes
# ──────────────────────────────────────────────

Create Static Route On T1
    [Documentation]    Add a static route to a Tier-1 gateway.
    [Arguments]    ${t1_id}    ${route_id}    ${network}    ${next_hop}
    ${hop}=    Create Dictionary    ip_address=${next_hop}
    ${next_hops}=    Create List    ${hop}
    ${body}=    Create Dictionary
    ...    display_name=${route_id}
    ...    network=${network}
    ...    next_hops=${next_hops}
    NSX REST PATCH
    ...    ${INFRA_BASE}/tier-1s/${t1_id}/static-routes/${route_id}
    ...    ${body}
    Log    Created static route ${route_id} on T1 ${t1_id}

Delete Static Route On T1
    [Documentation]    Delete a static route from a Tier-1 gateway.
    [Arguments]    ${t1_id}    ${route_id}
    Safe Delete Policy Object    ${INFRA_BASE}/tier-1s/${t1_id}/static-routes/${route_id}

Get Static Routes On T1
    [Documentation]    List all static routes on a Tier-1 gateway.
    [Arguments]    ${t1_id}
    ${body}=    NSX REST GET    ${INFRA_BASE}/tier-1s/${t1_id}/static-routes
    RETURN    ${body}

# ──────────────────────────────────────────────
# BGP
# ──────────────────────────────────────────────

Configure BGP On T0
    [Documentation]    Enable BGP and set local ASN on a T0 gateway locale service.
    [Arguments]    ${t0_id}    ${locale_service_id}    ${local_asn}
    ${body}=    Create Dictionary
    ...    local_as_num=${local_asn}
    ...    enabled=${True}
    NSX REST PATCH
    ...    ${INFRA_BASE}/tier-0s/${t0_id}/locale-services/${locale_service_id}/bgp
    ...    ${body}
    Log    Configured BGP on T0 ${t0_id} with ASN ${local_asn}

Create BGP Neighbor On T0
    [Documentation]    Create a BGP neighbor entry on a T0 gateway with optional BFD.
    [Arguments]    ${t0_id}    ${locale_service_id}    ${neighbor_id}    ${peer_ip}
    ...            ${remote_asn}    ${bfd_enabled}=${True}    ${bfd_interval}=500    ${bfd_multiplier}=3
    ${bfd}=    Create Dictionary
    ...    enabled=${bfd_enabled}
    ...    interval=${bfd_interval}
    ...    multiple=${bfd_multiplier}
    ${body}=    Create Dictionary
    ...    display_name=${neighbor_id}
    ...    neighbor_address=${peer_ip}
    ...    remote_as_num=${remote_asn}
    ...    bfd_config=${bfd}
    NSX REST PATCH
    ...    ${INFRA_BASE}/tier-0s/${t0_id}/locale-services/${locale_service_id}/bgp/neighbors/${neighbor_id}
    ...    ${body}
    Log    Created BGP neighbor ${neighbor_id} (${peer_ip}) on T0 ${t0_id}

Get BGP Neighbor Status
    [Documentation]    Retrieve BGP neighbor operational status.
    [Arguments]    ${t0_id}    ${locale_service_id}    ${neighbor_id}
    ${body}=    NSX REST GET
    ...    ${POLICY_BASE}/infra/tier-0s/${t0_id}/locale-services/${locale_service_id}/bgp/neighbors/${neighbor_id}/status
    RETURN    ${body}

Delete BGP Neighbor On T0
    [Documentation]    Delete a BGP neighbor from a T0 gateway.
    [Arguments]    ${t0_id}    ${locale_service_id}    ${neighbor_id}
    Safe Delete Policy Object
    ...    ${INFRA_BASE}/tier-0s/${t0_id}/locale-services/${locale_service_id}/bgp/neighbors/${neighbor_id}

Get BGP Routes On T0
    [Documentation]    Retrieve BGP routes learned from a specific neighbor on the T0 gateway.
    ...    Routes are reported per neighbor, not for the gateway as a whole.
    [Arguments]    ${t0_id}    ${locale_service_id}    ${neighbor_id}
    ${body}=    NSX REST GET
    ...    ${POLICY_BASE}/infra/tier-0s/${t0_id}/locale-services/${locale_service_id}/bgp/neighbors/${neighbor_id}/routes
    RETURN    ${body}

# ──────────────────────────────────────────────
# HA VIP
# ──────────────────────────────────────────────

Create HA VIP Config On T0
    [Documentation]    Configure an HA VIP on a T0 locale service.
    [Arguments]    ${t0_id}    ${locale_service_id}    ${vip_ip}    ${edge_path_1}    ${edge_path_2}
    ${vip_config}=    Create Dictionary
    ...    vip_subnets=@{EMPTY}
    ...    enabled=${True}
    ${vip_ip_list}=    Create List    ${vip_ip.split('/')[0]}
    ${subnet}=    Create Dictionary    prefix_len=${vip_ip.split('/')[1]}    ip_addresses=${vip_ip_list}
    ${vip_subnets}=    Create List    ${subnet}
    Set To Dictionary    ${vip_config}    vip_subnets=${vip_subnets}
    ${edge_paths}=    Create List    ${edge_path_1}    ${edge_path_2}
    Set To Dictionary    ${vip_config}    external_interface_paths=${edge_paths}
    ${ha_vip_configs}=    Create List    ${vip_config}
    ${body}=    Create Dictionary    ha_vip_configs=${ha_vip_configs}
    NSX REST PATCH
    ...    ${INFRA_BASE}/tier-0s/${t0_id}/locale-services/${locale_service_id}
    ...    ${body}
    Log    Configured HA VIP ${vip_ip} on T0 ${t0_id}

Remove HA VIP Config On T0
    [Documentation]    Remove HA VIP configuration from a T0 locale service.
    [Arguments]    ${t0_id}    ${locale_service_id}
    ${body}=    Create Dictionary    ha_vip_configs=@{EMPTY}
    NSX REST PATCH
    ...    ${INFRA_BASE}/tier-0s/${t0_id}/locale-services/${locale_service_id}
    ...    ${body}

Get T0 Locale Service
    [Documentation]    Retrieve the locale service config for a T0 gateway.
    [Arguments]    ${t0_id}    ${locale_service_id}
    ${body}=    NSX REST GET
    ...    ${INFRA_BASE}/tier-0s/${t0_id}/locale-services/${locale_service_id}
    RETURN    ${body}

# ──────────────────────────────────────────────
# NAT
# ──────────────────────────────────────────────

Create SNAT Rule On T1
    [Documentation]    Create an SNAT rule on a Tier-1 gateway.
    [Arguments]    ${t1_id}    ${rule_id}    ${translated_ip}    ${source_network}
    ${body}=    Create Dictionary
    ...    display_name=${rule_id}
    ...    action=SNAT
    ...    translated_network=${translated_ip}
    ...    source_network=${source_network}
    ...    enabled=${True}
    ...    logging=${False}
    NSX REST PATCH
    ...    ${INFRA_BASE}/tier-1s/${t1_id}/nat/USER/nat-rules/${rule_id}
    ...    ${body}
    Log    Created SNAT rule ${rule_id} on T1 ${t1_id}

Create DNAT Rule On T1
    [Documentation]    Create a DNAT rule on a Tier-1 gateway: inbound traffic to
    ...    ${destination_ip} is translated to the internal ${translated_ip}. An optional
    ...    ${translated_port} restricts the rule to a single service port.
    [Arguments]    ${t1_id}    ${rule_id}    ${destination_ip}    ${translated_ip}    ${translated_port}=${EMPTY}
    ${body}=    Create Dictionary
    ...    display_name=${rule_id}
    ...    action=DNAT
    ...    destination_network=${destination_ip}
    ...    translated_network=${translated_ip}
    ...    enabled=${True}
    ...    logging=${False}
    IF    '${translated_port}' != '${EMPTY}'
        Set To Dictionary    ${body}    translated_ports=${translated_port}
    END
    NSX REST PATCH
    ...    ${INFRA_BASE}/tier-1s/${t1_id}/nat/USER/nat-rules/${rule_id}
    ...    ${body}
    Log    Created DNAT rule ${rule_id} on T1 ${t1_id}: ${destination_ip} → ${translated_ip}

Delete NAT Rule On T1
    [Documentation]    Delete a NAT rule from a Tier-1 gateway.
    [Arguments]    ${t1_id}    ${rule_id}
    Safe Delete Policy Object
    ...    ${INFRA_BASE}/tier-1s/${t1_id}/nat/USER/nat-rules/${rule_id}

Get NAT Rules On T1
    [Documentation]    List all NAT rules on a Tier-1 gateway.
    [Arguments]    ${t1_id}
    ${body}=    NSX REST GET    ${INFRA_BASE}/tier-1s/${t1_id}/nat/USER/nat-rules
    RETURN    ${body}

Get NAT Statistics On T1
    [Documentation]    Retrieve NAT statistics for a Tier-1 gateway.
    [Arguments]    ${t1_id}
    ${body}=    NSX REST GET
    ...    ${POLICY_BASE}/infra/tier-1s/${t1_id}/nat/USER/nat-rules?action=statistics
    RETURN    ${body}

# ──────────────────────────────────────────────
# Load Balancer (Basic NSX LB)
# ──────────────────────────────────────────────

Create LB Service
    [Documentation]    Create an NSX LB service attached to a T1 gateway.
    [Arguments]    ${id}    ${t1_path}    ${size}=SMALL
    ${body}=    Create Dictionary
    ...    display_name=${id}
    ...    connectivity_path=${t1_path}
    ...    size=${size}
    NSX REST PATCH    ${INFRA_BASE}/lb-services/${id}    ${body}
    Log    Created LB service: ${id}

Create LB Pool
    [Documentation]    Create an NSX LB server pool with members. When ${monitor_path} is
    ...    provided the pool is bound to that active health monitor.
    [Arguments]    ${id}    ${members}    ${port}    ${monitor_path}=${EMPTY}
    ${member_list}=    Create List
    FOR    ${member_ip}    IN    @{members}
        ${member}=    Create Dictionary
        ...    display_name=${member_ip}
        ...    ip_address=${member_ip}
        ...    port=${port}
        Append To List    ${member_list}    ${member}
    END
    ${body}=    Create Dictionary
    ...    display_name=${id}
    ...    members=${member_list}
    IF    '${monitor_path}' != '${EMPTY}'
        ${monitor_paths}=    Create List    ${monitor_path}
        Set To Dictionary    ${body}    active_monitor_paths=${monitor_paths}
    END
    NSX REST PATCH    ${INFRA_BASE}/lb-pools/${id}    ${body}
    Log    Created LB pool: ${id} (monitor: ${monitor_path})

Create LB HTTP Monitor
    [Documentation]    Create an active HTTP health monitor profile. The pool that binds it
    ...    marks members UP only when they answer ${request_url} with one of ${response_codes}.
    [Arguments]    ${id}    ${monitor_port}    ${request_url}=/    ${response_codes}=${{[200]}}
    ${port_int}=    Convert To Integer    ${monitor_port}
    ${body}=    Create Dictionary
    ...    resource_type=LBHttpMonitorProfile
    ...    display_name=${id}
    ...    monitor_port=${port_int}
    ...    request_url=${request_url}
    ...    request_method=GET
    ...    response_status_codes=${response_codes}
    NSX REST PATCH    ${INFRA_BASE}/lb-monitor-profiles/${id}    ${body}
    Log    Created LB HTTP monitor: ${id} (port ${monitor_port}, url ${request_url})

Delete LB Monitor
    [Documentation]    Delete an LB monitor profile.
    [Arguments]    ${id}
    Safe Delete Policy Object    ${INFRA_BASE}/lb-monitor-profiles/${id}

Create LB Virtual Server
    [Documentation]    Create an NSX LB virtual server (TCP/L4).
    [Arguments]    ${id}    ${pool_path}    ${vip}    ${port}    ${lb_service_path}
    ${ports}=    Create List    ${port}
    ${body}=    Create Dictionary
    ...    display_name=${id}
    ...    ip_address=${vip}
    ...    ports=${ports}
    ...    pool_path=${pool_path}
    ...    lb_service_path=${lb_service_path}
    ...    application_profile_path=/infra/lb-app-profiles/default-tcp-lb-app-profile
    NSX REST PATCH    ${INFRA_BASE}/lb-virtual-servers/${id}    ${body}
    Log    Created LB virtual server: ${id}

Create LB HTTP Virtual Server
    [Documentation]    Create an NSX L7 HTTP virtual server (uses the default HTTP application
    ...    profile, so the LB terminates and proxies HTTP rather than forwarding raw TCP).
    [Arguments]    ${id}    ${pool_path}    ${vip}    ${port}    ${lb_service_path}
    ${ports}=    Create List    ${port}
    ${body}=    Create Dictionary
    ...    display_name=${id}
    ...    ip_address=${vip}
    ...    ports=${ports}
    ...    pool_path=${pool_path}
    ...    lb_service_path=${lb_service_path}
    ...    application_profile_path=/infra/lb-app-profiles/default-http-lb-app-profile
    NSX REST PATCH    ${INFRA_BASE}/lb-virtual-servers/${id}    ${body}
    Log    Created L7 HTTP LB virtual server: ${id}

Get LB Pool Status
    [Documentation]    Retrieve operational status of an LB pool.
    [Arguments]    ${id}    ${lb_service_id}
    ${body}=    NSX REST GET
    ...    ${POLICY_BASE}/infra/lb-services/${lb_service_id}/lb-pools/${id}/status
    RETURN    ${body}

Delete LB Virtual Server
    [Documentation]    Delete an LB virtual server.
    [Arguments]    ${id}
    Safe Delete Policy Object    ${INFRA_BASE}/lb-virtual-servers/${id}

Delete LB Pool
    [Documentation]    Delete an LB pool.
    [Arguments]    ${id}
    Safe Delete Policy Object    ${INFRA_BASE}/lb-pools/${id}

Delete LB Service
    [Documentation]    Delete an LB service.
    [Arguments]    ${id}
    Safe Delete Policy Object    ${INFRA_BASE}/lb-services/${id}

# ──────────────────────────────────────────────
# Tags
# ──────────────────────────────────────────────

Set Tags On Segment
    [Documentation]    Replace the tag set on a segment. ${tags} is a list of
    ...    scope|value strings, e.g.    Create List    app|web    tier|frontend
    [Arguments]    ${segment_id}    @{tags}
    ${tag_list}=    Create List
    FOR    ${entry}    IN    @{tags}
        ${scope}    ${value}=    Evaluate    ($entry.split('|', 1) + [''])[:2]
        ${tag}=    Create Dictionary    scope=${scope}    tag=${value}
        Append To List    ${tag_list}    ${tag}
    END
    ${body}=    Create Dictionary    tags=${tag_list}
    NSX REST PATCH    ${INFRA_BASE}/segments/${segment_id}    ${body}
    Log    Set tags on segment ${segment_id}: ${tags}

# ──────────────────────────────────────────────
# Groups (NSGroups)
# ──────────────────────────────────────────────

Create IP Group
    [Documentation]    Create a group whose membership is a static set of IP addresses/CIDRs.
    [Arguments]    ${group_id}    ${ip_addresses}    ${domain}=default
    ${expr}=    Create Dictionary
    ...    resource_type=IPAddressExpression
    ...    ip_addresses=${ip_addresses}
    ${expressions}=    Create List    ${expr}
    ${body}=    Create Dictionary    display_name=${group_id}    expression=${expressions}
    NSX REST PATCH    ${INFRA_BASE}/domains/${domain}/groups/${group_id}    ${body}
    Log    Created IP group ${group_id}: ${ip_addresses}

Create Tag Group
    [Documentation]    Create a group with dynamic membership: VMs carrying the tag
    ...    ${scope_value} (a scope|value string, e.g. app|web) join the group.
    [Arguments]    ${group_id}    ${scope_value}    ${domain}=default
    ${expr}=    Create Dictionary
    ...    resource_type=Condition
    ...    member_type=VirtualMachine
    ...    key=Tag
    ...    operator=EQUALS
    ...    value=${scope_value}
    ${expressions}=    Create List    ${expr}
    ${body}=    Create Dictionary    display_name=${group_id}    expression=${expressions}
    NSX REST PATCH    ${INFRA_BASE}/domains/${domain}/groups/${group_id}    ${body}
    Log    Created tag group ${group_id}: VMs tagged '${scope_value}'

Get Group
    [Documentation]    Retrieve a group definition by ID.
    [Arguments]    ${group_id}    ${domain}=default
    ${body}=    NSX REST GET    ${INFRA_BASE}/domains/${domain}/groups/${group_id}
    RETURN    ${body}

Get Group Members
    [Documentation]    Retrieve the effective (realized) VM members of a group.
    [Arguments]    ${group_id}    ${domain}=default
    ${body}=    NSX REST GET
    ...    ${INFRA_BASE}/domains/${domain}/groups/${group_id}/members/virtual-machines
    RETURN    ${body}

Delete Group
    [Documentation]    Delete a group by ID.
    [Arguments]    ${group_id}    ${domain}=default
    Safe Delete Policy Object    ${INFRA_BASE}/domains/${domain}/groups/${group_id}

# ──────────────────────────────────────────────
# Distributed Firewall (DFW)
# ──────────────────────────────────────────────

Create Security Policy
    [Documentation]    Create (or update) an empty DFW security policy in a domain. Lower
    ...    ${sequence_number} values are evaluated first relative to other policies.
    [Arguments]    ${policy_id}    ${sequence_number}=10    ${category}=Application    ${domain}=default
    ${body}=    Create Dictionary
    ...    display_name=${policy_id}
    ...    category=${category}
    ...    sequence_number=${sequence_number}
    NSX REST PATCH    ${INFRA_BASE}/domains/${domain}/security-policies/${policy_id}    ${body}
    Log    Created security policy ${policy_id} (category ${category})

Create DFW Rule
    [Documentation]    Create a distributed firewall rule inside a security policy.
    ...    ${action} is ALLOW, DROP, or REJECT. ${source_groups}/${destination_groups}/${services}
    ...    are lists of Policy paths (or ["ANY"]).
    [Arguments]    ${policy_id}    ${rule_id}    ${source_groups}    ${destination_groups}
    ...    ${action}=ALLOW    ${services}=${{['ANY']}}    ${sequence_number}=10    ${domain}=default
    ${body}=    Create Dictionary
    ...    display_name=${rule_id}
    ...    source_groups=${source_groups}
    ...    destination_groups=${destination_groups}
    ...    services=${services}
    ...    action=${action}
    ...    direction=IN_OUT
    ...    ip_protocol=IPV4_IPV6
    ...    sequence_number=${sequence_number}
    NSX REST PATCH
    ...    ${INFRA_BASE}/domains/${domain}/security-policies/${policy_id}/rules/${rule_id}
    ...    ${body}
    Log    Created DFW rule ${rule_id} (${action}) in policy ${policy_id}

Get DFW Rules
    [Documentation]    List the rules of a security policy.
    [Arguments]    ${policy_id}    ${domain}=default
    ${body}=    NSX REST GET
    ...    ${INFRA_BASE}/domains/${domain}/security-policies/${policy_id}/rules
    RETURN    ${body}

Delete DFW Rule
    [Documentation]    Delete a single DFW rule from a security policy.
    [Arguments]    ${policy_id}    ${rule_id}    ${domain}=default
    Safe Delete Policy Object
    ...    ${INFRA_BASE}/domains/${domain}/security-policies/${policy_id}/rules/${rule_id}

Delete Security Policy
    [Documentation]    Delete a security policy (and all its rules) by ID.
    [Arguments]    ${policy_id}    ${domain}=default
    Safe Delete Policy Object    ${INFRA_BASE}/domains/${domain}/security-policies/${policy_id}

# ──────────────────────────────────────────────
# Infra / Manager API
# ──────────────────────────────────────────────

Get Manager Cluster Status
    [Documentation]    Retrieve NSX Manager cluster status via the management API.
    ${body}=    NSX REST GET    ${MGMT_BASE}/cluster/status
    RETURN    ${body}

Get Transport Zones
    [Documentation]    List all transport zones.
    ${body}=    NSX REST GET    ${MGMT_BASE}/transport-zones
    RETURN    ${body}

Get Transport Node Status
    [Documentation]    Retrieve status for a specific transport node.
    [Arguments]    ${tn_id}
    ${body}=    NSX REST GET    ${MGMT_BASE}/transport-nodes/${tn_id}/status
    RETURN    ${body}

Get All Transport Node Statuses
    [Documentation]    List the status of all transport nodes.
    ${body}=    NSX REST GET    ${MGMT_BASE}/transport-nodes/status
    RETURN    ${body}

Get Compute Managers
    [Documentation]    List all registered compute managers (vCenter).
    ${body}=    NSX REST GET    ${MGMT_BASE}/fabric/compute-managers
    RETURN    ${body}

Get Compute Manager Status
    [Documentation]    Retrieve the registration and connectivity status of a compute manager.
    [Arguments]    ${cm_id}
    ${body}=    NSX REST GET    ${MGMT_BASE}/fabric/compute-managers/${cm_id}/status
    RETURN    ${body}
