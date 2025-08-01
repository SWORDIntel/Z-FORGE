#!/bin/bash
# Perfect Z-FORGE build script

set -e

echo "🚀 Starting Perfect Z-FORGE Build"
echo "=================================="

# Use the perfect configuration
CONFIG_FILE="/opt/github/Z-FORGE/config/universal/universal_build_spec_perfect.yml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Perfect config file not found: $CONFIG_FILE"
    exit 1
fi

# Clean any existing workspace
echo "🧹 Cleaning workspace..."
sudo rm -rf /tmp/zforge_workspace_perfect /tmp/zforge_workspace

# Create perfect workspace
echo "📁 Creating perfect workspace..."
mkdir -p /tmp/zforge_workspace_perfect

# Run the build with perfect config
echo "🔨 Starting build with perfect configuration..."
cd /opt/github/Z-FORGE

# Use the perfect config
python3 build.py --config="$CONFIG_FILE" --clean --verbose

echo "✅ Perfect build completed!"
