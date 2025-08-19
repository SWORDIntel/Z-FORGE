#!/bin/bash
# Z-FORGE Progressive Bootstrap Script
# Builds incrementally from minimal to full Proxmox VE 9 system

set -e  # Exit on any error
LOGDIR="logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Phase definitions - ordered by complexity
declare -A PHASES=(
    ["1"]="build_spec_working.yml:Minimal_Working_Build"
    ["2"]="build_spec_no_proxmox.yml:ZFS_Core_Build"
    ["3"]="build_spec_outside_packages.yml:Advanced_ZFS_Build"
    ["4"]="build_spec_trixie_clean.yml:Trixie_Clean_Build"
    ["5"]="build_spec_proxmox9.yml:Proxmox_VE9_Basic"
    ["6"]="build_spec_proxmox_full.yml:Full_Proxmox_VE9_System"
)

echo "🚀 Starting Z-FORGE Progressive Bootstrap - $TIMESTAMP"
echo "Target: Proxmox VE 9 on Debian Trixie (RAM-optimized builds)"
echo "========================================================"

# Create directories
mkdir -p "$LOGDIR" bootstrap_results

# System preparation
echo "=== Phase 0: Environment Preparation ===" | tee "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
echo "System Resources:" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
free -h | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
echo "TMPFS Status:" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
df -h /tmp | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
echo "Starting bootstrap at: $(date)" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"

# Clean any existing workspaces
echo "Cleaning previous build workspaces..."
sudo rm -rf /tmp/zforge-workspace-* 2>/dev/null || true

# Execute phases progressively
for phase in {1..6}; do
    IFS=':' read -r spec description <<< "${PHASES[$phase]}"
    
    echo "" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
    echo "=== Phase $phase: $(echo $description | tr '_' ' ') ===" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
    echo "Building with: $spec" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
    echo "Started at: $(date)" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
    
    start_time=$(date +%s)
    
    # Execute build with comprehensive logging
    if sudo python3 build.py --spec "build_specs/$spec" --verbose --debug 2>&1 | tee "$LOGDIR/phase${phase}-${description}-$TIMESTAMP.log"; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        
        echo "✅ Phase $phase SUCCESS - Duration: ${duration}s ($(($duration/60))m $(($duration%60))s)" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
        echo "Completed at: $(date)" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
        
        # Save success artifact with details
        cat > "bootstrap_results/phase${phase}_success.txt" << EOF
SUCCESS: Phase $phase - $(echo $description | tr '_' ' ')
Spec: $spec
Duration: ${duration}s
Completed: $(date)
EOF
        
        # Quick system check after each phase
        echo "Post-build system status:" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
        free -h | grep Mem | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
        
    else
        echo "❌ Phase $phase FAILED - $(echo $description | tr '_' ' ')" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
        echo "Failed at: $(date)" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
        echo ""
        echo "Bootstrap stopped at Phase $phase. Check logs for details:"
        echo "  Main log: $LOGDIR/phase${phase}-${description}-$TIMESTAMP.log"
        echo "  Summary:  $LOGDIR/bootstrap-summary-$TIMESTAMP.log"
        exit 1
    fi
    
    # Clean workspace between phases to ensure fresh start
    echo "Cleaning workspace before next phase..." | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
    sudo rm -rf /tmp/zforge-workspace-* 2>/dev/null || true
    
    # Brief pause to let system stabilize
    if [ $phase -lt 6 ]; then
        echo "Waiting 10 seconds before next phase..."
        sleep 10
    fi
done

# Final summary
echo "" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
echo "🎉 BOOTSTRAP COMPLETE! All phases successful." | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
echo "Final completion: $(date)" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
echo "" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"

# Generate final report
echo "📊 BOOTSTRAP RESULTS SUMMARY:" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
echo "=============================" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
ls -la bootstrap_results/ | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"

echo ""
echo "✅ Proxmox VE 9 on Trixie build system validated!"
echo "📁 Logs available in: $LOGDIR/"
echo "📁 Success markers in: bootstrap_results/"
echo "🚀 Ready for production builds!"