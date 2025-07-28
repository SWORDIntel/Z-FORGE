#!/usr/bin/env python3
"""
Fix subprocess.run calls by adding appropriate timeouts
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
import shutil
import sys

class SubprocessTimeoutFixer:
    def __init__(self, base_path: str = "builder/modules"):
        self.base_path = Path(base_path)
        self.fixed_files = []
        
    def categorize_command(self, cmd_text: str) -> int:
        """Return appropriate timeout based on command"""
        cmd_lower = cmd_text.lower()
        
        # Download operations - 5 minutes
        if any(x in cmd_lower for x in ['wget', 'git clone', 'git fetch', 'curl']):
            return 300
            
        # Package installations - 5 minutes
        if any(x in cmd_lower for x in ['apt-get install', 'dpkg -i', 'apt install', 'pip install']):
            return 300
            
        # Compilation/build operations - 10 minutes
        if any(x in cmd_lower for x in ['make', 'build', 'compile', './configure', 'setup.py']):
            return 600
            
        # Archive operations - 2 minutes
        if any(x in cmd_lower for x in ['tar ', 'zip ', 'unzip ', 'gzip']):
            return 120
            
        # Chroot operations
        if 'chroot' in cmd_lower:
            # Package management in chroot - 5 minutes
            if any(x in cmd_lower for x in ['apt-get', 'dpkg', 'apt ', 'pip']):
                return 300
            # Dracut/initramfs operations - 5 minutes
            elif any(x in cmd_lower for x in ['dracut', 'update-initramfs', 'mkinitramfs']):
                return 300
            # Other chroot operations - 1 minute
            else:
                return 60
                
        # Mount/unmount operations - 30 seconds
        if any(x in cmd_lower for x in ['mount', 'umount', 'mountpoint']):
            return 30
            
        # File system operations - 30 seconds
        if any(x in cmd_lower for x in ['mkdir', 'chmod', 'chown', 'rm -', 'cp ', 'mv ', 'ls ', 'find ', 'sudo mkdir', 'sudo chmod', 'sudo rm']):
            return 30
            
        # System info commands - 30 seconds
        if any(x in cmd_lower for x in ['lsblk', 'lspci', 'lsmod', 'dmidecode', 'which', 'modprobe', 'systemd-detect-virt', 'ipmi-fru']):
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
            
        # ISO/squashfs operations - 10 minutes
        if any(x in cmd_lower for x in ['mksquashfs', 'xorriso', 'mkisofs']):
            return 600
            
        # Default - 30 seconds
        return 30
        
    def fix_subprocess_call(self, content: str, call_match: re.Match) -> str:
        """Fix a single subprocess.run call by adding timeout"""
        call_text = call_match.group(0)
        
        # Skip if already has timeout
        if 'timeout' in call_text:
            return call_text
            
        # Determine appropriate timeout
        timeout = self.categorize_command(call_text)
        
        # Find the closing parenthesis
        # We need to properly handle nested parentheses
        paren_count = 0
        start = call_match.start()
        pos = start + len('subprocess.run(')
        
        while pos < len(content):
            if content[pos] == '(':
                paren_count += 1
            elif content[pos] == ')':
                if paren_count == 0:
                    # Found the closing parenthesis
                    break
                paren_count -= 1
            pos += 1
            
        if pos >= len(content):
            # Couldn't find closing parenthesis
            return call_text
            
        # Insert timeout parameter before closing parenthesis
        # Check if we need a comma
        insert_pos = pos
        
        # Look back to see if we need a comma
        i = pos - 1
        while i > start and content[i].isspace():
            i -= 1
            
        if i > start and content[i] not in ',(':
            # Need to add comma
            new_call = content[start:insert_pos] + f", timeout={timeout}" + content[insert_pos:]
        else:
            # Already has trailing comma or is empty
            new_call = content[start:insert_pos] + f"timeout={timeout}" + content[insert_pos:]
            
        return new_call
        
    def fix_file(self, filepath: Path) -> bool:
        """Fix all subprocess.run calls in a file"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                
            original_content = content
            
            # Find all subprocess.run calls
            pattern = r'subprocess\.run\s*\('
            matches = list(re.finditer(pattern, content))
            
            # Process in reverse order to maintain positions
            for match in reversed(matches):
                # Get the full call
                start = match.start()
                
                # Find the matching closing parenthesis
                paren_count = 1
                pos = match.end()
                
                while pos < len(content) and paren_count > 0:
                    if content[pos] == '(':
                        paren_count += 1
                    elif content[pos] == ')':
                        paren_count -= 1
                    pos += 1
                    
                if paren_count == 0:
                    call_text = content[start:pos]
                    
                    # Skip if already has timeout
                    if 'timeout' not in call_text:
                        # Create a match object for the full call
                        full_match = re.match(r'subprocess\.run\s*\(.*?\)', call_text, re.DOTALL)
                        if full_match:
                            new_call = self.fix_subprocess_call(content, match)
                            # Replace in content
                            content = content[:start] + new_call + content[pos:]
                            
            if content != original_content:
                # Backup original file
                backup_path = filepath.with_suffix(filepath.suffix + '.backup')
                shutil.copy2(filepath, backup_path)
                
                # Write fixed content
                with open(filepath, 'w') as f:
                    f.write(content)
                    
                self.fixed_files.append(filepath)
                return True
                
            return False
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            return False
            
    def fix_all_files(self):
        """Fix all Python files in the directory"""
        files_to_fix = []
        
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file.endswith('.py'):
                    filepath = Path(root) / file
                    
                    # Check if file needs fixing
                    with open(filepath, 'r') as f:
                        content = f.read()
                        
                    if 'subprocess.run' in content:
                        # Check for calls without timeout
                        pattern = r'subprocess\.run\s*\([^)]*\)'
                        matches = re.findall(pattern, content, re.DOTALL)
                        
                        for match in matches:
                            if 'timeout' not in match:
                                files_to_fix.append(filepath)
                                break
                                
        print(f"Found {len(files_to_fix)} files to fix")
        
        for filepath in files_to_fix:
            print(f"Fixing {filepath}...")
            if self.fix_file(filepath):
                print(f"  ✓ Fixed")
            else:
                print(f"  - No changes needed")
                
        print(f"\nFixed {len(self.fixed_files)} files")
        
    def generate_summary(self):
        """Generate a summary of fixes"""
        if not self.fixed_files:
            print("No files were modified")
            return
            
        print("\n=== Summary of Fixed Files ===")
        for filepath in sorted(self.fixed_files):
            print(f"  {filepath}")
            
        print(f"\nTotal files fixed: {len(self.fixed_files)}")
        print("Backup files created with .backup extension")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        print("Dry run mode - no files will be modified")
        # Just run the analyzer
        from analyze_subprocess_calls import SubprocessAnalyzer
        analyzer = SubprocessAnalyzer()
        analyzer.generate_report()
    else:
        fixer = SubprocessTimeoutFixer()
        fixer.fix_all_files()
        fixer.generate_summary()