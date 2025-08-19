# Z-FORGE System Maintenance Guide

## Regular Maintenance Tasks

### Daily Checks (Automated)

#### System Health Monitoring
```bash
# Add to crontab for daily health checks
0 6 * * * cd /opt/github/Z-FORGE && python3 builder/modules/build_pipeline_validator.py > /var/log/zforge/daily-health.log 2>&1
```

#### Log Rotation
```bash
# Clean old logs daily
0 2 * * * find /opt/github/Z-FORGE/logs -name "*.log" -mtime +7 -delete
```

### Weekly Maintenance

#### Validation Check
```bash
#!/bin/bash
# weekly-maintenance.sh
cd /opt/github/Z-FORGE

echo "=== Z-FORGE Weekly Maintenance $(date) ==="

# Run full validation
echo "Running system validation..."
python3 builder/modules/build_pipeline_validator.py

# Check APT permissions
echo "Checking APT permissions..."
ls -la /var/lib/apt/lists/partial/
ls -la /var/cache/apt/archives/partial/

# Clean temporary files
echo "Cleaning temporary files..."
find . -name "*.tmp" -delete
find . -name "*.bak" -delete

# Update package cache
apt update

echo "=== Maintenance Complete ==="
```

#### Workspace Cleanup
```bash
# Clean build workspaces
sudo rm -rf ~/zforge_workspace/temp/*
sudo rm -rf ~/zforge_workspace/cache/old/*
```

### Monthly Tasks

#### System Updates
```bash
# Update system packages
apt update && apt upgrade -y

# Update Python modules if needed
pip3 install --upgrade -r requirements.txt
```

#### Backup Important Configurations
```bash
# Backup build specifications
tar -czf backup/build-specs-$(date +%Y%m%d).tar.gz build_spec*.yml

# Backup custom configurations
tar -czf backup/configs-$(date +%Y%m%d).tar.gz config/
```

## Health Monitoring

### System Status Indicators

#### Perfect Health (Expected)
```bash
$ python3 builder/modules/build_pipeline_validator.py
Validation Results: ALL_CHECKS_PASSED
Checks: 100/100 passed
Critical: 0, Errors: 0, Warnings: 0
```

#### Warning Indicators
- Validation score < 100/100
- New warning messages
- Permission denied errors
- Module import failures

#### Critical Indicators
- Critical errors > 0
- Build failures
- System service failures
- Disk space < 5GB

### Monitoring Scripts

#### Health Check Script
```bash
#!/bin/bash
# health-check.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Z-FORGE Health Check $(date)"
echo "================================"

# Check validation score
VALIDATION=$(python3 builder/modules/build_pipeline_validator.py | grep "Checks:")
if [[ $VALIDATION == *"100/100 passed"* ]]; then
    echo -e "${GREEN}✓ Validation: PERFECT${NC}"
else
    echo -e "${RED}✗ Validation: ISSUES FOUND${NC}"
    echo "$VALIDATION"
fi

# Check disk space
DISK_FREE=$(df -h . | awk 'NR==2 {print $4}' | sed 's/G//')
if (( $(echo "$DISK_FREE > 10" | bc -l) )); then
    echo -e "${GREEN}✓ Disk Space: ${DISK_FREE}G available${NC}"
else
    echo -e "${YELLOW}⚠ Disk Space: Only ${DISK_FREE}G available${NC}"
fi

# Check APT permissions
if [[ -r /var/lib/apt/lists/partial/ ]]; then
    echo -e "${GREEN}✓ APT Permissions: OK${NC}"
else
    echo -e "${RED}✗ APT Permissions: ISSUES${NC}"
fi

# Check recent builds
if [[ -f /var/log/zforge/build.log ]]; then
    LAST_BUILD=$(stat -c %Y /var/log/zforge/build.log)
    CURRENT=$(date +%s)
    DAYS_SINCE=$(( (CURRENT - LAST_BUILD) / 86400 ))
    echo -e "${GREEN}✓ Last Build: ${DAYS_SINCE} days ago${NC}"
else
    echo -e "${YELLOW}⚠ No recent builds found${NC}"
fi

echo "================================"
```

### Alerting

#### Email Notifications
```bash
# Add to crontab for email alerts on issues
0 8 * * * cd /opt/github/Z-FORGE && ./scripts/maintenance/health-check.sh | mail -s "Z-FORGE Health Report" admin@example.com
```

#### Slack Integration
```bash
#!/bin/bash
# slack-notify.sh
WEBHOOK_URL="your-slack-webhook-url"

STATUS=$(python3 builder/modules/build_pipeline_validator.py | grep "Validation Results")

if [[ $STATUS != *"ALL_CHECKS_PASSED"* ]]; then
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"Z-FORGE Health Alert: $STATUS\"}" \
        $WEBHOOK_URL
fi
```

## Troubleshooting Common Issues

### APT Permission Problems

#### Symptoms
- Permission denied errors during builds
- Package download failures
- Cache access errors

#### Solution
```bash
# Fix APT permissions
sudo chown -R _apt:nogroup /var/lib/apt/lists/partial
sudo chmod 755 /var/lib/apt/lists/partial
sudo chown -R _apt:nogroup /var/cache/apt/archives/partial
sudo chmod 755 /var/cache/apt/archives/partial

# Verify fix
python3 builder/modules/build_pipeline_validator.py
```

### Validation Failures

#### Module Import Errors
```bash
# Check Python path and modules
python3 -c "import sys; print('\n'.join(sys.path))"
python3 scripts/test/check_python_imports.py
```

#### Missing Configuration
```bash
# Check for missing required fields
python3 scripts/test/show_validation_warnings.py

# Fix by adding required fields to build specs
```

### Build Failures

#### Workspace Issues
```bash
# Clean and recreate workspace
sudo rm -rf ~/zforge_workspace
mkdir -p ~/zforge_workspace/{temp,cache,chroot}
```

#### Chroot Problems
```bash
# Force cleanup chroot
sudo scripts/chroot/force_cleanup_chroot.sh

# Restart chroot services
sudo systemctl restart systemd-nspawn@zforge
```

### Performance Issues

#### Slow Builds
```bash
# Use prebuilt packages for speed
sudo python3 build.py --spec build_spec_outside_packages.yml

# Optimize workspace location
export ZFORGE_WORKSPACE="/fast/disk/workspace"
```

#### Memory Issues
```bash
# Monitor memory usage
watch -n 1 'free -h && ps aux --sort=-%mem | head -10'

# Reduce parallel jobs
export MAKEFLAGS="-j2"  # Instead of -j$(nproc)
```

## Backup and Recovery

### Configuration Backup
```bash
#!/bin/bash
# backup-config.sh

BACKUP_DIR="/backup/zforge/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup build specifications
cp build_spec*.yml "$BACKUP_DIR/"

# Backup custom configurations
cp -r config/ "$BACKUP_DIR/"

# Backup important scripts
cp -r scripts/custom/ "$BACKUP_DIR/" 2>/dev/null || true

# Create archive
tar -czf "$BACKUP_DIR.tar.gz" -C "$BACKUP_DIR" .
rm -rf "$BACKUP_DIR"

echo "Configuration backed up to $BACKUP_DIR.tar.gz"
```

### System Recovery
```bash
#!/bin/bash
# recovery.sh

echo "Z-FORGE System Recovery"
echo "======================"

# Reset to known good state
git checkout main
git pull origin main

# Restore from checkpoint
cp checkpoint/CHECKPOINT_20250803_APT_PERMISSIONS_PERFECT_VALIDATION.md ./CURRENT_STATE.md

# Fix common issues
sudo chown -R _apt:nogroup /var/lib/apt/lists/partial
sudo chmod 755 /var/lib/apt/lists/partial

# Validate system
python3 builder/modules/build_pipeline_validator.py

echo "Recovery complete. System should be operational."
```

## Performance Monitoring

### Build Time Tracking
```bash
# Track build performance
echo "$(date): Starting build" >> /var/log/zforge/performance.log
time sudo python3 build.py --spec build_spec_stable.yml
echo "$(date): Build completed" >> /var/log/zforge/performance.log
```

### Resource Usage Monitoring
```bash
# Monitor during builds
iostat -x 1 > /var/log/zforge/io-stats.log &
vmstat 1 > /var/log/zforge/memory-stats.log &
# Stop monitoring after build
```

## Update Procedures

### System Updates
```bash
# Safe update procedure
1. Create backup
2. Run health check
3. Update system packages
4. Update Z-FORGE components
5. Run validation
6. Test build process
```

### Configuration Updates
```bash
# Update build specifications
1. Backup current configs
2. Apply changes
3. Validate configurations
4. Test with small build
5. Deploy to production
```

The Z-FORGE system is designed for reliability and requires minimal maintenance when following these procedures.