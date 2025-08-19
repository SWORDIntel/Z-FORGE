#!/usr/bin/env python3
"""Comprehensive issue checker for Z-FORGE build system."""

import ast
import json
import yaml
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple
import importlib.util
import sys

class ComprehensiveChecker:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues = {
            'syntax_errors': [],
            'import_errors': [],
            'missing_methods': [],
            'config_errors': [],
            'missing_files': [],
            'circular_imports': [],
            'undefined_names': []
        }
        
    def check_syntax(self, file_path: Path) -> List[Dict]:
        """Check Python file for syntax errors."""
        errors = []
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            compile(content, str(file_path), 'exec')
        except SyntaxError as e:
            errors.append({
                'file': str(file_path.relative_to(self.project_root)),
                'line': e.lineno,
                'error': str(e.msg)
            })
        except Exception as e:
            errors.append({
                'file': str(file_path.relative_to(self.project_root)),
                'error': str(e)
            })
        return errors
        
    def check_imports(self, file_path: Path) -> List[Dict]:
        """Check for import errors."""
        errors = []
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self._can_import(alias.name):
                            errors.append({
                                'file': str(file_path.relative_to(self.project_root)),
                                'line': node.lineno,
                                'import': alias.name,
                                'type': 'missing_module'
                            })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    if module and not self._can_import(module):
                        errors.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'line': node.lineno,
                            'import': module,
                            'type': 'missing_module'
                        })
        except Exception as e:
            pass
        return errors
        
    def _can_import(self, module_name: str) -> bool:
        """Check if a module can be imported."""
        if module_name.startswith('.'):
            return True  # Relative imports need context
        try:
            spec = importlib.util.find_spec(module_name)
            return spec is not None
        except (ImportError, ModuleNotFoundError):
            # Check if it's a local module
            local_paths = [
                self.project_root / 'builder',
                self.project_root / 'builder' / 'modules',
                self.project_root / 'builder' / 'core'
            ]
            for path in local_paths:
                if (path / f"{module_name}.py").exists():
                    return True
                if (path / module_name).is_dir() and (path / module_name / "__init__.py").exists():
                    return True
            return False
            
    def check_module_methods(self, file_path: Path) -> List[Dict]:
        """Check if module has required execute() method."""
        errors = []
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
                
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node)
                    
            if classes:
                # Check main class (should have execute method)
                main_class = classes[0]  # Assume first class is main
                methods = [n.name for n in main_class.body if isinstance(n, ast.FunctionDef)]
                
                if 'execute' not in methods and 'run' not in methods:
                    # Check if it's a Calamares module (different pattern)
                    if not any(m in methods for m in ['name', 'run', 'setConfigurationMap']):
                        errors.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'class': main_class.name,
                            'missing': 'execute() or run() method'
                        })
        except Exception:
            pass
        return errors
        
    def check_yaml_configs(self) -> List[Dict]:
        """Check all YAML configuration files."""
        errors = []
        for yaml_file in self.project_root.glob("*.yml"):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)
                    
                # Check if it's a build spec
                if 'builder_config' in data and 'modules' in data:
                    # Validate module references
                    for module in data['modules']:
                        module_name = module.get('name', module)
                        if isinstance(module_name, str):
                            module_path = self.project_root / 'builder' / 'modules' / f"{module_name}.py"
                            if not module_path.exists():
                                errors.append({
                                    'file': yaml_file.name,
                                    'error': f'Module not found: {module_name}',
                                    'type': 'missing_module'
                                })
            except Exception as e:
                errors.append({
                    'file': yaml_file.name,
                    'error': str(e),
                    'type': 'parse_error'
                })
        return errors
        
    def check_undefined_names(self, file_path: Path) -> List[Dict]:
        """Check for undefined variable names."""
        errors = []
        try:
            # Run pyflakes to check for undefined names
            result = subprocess.run(
                ['python3', '-m', 'pyflakes', str(file_path)],
                capture_output=True,
                text=True
            )
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if 'undefined name' in line:
                        errors.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'error': line.split(':', 2)[-1].strip()
                        })
        except Exception:
            pass
        return errors
        
    def run_all_checks(self):
        """Run all checks on the project."""
        print("🔍 Running comprehensive checks on Z-FORGE build system...")
        print("=" * 70)
        
        # Check Python files
        python_files = list(self.project_root.rglob("*.py"))
        total_files = len(python_files)
        
        print(f"\nChecking {total_files} Python files...")
        
        for i, py_file in enumerate(python_files):
            if '__pycache__' in str(py_file):
                continue
                
            # Progress indicator
            if i % 10 == 0:
                print(f"  Progress: {i}/{total_files}", end='\r')
                
            # Syntax check
            syntax_errors = self.check_syntax(py_file)
            if syntax_errors:
                self.issues['syntax_errors'].extend(syntax_errors)
                
            # Import check
            import_errors = self.check_imports(py_file)
            if import_errors:
                self.issues['import_errors'].extend(import_errors)
                
            # Module method check
            if 'modules' in str(py_file) and py_file.name != '__init__.py':
                method_errors = self.check_module_methods(py_file)
                if method_errors:
                    self.issues['missing_methods'].extend(method_errors)
                    
            # Undefined names check
            undefined_errors = self.check_undefined_names(py_file)
            if undefined_errors:
                self.issues['undefined_names'].extend(undefined_errors)
                
        print(f"  Progress: {total_files}/{total_files} - Done!")
        
        # Check YAML configs
        print("\nChecking YAML configuration files...")
        config_errors = self.check_yaml_configs()
        if config_errors:
            self.issues['config_errors'].extend(config_errors)
            
        # Report results
        self.report_results()
        
    def report_results(self):
        """Report all found issues."""
        print("\n" + "=" * 70)
        print("📊 CHECK RESULTS")
        print("=" * 70)
        
        total_issues = sum(len(v) for v in self.issues.values())
        
        if total_issues == 0:
            print("✅ No issues found! The build system appears to be clean.")
            return
            
        print(f"❌ Found {total_issues} total issues:\n")
        
        # Syntax errors
        if self.issues['syntax_errors']:
            print(f"🔴 Syntax Errors ({len(self.issues['syntax_errors'])})")
            for error in self.issues['syntax_errors'][:5]:
                print(f"  {error['file']}:{error.get('line', '?')} - {error['error']}")
            if len(self.issues['syntax_errors']) > 5:
                print(f"  ... and {len(self.issues['syntax_errors']) - 5} more")
            print()
            
        # Import errors
        if self.issues['import_errors']:
            print(f"🟠 Import Errors ({len(self.issues['import_errors'])})")
            # Group by import
            import_groups = {}
            for error in self.issues['import_errors']:
                imp = error['import']
                if imp not in import_groups:
                    import_groups[imp] = []
                import_groups[imp].append(error['file'])
                
            for imp, files in list(import_groups.items())[:5]:
                print(f"  Missing: '{imp}' in {len(files)} file(s)")
                for file in files[:2]:
                    print(f"    - {file}")
            print()
            
        # Missing methods
        if self.issues['missing_methods']:
            print(f"🟡 Missing Methods ({len(self.issues['missing_methods'])})")
            for error in self.issues['missing_methods'][:5]:
                print(f"  {error['file']} - {error['class']} missing {error['missing']}")
            if len(self.issues['missing_methods']) > 5:
                print(f"  ... and {len(self.issues['missing_methods']) - 5} more")
            print()
            
        # Config errors
        if self.issues['config_errors']:
            print(f"🟣 Configuration Errors ({len(self.issues['config_errors'])})")
            for error in self.issues['config_errors']:
                print(f"  {error['file']} - {error['error']}")
            print()
            
        # Undefined names
        if self.issues['undefined_names']:
            print(f"🔵 Undefined Names ({len(self.issues['undefined_names'])})")
            for error in self.issues['undefined_names'][:5]:
                print(f"  {error['file']} - {error['error']}")
            if len(self.issues['undefined_names']) > 5:
                print(f"  ... and {len(self.issues['undefined_names']) - 5} more")
            print()
            
        # Summary
        print("=" * 70)
        print("📈 SUMMARY")
        print("=" * 70)
        for issue_type, issues in self.issues.items():
            if issues:
                print(f"  {issue_type}: {len(issues)}")
                
def main():
    project_root = Path('/opt/github/Z-FORGE')
    checker = ComprehensiveChecker(project_root)
    checker.run_all_checks()
    
if __name__ == '__main__':
    main()