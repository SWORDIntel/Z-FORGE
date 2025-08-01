#!/bin/bash
# Extract essential packages from Debian ISO or create minimal bootstrap
# Alternative approach to package installation

set -e

echo "═══════════════════════════════════════════════════════════════════"
echo "          Alternative Package Installation Methods"
echo "═══════════════════════════════════════════════════════════════════"

WORK_DIR="/opt/github/Z-FORGE/debian_packages"
mkdir -p "$WORK_DIR"

echo ""
echo "Option 1: Download Debian netinst ISO and extract packages"
echo "==========================================================="
echo ""
echo "wget https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.8.0-amd64-netinst.iso"
echo "mkdir -p /tmp/debian_iso"
echo "sudo mount -o loop debian-*.iso /tmp/debian_iso"
echo "cp /tmp/debian_iso/pool/main/*/*.deb $WORK_DIR/"
echo "sudo umount /tmp/debian_iso"
echo ""

echo "Option 2: Use debootstrap to create minimal system"
echo "==================================================="
echo ""
echo "sudo apt-get install debootstrap"
echo "sudo debootstrap --variant=minbase trixie ${CHROOT_PATH:-/home/john/zforge_workspace/chroot} http://deb.debian.org/debian"
echo ""

echo "Option 3: Manual minimal bootstrap"
echo "==================================="
echo ""

cat > "$WORK_DIR/manual_bootstrap.sh" << 'EOFBOOT'
#!/bin/bash
# Manual minimal bootstrap for chroot

set -e

CHROOT="${1:-${CHROOT_PATH:-/home/john/zforge_workspace/chroot}}"

echo "Creating minimal bootstrap in $CHROOT..."

# Create directory structure
mkdir -p "$CHROOT"/{bin,sbin,lib,lib64,usr/{bin,sbin,lib},etc,proc,sys,dev,tmp,var/{lib/dpkg,cache/apt,log}}

# Copy essential binaries from host
ESSENTIALS=(
    /bin/bash
    /bin/sh
    /bin/ls
    /bin/cat
    /bin/echo
    /bin/mkdir
    /bin/rm
    /bin/cp
    /bin/mv
    /bin/chmod
    /bin/chown
    /usr/bin/env
    /usr/bin/dpkg
    /usr/bin/apt-get
)

echo "Copying essential binaries..."
for bin in "${ESSENTIALS[@]}"; do
    if [ -f "$bin" ]; then
        cp "$bin" "$CHROOT$bin" 2>/dev/null || true
        # Copy libraries
        for lib in $(ldd "$bin" 2>/dev/null | awk '{print $3}' | grep '^/'); do
            dir=$(dirname "$lib")
            mkdir -p "$CHROOT$dir"
            cp "$lib" "$CHROOT$lib" 2>/dev/null || true
        done
    fi
done

# Copy ld-linux
cp /lib64/ld-linux-x86-64.so.2 "$CHROOT/lib64/" 2>/dev/null || true
cp -r /lib/x86_64-linux-gnu/ld-*.so* "$CHROOT/lib/x86_64-linux-gnu/" 2>/dev/null || true

# Create essential config files
cat > "$CHROOT/etc/passwd" << EOF
root:x:0:0:root:/root:/bin/bash
EOF

cat > "$CHROOT/etc/group" << EOF
root:x:0:
EOF

# Create dpkg status
touch "$CHROOT/var/lib/dpkg/status"
touch "$CHROOT/var/lib/dpkg/available"

# Create basic apt config
mkdir -p "$CHROOT/etc/apt"
cat > "$CHROOT/etc/apt/sources.list" << EOF
deb http://deb.debian.org/debian trixie main
deb http://deb.debian.org/debian trixie-updates main
deb http://security.debian.org/debian-security trixie-security main
EOF

echo "Minimal bootstrap complete!"
echo ""
echo "You can now:"
echo "1. Mount proc/sys/dev"
echo "2. Chroot into $CHROOT"
echo "3. Use dpkg -i to install .deb files"
EOFBOOT

chmod +x "$WORK_DIR/manual_bootstrap.sh"

echo "Option 4: Download specific packages from Debian archive"
echo "========================================================"
echo ""

cat > "$WORK_DIR/download_from_archive.sh" << 'EOFARCH'
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
EOFARCH

chmod +x "$WORK_DIR/download_from_archive.sh"

echo ""
echo "Scripts created in: $WORK_DIR"
echo ""
echo "Choose an option:"
echo "1. $WORK_DIR/manual_bootstrap.sh     - Create minimal bootstrap"
echo "2. $WORK_DIR/download_from_archive.sh - Download from Debian archive"
echo "3. Use debootstrap (recommended if available)"
echo "4. Extract from Debian ISO"