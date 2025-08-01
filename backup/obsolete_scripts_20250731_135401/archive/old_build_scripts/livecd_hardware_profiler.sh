#!/bin/bash
# Z-FORGE LiveCD Hardware Profiler
# Simplified version for running from LiveCD with GUI support

set -euo pipefail

# Check if running from LiveCD
if [[ ! -f /proc/cmdline ]] || ! grep -q "boot=live" /proc/cmdline 2>/dev/null; then
    echo "⚠️  Warning: Not running from LiveCD environment"
fi

# GUI detection
USE_GUI=false
if [[ -n "${DISPLAY:-}" ]] && command -v zenity >/dev/null 2>&1; then
    USE_GUI=true
fi

# Function to show message
show_message() {
    local title="$1"
    local message="$2"
    
    if $USE_GUI; then
        zenity --info --title="$title" --text="$message" --width=400
    else
        echo "═══ $title ═══"
        echo "$message"
        echo
    fi
}

# Function to show progress
show_progress() {
    local message="$1"
    
    if $USE_GUI; then
        echo "# $message"
    else
        echo "[*] $message"
    fi
}

# Main profiling function
run_profiler() {
    local output_dir="/tmp/zforge_profile"
    
    # Create output directory
    mkdir -p "$output_dir"
    
    if $USE_GUI; then
        (
            show_progress "Starting hardware detection..."
            sleep 1
            
            show_progress "Detecting CPU features..."
            sleep 2
            
            show_progress "Analyzing memory configuration..."
            sleep 1
            
            show_progress "Scanning storage devices..."
            sleep 2
            
            show_progress "Detecting network interfaces..."
            sleep 1
            
            show_progress "Identifying GPU devices..."
            sleep 1
            
            show_progress "Generating optimization profile..."
            
            # Run the actual profiler
            if [[ -x /usr/local/bin/profile_target_hardware.sh ]]; then
                sudo /usr/local/bin/profile_target_hardware.sh "$output_dir" >/tmp/profiler.log 2>&1
            else
                sudo /root/profile_target_hardware.sh "$output_dir" >/tmp/profiler.log 2>&1
            fi
            
            show_progress "Profile complete!"
            sleep 1
            
        ) | zenity --progress --title="Z-FORGE Hardware Profiler" \
                   --text="Profiling system hardware..." \
                   --percentage=0 --auto-close --width=400
    else
        # Console mode
        sudo /usr/local/bin/profile_target_hardware.sh "$output_dir" || \
        sudo /root/profile_target_hardware.sh "$output_dir"
    fi
    
    # Show results
    local profile_file=$(ls -t "$output_dir"/hardware_profile_*.yaml 2>/dev/null | head -1)
    local report_file=$(ls -t "$output_dir"/hardware_profile_*_report.txt 2>/dev/null | head -1)
    
    if [[ -f "$report_file" ]]; then
        if $USE_GUI; then
            zenity --text-info --title="Hardware Profile Report" \
                   --filename="$report_file" \
                   --width=600 --height=400
        else
            cat "$report_file"
        fi
    fi
    
    # Offer to save to USB
    show_message "Profile Complete" "Hardware profile saved to:\n$output_dir\n\nYou can copy this directory to a USB drive for building a custom ISO."
    
    if $USE_GUI; then
        if zenity --question --title="Save to USB?" \
                  --text="Would you like to save the profile to a USB drive?" \
                  --width=300; then
            save_to_usb "$output_dir"
        fi
    fi
}

# Function to save profile to USB
save_to_usb() {
    local source_dir="$1"
    
    # Find USB drives
    local usb_devices=()
    while IFS= read -r device; do
        if [[ -n "$device" ]]; then
            local device_info=$(lsblk -no SIZE,MODEL "$device" 2>/dev/null | head -1)
            usb_devices+=("$device" "$device_info")
        fi
    done < <(lsblk -ndo NAME,TRAN | grep usb | awk '{print "/dev/"$1}')
    
    if [[ ${#usb_devices[@]} -eq 0 ]]; then
        show_message "No USB Found" "No USB drives detected. Please insert a USB drive and try again."
        return
    fi
    
    # Select USB drive
    local selected=""
    if $USE_GUI; then
        selected=$(zenity --list --title="Select USB Drive" \
                         --column="Device" --column="Info" \
                         "${usb_devices[@]}" \
                         --width=400 --height=200)
    else
        echo "Available USB drives:"
        for ((i=0; i<${#usb_devices[@]}; i+=2)); do
            echo "  $((i/2+1)). ${usb_devices[i]} - ${usb_devices[i+1]}"
        done
        read -p "Select drive number: " choice
        selected="${usb_devices[$(((choice-1)*2))]}"
    fi
    
    if [[ -z "$selected" ]]; then
        return
    fi
    
    # Mount USB drive
    local mount_point="/tmp/usb_mount_$$"
    mkdir -p "$mount_point"
    
    # Find first partition on selected device
    local partition="${selected}1"
    if [[ ! -b "$partition" ]]; then
        partition="$selected"
    fi
    
    if sudo mount "$partition" "$mount_point" 2>/dev/null; then
        # Copy profile
        local dest_dir="$mount_point/zforge_profiles/$(hostname)_$(date +%Y%m%d)"
        sudo mkdir -p "$dest_dir"
        sudo cp -r "$source_dir"/* "$dest_dir/"
        
        # Create README
        cat > "$dest_dir/README.txt" <<EOF
Z-FORGE Hardware Profile
========================

Generated on: $(date)
Hostname: $(hostname)

This profile contains optimized build settings for your hardware.

To use this profile:
1. Copy this directory to your Z-FORGE build machine
2. Run: ./build_custom_iso.sh

The resulting ISO will be optimized for this specific hardware.

Files included:
- hardware_profile_*.yaml - Complete hardware profile
- hardware_profile_*_report.txt - Human-readable report
- build_custom_iso.sh - Build script

EOF
        
        sudo umount "$mount_point"
        show_message "Save Complete" "Profile saved to USB drive:\n$dest_dir"
    else
        show_message "Mount Failed" "Failed to mount USB drive. Please ensure it's formatted and try again."
    fi
    
    rmdir "$mount_point" 2>/dev/null || true
}

# Desktop entry creation
create_desktop_entry() {
    local desktop_file="/home/$(whoami)/Desktop/hardware-profiler.desktop"
    
    cat > "$desktop_file" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Z-FORGE Hardware Profiler
Comment=Profile this system for custom ISO build
Exec=/usr/local/bin/livecd_hardware_profiler.sh
Icon=computer
Terminal=false
Categories=System;
EOF
    
    chmod +x "$desktop_file"
}

# Main execution
main() {
    # Create desktop shortcut if in LiveCD with desktop
    if [[ -d "/home/$(whoami)/Desktop" ]] && [[ -n "${DISPLAY:-}" ]]; then
        create_desktop_entry
    fi
    
    # Show welcome message
    show_message "Z-FORGE Hardware Profiler" \
"This tool will analyze your hardware and create an optimized build profile.

The profile can be used to build a custom Z-FORGE ISO specifically optimized for this machine.

Click OK to begin hardware detection."
    
    # Run profiler
    run_profiler
}

# Run main
main "$@"