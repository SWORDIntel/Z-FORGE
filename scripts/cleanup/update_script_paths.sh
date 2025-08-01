#!/bin/bash
# Z-FORGE Script Path Update Tool
# Updates scripts to use consistent workspace paths

set -e

echo "════════════════════════════════════════════════════════════════════"
echo "           Z-FORGE Script Path Update Tool"
echo "════════════════════════════════════════════════════════════════════"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Counters
SCRIPTS_CHECKED=0
SCRIPTS_WITH_OLD_PATHS=0
SCRIPTS_UPDATED=0

# Backup directory for modified scripts
BACKUP_DIR="$PROJECT_ROOT/backup/script_updates_$(date +%Y%m%d_%H%M%S)"

# Patterns to search for
OLD_PATTERNS=(
    "${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}"
    "${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}_"
    "WORKSPACE=/tmp/zforge"
    "CHROOT_PATH=/tmp/zforge"
)

# Function to check if file contains old paths
check_script() {
    local file="$1"
    local found=false
    
    for pattern in "${OLD_PATTERNS[@]}"; do
        if grep -q "$pattern" "$file" 2>/dev/null; then
            found=true
            break
        fi
    done
    
    echo "$found"
}

# Function to display file with old paths highlighted
show_old_paths() {
    local file="$1"
    
    echo -e "\n${BLUE}File: $file${NC}"
    echo "---"
    
    for pattern in "${OLD_PATTERNS[@]}"; do
        grep -n "$pattern" "$file" 2>/dev/null | while read -r line; do
            echo -e "${YELLOW}$line${NC}"
        done
    done
}

# Find all shell scripts
echo "Scanning for shell scripts..."
echo ""

# Find scripts (excluding archive and backup directories)
SCRIPT_FILES=$(find "$PROJECT_ROOT" \
    -type f \
    -name "*.sh" \
    -not -path "*/archive/*" \
    -not -path "*/backup/*" \
    -not -path "*/.git/*" \
    -not -path "*/zfs-build/*" \
    2>/dev/null | sort)

# Check each script
echo "Checking scripts for old workspace paths..."
echo ""

SCRIPTS_TO_UPDATE=()

for script in $SCRIPT_FILES; do
    ((SCRIPTS_CHECKED++))
    
    if [ "$(check_script "$script")" = "true" ]; then
        ((SCRIPTS_WITH_OLD_PATHS++))
        relative_path="${script#$PROJECT_ROOT/}"
        SCRIPTS_TO_UPDATE+=("$relative_path")
        echo -e "${YELLOW}[FOUND]${NC} $relative_path"
    fi
done

echo ""
echo "Summary:"
echo "  Scripts checked: $SCRIPTS_CHECKED"
echo "  Scripts with old paths: $SCRIPTS_WITH_OLD_PATHS"

if [ $SCRIPTS_WITH_OLD_PATHS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ No scripts found with old workspace paths!${NC}"
    exit 0
fi

# Show details of scripts with old paths
echo ""
echo "Scripts containing old workspace paths:"
echo "======================================"

for script in "${SCRIPTS_TO_UPDATE[@]}"; do
    show_old_paths "$PROJECT_ROOT/$script"
done

# Ask if user wants to update
echo ""
echo "Recommended updates:"
echo "  ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace} -> \$HOME/zforge_workspace"
echo "  or use: \${ZFORGE_WORKSPACE:-\$HOME/zforge_workspace}"
echo ""
read -p "Would you like to update these scripts? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Update cancelled."
    echo ""
    echo "To manually update, edit the files and replace:"
    echo "  ${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}"
    echo "with:"
    echo "  \${ZFORGE_WORKSPACE:-\$HOME/zforge_workspace}"
    exit 0
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"
echo ""
echo "Backing up scripts to: $BACKUP_DIR"

# Update scripts
echo ""
echo "Updating scripts..."
echo ""

for script in "${SCRIPTS_TO_UPDATE[@]}"; do
    full_path="$PROJECT_ROOT/$script"
    backup_path="$BACKUP_DIR/$script"
    
    # Create backup
    mkdir -p "$(dirname "$backup_path")"
    cp "$full_path" "$backup_path"
    
    # Create temporary file for updates
    temp_file=$(mktemp)
    
    # Apply updates
    sed -e 's|${ZFORGE_WORKSPACE:-/home/john/zforge_workspace}|${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}|g' \
        -e 's|WORKSPACE=/tmp/zforge|WORKSPACE=${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}|g' \
        -e 's|CHROOT_PATH=/tmp/zforge|CHROOT_PATH=${ZFORGE_WORKSPACE:-$HOME/zforge_workspace}|g' \
        "$full_path" > "$temp_file"
    
    # Check if changes were made
    if ! cmp -s "$full_path" "$temp_file"; then
        mv "$temp_file" "$full_path"
        echo -e "${GREEN}[UPDATED]${NC} $script"
        ((SCRIPTS_UPDATED++))
    else
        rm "$temp_file"
        echo -e "${YELLOW}[NO CHANGE]${NC} $script"
    fi
done

# Final summary
echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "                        Update Summary"
echo "════════════════════════════════════════════════════════════════════"
echo ""
echo "Scripts updated: $SCRIPTS_UPDATED"
echo "Backups saved to: $BACKUP_DIR"
echo ""

if [ $SCRIPTS_UPDATED -gt 0 ]; then
    echo -e "${GREEN}✅ Scripts updated successfully!${NC}"
    echo ""
    echo "To review changes:"
    echo "  diff -r $BACKUP_DIR $PROJECT_ROOT"
    echo ""
    echo "To restore original scripts:"
    echo "  cp -r $BACKUP_DIR/* $PROJECT_ROOT/"
else
    echo -e "${YELLOW}No scripts were updated.${NC}"
fi