#!/bin/bash
# Test RAM-based containerized build approach

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo_info "🚀 Testing Z-FORGE RAM Container Concept"

# Test 1: Verify /dev/shm capacity
echo_info "Test 1: RAM Workspace Capacity"
shm_size=$(df -BG /dev/shm | awk 'NR==2 {print $2}' | sed 's/G//')
echo_info "/dev/shm available: ${shm_size}GB"

if [ "$shm_size" -ge 15 ]; then
    echo_info "✅ Sufficient RAM workspace (need 15GB, have ${shm_size}GB)"
else
    echo_warn "⚠️ Limited RAM workspace (need 15GB, have ${shm_size}GB)"
fi

# Test 2: Create test workspace
echo_info "Test 2: RAM Workspace Creation"
test_workspace="/dev/shm/zforge-test-$$"
mkdir -p "$test_workspace"
echo_info "✅ Created test workspace: $test_workspace"

# Test 3: Write performance test
echo_info "Test 3: RAM Workspace Performance"
time_start=$(date +%s.%N)
dd if=/dev/zero of="$test_workspace/test-1gb" bs=1M count=1024 &>/dev/null
time_end=$(date +%s.%N)
write_time=$(echo "$time_end - $time_start" | bc -l)
write_speed=$(echo "1024 / $write_time" | bc -l)

echo_info "✅ RAM Write: 1GB in ${write_time}s (${write_speed} MB/s)"

# Test 4: Container readiness simulation
echo_info "Test 4: Simulated Container Environment"
cat > "$test_workspace/container-test.py" << 'EOF'
#!/usr/bin/env python3
import os, sys, psutil, shutil

def test_container_env():
    print("🔧 Container Environment Test")
    
    # Check workspace
    workspace = "/workspace" if os.environ.get('ZFORGE_CONTAINER') else os.getcwd()
    print(f"Workspace: {workspace}")
    
    # Check memory
    mem = psutil.virtual_memory()
    print(f"Memory: {mem.total // (1024**3)}GB total, {mem.available // (1024**3)}GB available")
    
    # Check dependencies
    deps = ['debootstrap', 'mksquashfs', 'xorriso', 'python3']
    missing = []
    for dep in deps:
        if not shutil.which(dep):
            missing.append(dep)
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        return False
    else:
        print("✅ All dependencies available")
        return True

if __name__ == "__main__":
    success = test_container_env()
    sys.exit(0 if success else 1)
EOF

python3 "$test_workspace/container-test.py"
container_test_result=$?

# Test 5: Build simulation
echo_info "Test 5: Build Process Simulation"
build_dir="$test_workspace/zforge-build-test"
mkdir -p "$build_dir"/{workspace,cache,output}

# Simulate key build operations
echo_info "Simulating debootstrap workspace..."
mkdir -p "$build_dir/workspace/chroot"
echo "debian-trixie-chroot-simulation" > "$build_dir/workspace/chroot/test-file"

echo_info "Simulating package cache..."
mkdir -p "$build_dir/cache/packages"
touch "$build_dir/cache/packages/"{base.deb,kernel.deb,zfs.deb}

echo_info "Simulating ISO generation..."
mkdir -p "$build_dir/output"
echo "iso-content-simulation" > "$build_dir/output/test.iso"

# Calculate space usage
space_used=$(du -sh "$test_workspace" | cut -f1)
echo_info "✅ Test workspace usage: $space_used"

# Test 6: Resource monitoring
echo_info "Test 6: Resource Monitoring"
echo_info "CPU cores: $(nproc) (optimal: 4+)"
echo_info "RAM total: $(free -h | awk '/Mem:/ {print $2}') (optimal: 8GB+)"
echo_info "Disk free: $(df -h . | awk 'NR==2 {print $4}') (need: 10GB+)"

# Cleanup
echo_info "Cleaning up test workspace..."
rm -rf "$test_workspace"

# Summary
echo_info "🎯 RAM Container Test Summary"
if [ $container_test_result -eq 0 ] && [ "$shm_size" -ge 15 ]; then
    echo_info "✅ READY: RAM container approach is viable"
    echo_info "Expected performance: 3-5x faster than disk builds"
    echo_info "Recommended: 20GB tmpfs mount for full builds"
else
    echo_warn "⚠️ PARTIAL: Some limitations detected"
    echo_info "May still work with reduced performance/features"
fi

echo_info "Next: Run './docker-build.sh build' to create container"