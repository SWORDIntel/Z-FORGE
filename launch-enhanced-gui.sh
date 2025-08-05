#!/bin/bash
#
# Z-FORGE Enhanced GUI Launcher
# With automatic failure recovery and intelligent analysis
#

echo "========================================"
echo "Z-FORGE Build System - Enhanced Edition"
echo "========================================"
echo ""
echo "Features:"
echo "  ✅ Automatic failure recovery"
echo "  ✅ Intelligent error analysis"
echo "  ✅ Pre-build validation"
echo "  ✅ Real-time monitoring"
echo "  ✅ Build success recommendations"
echo ""

# Check if running as root/sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ Z-FORGE Enhanced GUI must be run with sudo"
    echo ""
    echo "Reason: Z-FORGE requires root permissions for:"
    echo "  • Chroot operations and package installations"
    echo "  • tmpfs mounting for high-performance builds"
    echo "  • APT operations and repository management"
    echo "  • System-level hardware detection"
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

# Create workspace if it doesn't exist
WORKSPACE="/home/john/zforge_workspace"
if [ ! -d "$WORKSPACE" ]; then
    echo "Creating workspace at $WORKSPACE..."
    mkdir -p "$WORKSPACE"
fi

# Run quick system check
echo ""
echo "Running quick system check..."
python3 tools/build_diagnostic_tool.py 2>/dev/null | grep "SYSTEM READY" > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ System ready to build!"
else
    echo "⚠️  System has some issues - the GUI will help you fix them"
fi

echo ""
echo "Starting Enhanced GUI..."
echo ""

# Launch the enhanced GUI
python3 zforge_gui_enhanced.py

echo ""
echo "GUI closed."