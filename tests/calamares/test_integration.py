#!/usr/bin/env python3
"""
Calamares Module Integration Test
Tests that all modules can be properly instantiated
"""

import sys
import os
import importlib

# Add calamares to path
sys.path.insert(0, 'calamares')

print('Testing Calamares Module Integration')
print('=' * 40)

# Module to class name mapping (actual Calamares naming convention)
modules = {
    'gpupassthrough': 'GpupassthroughJob',
    'hardwarehealth': 'HardwarehealthJob', 
    'networkconfig': 'NetworkconfigJob',
    'postinstall': 'PostinstallJob',
    'storagelayout': 'StoragelayoutJob',
    'zfsenhancedconfig': 'ZfsenhancedconfigJob',
    'zfsrichconfig': 'ZfsrichconfigJob',
    'zfsrootselect': 'ZfsrootselectJob',
    'zfspooldetect': 'ZfspooldetectJob',
    'zfsbootloader': 'ZfsbootloaderJob',
    'proxmoxconfig': 'ProxmoxconfigJob',
    'securityhardening': 'SecurityhardeningJob',
    'telemetryconsent': 'TelemetryconsentJob',
    'zforgefinalize': 'ZforgefinalizeJob'
}

passed = 0
failed = 0

for module_name, class_name in modules.items():
    try:
        # Add module path
        module_path = f'calamares/modules/{module_name}'
        sys.path.insert(0, module_path)
        
        # Import module
        if 'main' in sys.modules:
            del sys.modules['main']
        main = importlib.import_module('main')
        
        # Check for class
        if hasattr(main, class_name):
            job_class = getattr(main, class_name)
            # Instantiate without arguments (Calamares convention)
            job = job_class()
            print(f'  ✅ {module_name}: {class_name} OK')
            passed += 1
        else:
            print(f'  ❌ {module_name}: Class {class_name} not found')
            available = [c for c in dir(main) if 'Job' in c]
            if available:
                print(f'      Available: {", ".join(available)}')
            failed += 1
            
    except Exception as e:
        print(f'  ❌ {module_name}: {str(e)}')
        failed += 1
    finally:
        # Clean up path
        if module_path in sys.path:
            sys.path.remove(module_path)

print('=' * 40)
print(f'Results: {passed} passed, {failed} failed')

if failed == 0:
    print('✅ All modules pass integration test!')
    print('🎉 Perfect integration - all 14 modules working!')
else:
    print(f'❌ {failed} modules have issues')
    
# Exit with appropriate code
sys.exit(0 if failed == 0 else 1)