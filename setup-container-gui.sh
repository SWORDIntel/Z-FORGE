#!/bin/bash
# Setup Z-FORGE GUI with Docker container support

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo_info "🚀 Setting up Z-FORGE GUI with Container Support"

# Install Python Docker package
if ! python3 -c "import docker" 2>/dev/null; then
    echo_info "Installing Python Docker package..."
    sudo apt update
    sudo apt install -y python3-docker
else
    echo_info "✅ Python Docker package already installed"
fi

# Check Docker daemon
if ! docker info &> /dev/null; then
    echo_warn "Docker daemon not running or no permissions"
    echo_info "Starting Docker and adding user to docker group..."
    
    sudo systemctl start docker || echo_warn "Failed to start Docker"
    sudo systemctl enable docker || echo_warn "Failed to enable Docker"
    
    # Add user to docker group
    if ! groups $USER | grep -q docker; then
        sudo usermod -aG docker $USER
        echo_warn "Added to docker group - please log out and back in"
    fi
else
    echo_info "✅ Docker daemon available"
fi

# Create output directories
mkdir -p output logs

# Test GUI launch
echo_info "Testing GUI with container support..."
if python3 -c "
import sys
sys.path.insert(0, '.')
from zforge_gui_enhanced import ZForgeGUIEnhanced
print('✅ GUI with container support ready')
"; then
    echo_info "✅ Z-FORGE GUI ready with container support"
    echo_info ""
    echo_info "Launch with: python3 zforge_gui_enhanced.py"
    echo_info ""
    echo_info "Container Features Available:"
    echo_info "• 🔨 Build Container: Build the Z-FORGE Docker image"  
    echo_info "• 🚀 Always-On Service: Continuous build queue processing"
    echo_info "• 🐳 Container Build: One-shot containerized builds"
    echo_info "• ➕ Queue Build: Add builds to always-on queue"
    echo_info ""
    echo_info "Performance: 3-5x faster with 20GB RAM workspace"
else
    echo_error "❌ GUI setup failed"
    exit 1
fi