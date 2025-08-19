#!/bin/bash
#
# Z-FORGE Server Deployment Script
# Deploy freshly built Proxmox VE 9 images to multiple servers
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO_DIR="$SCRIPT_DIR/output"
NETWORK_BOOT_DIR="$SCRIPT_DIR/network-boot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check for recent build
check_iso() {
    local latest_iso=$(ls -t "$ISO_DIR"/*.iso 2>/dev/null | head -1)
    
    if [[ -z "$latest_iso" ]]; then
        log_error "No ISO found in $ISO_DIR"
        log_info "Please build an ISO first with: sudo python3 build.py --spec build_specs/build_spec_proxmox_full.yml"
        exit 1
    fi
    
    log_info "Found ISO: $(basename "$latest_iso")"
    echo "$latest_iso"
}

# Setup PXE server
setup_pxe_server() {
    local iso_file="$1"
    
    log_info "Setting up PXE server..."
    
    # Initialize PXE server
    cd "$NETWORK_BOOT_DIR"
    sudo ./pxe-server-manager.sh init
    
    # Deploy the ISO
    log_info "Deploying ISO to PXE server..."
    sudo ./pxe-server-manager.sh deploy-images "$ISO_DIR"
    
    # Start services
    log_info "Starting PXE services..."
    sudo ./pxe-server-manager.sh start
    
    # Show status
    sudo ./pxe-server-manager.sh status
}

# Run mass deployment
mass_deploy() {
    local mode="${1:-interactive}"
    
    log_info "Starting mass deployment orchestrator..."
    
    cd "$NETWORK_BOOT_DIR"
    
    if [[ "$mode" == "auto" ]]; then
        # Auto mode - deploy to all discovered clients
        log_info "Running in automatic mode - deploying to all discovered clients"
        sudo ./mass-deployment-orchestrator.sh auto-deploy
    else
        # Interactive mode - select clients
        log_info "Running in interactive mode"
        sudo ./mass-deployment-orchestrator.sh
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "========================================="
    echo "   Z-FORGE Server Deployment System"
    echo "========================================="
    echo ""
    echo "1) Setup PXE server with latest ISO"
    echo "2) Deploy to all servers (automatic)"
    echo "3) Deploy to selected servers (interactive)"
    echo "4) Check deployment status"
    echo "5) Stop PXE server"
    echo "6) View server logs"
    echo "q) Quit"
    echo ""
    echo -n "Select option: "
}

# Main execution
main() {
    log_info "Z-FORGE Server Deployment System"
    
    # Check for root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
    
    # Check for ISO
    ISO_FILE=$(check_iso)
    
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1)
                setup_pxe_server "$ISO_FILE"
                ;;
            2)
                mass_deploy "auto"
                ;;
            3)
                mass_deploy "interactive"
                ;;
            4)
                cd "$NETWORK_BOOT_DIR"
                sudo ./mass-deployment-orchestrator.sh status
                ;;
            5)
                cd "$NETWORK_BOOT_DIR"
                sudo ./pxe-server-manager.sh stop
                ;;
            6)
                tail -f /var/log/zfs-livecd-pxe/*.log
                ;;
            q|Q)
                log_info "Exiting..."
                exit 0
                ;;
            *)
                log_error "Invalid option"
                ;;
        esac
    done
}

# Run main function
main "$@"