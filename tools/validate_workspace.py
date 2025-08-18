#!/usr/bin/env python3
"""
Workspace Validation Tool
Tests the workspace setup and permission fixes
"""

import sys
import os
import yaml
from pathlib import Path

# Add builder modules to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from builder.modules.workspace_setup import WorkspaceSetup

def main():
    """Test workspace setup with validation"""
    
    print("=" * 60)
    print("Z-FORGE Workspace Validation Tool")
    print("=" * 60)
    
    # Load configuration
    config_path = Path("build_specs/build_spec_outside_packages.yml")
    if not config_path.exists():
        print(f"[!] Configuration file not found: {config_path}")
        return False
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    workspace_path = Path(config['builder_config']['workspace_path'])
    
    print(f"[+] Testing workspace: {workspace_path}")
    print(f"[+] Configuration: {config_path}")
    
    # Initialize workspace setup module
    workspace_setup = WorkspaceSetup(workspace_path, config)
    
    try:
        # Execute workspace setup
        result = workspace_setup.execute()
        
        if result['status'] == 'success':
            print("\n[+] Workspace Setup Results:")
            print(f"    ✓ Status: {result['status']}")
            print(f"    ✓ Workspace: {result['workspace']}")
            print(f"    ✓ Chroot: {result['chroot']}")
            print(f"    ✓ Available Space: {result.get('available_space_gb', 'N/A'):.1f}GB")
            print(f"    ✓ Directories Created: {result.get('directories_created', 'N/A')}")
            print(f"    ✓ Version: {result['version']}")
            
            # Test workspace functionality
            print("\n[+] Testing workspace functionality...")
            
            # Test write access
            test_file = workspace_path / "test_write.tmp"
            try:
                test_file.write_text("test")
                test_file.unlink()
                print("    ✓ Write access: OK")
            except Exception as e:
                print(f"    ✗ Write access: FAILED ({e})")
                return False
            
            # Check required directories
            required_dirs = ['temp', 'cache', 'build', 'chroot', 'output', 'logs']
            missing_dirs = []
            for dir_name in required_dirs:
                if not (workspace_path / dir_name).exists():
                    missing_dirs.append(dir_name)
            
            if missing_dirs:
                print(f"    ✗ Missing directories: {missing_dirs}")
                return False
            else:
                print(f"    ✓ All required directories present: {len(required_dirs)}")
            
            # Check chroot mount points
            mount_points = ['dev', 'proc', 'sys', 'run', 'tmp']
            chroot_path = workspace_path / 'chroot'
            missing_mounts = []
            for mount in mount_points:
                if not (chroot_path / mount).exists():
                    missing_mounts.append(mount)
            
            if missing_mounts:
                print(f"    ✗ Missing chroot mount points: {missing_mounts}")
                return False
            else:
                print(f"    ✓ All chroot mount points present: {len(mount_points)}")
            
            print("\n[+] Workspace validation PASSED ✓")
            return True
            
        else:
            print(f"\n[!] Workspace setup failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"\n[!] Workspace setup exception: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)