#!/bin/bash
# Manual minimal bootstrap for chroot

set -e

CHROOT="${1:-/tmp/zforge_workspace/chroot}"

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
