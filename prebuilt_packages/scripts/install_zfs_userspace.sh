#!/bin/bash
# Install ZFS userspace tools

set -e

CHROOT_PATH="${1:-/tmp/zforge_workspace/chroot}"
SCRIPT_DIR="$(dirname "$0")"

echo "Installing ZFS userspace tools to $CHROOT_PATH"

# Extract files
tar -xzf "$SCRIPT_DIR/zfs-userspace-*.tar.gz" -C "$CHROOT_PATH"

# Update library cache
chroot "$CHROOT_PATH" ldconfig

echo "ZFS userspace tools installed!"
