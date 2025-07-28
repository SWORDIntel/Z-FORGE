#!/bin/bash
# Z-FORGE Target Hardware Profiler
# Run this on target machines to generate optimal build configuration

set -euo pipefail

# Output file
OUTPUT_DIR="${1:-./zforge_profile}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROFILE_NAME="hardware_profile_${TIMESTAMP}"

echo "════════════════════════════════════════════════════════════════"
echo "          Z-FORGE Target Hardware Profiler"
echo "════════════════════════════════════════════════════════════════"
echo

# Create output directory
mkdir -p "$OUTPUT_DIR"
OUTPUT_FILE="$OUTPUT_DIR/${PROFILE_NAME}.yaml"
REPORT_FILE="$OUTPUT_DIR/${PROFILE_NAME}_report.txt"

# Start report
{
    echo "Z-FORGE Hardware Profile Report"
    echo "Generated: $(date)"
    echo "Hostname: $(hostname)"
    echo "════════════════════════════════════════════════════════════════"
    echo
} > "$REPORT_FILE"

# Function to detect CPU features and optimal flags
detect_cpu() {
    echo "[*] Detecting CPU..."
    
    local cpu_info=$(cat /proc/cpuinfo)
    local cpu_model=$(echo "$cpu_info" | grep "model name" | head -1 | cut -d: -f2 | xargs)
    local cpu_vendor=$(echo "$cpu_info" | grep "vendor_id" | head -1 | cut -d: -f2 | xargs)
    local cpu_cores=$(nproc)
    local cpu_arch=$(uname -m)
    
    # Detect CPU features for optimization
    local cpu_flags=$(echo "$cpu_info" | grep "^flags" | head -1 | cut -d: -f2)
    
    # Determine optimal GCC march flag
    local march_flag="native"
    local mtune_flag="native"
    
    # Detect specific CPU generation for better optimization
    if [[ "$cpu_vendor" == "GenuineIntel" ]]; then
        if echo "$cpu_flags" | grep -q " avx512f "; then
            march_flag="skylake-avx512"
        elif echo "$cpu_flags" | grep -q " avx2 "; then
            if echo "$cpu_model" | grep -q "E5-26[0-9][0-9] v4"; then
                march_flag="broadwell"
            elif echo "$cpu_model" | grep -q "E5-26[0-9][0-9] v3"; then
                march_flag="haswell"
            else
                march_flag="haswell"
            fi
        elif echo "$cpu_flags" | grep -q " avx "; then
            march_flag="sandybridge"
        else
            march_flag="core2"
        fi
    elif [[ "$cpu_vendor" == "AuthenticAMD" ]]; then
        if echo "$cpu_flags" | grep -q " avx512f "; then
            march_flag="znver4"
        elif echo "$cpu_flags" | grep -q " avx2 "; then
            if echo "$cpu_model" | grep -q "EPYC"; then
                march_flag="znver2"
            else
                march_flag="znver1"
            fi
        else
            march_flag="k8"
        fi
    fi
    
    # Detect useful CPU features
    local features=""
    for feature in aes avx avx2 avx512f sse4_2 ssse3 popcnt rdrand; do
        if echo "$cpu_flags" | grep -q " $feature "; then
            features="$features $feature"
        fi
    done
    
    cat >> "$REPORT_FILE" <<EOF
CPU Information:
  Model: $cpu_model
  Vendor: $cpu_vendor
  Architecture: $cpu_arch
  Cores: $cpu_cores
  Optimal march: $march_flag
  Features:$features

EOF

    # Write to YAML
    cat >> "$OUTPUT_FILE" <<EOF
# Z-FORGE Hardware Profile
# Generated on $(hostname) at $(date)

system_info:
  hostname: $(hostname)
  kernel: $(uname -r)
  arch: $cpu_arch

cpu_optimization:
  vendor: "$cpu_vendor"
  model: "$cpu_model"
  cores: $cpu_cores
  threads: $(grep -c ^processor /proc/cpuinfo)
  march_flag: "$march_flag"
  mtune_flag: "$mtune_flag"
  features: [$features]
  
compiler_flags:
  # Optimal GCC flags for this CPU
  CFLAGS: "-O2 -march=$march_flag -mtune=$mtune_flag -pipe"
  CXXFLAGS: "-O2 -march=$march_flag -mtune=$mtune_flag -pipe"
  # Parallel compilation
  MAKEFLAGS: "-j$((cpu_cores + 1))"

EOF
}

# Function to detect memory configuration
detect_memory() {
    echo "[*] Detecting memory..."
    
    local total_mem=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local total_mem_gb=$((total_mem / 1024 / 1024))
    
    # Detect memory speed if possible
    local mem_speed="Unknown"
    local mem_type="Unknown"
    if command -v dmidecode >/dev/null 2>&1 && [[ $EUID -eq 0 ]]; then
        mem_speed=$(dmidecode -t memory | grep "Speed:" | grep -v "Unknown" | head -1 | awk '{print $2 $3}')
        mem_type=$(dmidecode -t memory | grep "Type:" | grep -v "Unknown" | head -1 | awk '{print $2}')
    fi
    
    # Calculate optimal ZFS ARC size (max 50% of RAM)
    local arc_max_gb=$((total_mem_gb / 2))
    if [[ $arc_max_gb -gt 64 ]]; then
        arc_max_gb=64  # Cap at 64GB
    fi
    
    cat >> "$REPORT_FILE" <<EOF
Memory Information:
  Total: ${total_mem_gb}GB
  Type: $mem_type
  Speed: $mem_speed
  Recommended ARC Max: ${arc_max_gb}GB

EOF

    cat >> "$OUTPUT_FILE" <<EOF
memory_config:
  total_gb: $total_mem_gb
  type: "$mem_type"
  speed: "$mem_speed"
  
  # Memory-based optimizations
  zfs_arc_max_gb: $arc_max_gb
  vm_swappiness: $(if [[ $total_mem_gb -ge 64 ]]; then echo 1; else echo 10; fi)
  
  # Build optimization
  tmpfs_build: $(if [[ $total_mem_gb -ge 32 ]]; then echo "true"; else echo "false"; fi)
  parallel_jobs: $(if [[ $total_mem_gb -ge 16 ]]; then echo $((cpu_cores + 1)); else echo $((cpu_cores / 2 + 1)); fi)

EOF
}

# Function to detect storage devices
detect_storage() {
    echo "[*] Detecting storage..."
    
    cat >> "$REPORT_FILE" <<EOF
Storage Devices:
EOF

    echo "storage_devices:" >> "$OUTPUT_FILE"
    
    for device in /sys/block/sd* /sys/block/nvme*; do
        if [[ -e "$device" ]]; then
            local dev_name=$(basename "$device")
            local dev_model="Unknown"
            local dev_size="Unknown"
            local dev_rota="Unknown"
            
            if [[ -e "$device/device/model" ]]; then
                dev_model=$(cat "$device/device/model" | tr -d '\n' | xargs)
            fi
            
            if [[ -e "$device/size" ]]; then
                local sectors=$(cat "$device/size")
                dev_size=$(( sectors * 512 / 1024 / 1024 / 1024 ))GB
            fi
            
            if [[ -e "$device/queue/rotational" ]]; then
                dev_rota=$(cat "$device/queue/rotational")
            fi
            
            local dev_type="HDD"
            if [[ "$dev_rota" == "0" ]]; then
                dev_type="SSD"
            fi
            if [[ "$dev_name" == nvme* ]]; then
                dev_type="NVMe"
            fi
            
            cat >> "$REPORT_FILE" <<EOF
  - $dev_name: $dev_model ($dev_size, $dev_type)
EOF

            cat >> "$OUTPUT_FILE" <<EOF
  - device: "/dev/$dev_name"
    model: "$dev_model"
    size: "$dev_size"
    type: "$dev_type"
    rotational: $dev_rota
EOF
        fi
    done
    
    echo >> "$REPORT_FILE"
}

# Function to detect network interfaces
detect_network() {
    echo "[*] Detecting network interfaces..."
    
    cat >> "$REPORT_FILE" <<EOF
Network Interfaces:
EOF

    echo "network_interfaces:" >> "$OUTPUT_FILE"
    
    for iface in /sys/class/net/*; do
        if [[ -e "$iface" ]] && [[ "$(basename "$iface")" != "lo" ]]; then
            local if_name=$(basename "$iface")
            local if_mac="Unknown"
            local if_driver="Unknown"
            local if_speed="Unknown"
            
            if [[ -e "$iface/address" ]]; then
                if_mac=$(cat "$iface/address")
            fi
            
            if [[ -e "$iface/device/driver" ]]; then
                if_driver=$(basename $(readlink "$iface/device/driver"))
            fi
            
            if [[ -e "$iface/speed" ]] && [[ -r "$iface/speed" ]]; then
                local speed=$(cat "$iface/speed" 2>/dev/null || echo "-1")
                if [[ "$speed" != "-1" ]]; then
                    if_speed="${speed}Mbps"
                fi
            fi
            
            cat >> "$REPORT_FILE" <<EOF
  - $if_name: $if_mac (Driver: $if_driver, Speed: $if_speed)
EOF

            cat >> "$OUTPUT_FILE" <<EOF
  - name: "$if_name"
    mac: "$if_mac"
    driver: "$if_driver"
    speed: "$if_speed"
EOF
        fi
    done
    
    echo >> "$REPORT_FILE"
}

# Function to detect GPU
detect_gpu() {
    echo "[*] Detecting GPU..."
    
    cat >> "$REPORT_FILE" <<EOF
GPU Devices:
EOF

    echo "gpu_devices:" >> "$OUTPUT_FILE"
    
    if command -v lspci >/dev/null 2>&1; then
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                local gpu_info="$line"
                local gpu_vendor="Unknown"
                
                if echo "$line" | grep -q "NVIDIA"; then
                    gpu_vendor="NVIDIA"
                elif echo "$line" | grep -q "AMD"; then
                    gpu_vendor="AMD"
                elif echo "$line" | grep -q "Intel"; then
                    gpu_vendor="Intel"
                fi
                
                cat >> "$REPORT_FILE" <<EOF
  - $gpu_info
EOF

                cat >> "$OUTPUT_FILE" <<EOF
  - vendor: "$gpu_vendor"
    info: "$gpu_info"
EOF
            fi
        done < <(lspci | grep -E "VGA|3D|Display")
    fi
    
    echo >> "$REPORT_FILE"
}

# Function to detect system vendor
detect_system() {
    echo "[*] Detecting system..."
    
    local sys_vendor="Unknown"
    local sys_model="Unknown"
    local sys_serial="Unknown"
    
    if [[ -e /sys/class/dmi/id/sys_vendor ]]; then
        sys_vendor=$(cat /sys/class/dmi/id/sys_vendor)
    fi
    
    if [[ -e /sys/class/dmi/id/product_name ]]; then
        sys_model=$(cat /sys/class/dmi/id/product_name)
    fi
    
    if [[ -e /sys/class/dmi/id/product_serial ]] && [[ $EUID -eq 0 ]]; then
        sys_serial=$(cat /sys/class/dmi/id/product_serial)
    fi
    
    cat >> "$REPORT_FILE" <<EOF
System Information:
  Vendor: $sys_vendor
  Model: $sys_model
  Serial: $sys_serial

EOF

    cat >> "$OUTPUT_FILE" <<EOF
system_hardware:
  vendor: "$sys_vendor"
  model: "$sys_model"
  serial: "$sys_serial"

EOF
}

# Function to generate build recommendations
generate_recommendations() {
    echo "[*] Generating build recommendations..."
    
    cat >> "$OUTPUT_FILE" <<EOF
# Build Recommendations
build_recommendations:
  # Kernel configuration
  kernel_config:
    # Use native CPU optimizations
    CONFIG_MCORE2: $(if grep -q "Intel" /proc/cpuinfo; then echo "y"; else echo "n"; fi)
    CONFIG_MK8: $(if grep -q "AMD" /proc/cpuinfo; then echo "y"; else echo "n"; fi)
    CONFIG_MNATIVE: y
    
  # Module selection based on hardware
  recommended_modules:
EOF

    # Check for Dell hardware
    if [[ -e /sys/class/dmi/id/sys_vendor ]] && grep -qi "Dell" /sys/class/dmi/id/sys_vendor; then
        echo "    - DellR730xdOptimize" >> "$OUTPUT_FILE"
    fi
    
    # Check for RAID controllers
    if lspci 2>/dev/null | grep -qi "RAID\|PERC\|MegaRAID"; then
        echo "    - RAIDManagement" >> "$OUTPUT_FILE"
    fi
    
    # Check for high-performance NVMe
    if ls /sys/block/nvme* >/dev/null 2>&1; then
        echo "    - NVMeOptimization" >> "$OUTPUT_FILE"
    fi
    
    cat >> "$OUTPUT_FILE" <<EOF
    
  # ZFS pool configuration
  zfs_pool_config:
    # Ashift based on storage type
    ashift: $(if ls /sys/block/nvme* >/dev/null 2>&1; then echo 13; else echo 12; fi)
    # Compression based on CPU features
    compression: $(if grep -q " avx2 " /proc/cpuinfo; then echo "zstd"; else echo "lz4"; fi)
    
  # Performance tuning
  performance_tuning:
    cpu_governor: "performance"
    turbo_boost: true
    disable_mitigations: false  # Set to true for maximum performance

EOF
}

# Function to create build script
create_build_script() {
    echo "[*] Creating custom build script..."
    
    local build_script="$OUTPUT_DIR/build_custom_iso.sh"
    
    cat > "$build_script" <<'SCRIPT_HEADER'
#!/bin/bash
# Z-FORGE Custom ISO Build Script
# Generated from hardware profile

set -euo pipefail

# Path to Z-FORGE repository
ZFORGE_DIR="${ZFORGE_DIR:-/opt/github/Z-FORGE}"

# Copy this profile to Z-FORGE
cp "$(dirname "$0")/hardware_profile_*.yaml" "$ZFORGE_DIR/hardware_profile.yaml"

# Create custom build_spec.yml
cat > "$ZFORGE_DIR/build_spec_custom.yml" <<'EOF'
SCRIPT_HEADER

    # Include the YAML content
    cat "$OUTPUT_FILE" >> "$build_script"
    
    cat >> "$build_script" <<'SCRIPT_FOOTER'
EOF

# Run the build with custom spec
cd "$ZFORGE_DIR"
echo "Starting custom ISO build with hardware-optimized settings..."
sudo ./build-iso.sh

echo "Build complete! ISO optimized for your hardware."
SCRIPT_FOOTER

    chmod +x "$build_script"
    
    echo "Build script created: $build_script" >> "$REPORT_FILE"
}

# Main execution
main() {
    echo "Profiling hardware..."
    echo
    
    # Run all detection functions
    detect_system
    detect_cpu
    detect_memory
    detect_storage
    detect_network
    detect_gpu
    generate_recommendations
    create_build_script
    
    # Summary
    echo
    echo "════════════════════════════════════════════════════════════════"
    echo "Profile Complete!"
    echo
    echo "Files created:"
    echo "  - Profile: $OUTPUT_FILE"
    echo "  - Report: $REPORT_FILE"
    echo "  - Build Script: $OUTPUT_DIR/build_custom_iso.sh"
    echo
    echo "To build a custom ISO for this hardware:"
    echo "  1. Copy $OUTPUT_DIR to your build machine"
    echo "  2. Run: $OUTPUT_DIR/build_custom_iso.sh"
    echo
    echo "════════════════════════════════════════════════════════════════"
    
    # Display report
    echo
    cat "$REPORT_FILE"
}

# Check if running as root for full detection
if [[ $EUID -ne 0 ]]; then
    echo "⚠️  Running as non-root. Some hardware details may be limited."
    echo "   For full profiling, run: sudo $0"
    echo
fi

# Run main
main