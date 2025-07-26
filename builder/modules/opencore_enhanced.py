#!/usr/bin/env python3
"""
Enhanced OpenCore Installation Module for Z-FORGE
Provides flexible installation options: vFlash, USB, or secondary drives
"""

import os
import subprocess
import shutil
import tempfile
import json
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
import logging
try:
    import requests
except ImportError:
    requests = None

class OpenCoreNVME:
    """Enhanced OpenCore installation with flexible target options"""
    
    OPENCORE_VERSION = "0.9.9"
    OPENCORE_URL = f"https://github.com/acidanthera/OpenCorePkg/releases/download/{OPENCORE_VERSION}/OpenCore-{OPENCORE_VERSION}-RELEASE.zip"
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.chroot_path = self.workspace / "chroot"
        self.logger = logging.getLogger(__name__)
        self.opencore_dir = self.workspace / "opencore"
        self.opencore_dir.mkdir(parents=True, exist_ok=True)
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Execute enhanced OpenCore installation with flexible options"""
        try:
            self.logger.info("Starting enhanced OpenCore installation...")
            
            # Check if we're building an ISO (configure for post-install)
            is_iso_build = self.config.get('builder_config', {}).get('output_iso_name') is not None
            if is_iso_build:
                self.logger.info("ISO build detected - preparing OpenCore for post-install")
                return self._prepare_for_iso_install()
            
            # For direct hardware installation
            return self._install_on_hardware()
            
        except Exception as e:
            self.logger.error(f"Enhanced OpenCore installation failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _prepare_for_iso_install(self) -> Dict:
        """Prepare OpenCore components for post-install on live ISO"""
        self.logger.info("Preparing OpenCore components for ISO...")
        
        # Download and prepare OpenCore
        opencore_archive = self._download_opencore()
        opencore_files = self._prepare_opencore(opencore_archive)
        
        # Create installation script for post-install
        self._create_post_install_script()
        
        # Copy OpenCore files to chroot for later installation
        opencore_dest = self.chroot_path / "opt/zforge/opencore"
        opencore_dest.mkdir(parents=True, exist_ok=True)
        
        # Copy essential OpenCore files
        for file_path in opencore_files:
            dest_path = opencore_dest / file_path.name
            shutil.copy2(file_path, dest_path)
        
        return {
            'status': 'success',
            'message': 'OpenCore prepared for post-install',
            'post_install': True,
            'opencore_version': self.OPENCORE_VERSION
        }
    
    def _install_on_hardware(self) -> Dict:
        """Install OpenCore directly on hardware"""
        self.logger.info("Installing OpenCore on hardware...")
        
        # Detect available installation targets
        install_targets = self._detect_install_targets()
        
        if not install_targets:
            self.logger.warning("No suitable installation targets found")
            return {
                'status': 'warning',
                'message': 'No installation targets available'
            }
        
        # Select best installation target
        selected_target = self._select_install_target(install_targets)
        
        # Download and prepare OpenCore
        opencore_archive = self._download_opencore()
        opencore_files = self._prepare_opencore(opencore_archive)
        
        # Create system-specific configuration
        config_plist = self._create_enhanced_config()
        
        # Install to selected target
        self._install_to_target(selected_target, opencore_files, config_plist)
        
        return {
            'status': 'success',
            'install_target': selected_target,
            'opencore_version': self.OPENCORE_VERSION,
            'features': {
                'nvme_boot': True,
                'raid_support': True,
                'flexible_install': True,
                'auto_detection': True
            }
        }
    
    def _detect_install_targets(self) -> List[Dict[str, Any]]:
        """Detect available OpenCore installation targets"""
        self.logger.info("Detecting OpenCore installation targets...")
        targets = []
        
        try:
            # Check for vFlash (Dell servers)
            vflash_targets = self._detect_vflash()
            targets.extend(vflash_targets)
            
            # Check for USB drives
            usb_targets = self._detect_usb_drives()
            targets.extend(usb_targets)
            
            # Check for secondary storage devices
            secondary_targets = self._detect_secondary_drives()
            targets.extend(secondary_targets)
            
            # Check for SD cards (some servers have internal SD)
            sd_targets = self._detect_sd_cards()
            targets.extend(sd_targets)
            
            self.logger.info(f"Found {len(targets)} potential installation targets")
            for target in targets:
                self.logger.info(f"  - {target['type']}: {target['device']} ({target['size']})")
                
        except Exception as e:
            self.logger.error(f"Error detecting install targets: {e}")
        
        return targets
    
    def _detect_vflash(self) -> List[Dict[str, Any]]:
        """Detect Dell vFlash or similar embedded storage"""
        vflash_targets = []
        
        try:
            # Check for Dell vFlash (usually shows as USB device)
            lsblk_result = subprocess.run(
                ['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,MODEL,VENDOR'],
                capture_output=True, text=True
            )
            
            if lsblk_result.returncode == 0:
                devices = json.loads(lsblk_result.stdout)
                
                for device in devices.get('blockdevices', []):
                    model = device.get('model', '').upper()
                    vendor = device.get('vendor', '').upper()
                    
                    # Check for vFlash indicators
                    if any(indicator in model for indicator in ['VFLASH', 'IDSDM', 'DELLBOSS']):
                        vflash_targets.append({
                            'type': 'vFlash',
                            'device': f"/dev/{device['name']}",
                            'size': device.get('size', 'Unknown'),
                            'model': model,
                            'vendor': vendor,
                            'priority': 10,  # Highest priority
                            'description': 'Dell vFlash/IDSDM embedded storage'
                        })
                    
                    # Check for BOSS cards (Dell Boot Optimized Storage)
                    elif 'BOSS' in model or 'DELLBOSS' in vendor:
                        vflash_targets.append({
                            'type': 'BOSS',
                            'device': f"/dev/{device['name']}",
                            'size': device.get('size', 'Unknown'),
                            'model': model,
                            'vendor': vendor,
                            'priority': 9,
                            'description': 'Dell BOSS card storage'
                        })
                        
        except Exception as e:
            self.logger.debug(f"vFlash detection error: {e}")
        
        return vflash_targets
    
    def _detect_usb_drives(self) -> List[Dict[str, Any]]:
        """Detect USB drives suitable for OpenCore"""
        usb_targets = []
        
        try:
            # Look for USB storage devices
            usb_result = subprocess.run(
                ['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,TRAN,MODEL'],
                capture_output=True, text=True
            )
            
            if usb_result.returncode == 0:
                devices = json.loads(usb_result.stdout)
                
                for device in devices.get('blockdevices', []):
                    if device.get('tran') == 'usb' and device.get('type') == 'disk':
                        # Check size (need at least 128MB for OpenCore)
                        size_str = device.get('size', '0')
                        try:
                            if 'G' in size_str:
                                size_gb = float(size_str.replace('G', ''))
                                if size_gb >= 0.128:  # 128MB minimum
                                    usb_targets.append({
                                        'type': 'USB',
                                        'device': f"/dev/{device['name']}",
                                        'size': size_str,
                                        'model': device.get('model', 'Unknown USB'),
                                        'priority': 7,
                                        'description': 'USB storage device'
                                    })
                        except ValueError:
                            pass
                            
        except Exception as e:
            self.logger.debug(f"USB detection error: {e}")
        
        return usb_targets
    
    def _detect_secondary_drives(self) -> List[Dict[str, Any]]:
        """Detect secondary drives for OpenCore installation"""
        secondary_targets = []
        
        try:
            # Get all block devices
            lsblk_result = subprocess.run(
                ['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT'],
                capture_output=True, text=True
            )
            
            if lsblk_result.returncode == 0:
                devices = json.loads(lsblk_result.stdout)
                
                for device in devices.get('blockdevices', []):
                    if device.get('type') == 'disk':
                        # Skip if mounted (likely system drive)
                        if not device.get('mountpoint') and not self._has_mounted_partitions(device):
                            # Check if it's not the primary drive
                            if not device['name'].startswith('sda'):
                                secondary_targets.append({
                                    'type': 'Secondary Drive',
                                    'device': f"/dev/{device['name']}",
                                    'size': device.get('size', 'Unknown'),
                                    'priority': 5,
                                    'description': f"Secondary storage device ({device['name']})"
                                })
                                
        except Exception as e:
            self.logger.debug(f"Secondary drive detection error: {e}")
        
        return secondary_targets
    
    def _detect_sd_cards(self) -> List[Dict[str, Any]]:
        """Detect SD cards (some servers have internal SD slots)"""
        sd_targets = []
        
        try:
            # Look for SD card devices
            for sd_dev in ['/dev/mmcblk0', '/dev/mmcblk1']:
                if Path(sd_dev).exists():
                    # Get size
                    size_result = subprocess.run(
                        ['lsblk', '-b', '-d', '-n', '-o', 'SIZE', sd_dev],
                        capture_output=True, text=True
                    )
                    
                    if size_result.returncode == 0:
                        size_bytes = int(size_result.stdout.strip())
                        size_mb = size_bytes // (1024 * 1024)
                        
                        if size_mb >= 128:  # 128MB minimum
                            sd_targets.append({
                                'type': 'SD Card',
                                'device': sd_dev,
                                'size': f"{size_mb}MB",
                                'priority': 6,
                                'description': 'Internal SD card storage'
                            })
                            
        except Exception as e:
            self.logger.debug(f"SD card detection error: {e}")
        
        return sd_targets
    
    def _has_mounted_partitions(self, device: Dict) -> bool:
        """Check if device has any mounted partitions"""
        for child in device.get('children', []):
            if child.get('mountpoint'):
                return True
        return False
    
    def _select_install_target(self, targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select the best installation target based on priority"""
        if not targets:
            raise Exception("No installation targets available")
        
        # Sort by priority (highest first)
        sorted_targets = sorted(targets, key=lambda x: x['priority'], reverse=True)
        selected = sorted_targets[0]
        
        self.logger.info(f"Selected installation target: {selected['type']} - {selected['device']}")
        return selected
    
    def _create_enhanced_config(self) -> str:
        """Create enhanced OpenCore configuration with RAID support"""
        self.logger.info("Creating enhanced OpenCore configuration...")
        
        # Detect RAID controllers
        raid_controllers = self._detect_raid_controllers()
        
        # Enhanced driver list based on detected hardware
        drivers = [
            "OpenRuntime.efi",
            "OpenCanopy.efi",
            "AudioDxe.efi",
            "OpenUsbKbDxe.efi",
            "Ps2KeyboardDxe.efi",
            "Ps2MouseDxe.efi",
            "UsbMouseDxe.efi",
            "NvmExpressDxe.efi",
            "XhciDxe.efi",
            "ExFatDxe.efi",
            "OpenPartitionDxe.efi",
            "OpenHfsPlus.efi"
        ]
        
        # Add RAID controller specific drivers
        for controller in raid_controllers:
            if 'Dell PERC' in controller['name']:
                drivers.append("DellPercDxe.efi")
            elif 'LSI' in controller['name'] or 'MegaRAID' in controller['name']:
                drivers.append("LsiRaidDxe.efi")
            elif 'Adaptec' in controller['name']:
                drivers.append("AdaptecDxe.efi")
        
        # Create config.plist content
        config_content = {
            "ACPI": {
                "Add": [],
                "Delete": [],
                "Patch": [],
                "Quirks": {
                    "FadtEnableReset": False,
                    "NormalizeHeaders": False,
                    "RebaseRegions": False,
                    "ResetHwSig": False,
                    "ResetLogoStatus": False
                }
            },
            "DeviceProperties": {
                "Add": {},
                "Delete": {}
            },
            "Kernel": {
                "Add": [],
                "Block": [],
                "Patch": [],
                "Quirks": {
                    "AppleCpuPmCfgLock": False,
                    "AppleXcpmCfgLock": False,
                    "DisableIoMapper": True,
                    "DummyPowerManagement": False,
                    "ExternalDiskIcons": False,
                    "IncreasePciBarSize": False,
                    "PowerTimeoutKernelPanic": True,
                    "ThirdPartyDrives": False,
                    "XhciPortLimit": False
                }
            },
            "Misc": {
                "BlessOverride": [],
                "Boot": {
                    "ConsoleAttributes": 0,
                    "HibernateMode": "None",
                    "LauncherOption": "Disabled",
                    "LauncherPath": "Default",
                    "PickerAttributes": 1,
                    "PickerAudioAssist": False,
                    "PickerMode": "External",
                    "PickerVariant": "Default",
                    "PollAppleHotKeys": False,
                    "ShowPicker": True,
                    "TakeoffDelay": 0,
                    "Timeout": 5
                },
                "Debug": {
                    "AppleDebug": False,
                    "ApplePanic": False,
                    "DisableWatchDog": False,
                    "DisplayDelay": 0,
                    "DisplayLevel": 2147483650,
                    "SerialInit": False,
                    "SysReport": False,
                    "Target": 3
                },
                "Entries": [
                    {
                        "Arguments": "",
                        "Auxiliary": False,
                        "Comment": "ZFSBootMenu",
                        "Enabled": True,
                        "Name": "ZFSBootMenu",
                        "Path": "\\EFI\\zbm\\vmlinuz.efi"
                    }
                ],
                "Security": {
                    "AllowNvramReset": True,
                    "AllowSetDefault": True,
                    "AuthRestart": False,
                    "BlacklistAppleUpdate": True,
                    "DmgLoading": "Signed",
                    "EnablePassword": False,
                    "ExposeSensitiveData": 6,
                    "Vault": "Optional"
                },
                "Tools": []
            },
            "NVRAM": {
                "Add": {
                    "7C436110-AB2A-4BBB-A880-FE41995C9F82": {
                        "SystemAudioVolume": "Bg==",
                        "boot-args": "-v keepsyms=1",
                        "csr-active-config": "AAAAAA==",
                        "prev-lang:kbd": "",
                        "run-efi-updater": "No"
                    }
                },
                "Delete": {
                    "7C436110-AB2A-4BBB-A880-FE41995C9F82": [
                        "UIScale",
                        "DefaultBackgroundColor"
                    ]
                },
                "LegacyEnable": False,
                "LegacyOverwrite": False,
                "LegacySchema": {
                    "7C436110-AB2A-4BBB-A880-FE41995C9F82": "",
                    "8BE4DF61-93CA-11D2-AA0D-00E098032B8C": "",
                    "4D1EDE05-38C7-4A6A-9CC6-4BCCA8B38C14": "",
                    "EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9": "",
                    "4D1FDA02-38C7-4A6A-9CC6-4BCCA8B30102": ""
                },
                "WriteFlash": True
            },
            "PlatformInfo": {
                "Automatic": True,
                "CustomMemory": False,
                "Generic": {
                    "AdviseWindows": False,
                    "MaxBIOSVersion": False,
                    "MLB": "M0000000000000001",
                    "ProcessorType": 0,
                    "ROM": "112233445566",
                    "SpoofVendor": True,
                    "SystemMemoryStatus": "Auto",
                    "SystemProductName": "MacPro7,1",
                    "SystemSerialNumber": "M00000000001",
                    "SystemUUID": "00000000-0000-0000-0000-000000000000"
                },
                "UpdateDataHub": True,
                "UpdateNVRAM": True,
                "UpdateSMBIOS": True,
                "UpdateSMBIOSMode": "Create"
            },
            "UEFI": {
                "APFS": {
                    "EnableJumpstart": True,
                    "GlobalConnect": False,
                    "HideVerbose": True,
                    "JumpstartHotPlug": False,
                    "MinDate": 0,
                    "MinVersion": 0
                },
                "Audio": {
                    "AudioCodec": 0,
                    "AudioDevice": "PciRoot(0x0)/Pci(0x1f,0x3)",
                    "AudioOut": 0,
                    "AudioSupport": False,
                    "MinimumVolume": 20,
                    "PlayChime": "Auto",
                    "VolumeAmplifier": 0
                },
                "ConnectDrivers": True,
                "Drivers": drivers,
                "Input": {
                    "KeyFiltering": False,
                    "KeyForgetThreshold": 5,
                    "KeyMergeThreshold": 2,
                    "KeySupport": True,
                    "KeySupportMode": "Auto",
                    "KeySwap": False,
                    "PointerSupport": False,
                    "PointerSupportMode": "",
                    "TimerResolution": 50000
                },
                "Output": {
                    "TextRenderer": "BuiltinGraphics",
                    "ConsoleMode": "",
                    "Resolution": "1024x768@32",
                    "ClearScreenOnModeSwitch": False,
                    "IgnoreTextInGraphics": False,
                    "ProvideConsoleGop": True,
                    "DirectGopRendering": False,
                    "ReconnectOnResChange": False,
                    "ReplaceTabWithSpace": False,
                    "SanitiseClearScreen": False,
                    "UgaPassThrough": False
                },
                "ProtocolOverrides": {
                    "AppleAudio": False,
                    "AppleBootPolicy": False,
                    "AppleDebugLog": False,
                    "AppleEg2Info": False,
                    "AppleFramebufferInfo": False,
                    "AppleImageConversion": False,
                    "AppleImg4Verification": False,
                    "AppleKeyMap": False,
                    "AppleRtcRam": False,
                    "AppleSecureBoot": False,
                    "AppleSmcIo": False,
                    "AppleUserInterfaceTheme": False,
                    "DataHub": False,
                    "DeviceProperties": False,
                    "FirmwareVolume": False,
                    "HashServices": False,
                    "OSInfo": False,
                    "PciIo": False,
                    "UnicodeCollation": False
                },
                "Quirks": {
                    "ActivateHpetSupport": False,
                    "DisableSecurityPolicy": False,
                    "EnableVectorAcceleration": True,
                    "ExitBootServicesDelay": 0,
                    "ForceOcWriteFlash": False,
                    "ForgeUefiSupport": False,
                    "IgnoreInvalidFlexRatio": False,
                    "ReleaseUsbOwnership": False,
                    "ReloadOptionRoms": False,
                    "RequestBootVarRouting": True,
                    "TscSyncTimeout": 0,
                    "UnblockFsConnect": False
                },
                "ReservedMemory": []
            }
        }
        
        return json.dumps(config_content, indent=2)
    
    def _detect_raid_controllers(self) -> List[Dict[str, Any]]:
        """Detect RAID controllers for driver selection"""
        controllers = []
        
        try:
            # Use lspci to detect RAID controllers
            lspci_result = subprocess.run(
                ['lspci', '-v'],
                capture_output=True, text=True
            )
            
            if lspci_result.returncode == 0:
                for line in lspci_result.stdout.split('\n'):
                    line_upper = line.upper()
                    if 'RAID' in line_upper or 'STORAGE' in line_upper:
                        if 'DELL' in line_upper and 'PERC' in line_upper:
                            controllers.append({'name': 'Dell PERC', 'type': 'dell_perc'})
                        elif 'LSI' in line_upper or 'MEGARAID' in line_upper:
                            controllers.append({'name': 'LSI MegaRAID', 'type': 'lsi_megaraid'})
                        elif 'ADAPTEC' in line_upper:
                            controllers.append({'name': 'Adaptec', 'type': 'adaptec'})
                        elif 'HP' in line_upper or 'SMART ARRAY' in line_upper:
                            controllers.append({'name': 'HP Smart Array', 'type': 'hp_smartarray'})
                            
        except Exception as e:
            self.logger.debug(f"RAID controller detection error: {e}")
        
        return controllers
    
    def _download_opencore(self) -> Path:
        """Download OpenCore release"""
        self.logger.info(f"Downloading OpenCore {self.OPENCORE_VERSION}...")
        
        archive_path = self.opencore_dir / f"OpenCore-{self.OPENCORE_VERSION}.zip"
        
        if archive_path.exists():
            self.logger.info("OpenCore already downloaded")
            return archive_path
        
        try:
            if requests:
                response = requests.get(self.OPENCORE_URL, stream=True)
                response.raise_for_status()
                
                with open(archive_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                # Fallback to wget
                subprocess.run([
                    'wget', '-O', str(archive_path), self.OPENCORE_URL
                ], check=True)
                
        except Exception as e:
            self.logger.error(f"Failed to download OpenCore: {e}")
            raise
        
        return archive_path
    
    def _prepare_opencore(self, archive_path: Path) -> List[Path]:
        """Extract and prepare OpenCore files"""
        self.logger.info("Preparing OpenCore files...")
        
        extract_dir = self.opencore_dir / "extracted"
        extract_dir.mkdir(exist_ok=True)
        
        # Extract archive
        subprocess.run([
            'unzip', '-o', str(archive_path), '-d', str(extract_dir)
        ], check=True)
        
        # Find essential files
        opencore_files = []
        
        # Essential EFI files
        for file_pattern in ['OpenCore.efi', '*.efi']:
            files = list(extract_dir.rglob(file_pattern))
            opencore_files.extend(files)
        
        return opencore_files
    
    def _install_to_target(self, target: Dict[str, Any], opencore_files: List[Path], config_plist: str):
        """Install OpenCore to selected target"""
        self.logger.info(f"Installing OpenCore to {target['device']}...")
        
        device = target['device']
        
        # Create EFI partition if needed
        self._prepare_efi_partition(device)
        
        # Mount EFI partition
        mount_point = self._mount_efi_partition(device)
        
        try:
            # Create OpenCore directory structure
            oc_dir = mount_point / "EFI" / "OC"
            oc_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy OpenCore files
            for file_path in opencore_files:
                if file_path.suffix == '.efi':
                    dest_path = oc_dir / file_path.name
                    shutil.copy2(file_path, dest_path)
            
            # Write config.plist
            config_path = oc_dir / "config.plist"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(config_plist)
            
            # Create boot entry
            self._create_boot_entry(mount_point)
            
        finally:
            # Unmount
            subprocess.run(['umount', str(mount_point)], check=False)
    
    def _prepare_efi_partition(self, device: str):
        """Create EFI partition on target device"""
        self.logger.info(f"Preparing EFI partition on {device}...")
        
        # Create partition table and EFI partition
        commands = [
            f"parted -s {device} mklabel gpt",
            f"parted -s {device} mkpart primary fat32 1MiB 513MiB",
            f"parted -s {device} set 1 esp on",
            f"mkfs.fat -F32 {device}1"
        ]
        
        for cmd in commands:
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.warning(f"Command failed: {cmd} - {result.stderr}")
    
    def _mount_efi_partition(self, device: str) -> Path:
        """Mount EFI partition and return mount point"""
        mount_point = Path(tempfile.mkdtemp(prefix='opencore_'))
        
        subprocess.run([
            'mount', f'{device}1', str(mount_point)
        ], check=True)
        
        return mount_point
    
    def _create_boot_entry(self, mount_point: Path):
        """Create UEFI boot entry for OpenCore"""
        boot_dir = mount_point / "EFI" / "BOOT"
        boot_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy OpenCore as default boot loader
        oc_efi = mount_point / "EFI" / "OC" / "OpenCore.efi"
        if oc_efi.exists():
            shutil.copy2(oc_efi, boot_dir / "BOOTX64.EFI")
    
    def _create_post_install_script(self):
        """Create post-install script for ISO builds"""
        script_content = '''#!/bin/bash
# Z-FORGE OpenCore Post-Install Script

echo "=== Z-FORGE OpenCore Installation ==="

# Detect installation targets
echo "Detecting installation targets..."

# Function to detect vFlash
detect_vflash() {
    lsblk -J -o NAME,SIZE,TYPE,MODEL,VENDOR | jq -r '.blockdevices[] | select(.model and (.model | test("VFLASH|IDSDM|DELLBOSS"; "i"))) | "/dev/" + .name'
}

# Function to detect USB drives
detect_usb() {
    lsblk -J -o NAME,SIZE,TYPE,TRAN | jq -r '.blockdevices[] | select(.tran == "usb" and .type == "disk") | "/dev/" + .name'
}

# Detect targets
VFLASH=$(detect_vflash)
USB_DRIVES=$(detect_usb)

echo "Available targets:"
if [ -n "$VFLASH" ]; then
    echo "  - vFlash: $VFLASH (recommended)"
fi

if [ -n "$USB_DRIVES" ]; then
    echo "  - USB drives: $USB_DRIVES"
fi

# Select target
if [ -n "$VFLASH" ]; then
    TARGET="$VFLASH"
    echo "Selected: vFlash ($TARGET)"
elif [ -n "$USB_DRIVES" ]; then
    TARGET=$(echo "$USB_DRIVES" | head -n1)
    echo "Selected: USB drive ($TARGET)"
else
    echo "No suitable targets found"
    exit 1
fi

# Install OpenCore
echo "Installing OpenCore to $TARGET..."

# Create EFI partition
parted -s "$TARGET" mklabel gpt
parted -s "$TARGET" mkpart primary fat32 1MiB 513MiB
parted -s "$TARGET" set 1 esp on
mkfs.fat -F32 "${TARGET}1"

# Mount and copy files
MOUNT_POINT=$(mktemp -d)
mount "${TARGET}1" "$MOUNT_POINT"

mkdir -p "$MOUNT_POINT/EFI/OC"
cp -r /opt/zforge/opencore/* "$MOUNT_POINT/EFI/OC/"

# Create boot entry
mkdir -p "$MOUNT_POINT/EFI/BOOT"
cp "$MOUNT_POINT/EFI/OC/OpenCore.efi" "$MOUNT_POINT/EFI/BOOT/BOOTX64.EFI"

umount "$MOUNT_POINT"
rmdir "$MOUNT_POINT"

echo "OpenCore installation completed!"
echo "Target: $TARGET"
'''
        
        script_path = self.chroot_path / "usr/local/bin/zforge-opencore-install"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        
        self.logger.info("Created OpenCore post-install script")
