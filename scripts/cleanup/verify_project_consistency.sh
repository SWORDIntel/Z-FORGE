#!/bin/bash
# Z-FORGE Project Consistency Verification
# Verifies all scripts are in sync and project is clean

set -e

echo "════════════════════════════════════════════════════════════════════"
echo "         Z-FORGE Project Consistency Verification"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing: $test_name... "
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to check for pattern in scripts
check_no_pattern() {
    local pattern="$1"
    local exclude_dirs="*/archive/* */backup/* */.git/* */zfs-build/*"
    
    ! find "$PROJECT_ROOT" -type f -name "*.sh" \
        -not -path "*/archive/*" \
        -not -path "*/backup/*" \
        -not -path "*/.git/*" \
        -not -path "*/zfs-build/*" \
        -exec grep -l "$pattern" {} \; 2>/dev/null | grep -q .
}

echo "1. Directory Structure Tests"
echo "============================"

run_test "Scripts directory exists" "[ -d '$PROJECT_ROOT/scripts' ]"
run_test "Build scripts directory exists" "[ -d '$PROJECT_ROOT/scripts/build' ]"
run_test "Chroot scripts directory exists" "[ -d '$PROJECT_ROOT/scripts/chroot' ]"
run_test "Workspace scripts directory exists" "[ -d '$PROJECT_ROOT/scripts/workspace' ]"
run_test "Docs directory exists" "[ -d '$PROJECT_ROOT/docs' ]"
run_test "Config directory exists" "[ -d '$PROJECT_ROOT/config' ]"

echo ""
echo "2. Critical Files Tests"
echo "======================="

run_test "README.md exists" "[ -f '$PROJECT_ROOT/README.md' ]"
run_test "Makefile.no_tmp exists" "[ -f '$PROJECT_ROOT/Makefile.no_tmp' ]"
run_test "build.py exists" "[ -f '$PROJECT_ROOT/build.py' ]"
run_test "Main build script exists" "[ -f '$PROJECT_ROOT/scripts/build/build.sh' ]"
run_test "Bootstrap script exists" "[ -f '$PROJECT_ROOT/scripts/chroot/bootstrap_chroot.sh' ]"

echo ""
echo "3. Path Consistency Tests"
echo "========================"

run_test "No scripts use ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}" "check_no_pattern '${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}'"
run_test "No hardcoded /tmp paths" "check_no_pattern 'WORKSPACE=/tmp/zforge'"
run_test "No legacy chroot paths" "check_no_pattern 'CHROOT_PATH=/tmp/zforge'"

echo ""
echo "4. Script Executable Tests"
echo "========================="

# Check if key scripts are executable
KEY_SCRIPTS=(
    "scripts/build/build.sh"
    "scripts/chroot/bootstrap_chroot.sh"
    "scripts/chroot/complete_zfs_install.sh"
    "scripts/workspace/setup_no_tmp_build.sh"
)

for script in "${KEY_SCRIPTS[@]}"; do
    run_test "$(basename "$script") is executable" "[ -x '$PROJECT_ROOT/$script' ]"
done

echo ""
echo "5. Obsolete Files Tests"
echo "======================"

run_test "No old_build_scripts directory" "[ ! -d '$PROJECT_ROOT/archive/old_build_scripts' ]"
run_test "No old_scripts directory" "[ ! -d '$PROJECT_ROOT/archive/old_scripts' ]"
run_test "Archive directory is clean" "[ ! -d '$PROJECT_ROOT/archive' ] || [ -z \"\$(ls -A '$PROJECT_ROOT/archive' 2>/dev/null)\" ]"

echo ""
echo "6. Configuration Tests"
echo "===================="

run_test "build_spec_no_tmp.yml exists" "[ -f '$PROJECT_ROOT/build_spec_no_tmp.yml' ]"
run_test "build_spec.lock exists" "[ -f '$PROJECT_ROOT/build_spec.lock' ]"
run_test "Valid YAML in build_spec_no_tmp.yml" "python3 -c 'import yaml; yaml.safe_load(open(\"$PROJECT_ROOT/build_spec_no_tmp.yml\"))'"

echo ""
echo "7. Python Module Tests"
echo "===================="

run_test "Builder module exists" "[ -d '$PROJECT_ROOT/builder' ]"
run_test "Core module exists" "[ -d '$PROJECT_ROOT/builder/core' ]"
run_test "__init__.py exists" "[ -f '$PROJECT_ROOT/builder/__init__.py' ]"

echo ""
echo "8. Documentation Tests"
echo "===================="

run_test "QUICKSTART.md exists" "[ -f '$PROJECT_ROOT/QUICKSTART.md' ]"
run_test "TROUBLESHOOTING.md exists" "[ -f '$PROJECT_ROOT/TROUBLESHOOTING.md' ]"
run_test "Docs README exists" "[ -f '$PROJECT_ROOT/docs/README.md' ]"

# Summary
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "                    Verification Summary"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All consistency checks passed!${NC}"
    echo ""
    echo "The project is in a clean, consistent state."
else
    echo -e "${RED}⚠️  Some consistency checks failed.${NC}"
    echo ""
    echo "Please review the failed tests above and:"
    echo "1. Run cleanup script: ./scripts/cleanup/cleanup_obsolete_scripts.sh"
    echo "2. Update paths: ./scripts/cleanup/update_script_paths.sh"
    echo "3. Fix any missing files or directories"
fi

# Additional information
echo ""
echo "Quick Statistics:"
echo "================"

# Count scripts
total_scripts=$(find "$PROJECT_ROOT/scripts" -name "*.sh" -type f 2>/dev/null | wc -l)
echo "Active scripts: $total_scripts"

# Count documentation files
total_docs=$(find "$PROJECT_ROOT/docs" -name "*.md" -type f 2>/dev/null | wc -l)
echo "Documentation files: $total_docs"

# Check workspace
if [ -n "$ZFORGE_WORKSPACE" ]; then
    echo "Current workspace: $ZFORGE_WORKSPACE"
else
    echo "Workspace: Not set (will use ~/zforge_workspace)"
fi

echo ""
echo "For detailed analysis, see: SCRIPT_CONSISTENCY_ANALYSIS.md"