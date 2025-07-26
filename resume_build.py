#!/usr/bin/env python3
"""Simple script to resume Z-FORGE build without interactive prompts"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from builder.core.builder import ZForgeBuilder
from builder.core.lockfile import BuildLockfile
from pathlib import Path

def main():
    print("Resuming Z-FORGE build...")
    
    # Load the existing lockfile
    lockfile_path = Path("build_spec.lock")
    if not lockfile_path.exists():
        print("Error: No lockfile found. Cannot resume.")
        sys.exit(1)
    
    lockfile = BuildLockfile(lockfile_path)
    
    # Create builder with the original config
    builder = ZForgeBuilder("build_spec.yml")
    
    # Resume the build
    result = builder.execute_pipeline(lockfile=lockfile, resume=True)
    
    if result['status'] == 'success':
        print(f"\n[+] Build completed successfully!")
        if result.get('iso_path'):
            print(f"[+] ISO location: {result['iso_path']}")
        print(f"[+] Build log: {result['log_path']}")
        print(f"[+] Lockfile: {result['lockfile_path']}")
    else:
        print(f"\n[!] Build failed: {result['error']}")
        print(f"[!] Failed module: {result.get('module', 'unknown')}")
        print(f"[!] Check log for details: {result['log_path']}")
        sys.exit(1)

if __name__ == "__main__":
    main()