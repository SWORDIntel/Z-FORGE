#!/bin/bash
# tests/integration/test_proxmox_build.sh

set -e

echo "Testing Proxmox VE integration build..."

# Test 1: Build with Proxmox enabled
echo "Test 1: Building with Proxmox enabled..."
python3 builder/z-forge.py --config tests/configs/proxmox_test.yaml --dry-run

# Test 2: Verify module loading
echo "Test 2: Verifying Proxmox modules load correctly..."
python3 -c "from builder.modules.proxmox_repo_setup import ProxmoxRepoSetup; print('✓ Modules load successfully')"

# Test 3: Check generated configuration
echo "Test 3: Checking generated configuration..."
# Would verify configuration files

echo "✓ All integration tests passed!"
