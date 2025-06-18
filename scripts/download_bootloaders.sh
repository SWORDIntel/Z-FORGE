#!/bin/bash
# scripts/download_bootloaders.sh
# Downloads and prepares bootloader binaries for Z-Forge

set -e

BOOTLOADERS_DIR="/usr/share/zforge/bootloaders"
TEMP_DIR="/tmp/zforge-bootloaders"

echo "====== Z-Forge Bootloader Acquisition ======"

# Create directories
mkdir -p "$BOOTLOADERS_DIR"/{zfsbootmenu,opencore}
mkdir -p "$TEMP_DIR"

echo "[*] Downloading ZFSBootMenu..."
# Get latest ZFSBootMenu
wget -q --show-progress -O "$TEMP_DIR/zbm.zip" \
  "https://github.com/zbm-dev/zfsbootmenu/releases/latest/download/zfsbootmenu-release.zip"

echo "[*] Extracting ZFSBootMenu..."
unzip -q "$TEMP_DIR/zbm.zip" -d "$TEMP_DIR/zbm"
cp -r "$TEMP_DIR/zbm/EFI" "$BOOTLOADERS_DIR/zfsbootmenu/"

echo "[*] Downloading OpenCore..."
# Get OpenCore
wget -q --show-progress -O "$TEMP_DIR/opencore.zip" \
  "https://github.com/acidanthera/OpenCorePkg/releases/download/0.9.7/OpenCore-0.9.7-RELEASE.zip"

echo "[*] Extracting OpenCore..."
unzip -q "$TEMP_DIR/opencore.zip" -d "$TEMP_DIR/opencore"
cp -r "$TEMP_DIR/opencore/X64/EFI" "$BOOTLOADERS_DIR/opencore/"

echo "[*] Downloading NVMe driver..."
# Get NVMe driver
wget -q --show-progress -O "$BOOTLOADERS_DIR/opencore/EFI/OC/Drivers/NvmExpressDxe.efi" \
  "https://github.com/acidanthera/OpenCorePkg/raw/master/Staging/NvmExpressDxe/NvmExpressDxe.efi"

echo "[*] Creating OpenCore config template..."
# Create OpenCore configuration template
cat > "$BOOTLOADERS_DIR/opencore/EFI/OC/config.plist" << 'EOT'
<?xml version="1.0" encoding="UTF-8"?>
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
</plist>
EOT

# Create ZFSBootMenu configuration template
cat > "$BOOTLOADERS_DIR/zfsbootmenu/zfsbootmenu.conf" << 'EOT'
# ZFSBootMenu configuration template

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
    Enabled: false

EFI:
  ImageDir: /boot/efi/EFI/zfsbootmenu
  Versions: false
  Enabled: true

Kernel:
  CommandLine: "ro quiet loglevel=4"
  Prefix: vmlinuz

ZFS:
  PoolName: rpool
  DefaultSet: rpool/ROOT/proxmox
  ShowSnapshots: true
EOT

# Cleanup
rm -rf "$TEMP_DIR"

echo "[+] Bootloaders prepared successfully!"
echo "    ZFSBootMenu: $BOOTLOADERS_DIR/zfsbootmenu/"
echo "    OpenCore: $BOOTLOADERS_DIR/opencore/"
echo ""
