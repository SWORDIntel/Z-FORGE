#!/bin/bash
#
# ZFS LiveCD Builder - Mass Deployment Orchestrator
# Advanced mass deployment system with scheduling and monitoring
#
# Features:
# - Wake-on-LAN coordination
# - Parallel deployment management
# - Progress monitoring and reporting
# - Failure handling and recovery
#

set -euo pipefail

# Source common libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
# shellcheck source=../../../lib/common.sh
source "$PROJECT_ROOT/lib/common.sh"

# Mass deployment configuration
readonly MASS_DEPLOY_VERSION="2.0.0"
readonly DEPLOYMENT_CONFIG_DIR="$PROJECT_ROOT/config/deployment"
readonly DEPLOYMENT_LOG_DIR="/var/log/zfs-livecd-deployment"
readonly DEPLOYMENT_STATE_DIR="/var/lib/zfs-livecd-deployment"

# Deployment limits and settings
readonly MAX_CONCURRENT_DEPLOYMENTS=50
readonly DEPLOYMENT_TIMEOUT_SECONDS=3600
readonly WOL_RETRY_COUNT=3
readonly WOL_RETRY_INTERVAL=30
readonly PROGRESS_UPDATE_INTERVAL=10

# Deployment state tracking
declare -A DEPLOYMENT_STATUS
declare -A DEPLOYMENT_START_TIMES
declare -A DEPLOYMENT_PROGRESS
declare -A CLIENT_MAC_ADDRESSES
declare -A CLIENT_HOSTNAMES
declare -g DEPLOYMENT_SESSION_ID=""
declare -g DEPLOYMENT_ACTIVE=false

# Initialize mass deployment system
mass_deploy_init() {
    local config_file="${1:-$DEPLOYMENT_CONFIG_DIR/mass-deployment.conf}"
    
    log_info "Initializing Mass Deployment Orchestrator v$MASS_DEPLOY_VERSION"
    
    # Create necessary directories
    for dir in "$DEPLOYMENT_CONFIG_DIR" "$DEPLOYMENT_LOG_DIR" "$DEPLOYMENT_STATE_DIR"; do
        safe_mkdir "$dir" 755
    done
    
    # Generate unique session ID
    DEPLOYMENT_SESSION_ID="deploy-$(date +%Y%m%d-%H%M%S)-$$"
    
    # Load configuration
    if [[ -f "$config_file" ]]; then
        # shellcheck source=/dev/null
        source "$config_file"
        log_info "Configuration loaded from: $config_file"
    else
        mass_deploy_create_default_config "$config_file"
    fi
    
    # Create session directory
    safe_mkdir "$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID" 755
    
    log_info "Mass deployment system initialized"
    log_info "Session ID: $DEPLOYMENT_SESSION_ID"
}

# Create default mass deployment configuration
mass_deploy_create_default_config() {
    local config_file="$1"
    
    log_info "Creating default mass deployment configuration: $config_file"
    
    cat > "$config_file" << EOF
# ZFS LiveCD Mass Deployment Configuration
# Generated: $(date)

# Deployment Settings
MAX_CONCURRENT_DEPLOYMENTS=$MAX_CONCURRENT_DEPLOYMENTS
DEPLOYMENT_TIMEOUT_SECONDS=$DEPLOYMENT_TIMEOUT_SECONDS
PROGRESS_UPDATE_INTERVAL=$PROGRESS_UPDATE_INTERVAL

# Wake-on-LAN Settings
ENABLE_WOL=true
WOL_RETRY_COUNT=$WOL_RETRY_COUNT
WOL_RETRY_INTERVAL=$WOL_RETRY_INTERVAL
WOL_BROADCAST_ADDRESS="255.255.255.255"

# Network Settings
PXE_SERVER_IP=""
DHCP_LEASE_CHECK_INTERVAL=30
NETWORK_SCAN_ENABLED=true
PING_TIMEOUT=5

# Monitoring Settings
ENABLE_MONITORING=true
MONITORING_WEBHOOK=""
SLACK_WEBHOOK=""
EMAIL_NOTIFICATIONS=""

# Deployment Profiles
DEFAULT_DEPLOYMENT_PROFILE="standard"
DEPLOYMENT_PROFILES_DIR="$DEPLOYMENT_CONFIG_DIR/profiles"

# Logging Settings
LOG_LEVEL="INFO"
LOG_ROTATION_SIZE="100M"
LOG_RETENTION_DAYS=30

# Recovery Settings
AUTO_RETRY_FAILED=true
MAX_RETRY_ATTEMPTS=3
RECOVERY_DELAY_SECONDS=300
EOF

    chmod 600 "$config_file"
    log_info "Default configuration created: $config_file"
}

# Load client database from file
mass_deploy_load_clients() {
    local client_db_file="${1:-$DEPLOYMENT_CONFIG_DIR/clients.db}"
    local loaded_count=0
    
    if [[ ! -f "$client_db_file" ]]; then
        log_warn "Client database not found: $client_db_file"
        mass_deploy_create_sample_client_db "$client_db_file"
        return 1
    fi
    
    log_info "Loading client database: $client_db_file"
    
    # Parse client database
    while IFS=',' read -r mac hostname description location profile; do
        # Skip comments and empty lines
        [[ "$mac" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$mac" ]] && continue
        
        # Validate MAC address format
        if [[ ! "$mac" =~ ^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$ ]]; then
            log_warn "Invalid MAC address format: $mac"
            continue
        fi
        
        # Store client information
        CLIENT_MAC_ADDRESSES["$hostname"]="$mac"
        CLIENT_HOSTNAMES["$mac"]="$hostname"
        DEPLOYMENT_STATUS["$mac"]="PENDING"
        
        ((loaded_count++))
        
    done < <(grep -v '^[[:space:]]*#' "$client_db_file" | grep -v '^[[:space:]]*$')
    
    log_info "Loaded $loaded_count clients from database"
    return 0
}

# Create sample client database
mass_deploy_create_sample_client_db() {
    local client_db_file="$1"
    
    log_info "Creating sample client database: $client_db_file"
    
    cat > "$client_db_file" << EOF
# ZFS LiveCD Client Database
# Format: MAC_ADDRESS,HOSTNAME,DESCRIPTION,LOCATION,PROFILE
# Example: 00:11:22:33:44:55,workstation-01,Development Machine,Lab-A,developer
#
# Profiles available: standard, minimal, developer, server, recovery
#

# Example clients (remove or replace with actual data)
00:11:22:33:44:01,workstation-01,Primary Development Machine,Lab-A,developer
00:11:22:33:44:02,workstation-02,Secondary Development Machine,Lab-A,developer
00:11:22:33:44:03,server-01,Test Server,Server Room,server
00:11:22:33:44:04,laptop-01,Mobile Development Unit,Mobile,minimal
00:11:22:33:44:05,recovery-station,Emergency Recovery Station,IT Office,recovery
EOF
    
    chmod 644 "$client_db_file"
    log_info "Sample client database created: $client_db_file"
}

# Network discovery for client identification
mass_deploy_network_discovery() {
    local network_range="${1:-auto}"
    local discovery_timeout="${2:-60}"
    
    log_info "Starting network discovery"
    
    # Auto-detect network range if not specified
    if [[ "$network_range" == "auto" ]]; then
        network_range=$(ip route | grep -E '192\.168\.|10\.|172\.' | grep -v default | head -1 | awk '{print $1}')
        if [[ -z "$network_range" ]]; then
            log_error "Unable to auto-detect network range"
            return 1
        fi
    fi
    
    log_info "Scanning network range: $network_range"
    
    # Create discovery results file
    local discovery_file="$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/network-discovery.txt"
    
    # Perform network scan
    nmap -sn "$network_range" | grep -E 'Nmap scan report|MAC Address' | paste - - | \
    while read -r scan_line; do
        local ip_addr=$(echo "$scan_line" | grep -oP 'for \K[\d.]+')
        local mac_addr=$(echo "$scan_line" | grep -oP 'MAC Address: \K[0-9a-fA-F:]{17}')
        local vendor=$(echo "$scan_line" | grep -oP 'MAC Address: [0-9a-fA-F:]+ \(\K[^)]+')
        
        if [[ -n "$ip_addr" && -n "$mac_addr" ]]; then
            local hostname=""
            hostname=$(nslookup "$ip_addr" 2>/dev/null | grep -oP 'name = \K[^.]+' || echo "unknown")
            
            echo "$mac_addr,$ip_addr,$hostname,$vendor,$(date '+%Y-%m-%d %H:%M:%S')" >> "$discovery_file"
            
            # Check if this MAC is in our client database
            if [[ -n "${CLIENT_HOSTNAMES[$mac_addr]:-}" ]]; then
                log_info "Found registered client: $mac_addr (${CLIENT_HOSTNAMES[$mac_addr]})"
            fi
        fi
    done
    
    log_info "Network discovery completed. Results: $discovery_file"
    
    # Display summary
    if [[ -f "$discovery_file" ]]; then
        local total_hosts=$(wc -l < "$discovery_file")
        local registered_hosts=0
        
        while IFS=',' read -r mac_addr _; do
            [[ -n "${CLIENT_HOSTNAMES[$mac_addr]:-}" ]] && ((registered_hosts++))
        done < "$discovery_file"
        
        log_info "Discovery summary: $total_hosts hosts found, $registered_hosts registered clients"
    fi
}

# Send Wake-on-LAN packets to clients
mass_deploy_wake_clients() {
    local client_list="${1:-all}"
    local wol_delay="${2:-$WOL_RETRY_INTERVAL}"
    
    log_info "Sending Wake-on-LAN packets"
    
    declare -a target_macs
    
    # Build target MAC list
    if [[ "$client_list" == "all" ]]; then
        for mac in "${!CLIENT_HOSTNAMES[@]}"; do
            target_macs+=("$mac")
        done
    else
        # Parse comma-separated list
        IFS=',' read -ra client_names <<< "$client_list"
        for client_name in "${client_names[@]}"; do
            if [[ -n "${CLIENT_MAC_ADDRESSES[$client_name]:-}" ]]; then
                target_macs+=("${CLIENT_MAC_ADDRESSES[$client_name]}")
            else
                log_warn "Client not found in database: $client_name"
            fi
        done
    fi
    
    if [[ ${#target_macs[@]} -eq 0 ]]; then
        log_error "No valid clients found for Wake-on-LAN"
        return 1
    fi
    
    log_info "Waking ${#target_macs[@]} clients"
    
    # Send WOL packets with retries
    for retry in $(seq 1 $WOL_RETRY_COUNT); do
        log_info "WOL attempt $retry/$WOL_RETRY_COUNT"
        
        for mac_addr in "${target_macs[@]}"; do
            local hostname="${CLIENT_HOSTNAMES[$mac_addr]}"
            
            log_debug "Sending WOL packet to $mac_addr ($hostname)"
            
            # Send using multiple methods for reliability
            wakeonlan "$mac_addr" 2>/dev/null || true
            etherwake "$mac_addr" 2>/dev/null || true
            
            # Log attempt
            echo "$(date '+%Y-%m-%d %H:%M:%S'),$mac_addr,$hostname,WOL_SENT,attempt_$retry" >> \
                "$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/wol-log.txt"
        done
        
        # Wait between retry attempts
        if [[ $retry -lt $WOL_RETRY_COUNT ]]; then
            log_info "Waiting ${wol_delay}s before next attempt..."
            sleep "$wol_delay"
        fi
    done
    
    log_info "Wake-on-LAN sequence completed"
    
    # Wait for clients to boot and request DHCP
    log_info "Waiting for clients to come online..."
    sleep 60
    
    # Check which clients are responding
    mass_deploy_check_client_status
}

# Check client status and DHCP assignments
mass_deploy_check_client_status() {
    log_info "Checking client status"
    
    local status_file="$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/client-status.txt"
    local dhcp_leases="/var/lib/dhcp/dhcpd.leases"
    local online_count=0
    local total_count=${#CLIENT_HOSTNAMES[@]}
    
    # Check DHCP leases
    for mac_addr in "${!CLIENT_HOSTNAMES[@]}"; do
        local hostname="${CLIENT_HOSTNAMES[$mac_addr]}"
        local ip_addr=""
        local status="OFFLINE"
        
        # Check DHCP lease
        if [[ -f "$dhcp_leases" ]]; then
            ip_addr=$(awk '/lease/ { ip = $2 } /client-identifier/ { id = $2 } /hardware ethernet/ { mac = $3; gsub(/[";]/, "", mac) } /binding state active/ { state = "active" } /^}/ { if (mac == "'$mac_addr'" && state == "active") print ip; mac=""; state="" }' "$dhcp_leases" | tail -1)
        fi
        
        # Try alternative DHCP lease locations
        if [[ -z "$ip_addr" && -f "/var/lib/dhcpcd5/dhcpcd.leases" ]]; then
            ip_addr=$(grep -A5 -B5 "$mac_addr" /var/lib/dhcpcd5/dhcpcd.leases | grep "new_ip_address" | cut -d'=' -f2 | tr -d "'" | head -1)
        fi
        
        # Ping test if IP found
        if [[ -n "$ip_addr" ]]; then
            if ping -c 1 -W 2 "$ip_addr" >/dev/null 2>&1; then
                status="ONLINE"
                ((online_count++))
                DEPLOYMENT_STATUS["$mac_addr"]="READY"
                log_info "Client online: $hostname ($mac_addr) -> $ip_addr"
            else
                status="DHCP_ONLY"
                DEPLOYMENT_STATUS["$mac_addr"]="DHCP_ASSIGNED"
            fi
        else
            DEPLOYMENT_STATUS["$mac_addr"]="OFFLINE"
        fi
        
        # Log status
        echo "$(date '+%Y-%m-%d %H:%M:%S'),$mac_addr,$hostname,$ip_addr,$status" >> "$status_file"
    done
    
    log_info "Client status check completed: $online_count/$total_count online"
    
    # Return success if any clients are online
    [[ $online_count -gt 0 ]]
}

# Execute mass deployment
mass_deploy_execute() {
    local deployment_profile="${1:-standard}"
    local max_concurrent="${2:-$MAX_CONCURRENT_DEPLOYMENTS}"
    
    log_info "Starting mass deployment execution"
    log_info "Profile: $deployment_profile, Max concurrent: $max_concurrent"
    
    DEPLOYMENT_ACTIVE=true
    
    # Create deployment tracking files
    local deployment_log="$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/deployment.log"
    local progress_file="$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/progress.txt"
    
    # Initialize progress tracking
    for mac_addr in "${!CLIENT_HOSTNAMES[@]}"; do
        if [[ "${DEPLOYMENT_STATUS[$mac_addr]}" == "READY" ]]; then
            DEPLOYMENT_PROGRESS["$mac_addr"]=0
            DEPLOYMENT_START_TIMES["$mac_addr"]=$(date +%s)
        fi
    done
    
    # Start progress monitoring in background
    mass_deploy_monitor_progress &
    local monitor_pid=$!
    
    # Start deployment batches
    local active_deployments=0
    local completed_deployments=0
    local failed_deployments=0
    local total_deployments=0
    
    # Count ready clients
    for mac_addr in "${!CLIENT_HOSTNAMES[@]}"; do
        [[ "${DEPLOYMENT_STATUS[$mac_addr]}" == "READY" ]] && ((total_deployments++))
    done
    
    log_info "Starting deployment for $total_deployments clients"
    
    # Process deployments in batches
    for mac_addr in "${!CLIENT_HOSTNAMES[@]}"; do
        if [[ "${DEPLOYMENT_STATUS[$mac_addr]}" != "READY" ]]; then
            continue
        fi
        
        # Wait for available slot
        while [[ $active_deployments -ge $max_concurrent ]]; do
            sleep 5
            mass_deploy_check_active_deployments
            # Update counters based on completed deployments
        done
        
        # Start deployment for this client
        local hostname="${CLIENT_HOSTNAMES[$mac_addr]}"
        log_info "Starting deployment: $hostname ($mac_addr)"
        
        DEPLOYMENT_STATUS["$mac_addr"]="DEPLOYING"
        
        # Launch deployment in background
        mass_deploy_single_client "$mac_addr" "$deployment_profile" &
        local deploy_pid=$!
        
        # Track deployment
        echo "$deploy_pid,$mac_addr,$hostname,$(date +%s)" >> \
            "$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/active-deployments.txt"
        
        ((active_deployments++))
        
        # Brief delay between deployment starts
        sleep 2
    done
    
    # Wait for all deployments to complete
    log_info "All deployments started, waiting for completion..."
    
    while [[ $active_deployments -gt 0 ]]; do
        sleep 30
        mass_deploy_check_active_deployments
        
        local current_completed=0
        local current_failed=0
        
        for mac_addr in "${!DEPLOYMENT_STATUS[@]}"; do
            case "${DEPLOYMENT_STATUS[$mac_addr]}" in
                "COMPLETED") ((current_completed++)) ;;
                "FAILED"|"TIMEOUT") ((current_failed++)) ;;
            esac
        done
        
        completed_deployments=$current_completed
        failed_deployments=$current_failed
        active_deployments=$((total_deployments - completed_deployments - failed_deployments))
        
        log_info "Deployment progress: $completed_deployments completed, $failed_deployments failed, $active_deployments active"
    done
    
    # Stop progress monitor
    kill $monitor_pid 2>/dev/null || true
    
    DEPLOYMENT_ACTIVE=false
    
    # Generate final report
    mass_deploy_generate_report
    
    log_info "Mass deployment completed"
    log_info "Results: $completed_deployments completed, $failed_deployments failed"
    
    return $([[ $failed_deployments -eq 0 ]] && echo 0 || echo 1)
}

# Deploy to a single client
mass_deploy_single_client() {
    local mac_addr="$1"
    local profile="$2"
    local hostname="${CLIENT_HOSTNAMES[$mac_addr]}"
    local deployment_start=$(date +%s)
    
    log_info "Deploying to client: $hostname ($mac_addr)"
    
    # Client-specific deployment logic would go here
    # For now, simulate deployment process
    
    local deployment_steps=("Preparing boot environment" "Loading kernel" "Mounting filesystems" "Configuring system" "Finalizing setup")
    local step_count=${#deployment_steps[@]}
    
    for i in "${!deployment_steps[@]}"; do
        local step="${deployment_steps[$i]}"
        local progress=$(( (i + 1) * 100 / step_count ))
        
        log_debug "$hostname: $step"
        
        # Update progress
        DEPLOYMENT_PROGRESS["$mac_addr"]=$progress
        
        # Simulate work (replace with actual deployment logic)
        sleep $((RANDOM % 30 + 10))
        
        # Check for timeout
        local current_time=$(date +%s)
        local elapsed=$((current_time - deployment_start))
        
        if [[ $elapsed -gt $DEPLOYMENT_TIMEOUT_SECONDS ]]; then
            log_error "Deployment timeout for $hostname ($mac_addr)"
            DEPLOYMENT_STATUS["$mac_addr"]="TIMEOUT"
            return 1
        fi
    done
    
    # Mark as completed
    DEPLOYMENT_STATUS["$mac_addr"]="COMPLETED"
    DEPLOYMENT_PROGRESS["$mac_addr"]=100
    
    local deployment_time=$(($(date +%s) - deployment_start))
    log_info "Deployment completed for $hostname in ${deployment_time}s"
    
    return 0
}

# Monitor deployment progress
mass_deploy_monitor_progress() {
    local progress_file="$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/progress.txt"
    
    while [[ $DEPLOYMENT_ACTIVE == true ]]; do
        local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
        
        # Write current progress to file
        echo "# Deployment Progress Report - $timestamp" > "$progress_file"
        echo "# Session: $DEPLOYMENT_SESSION_ID" >> "$progress_file"
        echo "" >> "$progress_file"
        
        for mac_addr in "${!CLIENT_HOSTNAMES[@]}"; do
            local hostname="${CLIENT_HOSTNAMES[$mac_addr]}"
            local status="${DEPLOYMENT_STATUS[$mac_addr]}"
            local progress="${DEPLOYMENT_PROGRESS[$mac_addr]:-0}"
            
            echo "$mac_addr,$hostname,$status,$progress%" >> "$progress_file"
        done
        
        # Send progress update to monitoring systems
        mass_deploy_send_progress_update
        
        sleep $PROGRESS_UPDATE_INTERVAL
    done
}

# Check active deployments and clean up completed ones
mass_deploy_check_active_deployments() {
    local active_file="$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/active-deployments.txt"
    
    if [[ ! -f "$active_file" ]]; then
        return 0
    fi
    
    # Check each active deployment
    while IFS=',' read -r pid mac_addr hostname start_time; do
        if ! kill -0 "$pid" 2>/dev/null; then
            # Process has finished, update status if not already set
            if [[ "${DEPLOYMENT_STATUS[$mac_addr]}" == "DEPLOYING" ]]; then
                # Check exit status would require more complex tracking
                # For now, assume success if process completed
                DEPLOYMENT_STATUS["$mac_addr"]="COMPLETED"
                DEPLOYMENT_PROGRESS["$mac_addr"]=100
                log_info "Deployment completed for $hostname ($mac_addr)"
            fi
            
            # Remove from active list
            sed -i "/^$pid,/d" "$active_file"
        fi
    done < "$active_file"
}

# Send progress updates to monitoring systems
mass_deploy_send_progress_update() {
    local webhook_url="${MONITORING_WEBHOOK:-}"
    
    if [[ -z "$webhook_url" ]]; then
        return 0
    fi
    
    # Count deployment status
    local total=0
    local completed=0
    local failed=0
    local active=0
    
    for mac_addr in "${!DEPLOYMENT_STATUS[@]}"; do
        case "${DEPLOYMENT_STATUS[$mac_addr]}" in
            "COMPLETED") ((completed++)) ;;
            "FAILED"|"TIMEOUT") ((failed++)) ;;
            "DEPLOYING") ((active++)) ;;
        esac
        ((total++))
    done
    
    # Create JSON payload
    local payload=$(cat << EOF
{
    "session_id": "$DEPLOYMENT_SESSION_ID",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)",
    "status": {
        "total": $total,
        "completed": $completed,
        "failed": $failed,
        "active": $active
    }
}
EOF
)
    
    # Send webhook
    curl -X POST -H "Content-Type: application/json" -d "$payload" "$webhook_url" 2>/dev/null || true
}

# Generate deployment report
mass_deploy_generate_report() {
    local report_file="$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/final-report.txt"
    local html_report="$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/final-report.html"
    
    log_info "Generating deployment report"
    
    # Text report
    cat > "$report_file" << EOF
ZFS LiveCD Mass Deployment Report
=================================
Session ID: $DEPLOYMENT_SESSION_ID
Generated: $(date)

Deployment Summary:
EOF
    
    local total_clients=0
    local completed_clients=0
    local failed_clients=0
    local offline_clients=0
    
    for mac_addr in "${!CLIENT_HOSTNAMES[@]}"; do
        local status="${DEPLOYMENT_STATUS[$mac_addr]}"
        ((total_clients++))
        
        case "$status" in
            "COMPLETED") ((completed_clients++)) ;;
            "FAILED"|"TIMEOUT") ((failed_clients++)) ;;
            "OFFLINE"|"PENDING") ((offline_clients++)) ;;
        esac
    done
    
    cat >> "$report_file" << EOF
- Total Clients: $total_clients
- Completed Successfully: $completed_clients
- Failed Deployments: $failed_clients
- Offline/Not Attempted: $offline_clients
- Success Rate: $(( completed_clients * 100 / total_clients ))%

Detailed Results:
EOF
    
    printf "%-18s %-20s %-12s %-8s %s\n" "MAC Address" "Hostname" "Status" "Progress" "Notes" >> "$report_file"
    printf "%s\n" "$(printf '=%.0s' {1..80})" >> "$report_file"
    
    for mac_addr in "${!CLIENT_HOSTNAMES[@]}"; do
        local hostname="${CLIENT_HOSTNAMES[$mac_addr]}"
        local status="${DEPLOYMENT_STATUS[$mac_addr]}"
        local progress="${DEPLOYMENT_PROGRESS[$mac_addr]:-0}%"
        local notes=""
        
        case "$status" in
            "TIMEOUT") notes="Deployment timed out" ;;
            "FAILED") notes="Deployment failed" ;;
            "OFFLINE") notes="Client not responding" ;;
            "COMPLETED") notes="Successfully deployed" ;;
        esac
        
        printf "%-18s %-20s %-12s %-8s %s\n" "$mac_addr" "$hostname" "$status" "$progress" "$notes" >> "$report_file"
    done
    
    # Add timing information
    echo "" >> "$report_file"
    echo "Deployment Timeline:" >> "$report_file"
    
    if [[ -f "$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/deployment.log" ]]; then
        tail -20 "$DEPLOYMENT_STATE_DIR/$DEPLOYMENT_SESSION_ID/deployment.log" >> "$report_file"
    fi
    
    log_info "Deployment report generated: $report_file"
}

# Main function
main() {
    case "${1:-}" in
        init|initialize)
            mass_deploy_init "${2:-}"
            ;;
        load-clients)
            mass_deploy_init
            mass_deploy_load_clients "${2:-}"
            ;;
        network-discovery)
            mass_deploy_init
            mass_deploy_network_discovery "${2:-auto}" "${3:-60}"
            ;;
        wake-clients)
            mass_deploy_init
            mass_deploy_load_clients
            mass_deploy_wake_clients "${2:-all}" "${3:-$WOL_RETRY_INTERVAL}"
            ;;
        check-status)
            mass_deploy_init
            mass_deploy_load_clients
            mass_deploy_check_client_status
            ;;
        deploy)
            mass_deploy_init
            mass_deploy_load_clients
            mass_deploy_execute "${2:-standard}" "${3:-$MAX_CONCURRENT_DEPLOYMENTS}"
            ;;
        full-deployment)
            mass_deploy_init
            mass_deploy_load_clients
            mass_deploy_network_discovery
            mass_deploy_wake_clients
            sleep 60
            mass_deploy_check_client_status
            mass_deploy_execute "${2:-standard}" "${3:-$MAX_CONCURRENT_DEPLOYMENTS}"
            ;;
        create-config)
            mass_deploy_create_default_config "${2:-$DEPLOYMENT_CONFIG_DIR/mass-deployment.conf}"
            ;;
        create-client-db)
            mass_deploy_create_sample_client_db "${2:-$DEPLOYMENT_CONFIG_DIR/clients.db}"
            ;;
        *)
            echo "ZFS LiveCD Mass Deployment Orchestrator v$MASS_DEPLOY_VERSION"
            echo ""
            echo "Usage: $0 COMMAND [OPTIONS]"
            echo ""
            echo "Commands:"
            echo "  init [config]              Initialize deployment system"
            echo "  load-clients [db_file]     Load client database"
            echo "  network-discovery [range]  Discover network clients"
            echo "  wake-clients [list]        Send Wake-on-LAN packets"
            echo "  check-status               Check client online status"
            echo "  deploy [profile] [max]     Execute mass deployment"
            echo "  full-deployment [profile]  Complete deployment cycle"
            echo "  create-config [file]       Create default configuration"
            echo "  create-client-db [file]    Create sample client database"
            echo ""
            echo "Examples:"
            echo "  $0 full-deployment                    # Complete deployment"
            echo "  $0 deploy standard 25                 # Deploy with max 25 concurrent"
            echo "  $0 wake-clients workstation-01,server-01  # Wake specific clients"
            echo "  $0 network-discovery 192.168.1.0/24  # Discover specific network"
            echo ""
            exit 0
            ;;
    esac
}

# Execute main function
main "$@"