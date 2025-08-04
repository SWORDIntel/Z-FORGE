#!/bin/bash
# Use the configuration that was working before

echo "=== Using proven working configuration ==="

# Check if we have the original working build_spec.yml
if [ -f "build_spec.yml.trixie_backup" ]; then
    echo "✓ Found backup of working configuration"
    cp build_spec.yml.trixie_backup build_spec.yml
    echo "✓ Restored original build_spec.yml"
else
    echo "Using current build_spec.yml"
fi

# Clean workspace for fresh start
echo "Cleaning workspace..."
sudo rm -rf ~/zforge_workspace/*

# Run the original build that was working
echo "Starting build with original configuration..."
sudo python3 build.py --spec build_spec.yml

echo "Build started with working configuration!"