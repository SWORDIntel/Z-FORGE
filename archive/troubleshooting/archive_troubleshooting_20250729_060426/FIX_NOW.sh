#!/bin/bash
# Z-FORGE Ultimate Fix Script

clear

cat << 'EOF'
╔════════════════════════════════════════════════════════════════════════╗
║                    Z-FORGE KERNEL/ZFS FIX SYSTEM                       ║
╠════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  This system will automatically fix your kernel and ZFS installation   ║
║  issues using the UltraThink Multi-Agent System.                      ║
║                                                                        ║
║  The UltraThink system deploys multiple specialized agents:            ║
║    • Diagnostic Agent - Analyzes all system issues                     ║
║    • Repair Agent - Fixes DPKG and APT problems                       ║
║    • Repository Agent - Configures correct Trixie sources              ║
║    • Kernel Agents - Try multiple installation strategies              ║
║    • ZFS Agent - Installs ZFS with DKMS support                       ║
║    • Verification Agent - Confirms everything is working               ║
║                                                                        ║
║  If the automatic system fails, a comprehensive fallback will run.     ║
║                                                                        ║
╚════════════════════════════════════════════════════════════════════════╝
EOF

echo
echo "Press Enter to start the fix process, or Ctrl+C to cancel..."
read -r

# Check if we need sudo
if [ "$EUID" -ne 0 ]; then
    echo "🔐 Requesting administrator privileges..."
    exec sudo "$0" "$@"
fi

# Run the launcher
echo
echo "🚀 Starting UltraThink Multi-Agent System..."
echo

/opt/github/Z-FORGE/launch_ultrathink.sh

# Check result
if [ $? -eq 0 ]; then
    echo
    echo "════════════════════════════════════════════════════════════════"
    echo "✅ SUCCESS! Your system has been fixed!"
    echo "════════════════════════════════════════════════════════════════"
    echo
    echo "The following has been completed:"
    echo "  • Debian Trixie kernel 6.12.x installed"
    echo "  • ZFS packages installed with DKMS support"
    echo "  • APT repositories configured correctly"
    echo "  • All package conflicts resolved"
    echo
else
    echo
    echo "════════════════════════════════════════════════════════════════"
    echo "❌ The automatic fix encountered issues."
    echo "════════════════════════════════════════════════════════════════"
    echo
    echo "Don't worry! We have a comprehensive fallback system."
    echo "The fallback will manually perform all necessary fixes."
    echo
    echo "Would you like to run the fallback fix? (recommended) [Y/n]"
    read -r response
    
    if [[ ! "$response" =~ ^[Nn]$ ]]; then
        echo
        echo "🔧 Running comprehensive fallback fix..."
        /opt/github/Z-FORGE/ultrathink_fallback.sh
    fi
fi

echo
echo "Fix process completed. Check the logs in /opt/github/Z-FORGE/ for details."
echo