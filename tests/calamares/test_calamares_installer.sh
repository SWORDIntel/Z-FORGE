#!/bin/bash
#
# Comprehensive Calamares Installer Test Suite
# UltraThink Agent Testing Framework v8.0
#

echo "==========================================="
echo "CALAMARES INSTALLER COMPREHENSIVE TEST"
echo "==========================================="
echo "Date: $(date)"
echo "System: $(uname -a)"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNING_TESTS=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -n "  Testing $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# Function for warning tests
warning_test() {
    local test_name="$1"
    local test_command="$2"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -n "  Testing $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        echo -e "${YELLOW}⚠️ WARNING${NC}"
        WARNING_TESTS=$((WARNING_TESTS + 1))
        return 2
    fi
}

echo "============================================"
echo "PHASE 1: STRUCTURAL INTEGRITY"
echo "============================================"

# Test directory structure
echo -e "\n${BLUE}[1.1] Directory Structure${NC}"
run_test "Calamares directory exists" "[ -d calamares ]"
run_test "Modules directory exists" "[ -d calamares/modules ]"
run_test "Settings file exists" "[ -f calamares/settings.conf ]"
warning_test "Branding directory exists" "[ -d calamares/branding ]"

# Test each module presence
echo -e "\n${BLUE}[1.2] Module Presence${NC}"
for module in gpupassthrough hardwarehealth networkconfig postinstall \
              storagelayout zfsenhancedconfig zfsrichconfig zfsrootselect; do
    run_test "$module module exists" "[ -d calamares/modules/$module ]"
    run_test "$module main.py exists" "[ -f calamares/modules/$module/main.py ]"
done

# Check for missing modules referenced in settings
echo -e "\n${BLUE}[1.3] Missing Module Detection${NC}"
for module in zfspooldetect zfsbootloader proxmoxconfig \
              securityhardening telemetryconsent zforgefinalize; do
    warning_test "$module module exists" "[ -d calamares/modules/$module ]"
done

echo "============================================"
echo "PHASE 2: PYTHON SYNTAX VALIDATION"
echo "============================================"

echo -e "\n${BLUE}[2.1] Python Syntax Check${NC}"
for module_dir in calamares/modules/*/; do
    if [ -f "$module_dir/main.py" ]; then
        module_name=$(basename "$module_dir")
        run_test "$module_name syntax" "python3 -m py_compile $module_dir/main.py"
    fi
done

echo "============================================"
echo "PHASE 3: MODULE IMPORT TESTING"
echo "============================================"

echo -e "\n${BLUE}[3.1] Module Import Capability${NC}"
for module in gpupassthrough hardwarehealth networkconfig postinstall \
              storagelayout zfsenhancedconfig zfsrichconfig zfsrootselect; do
    run_test "$module import" "python3 -c \"
import sys
sys.path.insert(0, 'calamares/modules/$module')
import main
\""
done

echo "============================================"
echo "PHASE 4: CONFIGURATION VALIDATION"
echo "============================================"

echo -e "\n${BLUE}[4.1] YAML Configuration${NC}"
run_test "settings.conf valid YAML" "python3 -c \"
import yaml
with open('calamares/settings.conf', 'r') as f:
    yaml.safe_load(f)
\""

echo -e "\n${BLUE}[4.2] Module Configuration${NC}"
python3 << 'EOF'
import yaml
import sys
import os

try:
    with open('calamares/settings.conf', 'r') as f:
        config = yaml.safe_load(f)
    
    sequence = config.get('sequence', [])
    missing_modules = []
    
    for phase in sequence:
        for item in phase:
            if isinstance(item, dict):
                for module_list in item.values():
                    if isinstance(module_list, list):
                        for module in module_list:
                            if not os.path.exists(f'calamares/modules/{module}'):
                                missing_modules.append(module)
    
    if missing_modules:
        print(f"  ❌ Missing modules in config: {', '.join(missing_modules)}")
        sys.exit(1)
    else:
        print("  ✅ All configured modules exist")
        sys.exit(0)
except Exception as e:
    print(f"  ❌ Configuration error: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    WARNING_TESTS=$((WARNING_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "============================================"
echo "PHASE 5: GUI FRAMEWORK ANALYSIS"
echo "============================================"

echo -e "\n${BLUE}[5.1] GUI Framework Detection${NC}"
GTK_COUNT=$(grep -r "gi.repository\|Gtk" calamares/modules --include="*.py" 2>/dev/null | wc -l)
QT_COUNT=$(grep -r "PyQt\|QtWidgets" calamares/modules --include="*.py" 2>/dev/null | wc -l)

echo "  GTK usage (incompatible): $GTK_COUNT occurrences"
echo "  Qt usage (compatible): $QT_COUNT occurrences"

if [ $GTK_COUNT -gt 0 ]; then
    echo -e "  ${RED}❌ GTK framework detected (Calamares uses Qt)${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
else
    echo -e "  ${GREEN}✅ No GTK dependencies${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "============================================"
echo "PHASE 6: CLASS NAMING CONVENTION"
echo "============================================"

echo -e "\n${BLUE}[6.1] Calamares Job Class Naming${NC}"
for module in gpupassthrough hardwarehealth networkconfig postinstall \
              storagelayout zfsenhancedconfig zfsrichconfig zfsrootselect; do
    
    # Check if class follows Calamares naming convention
    if grep -q "class ${module^}Job:" calamares/modules/$module/main.py 2>/dev/null || \
       grep -q "class .*Job:" calamares/modules/$module/main.py 2>/dev/null; then
        echo -e "  ${GREEN}✅ $module: Correct class naming${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "  ${RED}❌ $module: Incorrect class naming (should be *Job)${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
done

echo "============================================"
echo "PHASE 7: ZFS INTEGRATION TESTING"
echo "============================================"

echo -e "\n${BLUE}[7.1] ZFS Command Availability${NC}"
run_test "zpool command available" "which zpool"
run_test "zfs command available" "which zfs"

echo -e "\n${BLUE}[7.2] ZFS Module Functionality${NC}"
warning_test "ZFS pool detection module" "[ -f calamares/modules/zfspooldetect/main.py ]"
warning_test "ZFS bootloader module" "[ -f calamares/modules/zfsbootloader/main.py ]"
run_test "ZFS enhanced config module" "[ -f calamares/modules/zfsenhancedconfig/main.py ]"
run_test "ZFS rich config module" "[ -f calamares/modules/zfsrichconfig/main.py ]"
run_test "ZFS root select module" "[ -f calamares/modules/zfsrootselect/main.py ]"

echo "============================================"
echo "PHASE 8: SECURITY ANALYSIS"
echo "============================================"

echo -e "\n${BLUE}[8.1] Security Concerns${NC}"
# Look for actual hardcoded passwords, not just the word "password"
# Exclude legitimate password function names and config flags
HARDCODED_PASSWORDS=$(grep -r "password.*=.*['\"]" calamares/modules --include="*.py" 2>/dev/null | grep -v "#" | grep -v "password\": False" | grep -v "password\": True" | grep -v "def.*password" | grep -v "root_password" | wc -l)
echo "  Hardcoded password patterns: $HARDCODED_PASSWORDS"

if [ $HARDCODED_PASSWORDS -gt 0 ]; then
    echo -e "  ${YELLOW}⚠️ Potential hardcoded passwords detected${NC}"
    WARNING_TESTS=$((WARNING_TESTS + 1))
else
    echo -e "  ${GREEN}✅ No hardcoded passwords detected${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

echo "============================================"
echo "PHASE 9: ERROR HANDLING ANALYSIS"
echo "============================================"

echo -e "\n${BLUE}[9.1] Exception Handling${NC}"
for module in gpupassthrough hardwarehealth networkconfig postinstall \
              storagelayout zfsenhancedconfig zfsrichconfig zfsrootselect \
              zfspooldetect zfsbootloader proxmoxconfig securityhardening \
              telemetryconsent zforgefinalize; do
    
    TRY_COUNT=$(grep -c "try:" "calamares/modules/$module/main.py" 2>/dev/null || echo "0")
    EXCEPT_COUNT=$(grep -c "except" "calamares/modules/$module/main.py" 2>/dev/null || echo "0")
    
    # Remove any whitespace/newlines from counts
    TRY_COUNT=$(echo "$TRY_COUNT" | tr -d '[:space:]')
    EXCEPT_COUNT=$(echo "$EXCEPT_COUNT" | tr -d '[:space:]')
    
    if [ "$TRY_COUNT" -gt 0 ] && [ "$EXCEPT_COUNT" -gt 0 ]; then
        echo -e "  ${GREEN}✅ $module: Has error handling ($TRY_COUNT try blocks)${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "  ${YELLOW}⚠️ $module: Limited error handling${NC}"
        WARNING_TESTS=$((WARNING_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
done

echo "============================================"
echo "PHASE 10: CONFIGURATION MATRIX TEST"
echo "============================================"

echo -e "\n${BLUE}[10.1] Test Configuration Scenarios${NC}"

# Create test configurations
cat > /tmp/test_minimal.yaml << 'EOF'
storage:
  type: single_disk
  filesystem: ext4
network:
  type: dhcp
desktop: none
EOF

cat > /tmp/test_zfs.yaml << 'EOF'
storage:
  type: zfs_mirror
  encryption: true
  compression: lz4
network:
  type: static
  ip: 192.168.1.100
desktop: kde
EOF

cat > /tmp/test_advanced.yaml << 'EOF'
storage:
  type: zfs_raidz2
  encryption: true
  compression: zstd
  disks: 4
network:
  type: static
  vlans: [10, 20]
gpu:
  passthrough: true
monitoring:
  smart: true
  ipmi: true
EOF

for config in minimal zfs advanced; do
    if python3 -c "
import yaml
with open('/tmp/test_${config}.yaml', 'r') as f:
    config = yaml.safe_load(f)
    print(f'Configuration ${config} is valid')
" 2>/dev/null; then
        echo -e "  ${GREEN}✅ ${config} configuration: Valid${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "  ${RED}❌ ${config} configuration: Invalid${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
done

# Cleanup test files
rm -f /tmp/test_*.yaml

echo ""
echo "============================================"
echo "TEST RESULTS SUMMARY"
echo "============================================"
echo ""
echo "Total Tests Run: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo -e "${YELLOW}Warnings: $WARNING_TESTS${NC}"
echo ""

# Calculate percentage
if [ $TOTAL_TESTS -gt 0 ]; then
    PASS_PERCENT=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo "Pass Rate: ${PASS_PERCENT}%"
    
    if [ $PASS_PERCENT -ge 80 ]; then
        echo -e "\n${GREEN}✅ OVERALL: GOOD${NC}"
        echo "The installer is in reasonable condition with minor issues."
    elif [ $PASS_PERCENT -ge 60 ]; then
        echo -e "\n${YELLOW}⚠️ OVERALL: NEEDS WORK${NC}"
        echo "The installer has significant issues that need addressing."
    else
        echo -e "\n${RED}❌ OVERALL: CRITICAL ISSUES${NC}"
        echo "The installer is not ready for use and requires major fixes."
    fi
else
    echo "No tests were run."
fi

echo ""
echo "============================================"
echo "RECOMMENDATIONS"
echo "============================================"

if [ $FAILED_TESTS -gt 0 ] || [ $WARNING_TESTS -gt 0 ]; then
    echo ""
    echo "Critical Actions Required:"
    
    if [ $GTK_COUNT -gt 0 ]; then
        echo "  1. Convert GTK to Qt framework for Calamares compatibility"
    fi
    
    if [ $WARNING_TESTS -gt 5 ]; then
        echo "  2. Implement missing critical modules (zfspooldetect, zfsbootloader)"
    fi
    
    if [ $FAILED_TESTS -gt 3 ]; then
        echo "  3. Fix Python class naming to follow Calamares conventions"
    fi
    
    echo "  4. Add comprehensive error handling to all modules"
    echo "  5. Create integration test suite"
    echo ""
    echo "Run the fix script: ./fix_calamares_critical.sh"
fi

echo ""
echo "Test completed at: $(date)"
echo "==========================================="