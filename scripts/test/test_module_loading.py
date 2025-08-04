#!/usr/bin/env python3
"""Test that all modules can be loaded properly."""

import sys
import importlib.util
from pathlib import Path

def test_module_loading():
    """Test loading all builder modules."""
    project_root = Path(__file__).parent.parent.parent
    modules_dir = project_root / 'builder' / 'modules'
    
    print("Testing module loading...")
    print("=" * 70)
    
    failed_modules = []
    success_modules = []
    
    # Get all Python files in modules directory
    for py_file in modules_dir.glob('*.py'):
        if py_file.name == '__init__.py':
            continue
            
        module_name = py_file.stem
        
        try:
            # Try to import the module
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Try to find the expected class name
            expected_class = "".join(word.capitalize() for word in module_name.split('_'))
            
            if hasattr(module, expected_class):
                success_modules.append((module_name, expected_class))
                print(f"✅ {module_name} -> {expected_class}")
            else:
                # Try to find any class in the module
                classes = [name for name in dir(module) if isinstance(getattr(module, name), type)]
                if classes:
                    success_modules.append((module_name, classes[0]))
                    print(f"⚠️  {module_name} -> {classes[0]} (expected {expected_class})")
                else:
                    failed_modules.append((module_name, "No classes found"))
                    print(f"❌ {module_name} -> No classes found")
                    
        except Exception as e:
            failed_modules.append((module_name, str(e)))
            print(f"❌ {module_name} -> Import error: {e}")
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"✅ Successfully loaded: {len(success_modules)}")
    print(f"❌ Failed to load: {len(failed_modules)}")
    
    if failed_modules:
        print("\n❌ FAILED MODULES:")
        for module, error in failed_modules:
            print(f"  {module}: {error}")
    
    return len(failed_modules) == 0

if __name__ == '__main__':
    success = test_module_loading()
    sys.exit(0 if success else 1)