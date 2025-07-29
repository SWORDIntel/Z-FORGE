#!/bin/bash
# Download from Debian archive

PACKAGES_DIR="/opt/github/Z-FORGE/archive_packages"
mkdir -p "$PACKAGES_DIR"
cd "$PACKAGES_DIR"

# Base URL for Debian archive
ARCHIVE_URL="http://deb.debian.org/debian/pool/main"

# Download specific packages
wget -c "$ARCHIVE_URL/b/bash/bash_5.2.15-2+b7_amd64.deb"
wget -c "$ARCHIVE_URL/c/coreutils/coreutils_9.1-1_amd64.deb"
wget -c "$ARCHIVE_URL/g/glibc/libc6_2.36-9+deb12u9_amd64.deb"
wget -c "$ARCHIVE_URL/g/gcc-12/libgcc-s1_12.2.0-14_amd64.deb"
wget -c "$ARCHIVE_URL/g/gcc-12/gcc-12-base_12.2.0-14_amd64.deb"
wget -c "$ARCHIVE_URL/s/systemd/systemd_252.30-1~deb12u2_amd64.deb"
wget -c "$ARCHIVE_URL/s/systemd/libsystemd0_252.30-1~deb12u2_amd64.deb"
wget -c "$ARCHIVE_URL/s/systemd/systemd-sysv_252.30-1~deb12u2_all.deb"
wget -c "$ARCHIVE_URL/s/systemd/udev_252.30-1~deb12u2_amd64.deb"

echo "Download complete!"
echo "Packages in: $PACKAGES_DIR"
