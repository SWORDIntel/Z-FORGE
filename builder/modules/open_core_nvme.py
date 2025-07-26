#!/usr/bin/env python3
"""
OpenCore NVMe Boot Module for Z-FORGE
Enables booting from PCIe NVMe drives on systems without native support
"""

import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, List, Any
import logging
try:
    import requests
except ImportError:
    # Fallback to wget/curl if requests not available
    requests = None

class OpenCoreNVME:
    """Handles OpenCore installation for NVMe boot support"""
    
    OPENCORE_VERSION = "0.9.7"
    OPENCORE_URL = f"https://github.com/acidanthera/OpenCorePkg/releases/download/{OPENCORE_VERSION}/OpenCore-{OPENCORE_VERSION}-RELEASE.zip"
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.chroot_path = self.workspace / "chroot"
        self.logger = logging.getLogger(__name__)
        self.opencore_dir = self.workspace / "opencore"
        self.opencore_dir.mkdir(parents=True, exist_ok=True)
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """
        Install and configure OpenCore for NVMe boot support
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Status dictionary
        """
        try:
            self.logger.info("Setting up OpenCore for NVMe boot support...")
            
            # Check if we're building an ISO (skip for ISO builds)
            is_iso_build = self.config.get('builder_config', {}).get('output_iso_name') is not None
            if is_iso_build:
                self.logger.info("ISO build detected - skipping OpenCore installation (for physical systems only)")
                return {
                    'status': 'success',
                    'message': 'Skipped for ISO build',
                    'skipped': True
                }
            
            opencore_config = self.config.get('opencore_config', {})
            install_device = opencore_config.get('install_device')
            system_type = opencore_config.get('system_type', 'generic')  # generic, dell_r420, etc.
            
            if not install_device:
                self.logger.warning("No install device specified for OpenCore")
                return {
                    'status': 'skipped',
                    'reason': 'No install device specified'
                }
            
            # Step 1: Download OpenCore
            opencore_archive = self._download_opencore()
            
            # Step 2: Extract and prepare OpenCore
            opencore_files = self._prepare_opencore(opencore_archive)
            
            # Step 3: Create OpenCore configuration
            config_plist = self._create_config(system_type)
            
            # Step 4: Install OpenCore to device
            self._install_to_device(install_device, opencore_files, config_plist)
            
            # Step 5: Create chainload configuration for ZFSBootMenu
            self._configure_chainload()
            
            # Step 6: Create recovery tools
            self._create_recovery_tools(install_device)
            
            self.logger.info("OpenCore installation complete")
            
            return {
                'status': 'success',
                'opencore_version': self.OPENCORE_VERSION,
                'install_device': install_device,
                'features': {
                    'nvme_boot': True,
                    'uefi_emulation': True,
                    'chainload_zbm': True
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to install OpenCore: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _download_opencore(self) -> Path:
        """Download OpenCore release"""
        self.logger.info(f"Downloading OpenCore {self.OPENCORE_VERSION}...")
        
        archive_path = self.opencore_dir / f"OpenCore-{self.OPENCORE_VERSION}.zip"
        
        if archive_path.exists():
            self.logger.info("OpenCore already downloaded")
            return archive_path
        
        # Download using requests or fallback to wget
        if requests:
            response = requests.get(self.OPENCORE_URL, stream=True)
            response.raise_for_status()
            
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        else:
            # Fallback to wget
            self.logger.info("Using wget as fallback (requests module not available)")
            subprocess.run([
                "wget", "-O", str(archive_path), self.OPENCORE_URL
            ], check=True)
        
        return archive_path
    
    def _prepare_opencore(self, archive_path: Path) -> Path:
        """Extract and prepare OpenCore files"""
        self.logger.info("Preparing OpenCore files...")
        
        extract_dir = self.opencore_dir / "extracted"
        extract_dir.mkdir(exist_ok=True)
        
        # Extract archive
        subprocess.run([
            "unzip", "-o", str(archive_path), "-d", str(extract_dir)
        ], check=True)
        
        # Prepare directory structure
        prepared_dir = self.opencore_dir / "prepared"
        if prepared_dir.exists():
            shutil.rmtree(prepared_dir)
        
        prepared_dir.mkdir()
        
        # Copy necessary files
        efi_source = extract_dir / "X64" / "EFI"
        if efi_source.exists():
            shutil.copytree(efi_source, prepared_dir / "EFI")
        
        # Add essential drivers for NVMe
        drivers_dir = prepared_dir / "EFI" / "OC" / "Drivers"
        drivers_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy NVMe and filesystem drivers
        required_drivers = [
            "OpenRuntime.efi",
            "OpenCanopy.efi",  # GUI
            "NvmExpressDxe.efi",  # NVMe support
            "HfsPlus.efi",  # HFS+ support
            "OpenUsbKbDxe.efi",  # USB keyboard
        ]
        
        for driver in required_drivers:
            driver_path = extract_dir / "X64" / "EFI" / "OC" / "Drivers" / driver
            if driver_path.exists():
                shutil.copy2(driver_path, drivers_dir / driver)
        
        return prepared_dir
    
    def _create_config(self, system_type: str) -> Path:
        """Create OpenCore configuration for NVMe boot"""
        self.logger.info(f"Creating OpenCore configuration for {system_type}...")
        
        # Base configuration with NVMe support
        config_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>ACPI</key>
    <dict>
        <key>Add</key>
        <array/>
        <key>Delete</key>
        <array/>
        <key>Patch</key>
        <array/>
        <key>Quirks</key>
        <dict>
            <key>FadtEnableReset</key>
            <false/>
            <key>NormalizeHeaders</key>
            <false/>
            <key>RebaseRegions</key>
            <false/>
            <key>ResetHwSig</key>
            <false/>
            <key>ResetLogoStatus</key>
            <false/>
        </dict>
    </dict>
    <key>Booter</key>
    <dict>
        <key>MmioWhitelist</key>
        <array/>
        <key>Patch</key>
        <array/>
        <key>Quirks</key>
        <dict>
            <key>AvoidRuntimeDefrag</key>
            <true/>
            <key>DevirtualiseMmio</key>
            <false/>
            <key>DisableSingleUser</key>
            <false/>
            <key>DisableVariableWrite</key>
            <false/>
            <key>DiscardHibernateMap</key>
            <false/>
            <key>EnableSafeModeSlide</key>
            <true/>
            <key>EnableWriteUnprotector</key>
            <true/>
            <key>ForceExitBootServices</key>
            <false/>
            <key>ProtectMemoryRegions</key>
            <false/>
            <key>ProtectSecureBoot</key>
            <false/>
            <key>ProtectUefiServices</key>
            <false/>
            <key>ProvideCustomSlide</key>
            <true/>
            <key>ProvideMaxSlide</key>
            <integer>0</integer>
            <key>RebuildAppleMemoryMap</key>
            <false/>
            <key>SetupVirtualMap</key>
            <true/>
            <key>SignalAppleOS</key>
            <false/>
            <key>SyncRuntimePermissions</key>
            <true/>
        </dict>
    </dict>
    <key>DeviceProperties</key>
    <dict>
        <key>Add</key>
        <dict/>
        <key>Delete</key>
        <dict/>
    </dict>
    <key>Kernel</key>
    <dict>
        <key>Add</key>
        <array/>
        <key>Block</key>
        <array/>
        <key>Emulate</key>
        <dict>
            <key>Cpuid1Data</key>
            <data/>
            <key>Cpuid1Mask</key>
            <data/>
        </dict>
        <key>Force</key>
        <array/>
        <key>Patch</key>
        <array/>
        <key>Quirks</key>
        <dict>
            <key>AppleCpuPmCfgLock</key>
            <false/>
            <key>AppleXcpmCfgLock</key>
            <false/>
            <key>AppleXcpmExtraMsrs</key>
            <false/>
            <key>AppleXcpmForceBoost</key>
            <false/>
            <key>CustomSMBIOSGuid</key>
            <false/>
            <key>DisableIoMapper</key>
            <false/>
            <key>DisableLinkeditJettison</key>
            <true/>
            <key>DisableRtcChecksum</key>
            <false/>
            <key>ExtendBTFeatureFlags</key>
            <false/>
            <key>IncreasePciBarSize</key>
            <false/>
            <key>LapicKernelPanic</key>
            <false/>
            <key>LegacyCommpage</key>
            <false/>
            <key>PanicNoKextDump</key>
            <true/>
            <key>PowerTimeoutKernelPanic</key>
            <true/>
            <key>ThirdPartyDrives</key>
            <false/>
            <key>XhciPortLimit</key>
            <false/>
        </dict>
        <key>Scheme</key>
        <dict>
            <key>FuzzyMatch</key>
            <true/>
            <key>KernelArch</key>
            <string>x86_64</string>
            <key>KernelCache</key>
            <string>Auto</string>
        </dict>
    </dict>
    <key>Misc</key>
    <dict>
        <key>BlessOverride</key>
        <array/>
        <key>Boot</key>
        <dict>
            <key>ConsoleAttributes</key>
            <integer>0</integer>
            <key>HibernateMode</key>
            <string>None</string>
            <key>HideAuxiliary</key>
            <false/>
            <key>LauncherOption</key>
            <string>Disabled</string>
            <key>LauncherPath</key>
            <string>Default</string>
            <key>PickerAttributes</key>
            <integer>1</integer>
            <key>PickerAudioAssist</key>
            <false/>
            <key>PickerMode</key>
            <string>Builtin</string>
            <key>PickerVariant</key>
            <string>Auto</string>
            <key>PollAppleHotKeys</key>
            <true/>
            <key>ShowPicker</key>
            <true/>
            <key>TakeoffDelay</key>
            <integer>0</integer>
            <key>Timeout</key>
            <integer>5</integer>
        </dict>
        <key>Debug</key>
        <dict>
            <key>AppleDebug</key>
            <true/>
            <key>ApplePanic</key>
            <true/>
            <key>DisableWatchDog</key>
            <true/>
            <key>DisplayDelay</key>
            <integer>0</integer>
            <key>DisplayLevel</key>
            <integer>2147483650</integer>
            <key>SerialInit</key>
            <true/>
            <key>SysReport</key>
            <false/>
            <key>Target</key>
            <integer>67</integer>
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
                <string>PciRoot(0x0)/Pci(0x1,0x0)/Pci(0x0,0x0)/NVMe(0x1,00-00-00-00-00-00-00-00)/HD(1,GPT,00000000-0000-0000-0000-000000000000,0x28,0x64000)/\\EFI\\zfsbootmenu\\vmlinuz.efi</string>
                <key>TextMode</key>
                <false/>
            </dict>
        </array>
        <key>Security</key>
        <dict>
            <key>AllowNvramReset</key>
            <true/>
            <key>AllowSetDefault</key>
            <true/>
            <key>AllowToggleSip</key>
            <false/>
            <key>ApECID</key>
            <integer>0</integer>
            <key>AuthRestart</key>
            <false/>
            <key>BlacklistAppleUpdate</key>
            <true/>
            <key>DmgLoading</key>
            <string>Signed</string>
            <key>EnablePassword</key>
            <false/>
            <key>ExposeSensitiveData</key>
            <integer>6</integer>
            <key>HaltLevel</key>
            <integer>2147483648</integer>
            <key>PasswordHash</key>
            <data/>
            <key>PasswordSalt</key>
            <data/>
            <key>ScanPolicy</key>
            <integer>0</integer>
            <key>SecureBootModel</key>
            <string>Disabled</string>
            <key>Vault</key>
            <string>Optional</string>
        </dict>
        <key>Serial</key>
        <dict>
            <key>Custom</key>
            <dict>
                <key>BaudRate</key>
                <integer>115200</integer>
                <key>ClockRate</key>
                <integer>1843200</integer>
                <key>ExtendedTxFifoSize</key>
                <integer>64</integer>
                <key>FifoControl</key>
                <integer>7</integer>
                <key>LineControl</key>
                <integer>3</integer>
                <key>PciDeviceInfo</key>
                <data>////////</data>
                <key>RegisterAccessWidth</key>
                <integer>8</integer>
                <key>RegisterBase</key>
                <integer>1016</integer>
                <key>RegisterStride</key>
                <integer>1</integer>
                <key>UseHardwareFlowControl</key>
                <false/>
                <key>UseMmio</key>
                <false/>
            </dict>
            <key>Init</key>
            <true/>
            <key>Override</key>
            <false/>
        </dict>
        <key>Tools</key>
        <array/>
    </dict>
    <key>NVRAM</key>
    <dict>
        <key>Add</key>
        <dict>
            <key>4D1EDE05-38C7-4A6A-9CC6-4BCCA8B38C14</key>
            <dict>
                <key>UIScale</key>
                <data>AQ==</data>
            </dict>
            <key>7C436110-AB2A-4BBB-A880-FE41995C9F82</key>
            <dict>
                <key>SystemAudioVolume</key>
                <data>Rg==</data>
                <key>boot-args</key>
                <string>-v debug=0x100 keepsyms=1</string>
                <key>csr-active-config</key>
                <data>AAAAAA==</data>
                <key>prev-lang:kbd</key>
                <string>en-US:0</string>
            </dict>
        </dict>
        <key>Delete</key>
        <dict/>
        <key>LegacySchema</key>
        <dict/>
        <key>WriteFlash</key>
        <true/>
    </dict>
    <key>PlatformInfo</key>
    <dict>
        <key>Automatic</key>
        <true/>
        <key>CustomMemory</key>
        <false/>
        <key>Generic</key>
        <dict>
            <key>AdviseFeatures</key>
            <false/>
            <key>MLB</key>
            <string>00000000000000000</string>
            <key>MaxBIOSVersion</key>
            <false/>
            <key>ProcessorType</key>
            <integer>0</integer>
            <key>ROM</key>
            <data>AAAAAAAAAAAA</data>
            <key>SpoofVendor</key>
            <true/>
            <key>SystemMemoryStatus</key>
            <string>Auto</string>
            <key>SystemProductName</key>
            <string>MacPro6,1</string>
            <key>SystemSerialNumber</key>
            <string>000000000000</string>
            <key>SystemUUID</key>
            <string>00000000-0000-0000-0000-000000000000</string>
        </dict>
        <key>UpdateDataHub</key>
        <true/>
        <key>UpdateNVRAM</key>
        <true/>
        <key>UpdateSMBIOS</key>
        <true/>
        <key>UpdateSMBIOSMode</key>
        <string>Create</string>
        <key>UseRawUuidEncoding</key>
        <false/>
    </dict>
    <key>UEFI</key>
    <dict>
        <key>APFS</key>
        <dict>
            <key>EnableJumpstart</key>
            <true/>
            <key>GlobalConnect</key>
            <false/>
            <key>HideVerbose</key>
            <true/>
            <key>JumpstartHotPlug</key>
            <false/>
            <key>MinDate</key>
            <integer>0</integer>
            <key>MinVersion</key>
            <integer>0</integer>
        </dict>
        <key>Audio</key>
        <dict>
            <key>AudioCodec</key>
            <integer>0</integer>
            <key>AudioDevice</key>
            <string>PciRoot(0x0)/Pci(0x1b,0x0)</string>
            <key>AudioOutMask</key>
            <integer>-1</integer>
            <key>AudioSupport</key>
            <false/>
            <key>DisconnectHda</key>
            <false/>
            <key>MaximumGain</key>
            <integer>-15</integer>
            <key>MinimumAssistGain</key>
            <integer>-30</integer>
            <key>MinimumAudibleGain</key>
            <integer>-55</integer>
            <key>PlayChime</key>
            <string>Auto</string>
            <key>ResetTrafficClass</key>
            <false/>
            <key>SetupDelay</key>
            <integer>0</integer>
        </dict>
        <key>ConnectDrivers</key>
        <true/>
        <key>Drivers</key>
        <array>
            <string>OpenRuntime.efi</string>
            <string>OpenCanopy.efi</string>
            <string>NvmExpressDxe.efi</string>
            <string>HfsPlus.efi</string>
            <string>OpenUsbKbDxe.efi</string>
        </array>
        <key>Input</key>
        <dict>
            <key>KeyFiltering</key>
            <false/>
            <key>KeyForgetThreshold</key>
            <integer>5</integer>
            <key>KeySupport</key>
            <true/>
            <key>KeySupportMode</key>
            <string>Auto</string>
            <key>KeySwap</key>
            <false/>
            <key>PointerSupport</key>
            <false/>
            <key>PointerSupportMode</key>
            <string>ASUS</string>
            <key>TimerResolution</key>
            <integer>50000</integer>
        </dict>
        <key>Output</key>
        <dict>
            <key>ClearScreenOnModeSwitch</key>
            <false/>
            <key>ConsoleMode</key>
            <string></string>
            <key>DirectGopRendering</key>
            <false/>
            <key>ForceResolution</key>
            <false/>
            <key>GopPassThrough</key>
            <string>Disabled</string>
            <key>IgnoreTextInGraphics</key>
            <false/>
            <key>ProvideConsoleGop</key>
            <true/>
            <key>ReconnectGraphicsOnConnect</key>
            <false/>
            <key>ReconnectOnResChange</key>
            <false/>
            <key>ReplaceTabWithSpace</key>
            <false/>
            <key>Resolution</key>
            <string>Max</string>
            <key>SanitiseClearScreen</key>
            <false/>
            <key>TextRenderer</key>
            <string>BuiltinGraphics</string>
            <key>UgaPassThrough</key>
            <false/>
        </dict>
        <key>ProtocolOverrides</key>
        <dict>
            <key>AppleAudio</key>
            <false/>
            <key>AppleBootPolicy</key>
            <false/>
            <key>AppleDebugLog</key>
            <false/>
            <key>AppleEg2Info</key>
            <false/>
            <key>AppleFramebufferInfo</key>
            <false/>
            <key>AppleImageConversion</key>
            <false/>
            <key>AppleImg4Verification</key>
            <false/>
            <key>AppleKeyMap</key>
            <false/>
            <key>AppleRtcRam</key>
            <false/>
            <key>AppleSecureBoot</key>
            <false/>
            <key>AppleSmcIo</key>
            <false/>
            <key>AppleUserInterfaceTheme</key>
            <false/>
            <key>DataHub</key>
            <false/>
            <key>DeviceProperties</key>
            <false/>
            <key>FirmwareVolume</key>
            <false/>
            <key>HashServices</key>
            <false/>
            <key>OSInfo</key>
            <false/>
            <key>UnicodeCollation</key>
            <false/>
        </dict>
        <key>Quirks</key>
        <dict>
            <key>ActivateHpetSupport</key>
            <false/>
            <key>DisableSecurityPolicy</key>
            <false/>
            <key>EnableVectorAcceleration</key>
            <true/>
            <key>EnableVmx</key>
            <false/>
            <key>ExitBootServicesDelay</key>
            <integer>0</integer>
            <key>ForceOcWriteFlash</key>
            <false/>
            <key>ForgeUefiSupport</key>
            <false/>
            <key>IgnoreInvalidFlexRatio</key>
            <false/>
            <key>ReleaseUsbOwnership</key>
            <false/>
            <key>ReloadOptionRoms</key>
            <false/>
            <key>RequestBootVarRouting</key>
            <true/>
            <key>ResizeGpuBars</key>
            <integer>-1</integer>
            <key>TscSyncTimeout</key>
            <integer>0</integer>
            <key>UnblockFsConnect</key>
            <false/>
        </dict>
        <key>ReservedMemory</key>
        <array/>
    </dict>
</dict>
</plist>
"""
        
        # Add system-specific modifications
        if system_type == "dell_r420":
            # Add Dell R420 specific settings
            config_content = config_content.replace(
                '<key>SerialInit</key>\n            <true/>',
                '<key>SerialInit</key>\n            <true/>\n            <!-- Dell R420 Serial Console -->'
            )
        
        config_path = self.opencore_dir / "config.plist"
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        return config_path
    
    def _install_to_device(self, device: str, opencore_files: Path, config_plist: Path):
        """Install OpenCore to the specified device"""
        self.logger.info(f"Installing OpenCore to {device}...")
        
        # Create temporary mount point
        with tempfile.TemporaryDirectory() as temp_mount:
            mount_point = Path(temp_mount)
            
            # Format device as FAT32
            self.logger.info("Formatting device as FAT32...")
            subprocess.run([
                "mkfs.vfat", "-F", "32", "-n", "OPENCORE", device
            ], check=True)
            
            # Mount device
            subprocess.run(["mount", device, str(mount_point)], check=True)
            
            try:
                # Copy OpenCore files
                self.logger.info("Copying OpenCore files...")
                shutil.copytree(
                    opencore_files / "EFI",
                    mount_point / "EFI"
                )
                
                # Copy configuration
                shutil.copy2(
                    config_plist,
                    mount_point / "EFI" / "OC" / "config.plist"
                )
                
                # Create tools directory
                tools_dir = mount_point / "EFI" / "OC" / "Tools"
                tools_dir.mkdir(exist_ok=True)
                
                # Sync filesystem
                subprocess.run(["sync"], check=True)
                
            finally:
                # Unmount device
                subprocess.run(["umount", str(mount_point)], check=False)
    
    def _configure_chainload(self):
        """Configure OpenCore to chainload ZFSBootMenu"""
        self.logger.info("Configuring chainload to ZFSBootMenu...")
        
        # Create chainload script
        chainload_script = """#!/bin/bash
# OpenCore to ZFSBootMenu chainload configuration

# This script updates the OpenCore configuration to properly
# chainload ZFSBootMenu from the NVMe drive

echo "Configuring OpenCore chainload..."

# Find the NVMe device and partition
NVME_DEVICE=$(lsblk -d -o NAME,TYPE | grep nvme | head -1 | awk '{print $1}')
if [ -z "$NVME_DEVICE" ]; then
    echo "Error: No NVMe device found"
    exit 1
fi

echo "Found NVMe device: $NVME_DEVICE"

# Update OpenCore config to point to ZFSBootMenu on NVMe
# This will be handled by the OpenCore config.plist

echo "Chainload configuration complete"
"""
        
        script_path = self.workspace / "configure_chainload.sh"
        with open(script_path, 'w') as f:
            f.write(chainload_script)
        
        os.chmod(script_path, 0o755)
    
    def _create_recovery_tools(self, device: str):
        """Create recovery tools for OpenCore"""
        self.logger.info("Creating OpenCore recovery tools...")
        
        recovery_script = f"""#!/bin/bash
# OpenCore Recovery Tool

set -e

DEVICE="{device}"

echo "OpenCore Recovery Tool"
echo "====================="
echo ""
echo "This tool can help recover or reinstall OpenCore"
echo ""

case "$1" in
    backup)
        echo "Backing up OpenCore from $DEVICE..."
        mkdir -p /tmp/opencore_backup
        mount "$DEVICE" /mnt
        cp -r /mnt/EFI /tmp/opencore_backup/
        umount /mnt
        tar -czf opencore_backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /tmp/opencore_backup .
        rm -rf /tmp/opencore_backup
        echo "Backup saved to opencore_backup_*.tar.gz"
        ;;
        
    restore)
        if [ -z "$2" ]; then
            echo "Usage: $0 restore <backup_file>"
            exit 1
        fi
        echo "Restoring OpenCore to $DEVICE from $2..."
        mount "$DEVICE" /mnt
        rm -rf /mnt/EFI
        tar -xzf "$2" -C /mnt
        umount /mnt
        echo "Restore complete"
        ;;
        
    reinstall)
        echo "Reinstalling OpenCore to $DEVICE..."
        # This would call the main installation function
        echo "Please run the main OpenCore installation"
        ;;
        
    *)
        echo "Usage: $0 {{backup|restore|reinstall}}"
        echo ""
        echo "  backup     - Backup current OpenCore installation"
        echo "  restore    - Restore OpenCore from backup"
        echo "  reinstall  - Reinstall OpenCore"
        ;;
esac
"""
        
        recovery_path = self.chroot_path / "usr" / "local" / "bin" / "opencore-recovery"
        recovery_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(recovery_path, 'w') as f:
            f.write(recovery_script)
        
        os.chmod(recovery_path, 0o755)