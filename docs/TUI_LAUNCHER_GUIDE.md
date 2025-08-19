# Z-FORGE TUI Launcher Guide

**Version:** 1.0  
**Created:** January 31, 2025

## Overview

The Z-FORGE TUI (Text User Interface) Launcher provides an interactive menu system for all Z-FORGE operations, making it easy to build, diagnose, and maintain your Z-FORGE installation without memorizing commands.

## Installation

### Local Usage
```bash
cd /opt/github/Z-FORGE
./zforge-launcher.sh
```

### System-Wide Installation
```bash
cd /opt/github/Z-FORGE
sudo ln -s $(pwd)/zforge /usr/local/bin/
# Now run from anywhere:
zforge
```

## Main Features

### 1. System Status Dashboard
The launcher automatically displays:
- Workspace location and status
- Chroot bootstrap status
- ZFS installation status
- ISO build status
- Git repository status

### 2. Quick Build Menu
- **Complete Build**: Full bootstrap → ZFS → ISO pipeline
- **Bootstrap Only**: Create Debian chroot environment
- **Install ZFS Only**: Add ZFS to existing chroot
- **Build ISO Only**: Generate ISO from existing setup
- **Clean and Rebuild**: Start fresh from scratch

### 3. Diagnostics Menu
- **Pre-build Check**: Verify system requirements
- **Project Consistency**: Check all scripts are in sync
- **Script Path Check**: Verify no old /tmp paths remain
- **View Build Logs**: Browse recent build logs
- **Check Mounts**: View active chroot mounts
- **Test Chroot**: Verify chroot access works

### 4. Maintenance Menu
- **Clean Workspace**: Remove build artifacts
- **Remove Archives**: Clean up obsolete files
- **Update Paths**: Fix any remaining old paths
- **Fix Permissions**: Correct workspace permissions
- **Emergency Cleanup**: Force unmount all
- **Backup State**: Create project backup

### 5. Documentation Access
Quick access to all documentation:
- Quick Reference
- Build Guide
- Troubleshooting
- Latest Checkpoint
- ISO Build Details
- Full Documentation Index

### 6. Direct Chroot Access
Enter the chroot shell directly from the menu for manual operations.

## Menu Navigation

- Use number keys to select options
- Press `Enter` to confirm selection
- Use `0` to go back to previous menu
- Press `q` to quit from main menu

## Color Coding

- 🟢 **Green**: Success, ready, or available
- 🟡 **Yellow**: Warning or not configured
- 🔴 **Red**: Error or missing
- 🔵 **Blue**: Information
- 🟣 **Purple**: Menu headers
- 🟦 **Cyan**: Main header

## Common Workflows

### Fresh Build
1. Launch: `./zforge-launcher.sh`
2. Select: `1` (Quick Build Options)
3. Select: `1` (Complete Build)
4. Wait for completion (~15-25 minutes)

### Diagnostics Check
1. Launch: `./zforge-launcher.sh`
2. Select: `2` (Diagnostics & Testing)
3. Select: `2` (Verify Project Consistency)
4. Review results

### Clean Rebuild
1. Launch: `./zforge-launcher.sh`
2. Select: `1` (Quick Build Options)
3. Select: `5` (Clean and Rebuild Everything)
4. Confirm with `y`

## Keyboard Shortcuts

While not traditional shortcuts, the TUI uses simple number selection:
- `1-9`: Select menu option
- `0`: Back/Previous menu
- `q`: Quit (from main menu)
- `Enter`: Confirm selection

## Requirements

- Bash shell
- Terminal with color support
- Sudo access (for build operations)
- Z-FORGE project files

## Troubleshooting

### "Not in Z-FORGE root directory" Error
- Ensure you're running from the project root
- Check for `build_spec_no_tmp.yml` file

### Permission Denied
- Some operations require sudo
- The launcher will prompt when needed

### Colors Not Displaying
- Ensure terminal supports ANSI colors
- Try: `export TERM=xterm-256color`

## Advanced Usage

### Custom Workspace
```bash
export ZFORGE_WORKSPACE=/custom/path
./zforge-launcher.sh
```

### Non-Interactive Mode
For specific operations without menu:
```bash
# Direct build
sudo make -f Makefile.no_tmp build

# Direct bootstrap
sudo ./scripts/chroot/bootstrap_chroot.sh auto
```

## Integration

The launcher integrates with:
- All Z-FORGE build scripts
- Workspace management
- Chroot operations
- Documentation system
- Git operations

## Updates

The launcher is part of the Z-FORGE project and updates with:
```bash
git pull origin main
```

## Summary

The TUI launcher makes Z-FORGE accessible to users of all skill levels by providing:
- Visual system status
- Guided operations
- Easy documentation access
- Safe maintenance options
- Consistent user experience

No more memorizing complex commands - just launch and select!