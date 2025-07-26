#!/usr/bin/env python3
"""
Analyze subprocess.run calls in builder/modules to add appropriate timeouts
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict

class SubprocessAnalyzer:
    def __init__(self, base_path: str = "builder/modules"):
        self.base_path = Path(base_path)
        self.categories = {
            'quick': 30,      # Quick commands (ls, mkdir, chmod, etc)
            'install': 300,   # Package installations (apt-get, dpkg, etc)
            'compile': 600,   # Compilation tasks (make, build, etc)
            'download': 300,  # Downloads (wget, git clone, etc)
            'mount': 30,      # Mount/unmount operations
            'chroot': 300,    # Chroot operations (depends on inner command)
        }
        
    def categorize_command(self, cmd_text: str) -> Tuple[str, int]:
        """Categorize command and return category and timeout"""
        cmd_lower = cmd_text.lower()
        
        # Download operations
        if any(x in cmd_lower for x in ['wget', 'git clone', 'git fetch']):
            return 'download', 300
            
        # Package installations
        if any(x in cmd_lower for x in ['apt-get install', 'dpkg -i', 'apt install']):
            return 'install', 300
            
        # Compilation/build operations
        if any(x in cmd_lower for x in ['make', 'build', 'compile', './configure']):
            return 'compile', 600
            
        # Mount/unmount operations
        if any(x in cmd_lower for x in ['mount', 'umount', 'mountpoint']):
            return 'mount', 30
            
        # Chroot operations - check what's being run inside
        if 'chroot' in cmd_lower:
            if any(x in cmd_lower for x in ['apt-get', 'dpkg', 'dracut', 'update-initramfs']):
                return 'chroot', 300
            else:
                return 'chroot', 60
                
        # File system operations
        if any(x in cmd_lower for x in ['mkdir', 'chmod', 'chown', 'rm', 'cp', 'mv', 'ls', 'find']):
            return 'quick', 30
            
        # System info commands
        if any(x in cmd_lower for x in ['lsblk', 'lspci', 'lsmod', 'dmidecode', 'which', 'modprobe']):
            return 'quick', 30
            
        # ZFS operations
        if any(x in cmd_lower for x in ['zpool', 'zfs']):
            if 'import' in cmd_lower or 'export' in cmd_lower:
                return 'mount', 60
            else:
                return 'quick', 30
                
        # Default
        return 'quick', 30
        
    def find_subprocess_calls(self, filepath: Path) -> List[Dict]:
        """Find all subprocess.run calls without timeout in a file"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Pattern to find subprocess.run calls
            pattern = r'subprocess\.run\s*\(([^)]+)\)'
            matches = list(re.finditer(pattern, content, re.DOTALL))
            
            results = []
            for match in matches:
                call_text = match.group(0)
                if 'timeout' not in call_text:
                    # Get line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # Try to categorize the command
                    category, timeout = self.categorize_command(call_text)
                    
                    results.append({
                        'line': line_num,
                        'text': call_text[:200].replace('\n', ' ').strip(),
                        'category': category,
                        'timeout': timeout,
                        'start': match.start(),
                        'end': match.end()
                    })
            
            return results
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            return []
            
    def analyze_directory(self) -> Dict[str, List[Dict]]:
        """Analyze all Python files in the directory"""
        results = {}
        
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file.endswith('.py'):
                    filepath = Path(root) / file
                    calls = self.find_subprocess_calls(filepath)
                    if calls:
                        results[str(filepath)] = calls
                        
        return results
        
    def generate_report(self):
        """Generate a detailed report of all subprocess.run calls needing timeout"""
        results = self.analyze_directory()
        
        # Summary statistics
        total_calls = sum(len(calls) for calls in results.values())
        by_category = {}
        
        print(f"=== Subprocess.run Calls Without Timeout ===")
        print(f"Total files with issues: {len(results)}")
        print(f"Total calls needing timeout: {total_calls}")
        print()
        
        # Group by category
        for filepath, calls in results.items():
            for call in calls:
                cat = call['category']
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append((filepath, call))
                
        # Print by category
        for category, items in sorted(by_category.items()):
            print(f"\n=== {category.upper()} Commands (timeout: {self.categories.get(category, 30)}s) ===")
            print(f"Count: {len(items)}")
            
            # Show first 5 examples
            for i, (filepath, call) in enumerate(items[:5]):
                try:
                    rel_path = Path(filepath).relative_to(Path.cwd())
                except ValueError:
                    rel_path = filepath
                print(f"\n{rel_path}:{call['line']}")
                print(f"  {call['text'][:100]}...")
                
        # Detailed file list
        print("\n\n=== Files Needing Updates ===")
        for filepath in sorted(results.keys()):
            try:
                rel_path = Path(filepath).relative_to(Path.cwd())
            except ValueError:
                rel_path = filepath
            calls = results[filepath]
            print(f"\n{rel_path}: {len(calls)} calls")
            
            # Group by timeout value
            timeout_groups = {}
            for call in calls:
                timeout = call['timeout']
                if timeout not in timeout_groups:
                    timeout_groups[timeout] = []
                timeout_groups[timeout].append(call['line'])
                
            for timeout, lines in sorted(timeout_groups.items()):
                print(f"  - {len(lines)} calls need timeout={timeout}s (lines: {', '.join(map(str, lines[:10]))}{'...' if len(lines) > 10 else ''})")

if __name__ == "__main__":
    analyzer = SubprocessAnalyzer()
    analyzer.generate_report()