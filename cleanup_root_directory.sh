#!/bin/bash
# Clean up Z-FORGE root directory
# Organizes files and removes redundant items

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "              Z-FORGE Root Directory Cleanup"
echo "═══════════════════════════════════════════════════════════════════"

# Ensure we're in the right directory
cd /opt/github/Z-FORGE

# Create organized directories
echo "[1/5] Creating organized directory structure..."
mkdir -p {archive,scripts/{build,fix,test,download,agents},docs/checkpoints}

# Move files to appropriate locations
echo "[2/5] Moving files to organized locations..."

# Move all download scripts
echo "  Moving download scripts..."
mv -f download_*.sh scripts/download/ 2>/dev/null || true
mv -f *_download_*.sh scripts/download/ 2>/dev/null || true
mv -f aria2_download_zfs.sh scripts/download/ 2>/dev/null || true
mv -f simple_zfs_download.sh scripts/download/ 2>/dev/null || true
mv -f quick_download_zfs.sh scripts/download/ 2>/dev/null || true

# Move all build scripts
echo "  Moving build scripts..."
mv -f build_*.sh scripts/build/ 2>/dev/null || true
mv -f run_*.sh scripts/build/ 2>/dev/null || true
mv -f prebuild_zfs.sh scripts/build/ 2>/dev/null || true
mv -f prepare_*.sh scripts/build/ 2>/dev/null || true

# Move all fix scripts
echo "  Moving fix scripts..."
mv -f fix_*.sh scripts/fix/ 2>/dev/null || true
mv -f fix_*.py scripts/fix/ 2>/dev/null || true
mv -f quick_fix_*.sh scripts/fix/ 2>/dev/null || true

# Move all test scripts
echo "  Moving test scripts..."
mv -f test_*.sh scripts/test/ 2>/dev/null || true
mv -f diagnose_*.sh scripts/test/ 2>/dev/null || true

# Move all agent scripts
echo "  Moving agent scripts..."
mv -f ultrathink_*.py scripts/agents/ 2>/dev/null || true
mv -f ultrathink_*.sh scripts/agents/ 2>/dev/null || true

# Move checkpoints to docs
echo "  Moving checkpoints..."
mv -f CHECKPOINT_*.md docs/checkpoints/ 2>/dev/null || true

# Move wget logs to archive
echo "  Archiving wget logs..."
mv -f wget-log* archive/ 2>/dev/null || true

# Clean up empty directories
echo "[3/5] Removing empty directories..."
find . -type d -empty -delete 2>/dev/null || true

# Remove redundant backup files
echo "[4/5] Removing backup files..."
find . -name "*.bak" -type f -delete 2>/dev/null || true
find . -name "*~" -type f -delete 2>/dev/null || true

# Create index of important files
echo "[5/5] Creating directory index..."
cat > DIRECTORY_STRUCTURE.md << 'EOF'
# Z-FORGE Directory Structure

## Root Directory Files
- `Makefile` - Main build system
- `build_spec.yml` - Primary build configuration
- `build_spec_r730xd.yml` - Hardware-specific config
- `README.md` - Project documentation (TODO: create if missing)

## Key Directories
- `builder/` - Core build system
- `calamares/` - Installer modules
- `config/` - Configuration files
- `docs/` - Documentation
- `scripts/` - Organized scripts
  - `build/` - Build scripts
  - `fix/` - Fix and patch scripts
  - `test/` - Test scripts
  - `download/` - Download scripts
  - `agents/` - UltraThink agents
- `tests/` - Test suite
- `logs/` - Build logs
- `proxmox_integration/` - Proxmox VE integration
- `bootloaders/` - Boot configuration
- `archive/` - Archived files

## Important Files
- Main build: `make build`
- Clean: `make clean`
- Help: `make help`
EOF

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════════"
echo "                    Cleanup Complete"
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "Files organized into:"
echo "  📁 scripts/build/     - Build scripts"
echo "  📁 scripts/fix/       - Fix scripts"
echo "  📁 scripts/test/      - Test scripts"
echo "  📁 scripts/download/  - Download scripts"
echo "  📁 scripts/agents/    - UltraThink agents"
echo "  📁 docs/checkpoints/  - Checkpoint files"
echo "  📁 archive/           - Archived files"
echo ""
echo "Root directory now contains only essential files."
echo "See DIRECTORY_STRUCTURE.md for details."