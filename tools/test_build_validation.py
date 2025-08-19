#!/usr/bin/env python3
"""
Test Build Validation
Tests the workspace validation in the build launcher
"""

import sys
import os
import yaml
import subprocess
from pathlib import Path
from typing import Dict

# Add builder modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def validate_workspace_before_build(config_path: str) -> Dict:
    """Validate workspace requirements before starting build"""
    try:
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        workspace_path = Path(config['builder_config'].get('workspace_path', '/root/zforge_workspace'))
        
        # Check disk space
        if workspace_path.exists():
            parent_path = workspace_path.parent
        else:
            parent_path = workspace_path.parent if workspace_path.parent.exists() else Path('/root')
            
        statvfs = os.statvfs(parent_path)
        available_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
        
        if available_gb < 15:
            return {
                'status': False,
                'error': f'Insufficient disk space: {available_gb:.1f}GB available, 15GB required'
            }
        
        # Check root privileges
        if os.geteuid() != 0:
            try:
                subprocess.run(["sudo", "-n", "true"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                return {
                    'status': False,
                    'error': 'Root privileges required. Please run as root or configure sudo.'
                }
        
        # Check workspace directory accessibility
        if workspace_path.exists():
            try:
                test_file = workspace_path / '.access_test'
                test_file.write_text('test')
                test_file.unlink()
            except Exception as e:
                return {
                    'status': False,
                    'error': f'Workspace not accessible: {e}'
                }
        
        return {
            'status': True,
            'available_space_gb': available_gb,
            'workspace': str(workspace_path)
        }
        
    except Exception as e:
        return {
            'status': False,
            'error': f'Validation error: {e}'
        }

def fix_workspace_issues(config_path: str) -> Dict:
    """Attempt to fix common workspace issues"""
    try:
        # Load configuration
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        workspace_path = Path(config['builder_config'].get('workspace_path', '/root/zforge_workspace'))
        
        # Create workspace if missing
        if not workspace_path.exists():
            subprocess.run(["sudo", "mkdir", "-p", str(workspace_path)], check=True)
            subprocess.run(["sudo", "chmod", "777", str(workspace_path)], check=True)
        
        # Create required subdirectories
        required_dirs = ['temp', 'cache', 'build', 'chroot', 'output', 'logs', 'apt_cache', 'apt_state', 'iso_build', 'tmp']
        for dir_name in required_dirs:
            dir_path = workspace_path / dir_name
            if not dir_path.exists():
                subprocess.run(["sudo", "mkdir", "-p", str(dir_path)], check=True)
                if dir_name == 'tmp':
                    subprocess.run(["sudo", "chmod", "1777", str(dir_path)], check=True)
                else:
                    subprocess.run(["sudo", "chmod", "777", str(dir_path)], check=True)
        
        # Fix permissions
        subprocess.run(["sudo", "chmod", "777", str(workspace_path)], check=True)
        
        return {
            'status': True,
            'message': f'Fixed workspace issues at {workspace_path}'
        }
        
    except Exception as e:
        return {
            'status': False,
            'error': f'Failed to fix workspace: {e}'
        }

def main():
    """Test build validation functions"""
    
    print("=" * 60)
    print("Z-FORGE Build Validation Test")
    print("=" * 60)
    
    config_path = "build_specs/build_spec_outside_packages.yml"
    
    # Test workspace validation
    print(f"[+] Testing workspace validation with: {config_path}")
    
    result = validate_workspace_before_build(config_path)
    
    if result['status']:
        print(f"[+] Workspace validation PASSED:")
        print(f"    ✓ Available space: {result['available_space_gb']:.1f}GB")
        print(f"    ✓ Workspace: {result['workspace']}")
    else:
        print(f"[!] Workspace validation FAILED: {result['error']}")
        
        # Test workspace fix function
        print("[+] Testing workspace fix function...")
        fix_result = fix_workspace_issues(config_path)
        
        if fix_result['status']:
            print(f"[+] Workspace fix SUCCESSFUL: {fix_result['message']}")
            
            # Re-test validation
            print("[+] Re-testing validation after fix...")
            result = validate_workspace_before_build(config_path)
            
            if result['status']:
                print(f"[+] Workspace validation now PASSED:")
                print(f"    ✓ Available space: {result['available_space_gb']:.1f}GB") 
                print(f"    ✓ Workspace: {result['workspace']}")
            else:
                print(f"[!] Workspace validation still FAILED: {result['error']}")
                return False
        else:
            print(f"[!] Workspace fix FAILED: {fix_result['error']}")
            return False
    
    print("\n[+] Build validation test COMPLETED ✓")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)