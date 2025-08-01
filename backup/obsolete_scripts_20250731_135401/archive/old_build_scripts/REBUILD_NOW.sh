#!/bin/bash
# Z-FORGE Complete ISO Rebuild Launcher

clear

cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════════╗
║                    Z-FORGE COMPLETE ISO REBUILD                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  🚀 UltraThink Multi-Agent System v2.0                                   ║
║     Complete rebuild with perfect configuration                          ║
║                                                                          ║
║  This system will:                                                       ║
║    ✨ Analyze all current configuration issues                           ║
║    🔧 Create perfect Z-FORGE configuration files                         ║
║    🧹 Completely clean all workspaces and caches                        ║
║    🏗️  Rebuild the entire ISO from scratch                               ║
║    ✅ Verify everything is working correctly                             ║
║                                                                          ║
║  Key Improvements:                                                       ║
║    • Consistent Debian Trixie (testing) throughout                      ║
║    • Proper kernel 6.12.x installation from start                      ║
║    • ZFS packages compatible with kernel                                ║
║    • Clean APT sources configuration                                    ║
║    • No mixed stable/testing repositories                               ║
║                                                                          ║
║  ⚠️  WARNING: This will completely rebuild everything!                   ║
║     All existing workspace data will be lost.                           ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF

echo
echo "Estimated time: 30-60 minutes depending on your system"
echo "Required space: ~5GB free space recommended"
echo
echo "Press Enter to start the complete rebuild, or Ctrl+C to cancel..."
read -r

# Check if we need sudo
if [ "$EUID" -ne 0 ]; then
    echo "🔐 Requesting administrator privileges..."
    exec sudo "$0" "$@"
fi

# Launch the UltraThink rebuild system
echo
echo "🚀 Launching UltraThink ISO Rebuild System..."
echo

python3 /opt/github/Z-FORGE/ultrathink_iso_rebuild.py

# Check result
if [ $? -eq 0 ]; then
    echo
    echo "════════════════════════════════════════════════════════════════════"
    echo "🎉 SUCCESS! Your perfect Z-FORGE ISO has been created!"
    echo "════════════════════════════════════════════════════════════════════"
    echo
    echo "Your new ISO should be available at:"
    ls -la /opt/github/Z-FORGE/*.iso 2>/dev/null || echo "  (Check build directory for ISO files)"
    echo
    echo "Next steps:"
    echo "  1. Test the ISO in a VM to verify it works"
    echo "  2. Deploy to your target hardware"
    echo "  3. Enjoy your perfectly configured Proxmox system!"
    echo
else
    echo
    echo "════════════════════════════════════════════════════════════════════"
    echo "❌ The rebuild encountered issues."
    echo "════════════════════════════════════════════════════════════════════"
    echo
    echo "Check the logs for details:"
    echo "  - Main log: /opt/github/Z-FORGE/ultrathink_rebuild_*.log"  
    echo "  - Results: /opt/github/Z-FORGE/ultrathink_rebuild_results_*.json"
    echo
    echo "The perfect configuration files were still created and can be used manually:"
    echo "  - Perfect config: /opt/github/Z-FORGE/config/universal/universal_build_spec_perfect.yml"
    echo "  - Perfect build: /opt/github/Z-FORGE/perfect_build.sh"
fi

echo
echo "Rebuild process completed."