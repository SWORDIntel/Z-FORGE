#!/bin/bash
# Clean up Z-FORGE root directory from all troubleshooting scripts

echo "🧹 Cleaning up Z-FORGE root directory..."
echo "This will remove all diagnostic and fix scripts, keeping only essential files."
echo

# List of files to remove (all our troubleshooting attempts)
CLEANUP_FILES=(
    # Diagnostic scripts
    "diagnose_kernel_version.sh"
    "check_debian_kernels.sh" 
    "check_kernel_issue.sh"
    "quick_diagnose.sh"
    "quick_kernel_check.sh"
    
    # Fix scripts from various attempts
    "fix_zfs_apt_repos.py"
    "fix_zfs_apt_repos.sh"
    "fix_dpkg_interrupted.sh"
    "fix_kernel_trixie.py"
    "fix_trixie_kernel_version.sh"
    "fix_trixie_kernel_612.sh"
    "install_trixie_kernel_safe.sh"
    "recover_and_install.sh"
    "manual_kernel_fix.sh"
    "nuclear_kernel_fix.sh"
    
    # UltraThink v1 (failed attempts)
    "ultrathink_kernel_fix.py"
    "ultrathink_final_kernel_agent.py"
    "ultrathink_fallback.sh"
    "launch_ultrathink.sh"
    "FIX_NOW.sh"
    
    # Patch scripts
    "kernel_acquisition_trixie_patch.py"
    
    # Temporary/test files
    "wget-log*"
    
    # Old README files (we have the new comprehensive one)
    "KERNEL_FIX_README.md"
)

# Archive directory for moved files
ARCHIVE_DIR="/opt/github/Z-FORGE/archive_troubleshooting_$(date +%Y%m%d_%H%M%S)"

echo "Files to be removed:"
for file in "${CLEANUP_FILES[@]}"; do
    if [ -f "/opt/github/Z-FORGE/$file" ] || [ -f "/opt/github/Z-FORGE/"$file ]; then
        echo "  ✓ $file"
    fi
done

echo
echo "Files to be kept (essential for rebuild):"
echo "  ✓ ultrathink_iso_rebuild.py"
echo "  ✓ REBUILD_NOW.sh" 
echo "  ✓ ULTRATHINK_REBUILD_README.md"
echo "  ✓ cleanup_root_dir.sh (this script)"
echo "  ✓ All original Z-FORGE files (build.py, config/, builder/, etc.)"
echo

read -p "Proceed with cleanup? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

# Create archive directory
mkdir -p "$ARCHIVE_DIR"
echo "Created archive directory: $ARCHIVE_DIR"

# Move files to archive
moved_count=0
for file in "${CLEANUP_FILES[@]}"; do
    if [ -f "/opt/github/Z-FORGE/$file" ]; then
        mv "/opt/github/Z-FORGE/$file" "$ARCHIVE_DIR/"
        echo "Moved: $file"
        ((moved_count++))
    elif ls /opt/github/Z-FORGE/$file 2>/dev/null; then
        mv /opt/github/Z-FORGE/$file "$ARCHIVE_DIR/"
        echo "Moved: $file"
        ((moved_count++))
    fi
done

# Clean up any log files from troubleshooting
echo
echo "Cleaning up troubleshooting log files..."
log_count=0
for log_file in /opt/github/Z-FORGE/ultrathink_*.log /opt/github/Z-FORGE/nuclear_*.log /opt/github/Z-FORGE/ultrathink_*_*.json; do
    if [ -f "$log_file" ]; then
        mv "$log_file" "$ARCHIVE_DIR/"
        echo "Moved log: $(basename "$log_file")"
        ((log_count++))
    fi
done

echo
echo "🎉 Cleanup completed!"
echo "  • $moved_count troubleshooting scripts moved to archive"
echo "  • $log_count log files archived"
echo "  • Archive location: $ARCHIVE_DIR"
echo

echo "Remaining files in Z-FORGE root:"
ls -la /opt/github/Z-FORGE/*.sh /opt/github/Z-FORGE/*.py /opt/github/Z-FORGE/*.md 2>/dev/null | head -10

echo
echo "✨ Z-FORGE root directory is now clean!"
echo "Ready for perfect rebuild with: ./REBUILD_NOW.sh"