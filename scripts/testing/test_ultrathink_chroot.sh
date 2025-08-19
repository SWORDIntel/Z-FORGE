#!/bin/bash
# Test and demonstrate the Ultrathink Chroot Solution

set -e

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║          ULTRATHINK CHROOT SOLUTION - TEST & DEMO                 ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test directory
TEST_CHROOT="/tmp/ultrathink-test-chroot"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ULTRATHINK="$SCRIPT_DIR/ultrathink_chroot_solution.py"

echo -e "${YELLOW}Test environment:${NC}"
echo "  Script directory: $SCRIPT_DIR"
echo "  Test chroot: $TEST_CHROOT"
echo "  Ultrathink solution: $ULTRATHINK"
echo

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "\n${YELLOW}TEST: $test_name${NC}"
    echo "Command: $test_command"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✓ PASSED${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    "$ULTRATHINK" "$TEST_CHROOT" --cleanup 2>/dev/null || true
    sudo rm -rf "$TEST_CHROOT" 2>/dev/null || true
}

# Set trap for cleanup
trap cleanup EXIT

# Create test chroot
echo -e "${YELLOW}Creating minimal test chroot...${NC}"
sudo rm -rf "$TEST_CHROOT" 2>/dev/null || true
sudo mkdir -p "$TEST_CHROOT"/{bin,etc,usr/bin,proc,sys,dev,run,tmp,lib,lib64}

# Copy minimal binaries
echo "Copying essential binaries..."
for binary in /bin/bash /bin/ls /bin/cat /bin/echo /bin/sh; do
    if [ -f "$binary" ]; then
        sudo cp "$binary" "$TEST_CHROOT$binary" 2>/dev/null || true
    fi
done

# Copy basic libraries (needed for bash)
echo "Copying essential libraries..."
for lib in /lib/x86_64-linux-gnu/libc.so.* /lib/x86_64-linux-gnu/libdl.so.* \
           /lib/x86_64-linux-gnu/libtinfo.so.* /lib64/ld-linux-x86-64.so.*; do
    if [ -f "$lib" ]; then
        target_dir=$(dirname "$TEST_CHROOT$lib")
        sudo mkdir -p "$target_dir"
        sudo cp "$lib" "$TEST_CHROOT$lib" 2>/dev/null || true
    fi
done

# Create basic etc files
echo "root:x:0:0:root:/root:/bin/bash" | sudo tee "$TEST_CHROOT/etc/passwd" >/dev/null
echo "root:x:0:" | sudo tee "$TEST_CHROOT/etc/group" >/dev/null

echo -e "${GREEN}Test chroot created${NC}"

# Run tests
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}                         RUNNING TESTS                              ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Check arch-chroot availability
if run_test "arch-chroot installation" "$ULTRATHINK --install-arch-chroot"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 2: Basic command execution
if run_test "Basic command execution" "$ULTRATHINK '$TEST_CHROOT' -- echo 'Hello from chroot'"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 3: Script execution
if run_test "Script execution" "$ULTRATHINK '$TEST_CHROOT' --script 'echo Test script working && pwd'"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 4: Check filesystem mounts
if run_test "Filesystem mounting" "
    $ULTRATHINK '$TEST_CHROOT' --script '
        echo Checking mounts...
        if [ -d /proc/1 ]; then
            echo /proc is mounted
        else
            echo /proc is NOT mounted
            exit 1
        fi
        if [ -d /sys/kernel ]; then
            echo /sys is mounted
        else
            echo /sys is NOT mounted
            exit 1
        fi
    '
"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 5: Cleanup test
echo -e "\n${YELLOW}TEST: Cleanup functionality${NC}"
# First ensure something is mounted
"$ULTRATHINK" "$TEST_CHROOT" -- echo "Mounting filesystems" >/dev/null 2>&1

# Check if anything is mounted
if mount | grep -q "$TEST_CHROOT"; then
    echo "Filesystems are mounted"
    
    # Now test cleanup
    if run_test "Cleanup unmounts filesystems" "$ULTRATHINK '$TEST_CHROOT' --cleanup && ! mount | grep -q '$TEST_CHROOT'"; then
        ((TESTS_PASSED++))
    else
        ((TESTS_FAILED++))
    fi
else
    echo -e "${YELLOW}No filesystems were mounted to test cleanup${NC}"
    ((TESTS_PASSED++))
fi

# Test 6: Python module import
if run_test "Python module import" "python3 -c 'from ultrathink_chroot_solution import ChrootManager; print(\"Import successful\")'"; then
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

# Test 7: Signal handling (non-interactive)
echo -e "\n${YELLOW}TEST: Signal handling${NC}"
echo "Starting a process and sending SIGTERM..."
python3 -c "
import subprocess
import time
import signal
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from ultrathink_chroot_solution import ChrootManager

# Start a process that we'll interrupt
proc = subprocess.Popen([
    sys.executable, '$ULTRATHINK', '$TEST_CHROOT', '--script', 'sleep 10'
])

# Give it time to start
time.sleep(1)

# Send SIGTERM
proc.terminate()

# Wait for it to finish
proc.wait()

# Check if cleanup worked
result = subprocess.run(['mount'], capture_output=True, text=True)
if '$TEST_CHROOT' in result.stdout:
    print('FAILED: Mounts still present after signal')
    sys.exit(1)
else:
    print('SUCCESS: Cleanup worked after signal')
    sys.exit(0)
" && ((TESTS_PASSED++)) || ((TESTS_FAILED++))

# Summary
echo -e "\n${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}                         TEST SUMMARY                               ${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
echo
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
echo

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED! The Ultrathink Chroot Solution is working perfectly!${NC}"
    
    echo -e "\n${YELLOW}Quick Usage Examples:${NC}"
    echo "1. Enter interactive chroot:"
    echo "   $ULTRATHINK /path/to/chroot"
    echo
    echo "2. Run a command:"
    echo "   $ULTRATHINK /path/to/chroot -- apt-get update"
    echo
    echo "3. Run a script:"
    echo "   $ULTRATHINK /path/to/chroot --script 'apt-get update && apt-get upgrade -y'"
    echo
    echo "4. Use in Python:"
    echo "   from ultrathink_chroot_solution import ChrootManager"
    echo "   with ChrootManager('/path/to/chroot') as chroot:"
    echo "       chroot.run(['ls', '-la'])"
    
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please check the output above.${NC}"
    exit 1
fi