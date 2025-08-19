# Z-FORGE Bootstrap Build Guide
## Progressive Build Strategy for Maximum Success

### 🎯 **Philosophy**
Build incrementally from minimal working system to full Proxmox VE 9 on Trixie, validating each stage before proceeding.

---

## 📋 **Bootstrap Phases**

### **Phase 0: Environment Preparation**
```bash
# Create logs and workspace
mkdir -p logs bootstrap_results
sudo rm -rf /tmp/zforge-workspace-* 2>/dev/null || true

# Verify system resources
echo "=== Pre-Bootstrap System Check ===" | tee logs/bootstrap-prep-$(date +%Y%m%d_%H%M%S).log
free -h | tee -a logs/bootstrap-prep-$(date +%Y%m%d_%H%M%S).log
df -h /tmp | tee -a logs/bootstrap-prep-$(date +%Y%m%d_%H%M%S).log
```

### **Phase 1: Minimal Working Build (5 minutes)**
**Goal:** Validate core build system and RAM workspace
```bash
sudo python3 build.py --spec build_specs/build_spec_working.yml --verbose --debug 2>&1 | tee "logs/phase1-minimal-$(date +%Y%m%d_%H%M%S).log"
```
**Success Criteria:** 
- ✅ Debootstrap completes
- ✅ Basic chroot environment created
- ✅ RAM workspace functions properly

### **Phase 2: ZFS Core Build (10 minutes)**
**Goal:** Add ZFS without Proxmox complications
```bash
sudo python3 build.py --spec build_specs/build_spec_no_proxmox.yml --verbose --debug 2>&1 | tee "logs/phase2-zfs-core-$(date +%Y%m%d_%H%M%S).log"
```
**Success Criteria:**
- ✅ ZFS 2.3.3 builds successfully
- ✅ Kernel modules compile
- ✅ No Proxmox conflicts

### **Phase 3: Advanced ZFS Build (15 minutes)**
**Goal:** Full ZFS features with optimization
```bash
sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml --verbose --debug 2>&1 | tee "logs/phase3-zfs-advanced-$(date +%Y%m%d_%H%M%S).log"
```
**Success Criteria:**
- ✅ ZFS encryption works
- ✅ Advanced compression algorithms
- ✅ Outside package strategy succeeds

### **Phase 4: Trixie Clean Build (20 minutes)**
**Goal:** Validate Trixie repository stability
```bash
sudo python3 build.py --spec build_specs/build_spec_trixie_clean.yml --verbose --debug 2>&1 | tee "logs/phase4-trixie-clean-$(date +%Y%m%d_%H%M%S).log"
```
**Success Criteria:**
- ✅ Trixie packages install cleanly
- ✅ No repository conflicts
- ✅ System boots correctly

### **Phase 5: Proxmox VE 9 Basic (30 minutes)**
**Goal:** Minimal Proxmox VE 9 on Trixie
```bash
sudo python3 build.py --spec build_specs/build_spec_proxmox9.yml --verbose --debug 2>&1 | tee "logs/phase5-pve9-basic-$(date +%Y%m%d_%H%M%S).log"
```
**Success Criteria:**
- ✅ Trixie-native virtualization stack
- ✅ Basic PVE 9 functionality
- ✅ Web interface accessible

### **Phase 6: Full Proxmox VE 9 System (45 minutes)**
**Goal:** Complete Proxmox VE 9 with all features
```bash
sudo python3 build.py --spec build_specs/build_spec_proxmox_full.yml --verbose --debug 2>&1 | tee "logs/phase6-pve9-full-$(date +%Y%m%d_%H%M%S).log"
```
**Success Criteria:**
- ✅ All 8 Proxmox modules complete
- ✅ Clustering and HA ready
- ✅ Complete ISO generation

### **Phase 7: Performance Validation (10 minutes)**
**Goal:** TMPFS optimized build for maximum performance
```bash
sudo python3 build.py --spec build_specs/build_spec_tmpfs.yml --verbose --debug 2>&1 | tee "logs/phase7-performance-$(date +%Y%m%d_%H%M%S).log"
```

---

## 🚀 **Automated Bootstrap Script**

### **Full Progressive Bootstrap**
```bash
#!/bin/bash
# Z-FORGE Progressive Bootstrap Script

set -e  # Exit on any error
LOGDIR="logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Phase definitions
declare -A PHASES=(
    ["1"]="build_spec_working.yml:Minimal Working Build"
    ["2"]="build_spec_no_proxmox.yml:ZFS Core Build"
    ["3"]="build_spec_outside_packages.yml:Advanced ZFS Build"
    ["4"]="build_spec_trixie_clean.yml:Trixie Clean Build"
    ["5"]="build_spec_proxmox9.yml:Proxmox VE 9 Basic"
    ["6"]="build_spec_proxmox_full.yml:Full Proxmox VE 9 System"
    ["7"]="build_spec_tmpfs.yml:Performance Validation"
)

echo "🚀 Starting Z-FORGE Progressive Bootstrap - $TIMESTAMP"
mkdir -p "$LOGDIR" bootstrap_results

# System preparation
echo "=== Phase 0: Environment Preparation ===" | tee "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
free -h | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
df -h /tmp | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"

# Execute phases
for phase in {1..7}; do
    IFS=':' read -r spec description <<< "${PHASES[$phase]}"
    
    echo "=== Phase $phase: $description ===" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
    echo "Building with: $spec" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
    
    start_time=$(date +%s)
    
    if sudo python3 build.py --spec "build_specs/$spec" --verbose --debug 2>&1 | tee "$LOGDIR/phase$phase-$description-$TIMESTAMP.log"; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo "✅ Phase $phase SUCCESS - Duration: ${duration}s" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
        
        # Save success artifact
        echo "SUCCESS: Phase $phase - $description" > "bootstrap_results/phase${phase}_success.txt"
    else
        echo "❌ Phase $phase FAILED - $description" | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
        echo "Bootstrap stopped at Phase $phase. Check logs for details."
        exit 1
    fi
    
    # Clean workspace between phases
    sudo rm -rf /tmp/zforge-workspace-* 2>/dev/null || true
    sleep 5
done

echo "🎉 Bootstrap Complete! All phases successful." | tee -a "$LOGDIR/bootstrap-summary-$TIMESTAMP.log"
```

### **Quick Bootstrap Commands**

**Save the script:**
```bash
cat > bootstrap_progressive.sh << 'EOF'
#!/bin/bash
# Z-FORGE Progressive Bootstrap Script
set -e
LOGDIR="logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

declare -A PHASES=(
    ["1"]="build_spec_working.yml:Minimal Working Build"
    ["2"]="build_spec_no_proxmox.yml:ZFS Core Build"
    ["3"]="build_spec_outside_packages.yml:Advanced ZFS Build"
    ["4"]="build_spec_proxmox9.yml:Proxmox VE 9 Basic"
    ["5"]="build_spec_proxmox_full.yml:Full Proxmox VE 9 System"
)

echo "🚀 Starting Z-FORGE Progressive Bootstrap - $TIMESTAMP"
mkdir -p "$LOGDIR" bootstrap_results

for phase in {1..5}; do
    IFS=':' read -r spec description <<< "${PHASES[$phase]}"
    echo "=== Phase $phase: $description ==="
    start_time=$(date +%s)
    
    if sudo python3 build.py --spec "build_specs/$spec" --verbose --debug 2>&1 | tee "$LOGDIR/phase$phase-$(echo $description | tr ' ' '_')-$TIMESTAMP.log"; then
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        echo "✅ Phase $phase SUCCESS - Duration: ${duration}s"
        echo "SUCCESS: Phase $phase - $description" > "bootstrap_results/phase${phase}_success.txt"
    else
        echo "❌ Phase $phase FAILED - $description"
        exit 1
    fi
    
    sudo rm -rf /tmp/zforge-workspace-* 2>/dev/null || true
    sleep 5
done

echo "🎉 Bootstrap Complete!"
EOF

chmod +x bootstrap_progressive.sh
```

**Execute Bootstrap:**
```bash
./bootstrap_progressive.sh
```

---

## 📊 **Success Tracking**

### **Monitor Progress:**
```bash
# Real-time monitoring
tail -f logs/*.log | grep -E "(Phase|SUCCESS|FAILED|Building|✅|❌)"

# Check bootstrap results
ls -la bootstrap_results/
cat logs/bootstrap-summary-*.log
```

### **Failure Recovery:**
```bash
# Resume from specific phase
sudo python3 build.py --spec build_specs/build_spec_working.yml --resume --verbose --debug 2>&1 | tee logs/recovery-$(date +%Y%m%d_%H%M%S).log
```

---

## 🎯 **Current Active Build Specs (Trixie-Only)**

**All deprecated Bookworm specs moved to `build_specs/deprecated/`**

### **Active Specs:**
1. **build_spec_working.yml** - Minimal working modules
2. **build_spec_no_proxmox.yml** - ZFS-only build
3. **build_spec_outside_packages.yml** - High-performance ZFS
4. **build_spec_trixie_clean.yml** - Clean Trixie build
5. **build_spec_proxmox9.yml** - Basic Proxmox VE 9
6. **build_spec_proxmox_full.yml** - Complete Proxmox VE 9
7. **build_spec_tmpfs.yml** - Performance-optimized
8. **build_spec_no_tmp.yml** - Disk-based (compatibility)
9. **build_spec.yml** - Main full-featured build

All specs now use **RAM workspaces** for **3-5x performance** improvements! 🚀