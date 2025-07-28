#!/usr/bin/env python3
"""
Simple script to add timeouts to subprocess.run calls
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
import shutil

class TimeoutFixer:
    def __init__(self):
        self.timeout_rules = {
            # Download operations - 5 minutes
            'wget': 300,
            'git clone': 300,
            'curl': 300,
            
            # Package installations - 5 minutes
            'apt-get install': 300,
            'dpkg -i': 300,
            'apt install': 300,
            
            # Compilation - 10 minutes
            'make': 600,
            './configure': 600,
            'mksquashfs': 600,
            'xorriso': 600,
            
            # Chroot with package management - 5 minutes
            'chroot.*apt-get': 300,
            'chroot.*dpkg': 300,
            'chroot.*dracut': 300,
            'chroot.*update-initramfs': 300,
            
            # Archive operations - 2 minutes
            'tar ': 120,
            'unzip': 120,
            
            # ZFS import/export - 1 minute
            'zpool import': 60,
            'zpool export': 60,
            'zfs import': 60,
            
            # Git operations - 1 minute
            'git ': 60,
            
            # Chroot other - 1 minute
            'chroot': 60,
            
            # Mount operations - 30 seconds
            'mount': 30,
            'umount': 30,
            'mountpoint': 30,
            
            # Default - 30 seconds
            'default': 30
        }
        
    def get_timeout(self, call_text: str) -> int:
        """Determine appropriate timeout for a subprocess.run call"""
        call_lower = call_text.lower()
        
        # Check rules in order
        for pattern, timeout in self.timeout_rules.items():
            if pattern != 'default' and re.search(pattern, call_lower):
                return timeout
                
        return self.timeout_rules['default']
        
    def add_timeout_to_call(self, call_text: str, timeout: int) -> str:
        """Add timeout parameter to a subprocess.run call"""
        # Find the last closing parenthesis
        # Handle multi-line calls
        
        # Check if timeout already exists
        if 'timeout=' in call_text:
            return call_text
            
        # Find position to insert timeout
        # Look for the last argument or closing paren
        lines = call_text.split('\n')
        last_line_idx = len(lines) - 1
        
        # Find the line with closing paren
        for i in range(len(lines) - 1, -1, -1):
            if ')' in lines[i]:
                last_line_idx = i
                break
                
        last_line = lines[last_line_idx]
        
        # Insert timeout before the closing paren
        paren_pos = last_line.rfind(')')
        
        # Check if we need a comma
        # Look back from the paren position
        needs_comma = False
        for j in range(paren_pos - 1, -1, -1):
            if last_line[j] not in ' \t':
                if last_line[j] != '(' and last_line[j] != ',':
                    needs_comma = True
                break
                
        # Build the new line
        if needs_comma:
            new_line = last_line[:paren_pos] + f", timeout={timeout}" + last_line[paren_pos:]
        else:
            new_line = last_line[:paren_pos] + f"timeout={timeout}" + last_line[paren_pos:]
            
        lines[last_line_idx] = new_line
        
        return '\n'.join(lines)
        
    def fix_file(self, filepath: Path) -> Tuple[bool, int]:
        """Fix all subprocess.run calls in a file"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                
            original_content = content
            
            # Find all subprocess.run calls
            # This regex captures subprocess.run calls including multi-line ones
            pattern = r'subprocess\.run\s*\([^)]*(?:\([^)]*\)[^)]*)*\)'
            
            changes_made = 0
            
            def replace_call(match):
                nonlocal changes_made
                call_text = match.group(0)
                
                if 'timeout=' not in call_text:
                    timeout = self.get_timeout(call_text)
                    new_call = self.add_timeout_to_call(call_text, timeout)
                    if new_call != call_text:
                        changes_made += 1
                    return new_call
                return call_text
                
            # Replace all calls
            new_content = re.sub(pattern, replace_call, content, flags=re.DOTALL)
            
            if new_content != original_content:
                # Backup original
                backup_path = filepath.with_suffix(filepath.suffix + '.backup')
                shutil.copy2(filepath, backup_path)
                
                # Write new content
                with open(filepath, 'w') as f:
                    f.write(new_content)
                    
                return True, changes_made
                
            return False, 0
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            return False, 0
            
    def process_directory(self, base_path: Path = Path("builder/modules")):
        """Process all Python files in directory"""
        fixed_files = []
        total_changes = 0
        
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith('.py'):
                    filepath = Path(root) / file
                    
                    # Quick check if file needs processing
                    try:
                        with open(filepath, 'r') as f:
                            if 'subprocess.run' in f.read():
                                print(f"Processing {filepath}...")
                                fixed, changes = self.fix_file(filepath)
                                
                                if fixed:
                                    fixed_files.append((filepath, changes))
                                    total_changes += changes
                                    print(f"  ✓ Fixed {changes} calls")
                    except:
                        pass
                        
        return fixed_files, total_changes

def main():
    """Main function"""
    print("Adding timeouts to subprocess.run calls")
    print("=" * 60)
    
    fixer = TimeoutFixer()
    fixed_files, total_changes = fixer.process_directory()
    
    print("\n" + "=" * 60)
    print(f"Summary: Fixed {len(fixed_files)} files with {total_changes} total changes")
    
    if fixed_files:
        print("\nFiles modified:")
        for filepath, changes in sorted(fixed_files):
            print(f"  {filepath}: {changes} timeouts added")
            
        print("\nBackup files created with .backup extension")
        print("To review changes: diff <file> <file>.backup")
        print("\nTimeout values used:")
        print("  - Quick commands (ls, mkdir, etc): 30s")
        print("  - Package installations (apt-get): 300s (5 min)")
        print("  - Compilation tasks (make, build): 600s (10 min)")

if __name__ == "__main__":
    main()