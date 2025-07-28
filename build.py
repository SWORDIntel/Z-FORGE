#!/usr/bin/env python3
"""
Z-FORGE Build Launcher
Quick launcher for the automated build process
"""
import os
import sys
import subprocess
import glob
from pathlib import Path

def find_build_spec():
    """Find available build spec YAML files"""
    script_dir = Path(__file__).parent
    yaml_files = list(script_dir.glob("*.yml")) + list(script_dir.glob("*.yaml"))
    
    # Filter to build spec files
    build_specs = []
    for yaml_file in yaml_files:
        if 'build_spec' in yaml_file.name.lower() or yaml_file.name == 'build_spec.yml':
            build_specs.append(yaml_file)
    
    return build_specs

def select_build_spec(build_specs):
    """Select a build spec from available options"""
    if len(build_specs) == 0:
        return None
    elif len(build_specs) == 1:
        return build_specs[0]
    else:
        # Multiple specs found, check for default
        for spec in build_specs:
            if spec.name == 'build_spec.yml':
                return spec
        # No default, use first one
        return build_specs[0]

def main():
    """Launch the Z-FORGE build process"""
    # Check if running as root
    if os.geteuid() != 0:
        print("[!] This script must be run as root")
        print("    Relaunching with sudo...")
        # Relaunch with sudo
        args = ['sudo', sys.executable] + sys.argv
        os.execvp('sudo', args)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Fix Python path for imports
    sys.path.insert(0, str(script_dir))
    
    # Find build config
    build_specs = find_build_spec()
    config_file = select_build_spec(build_specs)
    
    if not config_file:
        print("[!] No build configuration found")
        print("    Please create a build_spec.yml file first")
        print("    Example: build_spec.yml, build_spec_r730xd.yml")
        sys.exit(1)
    
    # Parse command line arguments
    debug_mode = '--debug' in sys.argv
    config_override = None
    
    # Check for config override
    for i, arg in enumerate(sys.argv):
        if arg.startswith('--config='):
            config_override = arg.split('=', 1)[1]
        elif arg == '--config' and i + 1 < len(sys.argv):
            config_override = sys.argv[i + 1]
        elif arg.startswith('--workspace='):
            os.environ['ZFORGE_WORKSPACE'] = arg.split('=', 1)[1]
        elif arg == '--workspace' and i + 1 < len(sys.argv):
            os.environ['ZFORGE_WORKSPACE'] = sys.argv[i + 1]
    
    # Use override if provided
    if config_override:
        config_file = Path(config_override)
        if not config_file.exists():
            print(f"[!] Specified config not found: {config_override}")
            sys.exit(1)
    
    # Set environment variable for config file
    os.environ['ZFORGE_CONFIG'] = str(config_file)
    
    # Launch the actual build script
    build_script = Path("scripts/build/build-auto.py")
    if not build_script.exists():
        print(f"[!] Build script not found: {build_script}")
        sys.exit(1)
    
    # Build command with proper environment
    env = os.environ.copy()
    env['PYTHONPATH'] = str(script_dir) + ':' + env.get('PYTHONPATH', '')
    
    cmd = [sys.executable, str(build_script)]
    if debug_mode:
        cmd.append('--debug')
    
    # Execute build
    print("════════════════════════════════════════════════════════════════")
    print("                Z-FORGE BUILD LAUNCHER")
    print("════════════════════════════════════════════════════════════════")
    print()
    print(f"[*] Config: {config_file.name}")
    print(f"[*] Workspace: {os.environ.get('ZFORGE_WORKSPACE', '/tmp/zforge_workspace')}")
    print(f"[*] Debug mode: {'ON' if debug_mode else 'OFF'}")
    print()
    
    if len(build_specs) > 1:
        print(f"[*] Found {len(build_specs)} build configs:")
        for spec in build_specs:
            prefix = "  → " if spec == config_file else "    "
            print(f"{prefix}{spec.name}")
        print()
    
    try:
        # Run the build with fixed environment
        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n[!] Build interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"[!] Error launching build: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()