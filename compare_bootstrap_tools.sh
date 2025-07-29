#!/bin/bash
# Compare debootstrap and cdebootstrap performance

echo "═══════════════════════════════════════════════════════════════════"
echo "        Bootstrap Tool Comparison for Z-FORGE"
echo "═══════════════════════════════════════════════════════════════════"
echo ""

# Check which tools are available
echo "Checking available tools..."
echo ""

if command -v debootstrap >/dev/null 2>&1; then
    echo "✅ debootstrap: $(debootstrap --version 2>&1 | head -1)"
    DEBOOTSTRAP_SIZE=$(du -sh $(which debootstrap) 2>/dev/null | cut -f1)
    echo "   Size: $DEBOOTSTRAP_SIZE"
    echo "   Type: Shell script"
    echo "   Features: Full-featured, supports variants, hooks, etc."
else
    echo "❌ debootstrap: Not installed"
    echo "   Install: sudo apt-get install debootstrap"
fi

echo ""

if command -v cdebootstrap >/dev/null 2>&1; then
    echo "✅ cdebootstrap: Available"
    CDEBOOTSTRAP_SIZE=$(du -sh $(which cdebootstrap) 2>/dev/null | cut -f1)
    echo "   Size: $CDEBOOTSTRAP_SIZE"
    echo "   Type: Compiled C binary"
    echo "   Features: Fast, minimal memory usage, basic options"
else
    echo "❌ cdebootstrap: Not installed"
    echo "   Install: sudo apt-get install cdebootstrap"
fi

echo ""
echo "Advantages:"
echo ""
echo "debootstrap:"
echo "  + More mature and widely used"
echo "  + Supports more options and variants"
echo "  + Better documentation"
echo "  + Can be customized with hooks"
echo "  - Slower (shell script)"
echo "  - Uses more memory"
echo ""
echo "cdebootstrap:"
echo "  + Much faster (C implementation)"
echo "  + Lower memory footprint"
echo "  + Good for automated builds"
echo "  + Supports most common use cases"
echo "  - Fewer customization options"
echo "  - Less documentation"
echo ""
echo "Recommendation for Z-FORGE:"
echo "- Use cdebootstrap if speed is important (CI/CD, frequent rebuilds)"
echo "- Use debootstrap if you need advanced features or customization"
echo "- The bootstrap_chroot.sh script supports both!"
echo ""
echo "Usage:"
echo "  sudo ./bootstrap_chroot.sh auto         # Auto-select best available"
echo "  sudo ./bootstrap_chroot.sh cdebootstrap # Use cdebootstrap"
echo "  sudo ./bootstrap_chroot.sh debootstrap  # Use debootstrap"