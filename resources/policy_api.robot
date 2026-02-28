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
    ${adv}=    Run Keyword If    len($route_adv_types) > 0
    ...    Set Variable    ${route_adv_types}
    ...    ELSE    Create List    TIER1_CONNECTED
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
    [Documentation]    Retrieve BGP routes learned on the T0 gateway.
    [Arguments]    ${t0_id}    ${locale_service_id}
    ${body}=    NSX REST GET
    ...    ${POLICY_BASE}/infra/tier-0s/${t0_id}/locale-services/${locale_service_id}/bgp/neighbors/routes
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
    ${subnet}=    Create Dictionary    prefix_len=${vip_ip.split('/')[1]}    ip_addresses=@{["${vip_ip.split('/')[0]}"]}
    ${vip_subnets}=    Create List    ${subnet}
    Set To Dictionary    ${vip_config}    vip_subnets=${vip_subnets}
    ${edge_paths}=    Create List    ${edge_path_1}    ${edge_path_2}
    Set To Dictionary    ${vip_config}    external_interface_info=${edge_paths}
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
    [Documentation]    Create an NSX LB server pool with members.
    [Arguments]    ${id}    ${members}    ${port}
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
    NSX REST PATCH    ${INFRA_BASE}/lb-pools/${id}    ${body}
    Log    Created LB pool: ${id}

Create LB Virtual Server
    [Documentation]    Create an NSX LB virtual server (TCP/L4).
    [Arguments]    ${id}    ${pool_path}    ${vip}    ${port}    ${lb_service_path}
    ${body}=    Create Dictionary
    ...    display_name=${id}
    ...    ip_address=${vip}
    ...    ports=@{["${port}"]}
    ...    pool_path=${pool_path}
    ...    lb_service_path=${lb_service_path}
    ...    application_profile_path=/infra/lb-app-profiles/default-tcp-lb-app-profile
    NSX REST PATCH    ${INFRA_BASE}/lb-virtual-servers/${id}    ${body}
    Log    Created LB virtual server: ${id}

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
