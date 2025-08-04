#!/bin/bash
# Quick fix to use Debian Bookworm (stable) instead of Trixie

echo "=== Z-FORGE Quick Fix: Switch to Debian Bookworm ==="
echo "This will update your configuration to use stable Debian"
echo

# Backup current config
if [ -f "build_spec.yml" ]; then
    cp build_spec.yml build_spec.yml.trixie_backup
    echo "✓ Backed up current config to build_spec.yml.trixie_backup"
fi

# Update build_spec.yml to use bookworm
if [ -f "build_spec.yml" ]; then
    sed -i 's/debian_release: trixie/debian_release: bookworm/g' build_spec.yml
    sed -i 's/kernel_version: 6.9.7-amd64/kernel_version: 6.1.0-23-amd64/g' build_spec.yml
    echo "✓ Updated build_spec.yml to use Bookworm"
fi

# Create a minimal test config
cat > build_spec_minimal.yml << 'EOF'
# Minimal stable build for testing
builder_config:
  workspace_path: ~/zforge_workspace
  debian_release: bookworm
  debian_mirror: http://deb.debian.org/debian
  kernel_version: 6.1.0-23-amd64
  output_iso_name: zforge-minimal.iso
  iso_label: ZFORGE_MIN
  
modules:
  - name: workspace_setup
    enabled: true
  - name: debootstrap
    enabled: true
  - name: gpg_bypass
    enabled: true
  - name: chroot_setup
    enabled: true
  - name: kernel_acquisition
    enabled: true
  - name: live_environment
    enabled: true
  - name: squashfs
    enabled: true
  - name: iso_generation
    enabled: true
EOF

echo "✓ Created minimal test config: build_spec_minimal.yml"
echo

echo "=== Next Steps ==="
echo "1. For stable build with all features:"
echo "   sudo python3 build.py --spec build_spec_stable.yml"
echo
echo "2. For minimal test build:"
echo "   sudo python3 build.py --spec build_spec_minimal.yml"
echo
echo "3. For enhanced stable build with validation:"
echo "   sudo python3 scripts/build_stable.py"
echo
echo "The stable builds use Debian Bookworm which is much more reliable!"