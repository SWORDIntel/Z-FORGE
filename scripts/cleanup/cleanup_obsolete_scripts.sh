#!/bin/bash
# Z-FORGE Obsolete Script Cleanup
# Safely removes obsolete scripts identified in consistency analysis

set -e

echo "════════════════════════════════════════════════════════════════════"
echo "           Z-FORGE Obsolete Script Cleanup Tool"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Backup directory
BACKUP_DIR="$PROJECT_ROOT/backup/obsolete_scripts_$(date +%Y%m%d_%H%M%S)"

# Counters
FILES_REMOVED=0
FILES_BACKED_UP=0
ERRORS=0

# List of obsolete directories and files to remove
OBSOLETE_DIRS=(
    "archive/old_build_scripts"
    "archive/old_scripts"
    "archive/old_configs"
)

# Individual obsolete files (if any outside directories)
OBSOLETE_FILES=(
    # Add any specific files here if needed
)

# Function to safely remove a file or directory
safe_remove() {
    local path="$1"
    local full_path="$PROJECT_ROOT/$path"
    
    if [ ! -e "$full_path" ]; then
        echo -e "${YELLOW}[SKIP]${NC} Not found: $path"
        return 0
    fi
    
    # Create backup
    local backup_path="$BACKUP_DIR/$path"
    mkdir -p "$(dirname "$backup_path")"
    
    if cp -r "$full_path" "$backup_path" 2>/dev/null; then
        echo -e "${GREEN}[BACKUP]${NC} Backed up: $path"
        ((FILES_BACKED_UP++))
        
        # Remove the file/directory
        if rm -rf "$full_path"; then
            echo -e "${GREEN}[REMOVED]${NC} Deleted: $path"
            ((FILES_REMOVED++))
        else
            echo -e "${RED}[ERROR]${NC} Failed to remove: $path"
            ((ERRORS++))
        fi
    else
        echo -e "${RED}[ERROR]${NC} Failed to backup: $path"
        ((ERRORS++))
    fi
}

# Check if running from correct directory
if [ ! -f "$PROJECT_ROOT/README.md" ] || [ ! -d "$PROJECT_ROOT/scripts" ]; then
    echo -e "${RED}ERROR: Must be run from Z-FORGE project directory${NC}"
    echo "Current directory: $PROJECT_ROOT"
    exit 1
fi

# Create backup directory
echo "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Show what will be removed
echo ""
echo "The following obsolete items will be removed:"
echo "============================================="

for dir in "${OBSOLETE_DIRS[@]}"; do
    if [ -d "$PROJECT_ROOT/$dir" ]; then
        echo "  📁 $dir/"
        # Count files in directory
        file_count=$(find "$PROJECT_ROOT/$dir" -type f | wc -l)
        echo "     ($file_count files)"
    fi
done

for file in "${OBSOLETE_FILES[@]}"; do
    if [ -f "$PROJECT_ROOT/$file" ]; then
        echo "  📄 $file"
    fi
done

echo ""
read -p "Continue with cleanup? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# Remove obsolete directories
for dir in "${OBSOLETE_DIRS[@]}"; do
    safe_remove "$dir"
done

# Remove obsolete files
for file in "${OBSOLETE_FILES[@]}"; do
    safe_remove "$file"
done

# Summary
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "                        Cleanup Summary"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "Files backed up:  $FILES_BACKED_UP"
echo "Files removed:    $FILES_REMOVED"
echo "Errors:          $ERRORS"
echo ""
echo "Backup location: $BACKUP_DIR"

if [ $ERRORS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Cleanup completed successfully!${NC}"
    
    # Offer to remove empty archive directory
    if [ -d "$PROJECT_ROOT/archive" ]; then
        if [ -z "$(ls -A "$PROJECT_ROOT/archive")" ]; then
            echo ""
            read -p "Remove empty archive directory? [y/N] " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rmdir "$PROJECT_ROOT/archive" && echo -e "${GREEN}[REMOVED]${NC} Empty archive directory"
            fi
        fi
    fi
else
    echo ""
    echo -e "${RED}⚠️  Cleanup completed with errors. Check backup directory.${NC}"
fi

echo ""
echo "To restore backed up files:"
echo "  cp -r $BACKUP_DIR/* $PROJECT_ROOT/"
echo ""
echo "To permanently delete backups:"
echo "  rm -rf $BACKUP_DIR"