#!/bin/bash
#
# Z-FORGE Multi-Version Build Script with Comprehensive Logging
# Build different configurations with detailed logging and monitoring
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_BASE_DIR="$SCRIPT_DIR/logs/builds"
OUTPUT_DIR="$SCRIPT_DIR/output"
BUILD_TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Ensure directories exist
mkdir -p "$LOG_BASE_DIR"
mkdir -p "$OUTPUT_DIR"

# Logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$CURRENT_LOG"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$CURRENT_LOG"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$CURRENT_LOG"; }
log_section() { echo -e "\n${CYAN}═══════════════════════════════════════${NC}\n${CYAN}  $1${NC}\n${CYAN}═══════════════════════════════════════${NC}" | tee -a "$CURRENT_LOG"; }
log_build() { echo -e "${MAGENTA}[BUILD]${NC} $1" | tee -a "$CURRENT_LOG"; }

# Track build results
declare -A BUILD_RESULTS
declare -A BUILD_TIMES
declare -A BUILD_LOGS

# Monitor system resources during build
monitor_resources() {
    local pid=$1
    local log_file=$2
    
    echo "=== Resource Monitoring ===" >> "$log_file"
    while kill -0 $pid 2>/dev/null; do
        echo "$(date '+%Y-%m-%d %H:%M:%S')" >> "$log_file"
        echo "Memory Usage:" >> "$log_file"
        free -h >> "$log_file"
        echo "CPU Load:" >> "$log_file"
        uptime >> "$log_file"
        echo "Disk Usage (/tmp):" >> "$log_file"
        df -h /tmp >> "$log_file"
        echo "---" >> "$log_file"
        sleep 30
    done
}

# Build with comprehensive logging
build_version() {
    local spec_file=$1
    local spec_name=$(basename "$spec_file" .yml)
    local build_log="$LOG_BASE_DIR/${BUILD_TIMESTAMP}_${spec_name}.log"
    local resource_log="$LOG_BASE_DIR/${BUILD_TIMESTAMP}_${spec_name}_resources.log"
    
    CURRENT_LOG="$build_log"
    BUILD_LOGS["$spec_name"]="$build_log"
    
    log_section "Building: $spec_name"
    log_info "Specification: $spec_file"
    log_info "Log file: $build_log"
    log_info "Start time: $(date)"
    
    # Record start time
    local start_time=$(date +%s)
    
    # Start resource monitoring in background
    (monitor_resources $$ "$resource_log") &
    local monitor_pid=$!
    
    # Run the build with detailed output
    if sudo python3 build.py \
        --spec "$spec_file" \
        --workspace "/tmp/zforge-workspace-${spec_name}" \
        --verbose \
        2>&1 | tee -a "$build_log"; then
        
        BUILD_RESULTS["$spec_name"]="SUCCESS"
        log_info "✅ Build completed successfully!"
        
        # Move ISO to output directory with version name
        local iso_file=$(ls -t /tmp/zforge-workspace-${spec_name}/*.iso 2>/dev/null | head -1)
        if [[ -n "$iso_file" ]]; then
            local new_name="${OUTPUT_DIR}/${spec_name}_${BUILD_TIMESTAMP}.iso"
            mv "$iso_file" "$new_name"
            log_info "ISO saved: $new_name"
            log_info "ISO size: $(du -h "$new_name" | cut -f1)"
        fi
    else
        BUILD_RESULTS["$spec_name"]="FAILED"
        log_error "❌ Build failed!"
    fi
    
    # Stop resource monitoring
    kill $monitor_pid 2>/dev/null || true
    
    # Record end time and calculate duration
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    BUILD_TIMES["$spec_name"]="$duration"
    
    log_info "End time: $(date)"
    log_info "Duration: $(printf '%02d:%02d:%02d' $((duration/3600)) $((duration%3600/60)) $((duration%60)))"
    
    # Cleanup workspace to save space
    if [[ -d "/tmp/zforge-workspace-${spec_name}" ]]; then
        log_info "Cleaning up workspace..."
        sudo rm -rf "/tmp/zforge-workspace-${spec_name}"
    fi
    
    echo ""
}

# Generate summary report
generate_report() {
    local report_file="$LOG_BASE_DIR/${BUILD_TIMESTAMP}_summary.txt"
    
    {
        echo "═══════════════════════════════════════════════════════════════"
        echo "  Z-FORGE Build Summary Report"
        echo "  Date: $(date)"
        echo "═══════════════════════════════════════════════════════════════"
        echo ""
        echo "Build Results:"
        echo "--------------"
        
        for spec in "${!BUILD_RESULTS[@]}"; do
            local result="${BUILD_RESULTS[$spec]}"
            local duration="${BUILD_TIMES[$spec]}"
            local formatted_duration=$(printf '%02d:%02d:%02d' $((duration/3600)) $((duration%3600/60)) $((duration%60)))
            
            if [[ "$result" == "SUCCESS" ]]; then
                echo "✅ $spec: SUCCESS (Duration: $formatted_duration)"
            else
                echo "❌ $spec: FAILED (Duration: $formatted_duration)"
            fi
        done
        
        echo ""
        echo "Log Files:"
        echo "----------"
        for spec in "${!BUILD_LOGS[@]}"; do
            echo "$spec: ${BUILD_LOGS[$spec]}"
        done
        
        echo ""
        echo "System Information:"
        echo "------------------"
        echo "CPU: $(lscpu | grep 'Model name' | cut -d: -f2 | xargs)"
        echo "Cores: $(nproc)"
        echo "RAM: $(free -h | awk '/^Mem:/ {print $2}')"
        echo "Disk (/tmp): $(df -h /tmp | awk 'NR==2 {print $4}' | xargs) available"
        
    } | tee "$report_file"
    
    echo ""
    echo "Report saved: $report_file"
}

# Show available build specifications
show_specs() {
    echo ""
    echo "Available Build Specifications:"
    echo "-------------------------------"
    local i=1
    for spec in build_specs/*.yml; do
        [[ -f "$spec" ]] || continue
        local name=$(basename "$spec" .yml)
        local desc=$(grep -m1 "^#" "$spec" 2>/dev/null | sed 's/^# *//' || echo "No description")
        printf "%2d) %-30s - %s\n" $i "$name" "$desc"
        ((i++))
    done
    echo ""
}

# Main execution
main() {
    clear
    echo -e "${CYAN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║         Z-FORGE Multi-Version Build System                   ║
║                 with Comprehensive Logging                   ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    # Check for root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
    
    # Default log for general messages
    CURRENT_LOG="$LOG_BASE_DIR/${BUILD_TIMESTAMP}_general.log"
    
    # Parse command line arguments
    case "${1:-menu}" in
        all)
            # Build all active specs
            log_section "Building ALL Specifications"
            for spec in build_specs/*.yml; do
                [[ -f "$spec" ]] || continue
                [[ "$spec" == *"deprecated"* ]] && continue
                build_version "$spec"
            done
            generate_report
            ;;
            
        minimal)
            # Build minimal configuration
            log_section "Building Minimal Configuration"
            build_version "build_specs/build_spec_outside_packages.yml"
            generate_report
            ;;
            
        proxmox)
            # Build Proxmox configurations
            log_section "Building Proxmox Configurations"
            build_version "build_specs/build_spec_proxmox9.yml"
            build_version "build_specs/build_spec_proxmox_full.yml"
            generate_report
            ;;
            
        stable)
            # Build stable configuration
            log_section "Building Stable Configuration"
            build_version "build_specs/build_spec_stable.yml"
            generate_report
            ;;
            
        quick)
            # Quick test build
            log_section "Quick Test Build"
            build_version "build_specs/build_spec_trixie_clean.yml"
            generate_report
            ;;
            
        custom)
            # Custom selection
            show_specs
            echo -n "Enter spec numbers to build (space-separated): "
            read -r selections
            
            log_section "Building Selected Specifications"
            for num in $selections; do
                local spec=$(ls build_specs/*.yml 2>/dev/null | sed -n "${num}p")
                if [[ -f "$spec" ]]; then
                    build_version "$spec"
                else
                    log_error "Invalid selection: $num"
                fi
            done
            generate_report
            ;;
            
        watch)
            # Watch logs in real-time
            if [[ -n "${2:-}" ]]; then
                tail -f "$LOG_BASE_DIR"/*"$2"*.log
            else
                echo "Recent log files:"
                ls -lt "$LOG_BASE_DIR" | head -10
                echo ""
                echo "Usage: $0 watch <pattern>"
            fi
            ;;
            
        clean)
            # Clean up old logs and workspaces
            log_section "Cleaning up old builds"
            
            echo -n "Remove logs older than 7 days? [y/N]: "
            read -r answer
            if [[ "$answer" == "y" ]]; then
                find "$LOG_BASE_DIR" -type f -mtime +7 -delete
                log_info "Old logs removed"
            fi
            
            echo -n "Clean /tmp/zforge-* directories? [y/N]: "
            read -r answer
            if [[ "$answer" == "y" ]]; then
                sudo rm -rf /tmp/zforge-*
                log_info "Workspaces cleaned"
            fi
            ;;
            
        menu|*)
            # Interactive menu
            while true; do
                echo ""
                echo "Build Options:"
                echo "--------------"
                echo "1) Build ALL specifications"
                echo "2) Build Minimal (fastest, for testing)"
                echo "3) Build Proxmox versions"
                echo "4) Build Stable version"
                echo "5) Quick test build"
                echo "6) Custom selection"
                echo "7) Watch logs"
                echo "8) Clean old builds"
                echo "9) Show recent builds"
                echo "q) Quit"
                echo ""
                echo -n "Select option: "
                read -r choice
                
                case $choice in
                    1) $0 all; break ;;
                    2) $0 minimal; break ;;
                    3) $0 proxmox; break ;;
                    4) $0 stable; break ;;
                    5) $0 quick; break ;;
                    6) $0 custom; break ;;
                    7) $0 watch; break ;;
                    8) $0 clean ;;
                    9) 
                        echo ""
                        echo "Recent builds:"
                        ls -lt "$OUTPUT_DIR"/*.iso 2>/dev/null | head -10 || echo "No ISOs found"
                        echo ""
                        echo "Recent logs:"
                        ls -lt "$LOG_BASE_DIR" | head -10
                        ;;
                    q|Q) exit 0 ;;
                    *) log_error "Invalid option" ;;
                esac
            done
            ;;
    esac
}

# Command shortcuts for quick builds
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

# Example usage:
# sudo ./build-all-versions.sh all          # Build everything
# sudo ./build-all-versions.sh minimal      # Quick minimal build
# sudo ./build-all-versions.sh proxmox      # Proxmox builds only
# sudo ./build-all-versions.sh stable       # Stable version only
# sudo ./build-all-versions.sh custom       # Interactive selection
# sudo ./build-all-versions.sh watch build  # Watch logs with 'build' in name
# sudo ./build-all-versions.sh clean        # Clean old files