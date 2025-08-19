# =============================================================================
# /etc/zfs-backup/config.conf - Configuration for local ZFS backup v2.0
# =============================================================================

# Source dataset to backup (will recurse into child datasets by default)
SRC_DATASET="tank/data"

# Local destination dataset (e.g., on different pool or mirror)
DST_DATASET="backup/data"

# Logging and state directories
LOG_DIR="/var/log/zfs-backup"
METRICS_DIR="/var/lib/zfs-backup/metrics"
STATE_DIR="/var/lib/zfs-backup/state"

# Retention policies
RETENTION_DAYS=30      # Keep snapshots for N days (0 = disabled)
RETENTION_COUNT=0      # Keep N most recent snapshots (0 = use days)

# Backup behavior
RECURSIVE=true         # Recursively snapshot/send child datasets
CREATE_PARENT=true     # Auto-create parent datasets at destination
VERIFY_TRANSFER=true   # Verify snapshot after transfer

# Performance tuning
COMPRESSION="lz4"      # Compression algorithm (none, lz4, gzip, zstd)
ENABLE_MBUFFER=true    # Use mbuffer for better performance
MBUFFER_SIZE="1G"      # Memory buffer size (requires mbuffer installed)

# Snapshot naming
SNAPSHOT_PREFIX="autosnap"

# Hook scripts (must be executable)
# PRE_BACKUP_HOOK="/etc/zfs-backup/hooks/pre-backup.sh"
# POST_BACKUP_HOOK="/etc/zfs-backup/hooks/post-backup.sh"

# Health check URL (for integration with monitoring systems)
# The script will ping this URL on success, or append /fail on failure
# HEALTH_CHECK_URL="https://hc-ping.com/your-uuid-here"

# =============================================================================
# /etc/systemd/system/zfs-backup-local@.service - Systemd service unit
# =============================================================================
[Unit]
Description=Local ZFS Backup for %i
After=zfs.target
Requires=zfs.target

[Service]
Type=oneshot
Environment="SRC_DATASET=%i"
EnvironmentFile=-/etc/zfs-backup/config.conf
ExecStart=/usr/local/bin/zfs-backup-local.sh
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/zfs-backup /var/lib/zfs-backup /var/run

# Resource limits
CPUQuota=80%
MemoryLimit=4G
IOWeight=10
TasksMax=50

# Timeouts
TimeoutStartSec=0
TimeoutStopSec=4h

[Install]
WantedBy=multi-user.target

# =============================================================================
# /etc/systemd/system/zfs-backup-local@.timer - Systemd timer unit
# =============================================================================
[Unit]
Description=Daily Local ZFS Backup for %i
Documentation=man:zfs(8)

[Timer]
# Run daily at 2 AM
OnCalendar=daily
AccuracySec=1h
Persistent=true

[Install]
WantedBy=timers.target

# =============================================================================
# /etc/zfs-backup/hooks/pre-backup.sh - Example pre-backup hook
# =============================================================================
#!/bin/bash
# Pre-backup hook - called before snapshot creation
# Arguments: $1 = source dataset, $2 = destination dataset

set -euo pipefail

SRC_DATASET="$1"
DST_DATASET="$2"
LOG_FILE="/var/log/zfs-backup/hooks.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [PRE-BACKUP] $*" | tee -a "${LOG_FILE}"
}

# Check pool health
check_pool_health() {
    local pool="$1"
    if ! zpool status -x "${pool}" | grep -q "pool.*ONLINE"; then
        log "ERROR: Pool ${pool} is not healthy"
        return 1
    fi
    return 0
}

# Check both source and destination pools
SRC_POOL="${SRC_DATASET%%/*}"
DST_POOL="${DST_DATASET%%/*}"

log "Checking pool health for ${SRC_POOL} and ${DST_POOL}"
check_pool_health "${SRC_POOL}" || exit 1
check_pool_health "${DST_POOL}" || exit 1

# Example: Sync filesystem caches
log "Syncing filesystem caches"
sync

# Example: Application-specific preparation
# If you have databases or applications that need quiescing:
# systemctl stop myapp || true
# sleep 2

log "Pre-backup checks completed successfully"
exit 0

# =============================================================================
# /etc/zfs-backup/hooks/post-backup.sh - Example post-backup hook
# =============================================================================
#!/bin/bash
# Post-backup hook - called after backup completion
# Arguments: $1 = source dataset, $2 = destination dataset, $3 = exit code

set -euo pipefail

SRC_DATASET="$1"
DST_DATASET="$2"
EXIT_CODE="$3"
LOG_FILE="/var/log/zfs-backup/hooks.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [POST-BACKUP] $*" | tee -a "${LOG_FILE}"
}

# Log result
if [[ ${EXIT_CODE} -eq 0 ]]; then
    log "SUCCESS: Backup completed for ${SRC_DATASET} → ${DST_DATASET}"
    
    # Example: Update monitoring system
    # echo "backup.success:1|c" | nc -u -w1 statsd.local 8125
    
    # Example: Send success notification
    # echo "ZFS backup completed: ${SRC_DATASET}" | \
    #     mail -s "Backup Success" admin@example.com
else
    log "FAILURE: Backup failed for ${SRC_DATASET} → ${DST_DATASET} (exit: ${EXIT_CODE})"
    
    # Example: Send alert
    # echo "ZFS backup FAILED for ${SRC_DATASET}! Check logs at ${LOG_FILE}" | \
    #     mail -s "URGENT: Backup Failure" admin@example.com
fi

# Example: Restart applications if they were stopped
# systemctl start myapp || true

# Example: Clean up old log files (keep 30 days)
find /var/log/zfs-backup -name "*.log" -mtime +30 -delete 2>/dev/null || true

exit 0

# =============================================================================
# Installation Instructions
# =============================================================================
# 
# 1. Install the backup script:
#    sudo cp zfs-backup-local.sh /usr/local/bin/
#    sudo chmod +x /usr/local/bin/zfs-backup-local.sh
#
# 2. Create required directories:
#    sudo mkdir -p /etc/zfs-backup/hooks
#    sudo mkdir -p /var/log/zfs-backup
#    sudo mkdir -p /var/lib/zfs-backup/{metrics,state}
#
# 3. Install configuration:
#    sudo cp config.conf /etc/zfs-backup/
#    sudo chmod 644 /etc/zfs-backup/config.conf
#
# 4. Install systemd units:
#    sudo cp zfs-backup-local@.service /etc/systemd/system/
#    sudo cp zfs-backup-local@.timer /etc/systemd/system/
#    sudo systemctl daemon-reload
#
# 5. Enable for specific datasets (replace 'tank-data' with your dataset):
#    sudo systemctl enable --now zfs-backup-local@tank-data.timer
#
# 6. (Optional) Install mbuffer for better performance:
#    sudo apt-get install mbuffer    # Debian/Ubuntu
#    sudo yum install mbuffer         # RHEL/CentOS
#    sudo pkg install mbuffer         # FreeBSD
#
# 7. (Optional) Set up hooks:
#    sudo cp pre-backup.sh post-backup.sh /etc/zfs-backup/hooks/
#    sudo chmod +x /etc/zfs-backup/hooks/*.sh
#
# 8. Test the backup:
#    sudo /usr/local/bin/zfs-backup-local.sh
#
# 9. Check backup status:
#    sudo /usr/local/bin/zfs-backup-local.sh --status
#    sudo journalctl -u zfs-backup-local@tank-data
#
# =============================================================================
# Usage Examples
# =============================================================================
#
# 1. Manual backup with custom settings:
#    SRC_DATASET=tank/important DST_DATASET=backup/important \
#    RETENTION_DAYS=7 /usr/local/bin/zfs-backup-local.sh
#
# 2. Dry run (view what would be backed up):
#    zfs list -t snapshot -o name,used,creation -r tank/data
#
# 3. Monitor backup metrics:
#    tail -f /var/lib/zfs-backup/metrics/backup_metrics_*.log
#
# 4. Enable backups for multiple datasets:
#    for ds in tank/data tank/home tank/vms; do
#        sudo systemctl enable --now zfs-backup-local@${ds//\//-}.timer
#    done
#
# =============================================================================
