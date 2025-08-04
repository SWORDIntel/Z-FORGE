#!/usr/bin/env python3
"""Check all module files for class naming convention issues."""

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple

def to_class_name(module_name: str) -> str:
    """Convert module_name to expected ClassName."""
    # Handle special cases
    special_cases = {
        'gpg_bypass': 'GpgBypass',
        'iso_generation': 'IsoGeneration', 
        'zfs_build': 'ZfsBuild',
        'zfs_compression_optimizer': 'ZfsCompressionOptimizer',
        'zfs_encryption': 'ZfsEncryption',
        'zfs_pool_config': 'ZfsPoolConfig',
        'zfsbootmenu_install': 'ZfsbootmenuInstall',
        'zfs_boot_menu_install': 'ZfsBootMenuInstall'
    }
    
    if module_name in special_cases:
        return special_cases[module_name]
    
    # Standard conversion
    parts = module_name.split('_')
    return ''.join(word.capitalize() for word in parts)

def find_classes_in_file(file_path: Path) -> List[str]:
    """Find all class names defined in a Python file."""
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
        
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
        return classes
    except Exception as e:
        return []

def check_module_naming(project_root: Path) -> Dict[str, List[Dict]]:
    """Check all modules for naming convention issues."""
    results = {
        'correct': [],
        'incorrect': [],
        'missing': [],
        'multiple': []
    }
    
    # Find all module files
    module_dirs = [
        project_root / 'builder' / 'modules',
        project_root / 'calamares' / 'modules'
    ]
    
    for module_dir in module_dirs:
        if not module_dir.exists():
            continue
            
        for py_file in module_dir.rglob('*.py'):
            if py_file.name == '__init__.py' or '__pycache__' in str(py_file):
                continue
                
            module_name = py_file.stem
            expected_class = to_class_name(module_name)
            
            # Special case for main.py files
            if py_file.name == 'main.py':
                # Get parent directory name as module name
                module_name = py_file.parent.name
                expected_class = to_class_name(module_name)
            
            classes = find_classes_in_file(py_file)
            
            if not classes:
                results['missing'].append({
                    'file': str(py_file.relative_to(project_root)),
                    'module': module_name,
                    'expected': expected_class
                })
            elif len(classes) > 1:
                # Check if expected class is in the list
                if expected_class in classes:
                    results['correct'].append({
                        'file': str(py_file.relative_to(project_root)),
                        'module': module_name,
                        'class': expected_class
                    })
                else:
                    results['multiple'].append({
                        'file': str(py_file.relative_to(project_root)),
                        'module': module_name,
                        'expected': expected_class,
                        'found': classes
                    })
            else:
                actual_class = classes[0]
                if actual_class == expected_class:
                    results['correct'].append({
                        'file': str(py_file.relative_to(project_root)),
                        'module': module_name,
                        'class': actual_class
                    })
                else:
                    results['incorrect'].append({
                        'file': str(py_file.relative_to(project_root)),
                        'module': module_name,
                        'expected': expected_class,
                        'actual': actual_class
                    })
    
    return results

def main():
    """Main function."""
    project_root = Path('/opt/github/Z-FORGE')
    
    print("Checking all module files for naming convention issues...")
    print("=" * 70)
    
    results = check_module_naming(project_root)
    
    # Report incorrect names
    if results['incorrect']:
        print(f"\n❌ Found {len(results['incorrect'])} modules with incorrect class names:")
        for item in results['incorrect']:
            print(f"  {item['file']}")
            print(f"    Module: {item['module']}")
            print(f"    Expected: {item['expected']}")
            print(f"    Actual: {item['actual']}")
            print()
    
    # Report missing classes
    if results['missing']:
        print(f"\n⚠️  Found {len(results['missing'])} modules with no classes:")
        for item in results['missing']:
            print(f"  {item['file']}")
    
    # Report multiple classes
    if results['multiple']:
        print(f"\n⚠️  Found {len(results['multiple'])} modules with multiple classes:")
        for item in results['multiple']:
            print(f"  {item['file']}")
            print(f"    Expected: {item['expected']}")
            print(f"    Found: {', '.join(item['found'])}")
            print()
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"  ✅ Correct: {len(results['correct'])}")
    print(f"  ❌ Incorrect: {len(results['incorrect'])}")
    print(f"  ⚠️  Missing: {len(results['missing'])}")
    print(f"  ⚠️  Multiple: {len(results['multiple'])}")
    print(f"  📁 Total: {sum(len(v) for v in results.values())}")
    
    # List files that need fixing
    if results['incorrect']:
        print("\n🔧 Files that need class name fixes:")
        for item in results['incorrect']:
            print(f"  {item['file']}: {item['actual']} → {item['expected']}")

if __name__ == '__main__':
    main()