# Z-FORGE Build Scripts Explained

## Overview
Z-FORGE has three build-related scripts, each serving a specific purpose:

## 1. `build.sh` - Main Entry Point (RECOMMENDED)
**Purpose**: User-friendly wrapper script  
**Usage**: `sudo ./build.sh`

### What it does:
- Checks if running as root
- Sets up environment variables
- Runs build environment checks
- Calls `build-auto.py` to do the actual build
- Provides clean output and error handling

### Why use this:
- Simplest command to remember
- Handles all prerequisites
- Best for normal builds

## 2. `build-auto.py` - The Build Engine
**Purpose**: The actual modular build system  
**Usage**: `sudo python3 build-auto.py` (usually called by build.sh)

### What it does:
- Loads `build_spec.yml` configuration
- Executes all enabled modules in sequence
- Handles the modular pipeline we've been working on
- Generates the ISO
- **NEW**: Copies the ISO to your current directory after build

### Why it exists separately:
- Python provides better error handling than bash
- Easier to maintain and debug
- Can be called directly for debugging
- Modular architecture is cleaner in Python

## 3. `build-iso.sh` - Legacy Build System
**Purpose**: Original bash-based build script  
**Usage**: `sudo ./build-iso.sh` (not recommended)

### What it does:
- Older monolithic build approach
- Does not use the new modular system
- May not include latest features

### Why it's still there:
- Backward compatibility
- Some users might have automation that depends on it
- Fallback option if Python system fails
- Contains useful bash functions that could be referenced

## Build Output

After a successful build using `sudo ./build.sh`:

1. **ISO Location**: The ISO is created in `/tmp/zforge_workspace/`
2. **Auto-Copy**: The ISO is automatically copied to your current directory
3. **Filename**: `zforge-r730xd-proxmox-v3.iso` (or as configured)
4. **Size**: Typically 2-4GB depending on included packages

## Example Workflow

```bash
cd /opt/github/Z-FORGE
sudo ./build.sh

# After 30-60 minutes...
# ISO will be in current directory
ls -lh *.iso

# Write to USB
sudo dd if=zforge-r730xd-proxmox-v3.iso of=/dev/sdX bs=4M status=progress
```

## Summary

- **Use `build.sh`** for normal builds - it's the recommended method
- **`build-auto.py`** is the engine that does the actual work
- **`build-iso.sh`** is legacy - kept for compatibility

The modular design allows for better maintenance, debugging, and extensibility while providing a simple user interface through `build.sh`.