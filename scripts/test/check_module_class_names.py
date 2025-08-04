#!/usr/bin/env python3
"""
Check all module class names match what the module loader expects
"""

import os
import sys
import ast
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def get_class_names_from_file(file_path):
    """Extract class names from a Python file"""
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
        
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
        return classes
    except:
        return []

def expected_class_names(module_name):
    """Generate expected class names based on module loader logic"""
    # Direct match
    names = [module_name]
    
    # CamelCase from snake_case
    camel_case = "".join(word.capitalize() for word in module_name.split('_'))
    names.append(camel_case)
    
    # Title case without underscores
    title_case = module_name.title().replace("_", "")
    names.append(title_case)
    
    return list(set(names))  # Remove duplicates

def check_modules():
    """Check all modules in build_spec.yml"""
    import yaml
    
    # Load build specs
    build_specs = [
        'build_spec.yml',
        'build_spec_proxmox_full.yml', 
        'build_spec_no_tmp.yml'
    ]
    
    all_modules = set()
    
    for spec_file in build_specs:
        spec_path = project_root / spec_file
        if spec_path.exists():
            with open(spec_path, 'r') as f:
                spec = yaml.safe_load(f)
                if 'modules' in spec:
                    for module in spec['modules']:
                        if module.get('enabled', True):
                            all_modules.add(module['name'])
    
    print("Checking module class names...")
    print("=" * 80)
    
    issues = []
    modules_dir = project_root / "builder" / "modules"
    
    for module_name in sorted(all_modules):
        module_file = modules_dir / f"{module_name}.py"
        
        if not module_file.exists():
            print(f"❌ {module_name}: Module file not found!")
            issues.append(f"{module_name}: File not found")
            continue
        
        # Get actual class names
        actual_classes = get_class_names_from_file(module_file)
        
        # Get expected class names
        expected = expected_class_names(module_name)
        
        # Check if any expected name matches
        found = False
        for exp in expected:
            if exp in actual_classes:
                print(f"✅ {module_name}: Found class '{exp}'")
                found = True
                break
        
        if not found:
            print(f"❌ {module_name}: No matching class found!")
            print(f"   Expected one of: {expected}")
            print(f"   Found classes: {actual_classes}")
            issues.append(f"{module_name}: Expected {expected}, found {actual_classes}")
    
    print("\n" + "=" * 80)
    
    if issues:
        print(f"\n❌ Found {len(issues)} issues:\n")
        for issue in issues:
            print(f"  - {issue}")
        
        print("\nFixes needed:")
        print("1. Rename classes to match expected names")
        print("2. Or update module names in build_spec.yml")
    else:
        print("\n✅ All module class names are correct!")
    
    return len(issues)

if __name__ == "__main__":
    sys.exit(check_modules())