#!/usr/bin/env python3
"""
Z-FORGE Automated Build Script
Runs the full build process without user interaction
"""
import sys
import os
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'builder'))

from core.builder import ZForgeBuilder
from pathlib import Path

def main():
    """Run automated build"""
    print("════════════════════════════════════════════════════════════════")
    print("                Z-FORGE V3  AUTOMATED BUILD")
    print("════════════════════════════════════════════════════════════════")
    print()
    
    # Check if running as root
    if os.geteuid() != 0:
        print("[!] This script must be run as root (use sudo)")
        sys.exit(1)
    
    # Use default build configuration
    config_file = "build_spec.yml"
    
    # Check if config exists
    if not Path(config_file).exists():
        print(f"[!] Build configuration not found: {config_file}")
        print("    Please create a build_spec.yml file or specify a custom config")
        sys.exit(1)
    
    print(f"[*] Using configuration: {config_file}")
    print(f"[*] Workspace: {os.environ.get('ZFORGE_WORKSPACE', '/tmp/zforge_workspace')}")
    print()
    
    try:
        # Create builder instance
        builder = ZForgeBuilder(config_file)
        
        # Run the build
        print("[*] Starting automated build process...")
        print("[*] This will take 30-60 minutes depending on your system")
        print()
        
        result = builder.execute_pipeline()
        
        if result and result.get('status') == 'success':
            print()
            print("════════════════════════════════════════════════════════════════")
            print("                    BUILD SUCCESSFUL!")
            print("════════════════════════════════════════════════════════════════")
            print()
            
            iso_path = result.get('iso_path', 'Unknown')
            if iso_path and iso_path != 'Unknown' and Path(iso_path).exists():
                iso_size = Path(iso_path).stat().st_size / (1024**3)  # Size in GB
                print(f"[✓] ISO created at: {iso_path}")
                print(f"[✓] Size: {iso_size:.2f} GB")
                
                # Check if results contain ISO info
                if 'results' in result and 'ISOGeneration' in result['results']:
                    iso_info = result['results']['ISOGeneration']
                    print(f"[✓] SHA256: {iso_info.get('checksum', 'Not calculated')}")
                
                # Copy ISO to current directory
                current_dir = Path.cwd()
                iso_filename = Path(iso_path).name
                target_path = current_dir / iso_filename
                
                print()
                print(f"[*] Copying ISO to current directory...")
                try:
                    import shutil
                    shutil.copy2(iso_path, target_path)
                    print(f"[✓] ISO copied to: {target_path}")
                except Exception as e:
                    print(f"[!] Failed to copy ISO: {e}")
                    print(f"[!] ISO remains at: {iso_path}")
            else:
                print(f"[✓] Build completed successfully")
                print(f"[!] ISO path: {iso_path}")
                
            print(f"[✓] Log file: {result.get('log_path', 'Unknown')}")
            print()
            print("You can now write this ISO to a USB drive or use it for virtual machines")
            print()
        else:
            print()
            print("════════════════════════════════════════════════════════════════")
            print("                    BUILD FAILED!")
            print("════════════════════════════════════════════════════════════════")
            print()
            if result:
                print(f"[!] Status: {result.get('status', 'Unknown')}")
                print(f"[!] Error: {result.get('error', 'Unknown error')}")
                print(f"[!] Failed module: {result.get('module', 'Unknown')}")
                print(f"[!] Log file: {result.get('log_path', 'Unknown')}")
            else:
                print("[!] Build returned no result")
            print()
            sys.exit(1)
            
    except Exception as e:
        print()
        print("════════════════════════════════════════════════════════════════")
        print("                    BUILD FAILED!")
        print("════════════════════════════════════════════════════════════════")
        print()
        print(f"[!] Error: {e}")
        print()
        print("Check the log file for details:")
        print("  - logs/zforge_build_*.log")
        print()
        sys.exit(1)

if __name__ == "__main__":
    main()