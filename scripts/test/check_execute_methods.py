#!/usr/bin/env python3
"""Check which modules are missing execute() methods."""

import ast
from pathlib import Path
from typing import Dict, List

def check_module_for_execute(file_path: Path) -> Dict:
    """Check if a module has execute() method."""
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
            
        # Find all classes
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Get methods in this class
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({
                    'name': node.name,
                    'methods': methods,
                    'has_execute': 'execute' in methods,
                    'has_run': 'run' in methods
                })
                
        return {
            'file': str(file_path),
            'classes': classes
        }
    except Exception as e:
        return {
            'file': str(file_path),
            'error': str(e)
        }

def main():
    project_root = Path('/opt/github/Z-FORGE')
    modules_dir = project_root / 'builder' / 'modules'
    
    print("Checking modules for execute() methods...")
    print("=" * 70)
    
    # Get all module files
    module_files = []
    for py_file in modules_dir.rglob('*.py'):
        if '__pycache__' not in str(py_file) and py_file.name != '__init__.py':
            module_files.append(py_file)
            
    missing_execute = []
    has_execute = []
    is_calamares = []
    is_special = []
    
    for module_file in sorted(module_files):
        result = check_module_for_execute(module_file)
        
        if 'error' in result:
            continue
            
        # Skip if no classes
        if not result.get('classes'):
            continue
            
        # Get the main class (usually first one)
        main_class = result['classes'][0]
        rel_path = module_file.relative_to(project_root)
        
        # Check if it's a Calamares module
        if 'calamares' in str(module_file) or '/main.py' in str(module_file):
            is_calamares.append((rel_path, main_class['name']))
        # Check if it has execute or run
        elif main_class['has_execute'] or main_class['has_run']:
            has_execute.append((rel_path, main_class['name']))
        # Check if it's a special module (like validators, helpers)
        elif any(x in main_class['name'].lower() for x in ['validator', 'database', 'profile', 'widget', 'gui']):
            is_special.append((rel_path, main_class['name']))
        else:
            missing_execute.append((rel_path, main_class['name']))
            
    # Report results
    print(f"\n✅ Modules with execute() method: {len(has_execute)}")
    for path, class_name in has_execute[:5]:
        print(f"  {path} - {class_name}")
    if len(has_execute) > 5:
        print(f"  ... and {len(has_execute) - 5} more")
        
    print(f"\n🔵 Calamares modules (different pattern): {len(is_calamares)}")
    for path, class_name in is_calamares[:5]:
        print(f"  {path} - {class_name}")
        
    print(f"\n🟡 Special modules (helpers/validators): {len(is_special)}")
    for path, class_name in is_special[:5]:
        print(f"  {path} - {class_name}")
        
    print(f"\n❌ Modules missing execute() method: {len(missing_execute)}")
    for path, class_name in missing_execute:
        print(f"  {path} - {class_name}")
        
    # List the modules that need fixing
    if missing_execute:
        print("\n🔧 Modules that need execute() method added:")
        for path, class_name in missing_execute:
            if 'integrated_build_orchestrator' in str(path):
                print(f"  {path} - Orchestrator (may be OK)")
            elif 'kernel_acquisition_workaround' in str(path):
                print(f"  {path} - Workaround module")
            else:
                print(f"  {path} - {class_name}")

if __name__ == '__main__':
    main()