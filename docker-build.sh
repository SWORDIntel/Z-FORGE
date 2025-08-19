#!/bin/bash
# Z-FORGE Docker Build Script
# Build and run Z-FORGE in isolated container with RAM optimization

set -euo pipefail

# Configuration
CONTAINER_NAME="zforge-builder"
IMAGE_NAME="zforge:latest"
WORKSPACE_SIZE="20G"
LOG_DIR="$(pwd)/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo_error "Docker not installed. Install with: sudo apt install docker.io"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo_error "Docker daemon not running or no permissions. Try: sudo systemctl start docker"
        exit 1
    fi
}

# Build container image
build_image() {
    echo_info "Building Z-FORGE container image..."
    
    if docker build -t "$IMAGE_NAME" . --no-cache; then
        echo_info "Container image built successfully"
    else
        echo_error "Failed to build container image"
        exit 1
    fi
}

# Run container with optimal settings
run_container() {
    local build_spec="${1:-build_specs/build_spec_outside_packages.yml}"
    
    echo_info "Starting Z-FORGE container with RAM workspace..."
    echo_info "Build specification: $build_spec"
    
    # Stop existing container if running
    if docker ps -a --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo_warn "Stopping existing container..."
        docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    fi
    
    # Create logs directory
    mkdir -p "$LOG_DIR"
    
    # Run container with RAM optimization
    docker run -it --rm \
        --name "$CONTAINER_NAME" \
        --privileged \
        --tmpfs /workspace:rw,size="$WORKSPACE_SIZE",exec \
        -v "$LOG_DIR:/zforge/logs:rw" \
        -e "BUILD_SPEC=$build_spec" \
        "$IMAGE_NAME" \
        /bin/bash -c "
            echo '🚀 Z-FORGE RAM Container Ready'
            echo 'RAM Workspace: /workspace (${WORKSPACE_SIZE})'
            echo 'Build Spec: $build_spec'
            echo
            echo 'Quick Commands:'
            echo '  • Diagnostic: python3 tools/build_diagnostic_tool.py'
            echo '  • Build: sudo python3 build.py --spec $build_spec --workspace /workspace/zforge-build'
            echo '  • GUI: ./launch-enhanced-gui.sh'
            echo
            /bin/bash
        "
}

# Build and test function
build_and_test() {
    local build_spec="${1:-build_specs/build_spec_outside_packages.yml}"
    
    echo_info "Running automated build in container..."
    
    # Stop existing container if running
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
    
    # Create logs directory
    mkdir -p "$LOG_DIR"
    
    # Run automated build
    docker run --rm \
        --name "$CONTAINER_NAME-auto" \
        --privileged \
        --tmpfs /workspace:rw,size="$WORKSPACE_SIZE",exec \
        -v "$LOG_DIR:/zforge/logs:rw" \
        "$IMAGE_NAME" \
        /bin/bash -c "
            set -e
            echo '🔧 Running Z-FORGE diagnostic...'
            python3 tools/build_diagnostic_tool.py
            
            echo
            echo '🚀 Starting automated build...'
            echo 'Spec: $build_spec'
            echo 'Workspace: /workspace/zforge-build'
            echo
            
            sudo python3 build.py --spec '$build_spec' --workspace /workspace/zforge-build --auto-confirm
        "
}

# Show usage
show_usage() {
    cat << EOF
Z-FORGE Docker Build Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    build           Build the Docker image
    run [spec]      Run interactive container (default: build_spec_outside_packages.yml)
    auto [spec]     Run automated build in container
    shell           Open shell in running container
    stop            Stop running container
    clean           Remove container and image
    help            Show this help

Build Specifications:
    build_spec_outside_packages.yml     (95% success - RECOMMENDED)
    build_spec_minimal_proxmox.yml      (90% success)
    build_spec_tmpfs.yml                (85% success)
    build_spec_working.yml              (80% success)
    build_spec_proxmox9.yml             (75% success)
    build_spec_proxmox_full.yml         (75% success)
    build_spec.yml                      (70% success)
    build_spec_no_tmp.yml               (65% success)
    build_spec_trixie_clean.yml         (60% success)

Examples:
    $0 build                           # Build container image
    $0 run                             # Interactive with best spec
    $0 run build_spec_minimal_proxmox.yml  # Interactive with specific spec
    $0 auto                            # Automated build with best spec
    $0 shell                           # Open shell in running container

EOF
}

# Main script logic
case "${1:-help}" in
    "build")
        check_docker
        build_image
        ;;
    "run")
        check_docker
        run_container "${2:-build_specs/build_spec_outside_packages.yml}"
        ;;
    "auto")
        check_docker
        build_image
        build_and_test "${2:-build_specs/build_spec_outside_packages.yml}"
        ;;
    "shell")
        check_docker
        if docker ps --format 'table {{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            docker exec -it "$CONTAINER_NAME" /bin/bash
        else
            echo_error "Container $CONTAINER_NAME is not running"
            exit 1
        fi
        ;;
    "stop")
        check_docker
        docker rm -f "$CONTAINER_NAME" 2>/dev/null || echo_info "No container to stop"
        ;;
    "clean")
        check_docker
        docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
        docker rmi "$IMAGE_NAME" 2>/dev/null || true
        echo_info "Cleaned up container and image"
        ;;
    "help"|*)
        show_usage
        ;;
esac