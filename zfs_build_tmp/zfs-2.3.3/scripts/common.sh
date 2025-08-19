#!/bin/sh

# Directories
export BIN_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/tests/zfs-tests/bin
export SBIN_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3
export LIBEXEC_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3
export ZTS_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/tests
export SCRIPT_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/scripts

# General commands
export ZDB="${ZDB:-$SBIN_DIR/zdb}"
export ZFS="${ZFS:-$SBIN_DIR/zfs}"
export ZPOOL="${ZPOOL:-$SBIN_DIR/zpool}"
export ZTEST="${ZTEST:-$SBIN_DIR/ztest}"
export ZFS_SH="${ZFS_SH:-$SCRIPT_DIR/zfs.sh}"

# Test Suite
export RUNFILE_DIR="${RUNFILE_DIR:-$ZTS_DIR/runfiles}"
export TEST_RUNNER="${TEST_RUNNER:-$ZTS_DIR/test-runner/bin/test-runner.py}"
export ZTS_REPORT="${ZTS_REPORT:-$ZTS_DIR/test-runner/bin/zts-report.py}"
export STF_TOOLS="${STF_TOOLS:-$ZTS_DIR/test-runner}"
export STF_SUITE="${STF_SUITE:-$ZTS_DIR/zfs-tests}"

# Only required for in-tree use
export INTREE="yes"
export GDB="libtool --mode=execute gdb"
export LDMOD=/sbin/insmod

export CMD_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3
export UDEV_SCRIPT_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/udev
export UDEV_CMD_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/udev
export UDEV_RULE_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/udev/rules.d
export ZEDLET_ETC_DIR=$CMD_DIR/cmd/zed/zed.d
export ZEDLET_LIBEXEC_DIR=$CMD_DIR/cmd/zed/zed.d
export ZPOOL_SCRIPT_DIR=$CMD_DIR/cmd/zpool/zpool.d
export ZPOOL_SCRIPTS_PATH=$CMD_DIR/cmd/zpool/zpool.d
export ZPOOL_COMPAT_DIR=$CMD_DIR/cmd/zpool/compatibility.d
export CONTRIB_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/contrib
export LIB_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/.libs
export SYSCONF_DIR=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/etc

export INSTALL_UDEV_DIR=/lib/udev
export INSTALL_UDEV_RULE_DIR=/lib/udev/rules.d
export INSTALL_MOUNT_HELPER_DIR=/sbin
export INSTALL_SYSCONF_DIR=/etc
export INSTALL_PYTHON_DIR=/usr/lib/python3.13/site-packages
export INSTALL_PKGDATA_DIR=/usr/share/zfs

export KMOD_SPL=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/module/spl.ko
export KMOD_ZFS=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/module/zfs.ko
export KMOD_FREEBSD=/opt/github/Z-FORGE/zfs_build_tmp/zfs-2.3.3/module/openzfs.ko
