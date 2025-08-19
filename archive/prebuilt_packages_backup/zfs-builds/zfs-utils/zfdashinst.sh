#!/usr/bin/env bash
# repair_zfdash.sh  —  Re-deploy daemon & polkit policy
set -Eeuo pipefail
LOG=/var/log/repair_zfdash.log
exec > >(tee -a "$LOG") 2>&1

echo "[INFO] $(date -u +'%F %T')  starting ZfDash repair"

SRC=${1:-"$HOME/src/zfdash"}             # path to cloned repo
DAEMON=/opt/zfdash/bin/zfdash_daemon
POLICY=com.zfdash.policy
POLKIT_DIR=/usr/share/polkit-1/actions

echo "[INFO] Installing Python deps"
python3 -m pip install --upgrade -r "$SRC/requirements.txt"

echo "[INFO] Deploying daemon"
install -D -m755 "$SRC/src/zfdash_daemon.py" "$DAEMON"

echo "[INFO] Deploying polkit policy"
install -D -m644 "$SRC/install_service/$POLICY" "$POLKIT_DIR/$POLICY"

echo "[INFO] Validating"
pkexec --disable-internal-agent "$DAEMON" --check || {
    echo "[ERROR] Daemon still fails"; exit 1; }

echo "[INFO] Repair complete"

