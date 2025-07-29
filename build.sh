#!/bin/bash
# Simple Z-FORGE build script

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ ERROR: This script must be run with sudo"
   echo "Please run: sudo ./build.sh"
   exit 1
fi

echo "🚀 Starting Z-FORGE build..."
cd /opt/github/Z-FORGE/builder
python3 z-forge.py "$@"