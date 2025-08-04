#!/usr/bin/env python3
"""Check for actual Python import errors."""

import ast
import importlib.util
import sys
from pathlib import Path
from typing import List, Dict, Set

def get_imports_from_file(file_path: Path) -> Set[str]:
    """Extract all imports from a Python file."""
    imports = set()
    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
    except:
        pass
    return imports

def can_import(module_name: str, project_root: Path) -> bool:
    """Check if a module can be imported."""
    # Standard library modules
    if module_name in sys.stdlib_module_names:
        return True
        
    # Try to import it
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            return True
    except:
        pass
        
    # Check local modules
    if module_name.startswith('builder.'):
        parts = module_name.split('.')
        path = project_root
        for part in parts:
            path = path / part
        if path.with_suffix('.py').exists() or (path / '__init__.py').exists():
            return True
            
    return False

def main():
    project_root = Path('/opt/github/Z-FORGE')
    
    # Add project root to Python path
    sys.path.insert(0, str(project_root))
    
    print("Checking Python imports in active files...")
    print("=" * 70)
    
    # Find active Python files
    active_dirs = [
        project_root / 'builder',
        project_root / 'scripts' / 'test',
        project_root / 'scripts' / 'analysis',
        project_root / 'scripts' / 'agents'
    ]
    
    import_errors = []
    
    for dir_path in active_dirs:
        if not dir_path.exists():
            continue
            
        for py_file in dir_path.rglob('*.py'):
            if '__pycache__' in str(py_file) or 'backup' in str(py_file):
                continue
                
            imports = get_imports_from_file(py_file)
            for imp in imports:
                if not can_import(imp, project_root):
                    import_errors.append({
                        'file': str(py_file.relative_to(project_root)),
                        'import': imp
                    })
                    
    # Group by import
    import_groups = {}
    for error in import_errors:
        imp = error['import']
        if imp not in import_groups:
            import_groups[imp] = []
        import_groups[imp].append(error['file'])
        
    if import_groups:
        print(f"❌ Found {len(import_errors)} import errors:\n")
        for imp, files in sorted(import_groups.items()):
            print(f"Missing module: '{imp}'")
            for f in files[:3]:
                print(f"  - {f}")
            if len(files) > 3:
                print(f"  ... and {len(files) - 3} more")
            print()
    else:
        print("✅ No import errors found in active Python files!")
        
    # Check for common missing dependencies
    print("\nChecking for commonly needed packages...")
    common_packages = {
        'requests': 'HTTP library',
        'yaml': 'YAML parser',
        'gi': 'GTK bindings',
        'libcalamares': 'Calamares installer'
    }
    
    for pkg, desc in common_packages.items():
        if not can_import(pkg, project_root):
            print(f"⚠️  {pkg} ({desc}) - Not installed but may be needed")

if __name__ == '__main__':
    main()