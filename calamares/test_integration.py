#!/usr/bin/env python3
"""
Calamares Module Integration Test
Tests all modules can be loaded and initialized
"""

import sys
import os
from pathlib import Path

def test_module(module_name):
    """Test a single module"""
    try:
        # Add module to path
        module_path = Path(f"modules/{module_name}")
        sys.path.insert(0, str(module_path))
        
        # Import module
        import main
        
        # Check for correct class
        class_name = f"{module_name.capitalize()}Job"
        if hasattr(main, class_name):
            # Try to instantiate
            job_class = getattr(main, class_name)
            job = job_class({})
            print(f"  ✅ {module_name}: OK (class {class_name} found)")
            return True
        else:
            print(f"  ❌ {module_name}: Class {class_name} not found")
            return False
            
    except Exception as e:
        print(f"  ❌ {module_name}: {str(e)}")
        return False
    finally:
        # Remove from path
        if str(module_path) in sys.path:
            sys.path.remove(str(module_path))

def main():
    """Test all modules"""
    print("Testing Calamares Module Integration")
    print("=" * 40)
    
    modules = [
        'gpupassthrough', 'hardwarehealth', 'networkconfig', 'postinstall',
        'storagelayout', 'zfsenhancedconfig', 'zfsrichconfig', 'zfsrootselect',
        'zfspooldetect', 'zfsbootloader', 'proxmoxconfig', 'securityhardening',
        'telemetryconsent', 'zforgefinalize'
    ]
    
    passed = 0
    failed = 0
    
    for module in modules:
        if test_module(module):
            passed += 1
        else:
            failed += 1
    
    print("=" * 40)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All modules can be loaded!")
        return 0
    else:
        print(f"❌ {failed} modules have issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
