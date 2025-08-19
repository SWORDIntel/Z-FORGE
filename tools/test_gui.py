#!/usr/bin/env python3
"""
Test script for Z-FORGE GUI
Tests GUI components without requiring X11
"""

import sys
import os
from pathlib import Path
import yaml
import multiprocessing

def test_build_specs():
    """Test that all build specifications exist and are valid"""
    print("Testing build specifications...")
    
    build_specs = {
        "Stable Build": "build_specs/build_spec_stable.yml",
        "Outside Packages Build": "build_specs/build_spec_outside_packages.yml", 
        "Full Featured Build": "build_specs/build_spec.yml",
        "No /tmp Build": "build_specs/build_spec_no_tmp.yml",
        "Proxmox Full Build": "build_specs/build_spec_proxmox_full.yml",
        "Proxmox 9 Build": "build_specs/build_spec_proxmox9.yml"
    }
    
    missing_specs = []
    invalid_specs = []
    
    for name, filename in build_specs.items():
        spec_path = Path(filename)
        if not spec_path.exists():
            missing_specs.append(f"{name} ({filename})")
            continue
            
        try:
            with open(spec_path, 'r') as f:
                spec_data = yaml.safe_load(f)
                # Check for required fields
                if 'name' not in spec_data:
                    invalid_specs.append(f"{name} - missing 'name' field")
                if 'version' not in spec_data:
                    invalid_specs.append(f"{name} - missing 'version' field")
                    
        except Exception as e:
            invalid_specs.append(f"{name} - YAML error: {str(e)}")
            
    if missing_specs:
        print("❌ Missing build specifications:")
        for spec in missing_specs:
            print(f"   - {spec}")
    else:
        print("✅ All build specifications found")
        
    if invalid_specs:
        print("❌ Invalid build specifications:")
        for spec in invalid_specs:
            print(f"   - {spec}")
    else:
        print("✅ All build specifications are valid")
        
    return len(missing_specs) == 0 and len(invalid_specs) == 0

def test_system_requirements():
    """Test system requirements for GUI"""
    print("\\nTesting system requirements...")
    
    requirements_met = True
    
    # Test Python modules
    required_modules = ['tkinter', 'yaml', 'psutil', 'threading', 'subprocess']
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module} module available")
        except ImportError:
            print(f"❌ {module} module missing")
            requirements_met = False
            
    # Test system info
    try:
        cpu_count = multiprocessing.cpu_count()
        print(f"✅ CPU cores detected: {cpu_count}")
    except:
        print("❌ Could not detect CPU cores")
        requirements_met = False
        
    # Test build.py exists
    if Path('build.py').exists():
        print("✅ build.py found")
    else:
        print("❌ build.py not found (wrong directory?)")
        requirements_met = False
        
    return requirements_met

def test_gui_imports():
    """Test GUI-specific imports"""
    print("\\nTesting GUI imports...")
    
    try:
        # Test basic tkinter
        import tkinter as tk
        print("✅ tkinter imported successfully")
        
        # Test ttk
        from tkinter import ttk
        print("✅ ttk imported successfully")
        
        # Test other tkinter components
        from tkinter import scrolledtext, messagebox, filedialog
        print("✅ tkinter dialogs imported successfully")
        
        # Test creating root window (without showing)
        root = tk.Tk()
        root.withdraw()  # Hide the window
        print("✅ tkinter root window created successfully")
        root.destroy()
        
        return True
        
    except Exception as e:
        print(f"❌ GUI import error: {str(e)}")
        return False

def test_validation_system():
    """Test validation system integration"""
    print("\\nTesting validation system...")
    
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, 'builder/modules/build_pipeline_validator.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Validation system working")
            if "100/100 passed" in result.stdout:
                print("✅ System validation: PERFECT")
            else:
                print("⚠️  System validation: Has warnings")
        else:
            print(f"❌ Validation system failed: {result.stderr}")
            return False
            
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Validation system timeout")
        return False
    except Exception as e:
        print(f"❌ Validation system error: {str(e)}")
        return False

def test_directory_structure():
    """Test required directory structure"""
    print("\\nTesting directory structure...")
    
    required_paths = [
        ('build.py', 'file'),
        ('builder/', 'dir'),
        ('builder/modules/', 'dir'),
        ('builder/modules/build_pipeline_validator.py', 'file'),
        ('scripts/', 'dir'),
        ('config/', 'dir')
    ]
    
    structure_ok = True
    
    for path, path_type in required_paths:
        path_obj = Path(path)
        if path_type == 'file' and path_obj.is_file():
            print(f"✅ {path} (file)")
        elif path_type == 'dir' and path_obj.is_dir():
            print(f"✅ {path} (directory)")
        else:
            print(f"❌ {path} ({path_type}) missing")
            structure_ok = False
            
    return structure_ok

def main():
    """Run all tests"""
    print("Z-FORGE GUI Test Suite")
    print("=" * 50)
    
    tests = [
        ("Build Specifications", test_build_specs),
        ("System Requirements", test_system_requirements), 
        ("GUI Imports", test_gui_imports),
        ("Validation System", test_validation_system),
        ("Directory Structure", test_directory_structure)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {str(e)}")
            results[test_name] = False
            
    # Summary
    print("\\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        
    print(f"\\nTests passed: {passed}/{total}")
    
    if passed == total:
        print("\\n🎉 ALL TESTS PASSED - GUI should work correctly!")
        print("\\n💡 To run the GUI:")
        print("   python3 scripts/legacy-gui/zforge_gui.py")
        return 0
    else:
        print(f"\\n⚠️  {total - passed} tests failed - GUI may not work properly")
        print("\\n🔧 Fix the failed tests before running the GUI")
        return 1

if __name__ == "__main__":
    sys.exit(main())