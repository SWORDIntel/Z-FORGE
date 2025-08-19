#!/bin/bash
#
# Z-FORGE Enhanced GUI Launcher
# With automatic failure recovery and intelligent analysis
#

echo "======================================================"
echo "Z-FORGE RAM Server Build System v3.0 - Enhanced Edition"
echo "======================================================"
echo ""
echo "NEW FEATURES:"
echo "  ✅ ALL builds now use RAM workspaces (/dev/shm) for 3-5x performance"
echo "  ✅ ALL builds include FULL Proxmox VE 9 (not minimal)"
echo "  ✅ ALL builds include ZFS 2.3.3 with encryption + compression"
echo "  ✅ ALL builds use Debian Trixie as base OS"
echo "  ✅ Automatic failure recovery and intelligent error analysis"
echo "  ✅ Real-time monitoring with build success recommendations"
echo ""

# Check if running as root/sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ Z-FORGE Enhanced GUI must be run with sudo"
    echo ""
    echo "Reason: Z-FORGE RAM Server Build requires root permissions for:"
    echo "  • RAM workspace creation in /dev/shm"
    echo "  • Chroot operations and server package installations"
    echo "  • Proxmox VE 9 server component installations"
    echo "  • ZFS 2.3.3 module building and configuration"
    echo "  • APT operations and repository management"
    echo "  • System-level hardware detection for server optimization"
    echo ""
    echo "Please run: sudo ./launch-enhanced-gui.sh"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "Please install: sudo apt-get install python3"
    exit 1
fi

# Check required Python modules
echo "Checking dependencies..."
python3 -c "import tkinter" 2>/dev/null || {
    echo "❌ tkinter not installed"
    echo "Installing: sudo apt-get install python3-tk"
    sudo apt-get install -y python3-tk
}

python3 -c "import yaml" 2>/dev/null || {
    echo "❌ PyYAML not installed"
    echo "Installing: pip3 install pyyaml"
    pip3 install pyyaml
}

python3 -c "import psutil" 2>/dev/null || {
    echo "❌ psutil not installed"
    echo "Installing: pip3 install psutil"
    pip3 install psutil
}

# Check if in correct directory
if [ ! -f "build.py" ]; then
    echo "❌ Error: Not in Z-FORGE directory"
    echo "Please cd to the Z-FORGE root directory first"
    exit 1
fi

# Create RAM workspace if it doesn't exist (all builds now use /dev/shm)
WORKSPACE="/dev/shm/zforge-workspace"
if [ ! -d "$WORKSPACE" ]; then
    echo "Creating RAM workspace at $WORKSPACE for 3-5x performance..."
    mkdir -p "$WORKSPACE"
    echo "📈 RAM Build Mode: All server builds use /dev/shm workspace"
fi

# Run quick system check
echo ""
echo "Running quick system check..."
python3 tools/build_diagnostic_tool.py 2>/dev/null | grep "SYSTEM READY" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ System ready to build RAM-based Proxmox VE 9 servers!"
else
    echo "⚠️  System has some issues - the enhanced GUI will help you fix them for RAM server builds"
fi

echo ""
echo "Starting Enhanced GUI..."
echo ""

# Launch the enhanced GUI
python3 zforge_gui_enhanced.py

echo ""
echo "GUI closed."