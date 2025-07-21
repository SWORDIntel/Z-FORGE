#!/bin/bash
# Z-FORGE Module Dependency Checker
# Ensures all module dependencies are satisfied before build

set -euo pipefail

echo "════════════════════════════════════════════════════════════════"
echo "          Z-FORGE Module Dependency Checker"
echo "════════════════════════════════════════════════════════════════"
echo

# Module dependency definitions
declare -A MODULE_DEPS=(
    ["WorkspaceSetup"]=""
    ["Debootstrap"]="WorkspaceSetup"
    ["KernelAcquisition"]="Debootstrap"
    ["ZFSBuild"]="KernelAcquisition"
    ["DracutConfig"]="ZFSBuild"
    ["BootloaderSetup"]="DracutConfig"
    ["ProxmoxIntegration"]="ZFSBuild"
    ["SecurityHardening"]="Debootstrap"
    ["EncryptionSupport"]="ZFSBuild"
    ["LiveEnvironment"]="BootloaderSetup"
    ["CalamaresIntegration"]="LiveEnvironment"
    ["ISOGeneration"]="CalamaresIntegration"
)

# Module file checks
declare -A MODULE_CHECKS=(
    ["WorkspaceSetup"]="/tmp/zforge_workspace"
    ["Debootstrap"]="/tmp/zforge_workspace/chroot/etc/debian_version"
    ["KernelAcquisition"]="/tmp/zforge_workspace/chroot/boot/vmlinuz*"
    ["ZFSBuild"]="/tmp/zforge_workspace/chroot/lib/modules/*/kernel/zfs"
    ["DracutConfig"]="/tmp/zforge_workspace/chroot/etc/dracut.conf.d/zforge.conf"
    ["BootloaderSetup"]="/tmp/zforge_workspace/chroot/boot/grub"
    ["ProxmoxIntegration"]="/tmp/zforge_workspace/chroot/usr/bin/pveversion"
    ["SecurityHardening"]="/tmp/zforge_workspace/chroot/etc/security"
    ["EncryptionSupport"]="/tmp/zforge_workspace/chroot/usr/sbin/cryptsetup"
    ["LiveEnvironment"]="/tmp/zforge_workspace/live"
    ["CalamaresIntegration"]="/tmp/zforge_workspace/live/usr/bin/calamares"
    ["ISOGeneration"]="zforge-*.iso"
)

# Function to check if a module's output exists
check_module_output() {
    local module=$1
    local check_path=${MODULE_CHECKS[$module]}
    
    if [[ -z "$check_path" ]]; then
        return 0  # No check defined, assume OK
    fi
    
    # Use globbing for patterns
    if [[ "$check_path" == *"*"* ]]; then
        if ls $check_path >/dev/null 2>&1; then
            return 0
        else
            return 1
        fi
    else
        if [[ -e "$check_path" ]]; then
            return 0
        else
            return 1
        fi
    fi
}

# Function to check dependencies recursively
check_deps_recursive() {
    local module=$1
    local indent="${2:-}"
    
    echo "${indent}Checking $module..."
    
    # Check if module has dependencies
    local deps=${MODULE_DEPS[$module]:-}
    if [[ -n "$deps" ]]; then
        for dep in $deps; do
            if ! check_deps_recursive "$dep" "  $indent"; then
                echo "${indent}  ❌ Dependency $dep failed!"
                return 1
            fi
        done
    fi
    
    # Check module output
    if check_module_output "$module"; then
        echo "${indent}  ✅ $module output found"
        return 0
    else
        echo "${indent}  ⚠️  $module output missing (may not have run yet)"
        return 2  # Different code for missing vs failed
    fi
}

# Main dependency check
main() {
    local build_order=(
        "WorkspaceSetup"
        "Debootstrap"
        "KernelAcquisition"
        "ZFSBuild"
        "DracutConfig"
        "BootloaderSetup"
        "ProxmoxIntegration"
        "SecurityHardening"
        "EncryptionSupport"
        "LiveEnvironment"
        "CalamaresIntegration"
        "ISOGeneration"
    )
    
    echo "Build Order Verification:"
    echo "════════════════════════════════════════"
    
    local all_good=true
    
    for module in "${build_order[@]}"; do
        echo
        echo "Module: $module"
        echo "Dependencies: ${MODULE_DEPS[$module]:-none}"
        
        if check_deps_recursive "$module"; then
            echo "Status: Ready to build"
        else
            echo "Status: Dependencies not satisfied"
            all_good=false
        fi
    done
    
    echo
    echo "════════════════════════════════════════"
    
    if $all_good; then
        echo "✅ All dependencies satisfied!"
    else
        echo "⚠️  Some dependencies are not satisfied"
        echo "This is normal if the build hasn't started yet"
    fi
    
    # Show recommended build order
    echo
    echo "Recommended Build Order:"
    echo "════════════════════════════════════════"
    echo "Phase 1: Base System"
    echo "  1. WorkspaceSetup"
    echo "  2. Debootstrap"
    echo
    echo "Phase 2: Kernel & Core"
    echo "  3. KernelAcquisition"
    echo "  4. ZFSBuild"
    echo
    echo "Phase 3: Boot Infrastructure"
    echo "  5. DracutConfig"
    echo "  6. BootloaderSetup"
    echo
    echo "Phase 4: System Integration (can parallelize)"
    echo "  7. ProxmoxIntegration"
    echo "  8. SecurityHardening"
    echo "  9. EncryptionSupport"
    echo
    echo "Phase 5: Live Environment"
    echo "  10. LiveEnvironment"
    echo "  11. CalamaresIntegration"
    echo
    echo "Phase 6: ISO Generation"
    echo "  12. ISOGeneration"
}

# Run main
main "$@"