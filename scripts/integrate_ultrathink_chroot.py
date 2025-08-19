#!/usr/bin/env python3
"""
Integration script for Ultrathink Chroot Solution
This script demonstrates usage and can patch the existing Z-FORGE build system
to use the enhanced chroot implementation.
"""

import sys
import subprocess
import shutil
from pathlib import Path
import argparse
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from ultrathink_chroot_solution import ChrootManager, cleanup_all_chroots


def demonstrate_usage():
    """Demonstrate various usage patterns of the Ultrathink solution"""
    print("=" * 70)
    print("ULTRATHINK CHROOT SOLUTION - USAGE EXAMPLES")
    print("=" * 70)
    
    print("\n1. Command Line Usage:")
    print("-" * 50)
    print("# Enter interactive shell:")
    print("./ultrathink_chroot_solution.py /path/to/chroot")
    print("\n# Run a command:")
    print("./ultrathink_chroot_solution.py /path/to/chroot -- apt-get update")
    print("\n# Run a script:")
    print('./ultrathink_chroot_solution.py /path/to/chroot --script "apt-get update && apt-get upgrade -y"')
    print("\n# Cleanup mounts:")
    print("./ultrathink_chroot_solution.py /path/to/chroot --cleanup")
    
    print("\n\n2. Python Module Usage:")
    print("-" * 50)
    print("""
from ultrathink_chroot_solution import ChrootManager

# Method 1: Using context manager (recommended)
with ChrootManager('/path/to/chroot') as chroot:
    result = chroot.run(['apt-get', 'update'])
    print(result.stdout)
    
    # Run bash script
    result = chroot.run_bash('dpkg -l | grep linux')
    print(result.stdout)

# Method 2: Manual setup/cleanup
chroot = ChrootManager('/path/to/chroot')
try:
    chroot.prepare()
    result = chroot.run(['ls', '-la', '/'])
    print(result.stdout)
finally:
    chroot.cleanup()

# Method 3: As drop-in replacement for existing code
from builder.utils.chroot_manager_ultrathink import ChrootManager
# Use exactly like the original ChrootManager
""")
    
    print("\n\n3. Integration with Z-FORGE Build System:")
    print("-" * 50)
    print("Run: python3 integrate_ultrathink_chroot.py --patch-build-system")
    print("This will update the build system to use the Ultrathink solution.")


def test_chroot_functionality(chroot_path: Path):
    """Test the chroot functionality"""
    print(f"\nTesting chroot functionality at {chroot_path}...")
    
    try:
        # Create test chroot if it doesn't exist
        if not chroot_path.exists():
            print(f"Creating test chroot at {chroot_path}...")
            chroot_path.mkdir(parents=True, exist_ok=True)
            
            # Create minimal structure
            for dir in ["etc", "bin", "usr/bin", "proc", "sys", "dev", "run", "tmp"]:
                (chroot_path / dir).mkdir(parents=True, exist_ok=True)
            
            # Copy essential binaries
            for binary in ["/bin/bash", "/bin/ls", "/bin/cat", "/bin/echo"]:
                if Path(binary).exists():
                    target = chroot_path / binary.lstrip('/')
                    shutil.copy2(binary, target)
        
        # Test with ChrootManager
        print("\nTesting ChrootManager...")
        with ChrootManager(chroot_path) as chroot:
            # Test basic command
            print("- Running 'echo Hello from chroot'")
            result = chroot.run(['echo', 'Hello from chroot'])
            print(f"  Output: {result.stdout.strip()}")
            
            # Test mount points
            print("- Checking mount points")
            result = chroot.run(['ls', '-la', '/proc/'], check=False)
            if result.returncode == 0:
                print("  /proc mounted successfully")
            
            # Test bash script
            print("- Running bash script")
            result = chroot.run_bash('echo "Bash script works!" && pwd')
            print(f"  Output: {result.stdout.strip()}")
        
        print("\n✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def patch_build_system():
    """Patch the Z-FORGE build system to use Ultrathink chroot"""
    print("\nPatching Z-FORGE build system to use Ultrathink chroot...")
    
    patches_applied = 0
    
    # 1. Update imports in Python files that use chroot_manager
    python_files = [
        PROJECT_ROOT / "builder/modules/debootstrap.py",
        PROJECT_ROOT / "builder/modules/live_environment.py",
        PROJECT_ROOT / "builder/modules/desktop_environment.py",
        PROJECT_ROOT / "builder/modules/proxmox_integration.py",
    ]
    
    for py_file in python_files:
        if py_file.exists():
            content = py_file.read_text()
            
            # Check if already using ultrathink
            if "chroot_manager_ultrathink" in content:
                print(f"  ✓ {py_file.name} already using Ultrathink")
                continue
            
            # Replace import
            if "from builder.utils.chroot_manager import ChrootManager" in content:
                new_content = content.replace(
                    "from builder.utils.chroot_manager import ChrootManager",
                    "from builder.utils.chroot_manager_ultrathink import ChrootManager"
                )
                
                # Backup original
                backup = py_file.with_suffix('.py.backup_pre_ultrathink')
                shutil.copy2(py_file, backup)
                
                # Write updated content
                py_file.write_text(new_content)
                patches_applied += 1
                print(f"  ✓ Patched {py_file.name}")
    
    # 2. Create wrapper script for shell scripts
    wrapper_script = PROJECT_ROOT / "scripts/chroot/ultrathink_chroot_wrapper.sh"
    wrapper_content = """#!/bin/bash
# Ultrathink chroot wrapper for shell scripts
# This replaces 'chroot' commands with the ultrathink solution

ULTRATHINK_SOLUTION="$(dirname "$0")/../../ultrathink_chroot_solution.py"

if [ "$1" = "chroot" ]; then
    shift  # Remove 'chroot' command
    CHROOT_PATH="$1"
    shift  # Remove chroot path
    
    # Use ultrathink solution
    exec python3 "$ULTRATHINK_SOLUTION" "$CHROOT_PATH" -- "$@"
else
    # Direct usage
    exec python3 "$ULTRATHINK_SOLUTION" "$@"
fi
"""
    
    wrapper_script.write_text(wrapper_content)
    wrapper_script.chmod(0o755)
    print(f"  ✓ Created wrapper script at {wrapper_script}")
    
    # 3. Create alias script
    alias_script = PROJECT_ROOT / "scripts/chroot/chroot"
    alias_content = """#!/bin/bash
# Alias for chroot that uses ultrathink solution
exec "$(dirname "$0")/ultrathink_chroot_wrapper.sh" chroot "$@"
"""
    
    alias_script.write_text(alias_content)
    alias_script.chmod(0o755)
    print(f"  ✓ Created chroot alias at {alias_script}")
    
    print(f"\n✅ Patching complete! Applied {patches_applied} patches.")
    print("\nTo use the enhanced chroot in shell scripts, either:")
    print("1. Add 'scripts/chroot' to your PATH")
    print("2. Use './scripts/chroot/ultrathink_chroot_wrapper.sh' instead of 'chroot'")
    print("3. Call './ultrathink_chroot_solution.py' directly")


def main():
    parser = argparse.ArgumentParser(
        description="Integration helper for Ultrathink Chroot Solution"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Show usage examples"
    )
    
    parser.add_argument(
        "--test",
        metavar="PATH",
        help="Test chroot functionality with given path"
    )
    
    parser.add_argument(
        "--patch-build-system",
        action="store_true",
        help="Patch Z-FORGE build system to use Ultrathink chroot"
    )
    
    parser.add_argument(
        "--cleanup-all",
        action="store_true",
        help="Emergency cleanup of all active chroots"
    )
    
    args = parser.parse_args()
    
    if not any([args.demo, args.test, args.patch_build_system, args.cleanup_all]):
        # Default action - show demo
        args.demo = True
    
    if args.demo:
        demonstrate_usage()
    
    if args.test:
        test_path = Path(args.test)
        success = test_chroot_functionality(test_path)
        sys.exit(0 if success else 1)
    
    if args.patch_build_system:
        patch_build_system()
    
    if args.cleanup_all:
        print("Performing emergency cleanup of all active chroots...")
        cleanup_all_chroots()
        print("Cleanup complete.")


if __name__ == "__main__":
    main()