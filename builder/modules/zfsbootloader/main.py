#!/usr/bin/env python3
# calamares/modules/zfsbootloader/main.py

"""
ZFS Bootloader Module
Installs and configures ZFSBootMenu and optionally OpenCore
"""

import subprocess
import os
import shutil
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Optional

import libcalamares
from libcalamares.utils import check_target_env_call, target_env_call

def pretty_name():
    return "Installing ZFS Boot System"

def pretty_status_message():
    return "Configuring ZFS bootloader..."

def run():
    """
    Install bootloader for ZFS system
    Handles both single and two-stage boot configurations
    """
    
    # Get configuration from previous modules
    pool_name = libcalamares.globalstorage.value("install_pool")
    dataset = libcalamares.globalstorage.value("install_dataset")
    boot_mode = libcalamares.globalstorage.value("boot_mode", "single")  # single or two-stage
    secondary_device = libcalamares.globalstorage.value("secondary_boot_device")
    
    libcalamares.utils.debug(f"Installing bootloader for {pool_name}/{dataset}")
    libcalamares.utils.debug(f"Boot mode: {boot_mode}")
    
    try:
        # Detect system type (UEFI vs BIOS)
        is_uefi = os.path.exists("/sys/firmware/efi")
        libcalamares.utils.debug(f"UEFI mode: {is_uefi}")
        
        # Create mount points for bootloader installation
        target_mount = "/tmp/zforge_target"
        os.makedirs(target_mount, exist_ok=True)
        
        # Import pool for installation
        import_pool(pool_name)
        
        if boot_mode == "two-stage" and secondary_device:
            # Install OpenCore on secondary device
            install_opencore(secondary_device, is_uefi)
            
            # Configure ZFSBootMenu for two-stage boot
            install_zfsbootmenu(pool_name, dataset, target_mount, is_uefi, two_stage=True)
        else:
            # Standard boot configuration
            install_zfsbootmenu(pool_name, dataset, target_mount, is_uefi, two_stage=False)
        
        # Create recovery scripts
        create_recovery_scripts(target_mount, pool_name, dataset)
        
        # Export pool when done
        export_pool(pool_name)
        
        libcalamares.utils.debug("Bootloader installation complete")
        return None
        
    except Exception as e:
        libcalamares.utils.error(f"Bootloader installation failed: {str(e)}")
        return (f"Bootloader installation failed",
                f"Failed to install bootloader: {str(e)}\n"
                f"The system may not be bootable.")

def import_pool(pool_name):
    """Import ZFS pool for bootloader operations"""
    
    libcalamares.utils.debug(f"Importing pool {pool_name}")
    
    # Try normal import first
    result = subprocess.run(
        ["zpool", "import", pool_name],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        # Try force import if normal import fails
        subprocess.run(["zpool", "import", "-f", pool_name], check=True)

def export_pool(pool_name):
    """Export ZFS pool after operations"""
    
    libcalamares.utils.debug(f"Exporting pool {pool_name}")
    subprocess.run(["zpool", "export", pool_name], check=True)

def get_bootloader_binaries():
    """Get paths to bootloader binaries"""
    
    # Check in predefined locations
    zbm_paths = [
        "/usr/share/zforge/bootloaders/zfsbootmenu",
        "/iso/bootloaders/zfsbootmenu", 
        "/usr/lib/zfsbootmenu"
    ]
    
    opencore_paths = [
        "/usr/share/zforge/bootloaders/opencore",
        "/iso/bootloaders/opencore", 
        "/usr/lib/opencore"
    ]
    
    # Find ZFSBootMenu
    zbm_path = None
    for path in zbm_paths:
        if os.path.exists(path):
            zbm_path = path
            break
    
    # Find OpenCore
    oc_path = None
    for path in opencore_paths:
        if os.path.exists(path):
            oc_path = path
            break
    
    # If not found, download them
    if not zbm_path:
        zbm_path = download_zfsbootmenu()
    
    if not oc_path:
        oc_path = download_opencore()
    
    return {
        "zfsbootmenu": zbm_path,
        "opencore": oc_path
    }

def download_zfsbootmenu():
    """Download ZFSBootMenu if not found"""
    
    libcalamares.utils.debug("Downloading ZFSBootMenu")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    os.makedirs("/usr/share/zforge/bootloaders/zfsbootmenu", exist_ok=True)
    
    # Download latest ZFSBootMenu
    subprocess.run([
        "wget", "-O", f"{temp_dir}/zbm.zip",
        "https://github.com/zbm-dev/zfsbootmenu/releases/latest/download/zfsbootmenu-release.zip"
    ], check=True)
    
    # Extract
    subprocess.run(["unzip", f"{temp_dir}/zbm.zip", "-d", temp_dir], check=True)
    
    # Move to final location
    subprocess.run([
        "cp", "-r", f"{temp_dir}/EFI", "/usr/share/zforge/bootloaders/zfsbootmenu/"
    ], check=True)
    
    # Cleanup
    shutil.rmtree(temp_dir)
    
    return "/usr/share/zforge/bootloaders/zfsbootmenu"

def download_opencore():
    """Download OpenCore if not found"""
    
    libcalamares.utils.debug("Downloading OpenCore")
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    os.makedirs("/usr/share/zforge/bootloaders/opencore", exist_ok=True)
    
    # Download OpenCore
    subprocess.run([
        "wget", "-O", f"{temp_dir}/opencore.zip",
        "https://github.com/acidanthera/OpenCorePkg/releases/download/0.9.7/OpenCore-0.9.7-RELEASE.zip"
    ], check=True)
    
    # Extract
    subprocess.run(["unzip", f"{temp_dir}/opencore.zip", "-d", temp_dir], check=True)
    
    # Move to final location
    subprocess.run([
        "cp", "-r", f"{temp_dir}/X64/EFI", "/usr/share/zforge/bootloaders/opencore/"
    ], check=True)
    
    # Download NVMe driver
    subprocess.run([
        "wget", "-O", "/usr/share/zforge/bootloaders/opencore/EFI/OC/Drivers/NvmExpressDxe.efi",
        "https://github.com/acidanthera/OpenCorePkg/raw/master/Staging/NvmExpressDxe/NvmExpressDxe.efi"
    ], check=True)
    
    # Cleanup
    shutil.rmtree(temp_dir)
    
    return "/usr/share/zforge/bootloaders/opencore"

def install_zfsbootmenu(pool_name, dataset, target_mount, is_uefi, two_stage=False):
    """Install ZFSBootMenu bootloader"""
    
    libcalamares.utils.debug(f"Installing ZFSBootMenu (two_stage: {two_stage})")
    
    # Mount target dataset
    subprocess.run(["mount", "-t", "zfs", f"{pool_name}/{dataset}", target_mount], check=True)
    
    try:
        # Get bootloader paths
        bootloader_paths = get_bootloader_binaries()
        zbm_path = bootloader_paths["zfsbootmenu"]
        
        # Create boot directory
        boot_dir = os.path.join(target_mount, "boot")
        os.makedirs(boot_dir, exist_ok=True)
        
        # Create ZFSBootMenu directories
        zbm_dir = os.path.join(boot_dir, "zfsbootmenu")
        os.makedirs(zbm_dir, exist_ok=True)
        
        if is_uefi:
            # Create EFI directory
            efi_dir = os.path.join(boot_dir, "efi/EFI/zfsbootmenu")
            os.makedirs(efi_dir, exist_ok=True)
            
            # Copy ZFSBootMenu EFI files
            efi_src = os.path.join(zbm_path, "EFI")
            if os.path.exists(efi_src):
                subprocess.run(["cp", "-r", f"{efi_src}/*", efi_dir], check=True, shell=True)
        
        # Create ZFSBootMenu configuration
        zbm_config = f"""
Global:
  ManageImages: true
  BootMountPoint: /boot
  DracutConfDir: /etc/zfsbootmenu/dracut.conf.d
  InitCPIOConfig: /etc/zfsbootmenu/mkinitcpio.conf

Components:
  ImageDir: /boot/zfsbootmenu
  Versions: 3
  Enabled: true
  syslinux:
    Config: /boot/syslinux/syslinux.cfg
    Enabled: {'false' if is_uefi else 'true'}
  
EFI:
  ImageDir: /boot/efi/EFI/zfsbootmenu
  Versions: false
  Enabled: {'true' if is_uefi else 'false'}
  
Kernel:
  CommandLine: "ro quiet loglevel=4"
  Prefix: vmlinuz

ZFS:
  PoolName: {pool_name}
  DefaultSet: {dataset}
  ShowSnapshots: true
"""
        
        # Write configuration
        os.makedirs(os.path.join(target_mount, "etc/zfsbootmenu"), exist_ok=True)
        with open(os.path.join(target_mount, "etc/zfsbootmenu/config.yaml"), "w") as f:
            f.write(zbm_config)
        
        # Create dracut configuration for ZFSBootMenu
        os.makedirs(os.path.join(target_mount, "etc/zfsbootmenu/dracut.conf.d"), exist_ok=True)
        with open(os.path.join(target_mount, "etc/zfsbootmenu/dracut.conf.d/zfsbootmenu.conf"), "w") as f:
            f.write("""
# ZFSBootMenu dracut configuration
add_dracutmodules+=" zfs "
omit_dracutmodules+=" btrfs resume usrmount "
compress="zstd"
""")
        
        # Install ZFSBootMenu in chroot
        setup_script = f"""#!/bin/bash
set -e
# Install ZFSBootMenu
if command -v apt-get &>/dev/null; then
    apt-get update
    apt-get install -y zfsbootmenu
fi

# Generate ZFSBootMenu
if command -v generate-zbm &>/dev/null; then
    generate-zbm
fi

# Update bootloader if UEFI
if [ -d /boot/efi ]; then
    if command -v grub-install &>/dev/null; then
        grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=zforge
        grub-mkconfig -o /boot/grub/grub.cfg
    fi
fi
"""
        
        script_path = os.path.join(target_mount, "tmp/setup_zbm.sh")
        with open(script_path, "w") as f:
            f.write(setup_script)
        os.chmod(script_path, 0o755)
        
        subprocess.run(["chroot", target_mount, "/tmp/setup_zbm.sh"], check=True)
        
    finally:
        # Unmount target
        subprocess.run(["umount", target_mount], check=True)

def install_opencore(device, is_uefi):
    """Install OpenCore on secondary device for two-stage boot"""
    
    if not is_uefi:
        libcalamares.utils.debug("OpenCore requires UEFI, skipping in BIOS mode")
        return
    
    libcalamares.utils.debug(f"Installing OpenCore on {device}")
    
    # Get bootloader paths
    bootloader_paths = get_bootloader_binaries()
    oc_path = bootloader_paths["opencore"]
    
    # Create partition table
    subprocess.run(["wipefs", "-a", device], check=True)
    subprocess.run([
        "parted", "-s", device,
        "mklabel", "gpt",
        "mkpart", "ESP", "fat32", "1MiB", "512MiB",
        "set", "1", "esp", "on"
    ], check=True)
    
    # Determine ESP partition
    if device[-1].isdigit():
        esp = f"{device}p1"
    else:
        esp = f"{device}1"
    
    # Format ESP
    subprocess.run(["mkfs.vfat", "-F", "32", esp], check=True)
    
    # Mount ESP
    esp_dir = "/tmp/opencore_esp"
    os.makedirs(esp_dir, exist_ok=True)
    subprocess.run(["mount", esp, esp_dir], check=True)
    
    try:
        # Create EFI directory
        os.makedirs(os.path.join(esp_dir, "EFI/OC"), exist_ok=True)
        
        # Copy OpenCore files
        subprocess.run(["cp", "-r", f"{oc_path}/EFI/OC", os.path.join(esp_dir, "EFI/")], check=True)
        subprocess.run(["cp", "-r", f"{oc_path}/EFI/BOOT", os.path.join(esp_dir, "EFI/")], check=True)
        
        # Create OpenCore configuration
        configure_opencore(esp_dir)
        
    finally:
        # Unmount ESP
        subprocess.run(["umount", esp_dir], check=True)

def configure_opencore(esp_dir):
    """Configure OpenCore to chainload ZFSBootMenu"""
    
    # Basic OpenCore config template
    config_plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>ACPI</key>
    <dict>
        <key>Add</key>
        <array/>
        <key>Quirks</key>
        <dict>
            <key>FadtEnableReset</key>
            <false/>
        </dict>
    </dict>
    <key>Booter</key>
    <dict>
        <key>Quirks</key>
        <dict>
            <key>AvoidRuntimeDefrag</key>
            <true/>
        </dict>
    </dict>
    <key>DeviceProperties</key>
    <dict>
        <key>Add</key>
        <dict/>
    </dict>
    <key>Kernel</key>
    <dict>
        <key>Add</key>
        <array/>
        <key>Quirks</key>
        <dict/>
    </dict>
    <key>Misc</key>
    <dict>
        <key>Boot</key>
        <dict>
            <key>HibernateMode</key>
            <string>None</string>
            <key>PickerMode</key>
            <string>External</string>
            <key>ShowPicker</key>
            <true/>
            <key>Timeout</key>
            <integer>5</integer>
        </dict>
        <key>Security</key>
        <dict>
            <key>AllowNvramReset</key>
            <true/>
            <key>AllowSetDefault</key>
            <true/>
            <key>ScanPolicy</key>
            <integer>0</integer>
            <key>SecureBootModel</key>
            <string>Disabled</string>
            <key>Vault</key>
            <string>Optional</string>
        </dict>
        <key>Entries</key>
        <array>
            <dict>
                <key>Arguments</key>
                <string></string>
                <key>Auxiliary</key>
                <false/>
                <key>Comment</key>
                <string>ZFSBootMenu</string>
                <key>Enabled</key>
                <true/>
                <key>Name</key>
                <string>ZFSBootMenu</string>
                <key>Path</key>
                <string>PciRoot(0x0)/Pci(0x1,0x1)/Pci(0x0,0x0)/NVMe(0x1,00-00-00-00-00-00-00-00)/HD(1,GPT,00000000-0000-0000-0000-000000000000,0x800,0x100000)/EFI/zfsbootmenu/zfsbootmenu.efi</string>
            </dict>
        </array>
    </dict>
    <key>NVRAM</key>
    <dict>
        <key>Add</key>
        <dict/>
        <key>WriteFlash</key>
        <true/>
    </dict>
    <key>PlatformInfo</key>
    <dict>
        <key>Automatic</key>
        <true/>
        <key>Generic</key>
        <dict/>
        <key>UpdateDataHub</key>
        <true/>
        <key>UpdateNVRAM</key>
        <true/>
        <key>UpdateSMBIOS</key>
        <true/>
    </dict>
    <key>UEFI</key>
    <dict>
        <key>Drivers</key>
        <array>
            <string>OpenRuntime.efi</string>
            <string>NvmExpressDxe.efi</string>
        </array>
        <key>Input</key>
        <dict/>
        <key>Output</key>
        <dict/>
        <key>ProtocolOverrides</key>
        <dict/>
        <key>Quirks</key>
        <dict/>
    </dict>
</dict>
</plist>"""
    
    # Write config.plist
    with open(os.path.join(esp_dir, "EFI/OC/config.plist"), "w") as f:
        f.write(config_plist)

def create_recovery_scripts(target_mount, pool_name, dataset):
    """Create recovery and maintenance scripts"""
    
    # Create recovery script directory
    recovery_dir = os.path.join(target_mount, "root/zforge-recovery")
    os.makedirs(recovery_dir, exist_ok=True)
    
    # Create recovery script
    recovery_script = f"""#!/bin/bash
# Z-Forge Recovery Script
# Generated on $(subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip())

echo "Z-Forge ZFS Recovery Tool"
echo "========================"
echo ""
echo "Pool: {pool_name}"
echo "Root Dataset: {dataset}"
echo ""

# Function to reimport pool
reimport_pool() {{
    echo "Attempting to import pool {pool_name}..."
    zpool import -f {pool_name}
    if [ $? -eq 0 ]; then
        echo "Pool imported successfully"
    else
        echo "Failed to import pool"
        exit 1
    fi
}}

# Function to rebuild initramfs
rebuild_initramfs() {{
    echo "Rebuilding initramfs..."
    mount -t zfs {pool_name}/{dataset} /mnt
    mount --bind /dev /mnt/dev
    mount --bind /proc /mnt/proc
    mount --bind /sys /mnt/sys
    
    if command -v dracut &>/dev/null; then
        chroot /mnt dracut -f --regenerate-all
    else
        chroot /mnt update-initramfs -u -k all
    fi
    
    if command -v generate-zbm &>/dev/null; then
        chroot /mnt generate-zbm
    fi
    
    umount /mnt/sys
    umount /mnt/proc
    umount /mnt/dev
    umount /mnt
}}

# Function to reinstall bootloader
reinstall_bootloader() {{
    echo "Reinstalling bootloader..."
    if [ -d /sys/firmware/efi ]; then
        echo "Detected UEFI system"
        
        # Mount EFI partition
        mkdir -p /tmp/efi
        DISK=$(lsblk -o NAME,MOUNTPOINT -r | grep "/boot/efi" | cut -d' ' -f1 | sed 's/p[0-9]$//')
        EFI_PART=$(lsblk -o NAME,MOUNTPOINT -r | grep "/boot/efi" | cut -d' ' -f1)
        
        if [ -z "$EFI_PART" ]; then
            # Try to find EFI partition
            for d in $(lsblk -d -o NAME | grep -v "loop" | grep -v "sr0"); do
                for p in $(lsblk -o NAME,PARTTYPE -r | grep "c12a7328-f81f-11d2-ba4b-00a0c93ec93b" | cut -d' ' -f1); do
                    if [[ $p == $d* ]]; then
                        EFI_PART=$p
                        break
                    fi
                done
            done
            
            if [ -z "$EFI_PART" ]; then
                echo "No EFI partition found. Cannot reinstall bootloader."
                return 1
            fi
            
            mount /dev/$EFI_PART /tmp/efi
        else
            mount /dev/$EFI_PART /tmp/efi
        fi
        
        # Reimport pool and mount root dataset
        reimport_pool
        mount -t zfs {pool_name}/{dataset} /mnt
        
        # Copy ZFSBootMenu to EFI partition
        if [ -d "/mnt/boot/efi/EFI/zfsbootmenu" ]; then
            echo "Copying ZFSBootMenu from root dataset to EFI partition"
            mkdir -p /tmp/efi/EFI/zfsbootmenu
            cp -r /mnt/boot/efi/EFI/zfsbootmenu/* /tmp/efi/EFI/zfsbootmenu/
        elif [ -d "/usr/share/zfsbootmenu" ]; then
            echo "Copying ZFSBootMenu from installer"
            mkdir -p /tmp/efi/EFI/zfsbootmenu
            cp -r /usr/share/zfsbootmenu/* /tmp/efi/EFI/zfsbootmenu/
        else
            echo "ZFSBootMenu not found. Cannot reinstall bootloader."
            umount /tmp/efi
            umount /mnt
            return 1
        fi
        
        # Add EFI boot entry
        efibootmgr -c -d /dev/$DISK -p $(echo $EFI_PART | sed 's/.*[^0-9]//g') -L "ZFSBootMenu" -l "\\EFI\\zfsbootmenu\\zfsbootmenu.efi"
        
        umount /tmp/efi
        umount /mnt
    else
        echo "Detected BIOS system"
        reimport_pool
        mount -t zfs {pool_name}/{dataset} /mnt
        
        # Reinstall GRUB
        mount --bind /dev /mnt/dev
        mount --bind /proc /mnt/proc
        mount --bind /sys /mnt/sys
        
        DISK=$(lsblk -o NAME,MOUNTPOINT -r | grep "/" | head -1 | cut -d' ' -f1 | sed 's/[0-9]//g')
        
        if [ -z "$DISK" ]; then
            DISK=$(lsblk -d -o NAME | grep -v "loop" | grep -v "sr0" | head -1)
        fi
        
        chroot /mnt grub-install /dev/$DISK
        chroot /mnt update-grub
        
        umount /mnt/sys
        umount /mnt/proc
        umount /mnt/dev
        umount /mnt
    fi
    
    echo "Bootloader reinstallation complete"
}}

# Main menu
while true; do
    echo ""
    echo "Select recovery option:"
    echo "1. Import pool"
    echo "2. Rebuild initramfs"
    echo "3. Reinstall bootloader"
    echo "4. Exit"
    
    read -p "Choice: " choice
    
    case $choice in
        1) reimport_pool ;;
        2) rebuild_initramfs ;;
        3) reinstall_bootloader ;;
        4) exit 0 ;;
        *) echo "Invalid choice" ;;
    esac
done
"""
    
    # Write recovery script
    with open(os.path.join(recovery_dir, "recovery.sh"), "w") as f:
        f.write(recovery_script)
    os.chmod(os.path.join(recovery_dir, "recovery.sh"), 0o755)
