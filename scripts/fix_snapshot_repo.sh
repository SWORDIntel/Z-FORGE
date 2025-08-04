#!/bin/bash
# Fix the snapshot repository structure

echo "=== Fixing Trixie snapshot repository ==="

SNAPSHOT_DIR="/root/zforge_cache/trixie_snapshot"
REPO_DIR="$SNAPSHOT_DIR/repository"
PACKAGES_DIR="$SNAPSHOT_DIR/packages"

echo "Checking snapshot structure..."
ls -la "$SNAPSHOT_DIR/" 2>/dev/null || echo "Snapshot dir not found"
ls -la "$REPO_DIR/" 2>/dev/null || echo "Repository dir not found"
ls -la "$PACKAGES_DIR/" 2>/dev/null || echo "Packages dir not found"

# Check if we have the actual .deb files
echo "Checking for .deb files..."
find "$SNAPSHOT_DIR" -name "*.deb" | head -5

# If repository directory exists but is broken, recreate it
if [ -d "$PACKAGES_DIR" ] && [ "$(find "$PACKAGES_DIR" -name "*.deb" | wc -l)" -gt 0 ]; then
    echo "Found .deb files, recreating repository..."
    
    # Create/clean repository directory
    mkdir -p "$REPO_DIR"
    rm -f "$REPO_DIR"/*
    
    # Copy all .deb files to repository
    cp "$PACKAGES_DIR"/*.deb "$REPO_DIR"/ 2>/dev/null || echo "No .deb files to copy"
    
    # Generate Packages file
    cd "$REPO_DIR"
    dpkg-scanpackages . /dev/null > Packages
    gzip -c Packages > Packages.gz
    
    echo "✓ Repository recreated with $(ls *.deb 2>/dev/null | wc -l) packages"
    echo "✓ Packages file created: $(wc -l Packages)"
    
    # Create Release file
    cat > Release << EOF
Origin: Z-FORGE Trixie Snapshot
Label: Z-FORGE Trixie Snapshot
Suite: trixie-snapshot
Codename: trixie-snapshot
Date: $(date -R)
Architectures: amd64
Components: main
Description: Trixie package snapshot for stable builds
EOF
    
    echo "✓ Release file created"
    
else
    echo "✗ No .deb files found in snapshot"
    echo "Available directories:"
    find "$SNAPSHOT_DIR" -type d 2>/dev/null
fi

echo "Repository fix complete!"