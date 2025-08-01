#!/bin/bash
# Wrapper to run minimal ZFS build with sudo

SUDO_PASS="1786"
echo "$SUDO_PASS" | sudo -S /opt/github/Z-FORGE/zfs-builds/zfs-2.3.3/build-zfs-2.3.3-minimal.sh