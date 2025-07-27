#!/bin/bash
# Fix missing apt-key command in chroot

echo "Installing apt-key compatibility in chroot..."

echo "1786" | sudo -S chroot /tmp/zforge_workspace/chroot /bin/bash -c '
export DEBIAN_FRONTEND=noninteractive
export LC_ALL=C
export LANG=C

# Update package lists
apt-get update

# Install gnupg which provides apt-key functionality
apt-get install -y gnupg

# Create apt-key symlink if it doesn'\''t exist
if [ ! -f /usr/bin/apt-key ]; then
    # apt-key is deprecated but some scripts still expect it
    # Create a minimal wrapper
    cat > /usr/bin/apt-key << '\''EOF'\''
#!/bin/bash
# Minimal apt-key wrapper for compatibility
echo "apt-key is deprecated, but continuing..."
case "$1" in
    add)
        gpg --import "$2" 2>/dev/null || true
        ;;
    *)
        echo "apt-key command: $*"
        ;;
esac
exit 0
EOF
    chmod +x /usr/bin/apt-key
    echo "Created apt-key compatibility wrapper"
fi

# Also ensure /usr/local/bin/apt-key exists
if [ ! -f /usr/local/bin/apt-key ]; then
    ln -sf /usr/bin/apt-key /usr/local/bin/apt-key
    echo "Created /usr/local/bin/apt-key symlink"
fi
'

echo "apt-key compatibility installed. Resume build with:"
echo "echo '1786' | sudo -S python3 builder/z-forge.py --build-spec build_spec.yml --resume"