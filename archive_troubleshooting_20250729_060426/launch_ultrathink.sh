#!/bin/bash
# Launcher for UltraThink Multi-Agent System

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║          UltraThink Multi-Agent System Launcher           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "This script requires sudo privileges."
    echo "Relaunching with sudo..."
    exec sudo "$0" "$@"
fi

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 is required but not installed"
    echo "Please install Python 3 and try again"
    exit 1
fi

# Launch UltraThink
echo "🚀 Launching UltraThink Multi-Agent System..."
echo "This will:"
echo "  1. Deploy diagnostic agents to analyze the problem"
echo "  2. Repair DPKG and APT issues"
echo "  3. Fix repository configuration for Trixie"
echo "  4. Try multiple kernel installation strategies in parallel"
echo "  5. Install ZFS with DKMS support"
echo "  6. Verify the system is properly fixed"
echo
echo "Press Enter to continue or Ctrl+C to cancel..."
read -r

# Run the UltraThink system
python3 /opt/github/Z-FORGE/ultrathink_kernel_fix.py

# Check exit code
if [ $? -eq 0 ]; then
    echo
    echo "✅ UltraThink completed successfully!"
else
    echo
    echo "❌ UltraThink encountered issues."
    echo
    echo "Would you like to try the fallback manual fix? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "Running fallback fix..."
        /opt/github/Z-FORGE/ultrathink_fallback.sh
    fi
fi