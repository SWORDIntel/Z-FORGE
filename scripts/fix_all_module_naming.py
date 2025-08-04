#!/usr/bin/env python3
"""Fix all module naming convention issues."""

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Mapping of files to their correct class names
FIXES_TO_APPLY = {
    'builder/modules/calamares_zfstargetselector.py': {
        'old': 'ZFSTargetSelector',
        'new': 'CalamaresZfstargetselector'
    },
    'builder/modules/opencore_enhanced.py': {
        'old': 'OpenCoreNVME',
        'new': 'OpencoreEnhanced'
    },
    'builder/modules/live_environment_fixed.py': {
        'old': 'LiveEnvironment',
        'new': 'LiveEnvironmentFixed'
    },
    'builder/modules/autooptimizer.py': {
        'old': 'AutoOptimizer',
        'new': 'Autooptimizer'
    },
    'builder/modules/calamares_zfs_enhanced.py': {
        'old': 'ZFSConfigurationGUI',
        'new': 'CalamaresZfsEnhanced'
    },
    'builder/modules/gpgbypass.py': {
        'old': 'GpgBypass',
        'new': 'Gpgbypass'
    },
    'builder/modules/live_environment_backup.py': {
        'old': 'LiveEnvironment',
        'new': 'LiveEnvironmentBackup'
    },
    'builder/modules/kde_theme_config.py': {
        'old': 'KDEThemeConfig',
        'new': 'KdeThemeConfig'
    },
    'builder/modules/open_core_nvme.py': {
        'old': 'OpenCoreNVME',
        'new': 'OpenCoreNvme'
    },
    'builder/modules/zfs_build_perfect.py': {
        'old': 'PerfectZFSBuild',
        'new': 'ZfsBuildPerfect'
    },
    'builder/modules/zfs_boot_menu_install.py': {
        'old': 'ZfsbootmenuInstall',
        'new': 'ZfsBootMenuInstall'
    },
    'builder/modules/kernel_acquisition_perfect.py': {
        'old': 'PerfectKernelAcquisition',
        'new': 'KernelAcquisitionPerfect'
    },
    'builder/modules/opencorenvme.py': {
        'old': 'OpenCoreNVME',
        'new': 'Opencorenvme'
    },
    'builder/modules/zfsrootselect/main.py': {
        'old': 'ZFSTargetSelector',
        'new': 'Zfsrootselect'
    },
    'calamares/modules/postinstall/postinstall_gui.py': {
        'old': 'PostInstallWidget',
        'new': 'PostinstallGui'
    },
    'calamares/modules/postinstall/main.py': {
        'old': 'PostInstallViewStep',
        'new': 'Postinstall'
    },
    'calamares/modules/zfsrootselect/main.py': {
        'old': 'ZFSTargetSelector',
        'new': 'Zfsrootselect'
    },
    'calamares/modules/gpupassthrough/main.py': {
        'old': 'GPUPassthroughViewStep',
        'new': 'Gpupassthrough'
    },
    'calamares/modules/gpupassthrough/gpu_passthrough_gui.py': {
        'old': 'GPUPassthroughWidget',
        'new': 'GpuPassthroughGui'
    },
    'calamares/modules/hardwarehealth/hardware_health_gui.py': {
        'old': 'HardwareHealthWidget',
        'new': 'HardwareHealthGui'
    },
    'calamares/modules/hardwarehealth/main.py': {
        'old': 'HardwareHealthViewStep',
        'new': 'Hardwarehealth'
    },
    'calamares/modules/zfsenhancedconfig/zfs_enhanced_gui.py': {
        'old': 'ZFSEnhancedConfigWidget',
        'new': 'ZfsEnhancedGui'
    },
    'calamares/modules/zfsenhancedconfig/main.py': {
        'old': 'ZFSEnhancedConfigViewStep',
        'new': 'Zfsenhancedconfig'
    },
    'calamares/modules/networkconfig/main.py': {
        'old': 'NetworkConfigViewStep',
        'new': 'Networkconfig'
    },
    'calamares/modules/networkconfig/network_config_gui.py': {
        'old': 'NetworkConfigWidget',
        'new': 'NetworkConfigGui'
    },
    'calamares/modules/storagelayout/main.py': {
        'old': 'StorageLayoutViewStep',
        'new': 'Storagelayout'
    },
    'calamares/modules/storagelayout/storage_layout_gui.py': {
        'old': 'StorageLayoutWidget',
        'new': 'StorageLayoutGui'
    },
    'calamares/modules/zfsrichconfig/main.py': {
        'old': 'ZFSRichConfigViewStep',
        'new': 'Zfsrichconfig'
    }
}

def fix_class_name(file_path: Path, old_name: str, new_name: str) -> bool:
    """Fix class name in a file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace class definition
        pattern = rf'class {re.escape(old_name)}(\s*\(|:)'
        replacement = rf'class {new_name}\1'
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(file_path, 'w') as f:
                f.write(new_content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Main function."""
    project_root = Path('/opt/github/Z-FORGE')
    
    print("Fixing module naming convention issues...")
    print("=" * 70)
    
    fixed_count = 0
    
    for file_path, fix_info in FIXES_TO_APPLY.items():
        full_path = project_root / file_path
        
        if not full_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue
        
        print(f"Fixing {file_path}...")
        print(f"  {fix_info['old']} → {fix_info['new']}")
        
        if fix_class_name(full_path, fix_info['old'], fix_info['new']):
            print(f"  ✅ Fixed")
            fixed_count += 1
        else:
            print(f"  ❌ Failed or no change needed")
    
    print(f"\n📊 Summary:")
    print(f"  Fixed: {fixed_count}/{len(FIXES_TO_APPLY)} files")

if __name__ == '__main__':
    main()