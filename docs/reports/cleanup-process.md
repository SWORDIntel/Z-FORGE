# Z-FORGE Build Cleanup Process

## Overview

The Z-FORGE build system now includes comprehensive cleanup functionality to prevent "File exists" errors and ensure a clean build environment for each run.

## Components

### 1. Cleanup Script (`cleanup-workspace.sh`)

A standalone bash script that safely cleans up the build workspace:

- **Location**: `/cleanup-workspace.sh`
- **Purpose**: Complete removal of build workspace including mounted filesystems
- **Features**:
  - Unmounts all chroot filesystems (dev, proc, sys, etc.)
  - Kills processes using the workspace
  - Removes the workspace directory completely
  - Handles permission errors gracefully
  - Provides colored output for better visibility

**Usage**:
```bash
sudo ./cleanup-workspace.sh [WORKSPACE_PATH]
# Default workspace: /tmp/zforge_workspace
```

### 2. Build Script Enhancement (`build-iso.sh`)

The main build script now includes:

- **Cleanup trap**: Automatically cleans workspace on exit, error, or interrupt
- **Pre-build cleanup**: Removes existing workspace before starting
- **Error handling**: Ensures cleanup runs even if build fails

**Key features**:
```bash
# Trap handler runs on:
# - Normal exit (EXIT)
# - Interrupt (Ctrl+C) (INT)
# - Termination signal (TERM)
# - Any error (ERR)
trap cleanup EXIT INT TERM ERR
```

### 3. Python Cleanup Module (`workspace_cleanup.py`)

A Python module for use within the builder framework:

- **Location**: `/builder/modules/workspace_cleanup.py`
- **Class**: `WorkspaceCleanup`
- **Methods**:
  - `execute()`: Full cleanup process
  - `cleanup_on_error()`: Emergency cleanup (preserves workspace for debugging)

### 4. Workspace Setup Enhancement

The `WorkspaceSetup` module now:
- Checks for existing workspace
- Attempts to clean it before creating new one
- Unmounts any lingering filesystems
- Handles permission errors gracefully

## Cleanup Process Flow

1. **Check for mounted filesystems**
   - Unmount in reverse order: dev/pts, dev, proc, sys, run
   - Use lazy unmount (-l) if normal unmount fails

2. **Kill workspace processes**
   - Find processes with `lsof`
   - SIGTERM first, then SIGKILL if needed
   - Wait between signals

3. **Remove workspace directory**
   - Try normal removal first
   - Use sudo if permission denied
   - Force permissions change if needed

## When Cleanup Occurs

1. **Automatic cleanup**:
   - On successful build completion
   - On build failure or error
   - On user interrupt (Ctrl+C)
   - On termination signal

2. **Manual cleanup**:
   - Run `cleanup-workspace.sh` directly
   - Use when automatic cleanup fails

## Error Prevention

The cleanup process prevents these common errors:

1. **"File exists" errors**
   - Workspace cleaned before each build
   - Existing directories removed

2. **"Device busy" errors**
   - Filesystems properly unmounted
   - Processes terminated before removal

3. **Permission errors**
   - Sudo used where necessary
   - Permissions adjusted if needed

## Best Practices

1. **Always run builds as root** (required by debootstrap)

2. **Don't manually modify workspace** during builds

3. **Check for cleanup completion** before starting new build

4. **Use the cleanup script** if you encounter issues:
   ```bash
   sudo ./cleanup-workspace.sh
   ```

5. **For debugging**, the Python cleanup module can preserve workspace:
   ```python
   cleanup = WorkspaceCleanup(workspace, config)
   cleanup.cleanup_on_error()  # Preserves workspace
   ```

## Troubleshooting

If cleanup fails:

1. **Check for active processes**:
   ```bash
   sudo lsof +D /tmp/zforge_workspace
   ```

2. **Check for mounts**:
   ```bash
   mount | grep zforge_workspace
   ```

3. **Force unmount**:
   ```bash
   sudo umount -l /tmp/zforge_workspace/chroot/{dev/pts,dev,proc,sys}
   ```

4. **Force remove**:
   ```bash
   sudo rm -rf /tmp/zforge_workspace
   ```

## Integration

The cleanup system is fully integrated:

- Build script has trap handlers
- Workspace setup handles existing directories
- Debootstrap unmounts on completion/error
- Standalone script for manual cleanup

This ensures the build environment is always clean and prevents accumulation of stale workspace directories.