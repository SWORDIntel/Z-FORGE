#!/usr/bin/env python3
"""
Add appropriate timeouts to subprocess.run calls in builder/modules/*.py
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Tuple
import shutil

class SubprocessTimeoutAdder(ast.NodeTransformer):
    def __init__(self, filename: str):
        self.filename = filename
        self.modified = False
        
    def get_timeout_for_command(self, node: ast.Call) -> int:
        """Determine appropriate timeout based on command arguments"""
        # Try to extract command information
        cmd_str = ""
        
        if node.args:
            first_arg = node.args[0]
            
            # If it's a list literal, extract the commands
            if isinstance(first_arg, ast.List):
                for elt in first_arg.elts:
                    if isinstance(elt, ast.Constant):
                        cmd_str += str(elt.value) + " "
                    elif isinstance(elt, ast.Str):
                        cmd_str += elt.s + " "
                        
            # If it's a variable or expression, we'll use a default
            else:
                # Try to get string representation
                try:
                    cmd_str = ast.unparse(first_arg)
                except:
                    cmd_str = ""
                    
        cmd_lower = cmd_str.lower()
        
        # Download operations - 5 minutes
        if any(x in cmd_lower for x in ['wget', 'git clone', 'curl']):
            return 300
            
        # Package installations - 5 minutes
        if any(x in cmd_lower for x in ['apt-get install', 'dpkg -i', 'apt install']):
            return 300
            
        # Compilation/build operations - 10 minutes
        if any(x in cmd_lower for x in ['make', 'build', './configure']):
            return 600
            
        # ISO/squashfs operations - 10 minutes
        if any(x in cmd_lower for x in ['mksquashfs', 'xorriso', 'mkisofs']):
            return 600
            
        # Archive operations - 2 minutes
        if any(x in cmd_lower for x in ['tar ', 'unzip ', 'zip ']):
            return 120
            
        # Chroot operations
        if 'chroot' in cmd_lower:
            # Package management in chroot - 5 minutes
            if any(x in cmd_lower for x in ['apt-get', 'dpkg', 'dracut', 'update-initramfs']):
                return 300
            # Other chroot operations - 1 minute
            else:
                return 60
                
        # Mount/unmount operations - 30 seconds
        if any(x in cmd_lower for x in ['mount', 'umount', 'mountpoint']):
            return 30
            
        # ZFS operations
        if any(x in cmd_lower for x in ['zpool', 'zfs']):
            if 'import' in cmd_lower or 'export' in cmd_lower:
                return 60  # Import/export can take longer
            else:
                return 30
                
        # Git operations (non-clone) - 1 minute
        if 'git ' in cmd_lower and 'clone' not in cmd_lower:
            return 60
            
        # Default - 30 seconds
        return 30
        
    def visit_Call(self, node: ast.Call) -> ast.Call:
        """Visit a function call node"""
        # Check if this is subprocess.run
        if (isinstance(node.func, ast.Attribute) and 
            node.func.attr == 'run' and
            isinstance(node.func.value, ast.Name) and
            node.func.value.id == 'subprocess'):
            
            # Check if timeout is already present
            has_timeout = any(kw.arg == 'timeout' for kw in node.keywords)
            
            if not has_timeout:
                # Add timeout
                timeout_value = self.get_timeout_for_command(node)
                timeout_kw = ast.keyword(arg='timeout', value=ast.Constant(value=timeout_value))
                node.keywords.append(timeout_kw)
                self.modified = True
                
        return self.generic_visit(node)

def fix_file(filepath: Path) -> Tuple[bool, List[str]]:
    """Fix subprocess.run calls in a single file"""
    changes = []
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Parse the AST
        tree = ast.parse(content)
        
        # Transform the AST
        transformer = SubprocessTimeoutAdder(str(filepath))
        new_tree = transformer.visit(tree)
        
        if transformer.modified:
            # Generate new code
            new_content = ast.unparse(new_tree)
            
            # Backup original file
            backup_path = filepath.with_suffix(filepath.suffix + '.bak')
            shutil.copy2(filepath, backup_path)
            
            # Write new content
            with open(filepath, 'w') as f:
                f.write(new_content)
                
            # Find what changed
            import difflib
            diff = list(difflib.unified_diff(
                content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=str(filepath),
                tofile=str(filepath)
            ))
            
            for line in diff:
                if line.startswith('+') and 'timeout=' in line:
                    changes.append(line.strip())
                    
            return True, changes
            
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}")
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        
    return False, changes

def process_all_files(base_path: Path = Path("builder/modules")):
    """Process all Python files in the directory"""
    fixed_files = []
    all_changes = {}
    
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                
                # Check if file has subprocess.run
                try:
                    with open(filepath, 'r') as f:
                        if 'subprocess.run' in f.read():
                            print(f"Processing {filepath}...")
                            fixed, changes = fix_file(filepath)
                            
                            if fixed:
                                fixed_files.append(filepath)
                                all_changes[str(filepath)] = changes
                                print(f"  ✓ Fixed ({len(changes)} timeouts added)")
                            else:
                                print(f"  - No changes needed or error occurred")
                except:
                    pass
                    
    return fixed_files, all_changes

def main():
    """Main function"""
    print("Adding timeouts to subprocess.run calls...")
    print("=" * 60)
    
    fixed_files, all_changes = process_all_files()
    
    print("\n" + "=" * 60)
    print(f"Summary: Fixed {len(fixed_files)} files")
    
    if fixed_files:
        print("\nFiles modified:")
        for filepath in sorted(fixed_files):
            print(f"  - {filepath}")
            if str(filepath) in all_changes:
                for change in all_changes[str(filepath)][:3]:  # Show first 3 changes
                    print(f"    {change}")
                if len(all_changes[str(filepath)]) > 3:
                    print(f"    ... and {len(all_changes[str(filepath)]) - 3} more")
                    
        print("\nBackup files created with .bak extension")
        print("\nTo review changes, use: diff <file> <file>.bak")

if __name__ == "__main__":
    main()