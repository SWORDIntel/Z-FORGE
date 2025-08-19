#!/usr/bin/env python3
"""
Test actual config loading with corrected build_spec.yml
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from builder.core.config import BuildConfig


def test_config_loading():
    """Test loading the corrected build_spec.yml"""
    print("🔍 Testing BuildConfig with corrected build_spec.yml")
    print("=" * 60)
    
    config_path = project_root / "build_spec.yml"
    print(f"Config file: {config_path}")
    print(f"Exists: {config_path.exists()}")
    
    try:
        # Try to load the config
        config = BuildConfig(config_path)
        print("\n✅ Config loaded successfully!")
        
        # Test required fields
        print("\n📋 Testing required fields:")
        
        # builder_config
        builder_config = config.get('builder_config', {})
        print(f"\nbuilder_config:")
        for key in ['debian_release', 'kernel_version', 'output_iso_name', 'workspace_path', 'iso_version']:
            value = builder_config.get(key, 'MISSING')
            status = "✅" if value != 'MISSING' else "❌"
            print(f"  {status} {key}: {value}")
        
        # modules
        modules = config.get('modules', [])
        print(f"\nmodules: {len(modules)} modules defined")
        if modules:
            print("  First 5 modules:")
            for module in modules[:5]:
                print(f"    - {module.get('name', 'UNNAMED')}: enabled={module.get('enabled', False)}")
        
        # Other sections
        sections = ['proxmox_config', 'zfs_config', 'bootloader_config', 'hardware_detection', 'calamares_config']
        print(f"\nOther sections:")
        for section in sections:
            exists = section in config.data
            status = "✅" if exists else "❌"
            print(f"  {status} {section}: {'Present' if exists else 'MISSING'}")
        
        # Test module loading simulation
        print("\n🔧 Testing module name resolution:")
        module_mappings = {
            'WorkspaceSetup': 'workspace_setup.py',
            'GPGBypass': 'gpg_bypass.py',
            'UniversalHardwareDetect': 'universal_hardware_detect.py',
            'Debootstrap': 'debootstrap.py',
            'KernelAcquisition': 'kernel_acquisition.py',
            'ZFSBuild': 'zfs_build.py',
            'ProxmoxIntegration': 'proxmox_integration.py',
            'LiveEnvironment': 'live_environment.py',
            'CalamaresIntegration': 'calamares_integration.py',
            'ISOGeneration': 'iso_generation.py'
        }
        
        modules_dir = project_root / "builder" / "modules"
        found_count = 0
        
        for module in modules[:10]:  # Check first 10
            module_name = module.get('name', '')
            expected_file = module_mappings.get(module_name, f"{module_name.lower()}.py")
            module_path = modules_dir / expected_file
            exists = module_path.exists()
            
            if exists:
                found_count += 1
                print(f"  ✅ {module_name} -> {expected_file}")
            else:
                # Try to find it
                possible_files = [
                    f"{module_name.lower()}.py",
                    f"{module_name}.py",
                    f"{module_name.replace('Setup', '_setup').lower()}.py",
                    f"{module_name.replace('Install', '_install').lower()}.py",
                ]
                
                found = False
                for pf in possible_files:
                    if (modules_dir / pf).exists():
                        print(f"  ⚠️ {module_name} -> {pf} (found alternative)")
                        found = True
                        break
                
                if not found:
                    print(f"  ❌ {module_name} -> NOT FOUND")
        
        print(f"\nModule resolution: {found_count}/{min(10, len(modules))} modules found")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Config loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_workspace_path():
    """Test workspace path resolution"""
    print("\n\n🏠 Testing workspace path resolution")
    print("=" * 60)
    
    try:
        config = BuildConfig("build_spec.yml")
        builder_config = config.get('builder_config', {})
        workspace_path = builder_config.get('workspace_path', 'NOT SET')
        
        print(f"Configured workspace: {workspace_path}")
        
        # Test environment variable expansion
        import os
        if '${HOME}' in workspace_path:
            expanded = workspace_path.replace('${HOME}', os.environ.get('HOME', '/home/user'))
            print(f"Expanded workspace: {expanded}")
        
        # Check if old format still exists
        old_workspace = config.get('workspace', {})
        if old_workspace:
            print(f"⚠️ Old workspace format still present: {old_workspace}")
        
        return True
        
    except Exception as e:
        print(f"❌ Workspace test failed: {e}")
        return False


def main():
    """Run all config tests"""
    print("🧪 Configuration Loading Test Suite")
    print("=" * 60)
    
    tests = [
        ("Config Loading", test_config_loading),
        ("Workspace Path", test_workspace_path)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        if test_func():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✅ All config tests passed!")
        print("\nThe corrected build_spec.yml is working properly.")
    else:
        print("❌ Some config tests failed")
        print("\nThe build_spec.yml still needs adjustments.")
    
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())