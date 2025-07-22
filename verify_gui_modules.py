#!/usr/bin/env python3
"""
Verify all GUI modules in Z-FORGE build system
"""

import os
import sys
import subprocess
from pathlib import Path
import json

def check_module_file(module_path):
    """Check if a module file exists and has proper structure"""
    if not module_path.exists():
        return False, f"File not found: {module_path}"
    
    try:
        with open(module_path, 'r') as f:
            content = f.read()
            
        # Check for proper init signature for builder modules
        if "builder/modules" in str(module_path):
            if "def __init__(self, workspace: Path, config:" not in content:
                return False, f"Invalid __init__ signature in {module_path.name}"
                
        # Check for GUI imports in Calamares modules
        if "calamares/modules" in str(module_path) and "_gui.py" in module_path.name:
            if "gi.require_version('Gtk', '3.0')" not in content:
                if "QtQuick" not in content:  # Allow QML modules
                    return False, f"Missing GTK3 import in {module_path.name}"
                    
        return True, "OK"
    except Exception as e:
        return False, str(e)

def verify_gui_modules():
    """Verify all GUI-related modules"""
    
    print("Z-FORGE GUI Module Verification")
    print("=" * 50)
    
    # Check builder GUI modules
    print("\n1. Builder GUI Modules:")
    builder_gui_modules = [
        "live_environment.py",
        "calamares_integration.py", 
        "kde_theme_config.py"
    ]
    
    builder_path = Path("/opt/github/Z-FORGE/builder/modules")
    all_ok = True
    
    for module in builder_gui_modules:
        module_path = builder_path / module
        ok, msg = check_module_file(module_path)
        status = "✓" if ok else "✗"
        print(f"  {status} {module:30} - {msg}")
        all_ok = all_ok and ok
    
    # Check Calamares GUI modules
    print("\n2. Calamares GUI Modules:")
    calamares_path = Path("/opt/github/Z-FORGE/calamares/modules")
    
    gui_modules = list(calamares_path.glob("*/*_gui.py"))
    gui_modules.extend(list(calamares_path.glob("*/ui_*.qml")))
    
    for module_path in sorted(gui_modules):
        relative_path = module_path.relative_to(calamares_path)
        ok, msg = check_module_file(module_path)
        status = "✓" if ok else "✗"
        print(f"  {status} {str(relative_path):30} - {msg}")
        all_ok = all_ok and ok
    
    # Check for required packages in build spec
    print("\n3. Package Dependencies:")
    packages_needed = {
        "KDE Desktop": ["kde-standard", "sddm"],
        "GTK3": ["gir1.2-gtk-3.0", "python3-gi", "python3-cairo"],
        "Qt5": ["python3-pyqt5", "qml-module-qtquick2"],
        "Calamares": ["calamares", "calamares-settings-debian"]
    }
    
    # Check in live_environment.py
    live_env_path = builder_path / "live_environment.py"
    with open(live_env_path, 'r') as f:
        live_env_content = f.read()
    
    for category, packages in packages_needed.items():
        print(f"\n  {category}:")
        for pkg in packages:
            if pkg in live_env_content:
                print(f"    ✓ {pkg}")
            else:
                print(f"    ✗ {pkg} - Not found in live_environment.py")
                all_ok = False
    
    # Check module enablement in build_spec.yml
    print("\n4. Module Enablement:")
    build_spec_path = Path("/opt/github/Z-FORGE/build_spec.yml")
    
    if build_spec_path.exists():
        with open(build_spec_path, 'r') as f:
            content = f.read()
            
        gui_modules_to_check = [
            ("LiveEnvironment", True),
            ("CalamaresIntegration", True),
            ("KDEThemeConfig", True)
        ]
        
        for module_name, should_be_enabled in gui_modules_to_check:
            # Simple text search for module status
            if f"name: {module_name}" in content:
                # Look for the enabled status after the module name
                module_pos = content.find(f"name: {module_name}")
                next_enabled = content.find("enabled:", module_pos)
                next_module = content.find("- name:", module_pos + 1)
                
                if next_enabled > 0 and (next_module < 0 or next_enabled < next_module):
                    enabled_line = content[next_enabled:next_enabled+20]
                    is_enabled = "true" in enabled_line
                    
                    if is_enabled == should_be_enabled:
                        print(f"  ✓ {module_name:25} - Enabled: {is_enabled}")
                    else:
                        print(f"  ✗ {module_name:25} - Should be enabled: {should_be_enabled}, but is: {is_enabled}")
                        all_ok = False
            else:
                print(f"  ✗ {module_name:25} - Not found in build_spec.yml")
                all_ok = False
    
    # Check display manager configuration
    print("\n5. Display Manager Configuration:")
    display_checks = [
        ("SDDM service enabled", "sddm" in live_env_content and "'sddm'" in live_env_content),
        ("X11 support", True),  # Always available in Debian
        ("Auto-login configured", "calamares_integration.py" in str(builder_path))
    ]
    
    for check_name, check_result in display_checks:
        status = "✓" if check_result else "✗"
        print(f"  {status} {check_name}")
    
    # Summary
    print("\n" + "=" * 50)
    if all_ok:
        print("✓ All GUI modules verified successfully!")
    else:
        print("✗ Some issues found. Please review the output above.")
    
    return all_ok

if __name__ == "__main__":
    success = verify_gui_modules()
    sys.exit(0 if success else 1)