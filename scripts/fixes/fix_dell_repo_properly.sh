#!/bin/bash
# Fix Dell repository configuration properly

set -euo pipefail

echo "=== Fixing Dell Repository Configuration ==="

# 1. Create keyrings directory if it doesn't exist
echo "Creating keyrings directory..."
mkdir -p /usr/share/keyrings

# 2. Download and install Dell GPG key
echo "Downloading Dell GPG key..."
wget -qO - https://linux.dell.com/repo/pgp_pubkeys/0x1285491434D8786F.asc | \
    gpg --dearmor -o /usr/share/keyrings/dell-trusted.gpg

# Set proper permissions
chmod 644 /usr/share/keyrings/dell-trusted.gpg

echo "✅ Dell GPG key installed"

# 3. Find and update Dell repository entries
echo "Updating Dell repository configuration..."

# Check main sources.list
if grep -q "linux.dell.com" /etc/apt/sources.list 2>/dev/null; then
    echo "Updating /etc/apt/sources.list..."
    # Add signed-by if not present
    sed -i 's|deb https://linux.dell.com|deb [signed-by=/usr/share/keyrings/dell-trusted.gpg] https://linux.dell.com|g' /etc/apt/sources.list
    sed -i 's|deb \[signed-by=/usr/share/keyrings/dell-trusted.gpg\] \[signed-by=/usr/share/keyrings/dell-trusted.gpg\]|deb [signed-by=/usr/share/keyrings/dell-trusted.gpg]|g' /etc/apt/sources.list
fi

# Check sources.list.d
for file in /etc/apt/sources.list.d/*.list; do
    if [ -f "$file" ] && grep -q "linux.dell.com" "$file" 2>/dev/null; then
        echo "Updating $file..."
        # Add signed-by if not present
        sed -i 's|deb https://linux.dell.com|deb [signed-by=/usr/share/keyrings/dell-trusted.gpg] https://linux.dell.com|g' "$file"
        # Fix duplicate signed-by entries
        sed -i 's|deb \[signed-by=/usr/share/keyrings/dell-trusted.gpg\] \[signed-by=/usr/share/keyrings/dell-trusted.gpg\]|deb [signed-by=/usr/share/keyrings/dell-trusted.gpg]|g' "$file"
    fi
done

# 4. Fix APT permissions while we're at it
echo "Fixing APT permissions..."
if [ -d /var/lib/apt/lists/partial ]; then
    chown -R _apt:root /var/lib/apt/lists/partial
    chmod 755 /var/lib/apt/lists/partial
fi

if [ -d /var/lib/apt/lists ]; then
    chown -R root:root /var/lib/apt/lists
    chown -R _apt:root /var/lib/apt/lists/partial 2>/dev/null || true
    chmod 755 /var/lib/apt/lists
fi

# 5. Clean APT cache
echo "Cleaning APT cache..."
apt-get clean

# 6. Update package lists
echo "Updating package lists..."
apt-get update

# 7. Verify Dell repository is working
echo ""
echo "=== Verification ==="
echo "Dell GPG key present: $([ -f /usr/share/keyrings/dell-trusted.gpg ] && echo "✅ Yes" || echo "❌ No")"
echo ""
echo "Dell repository entries:"
grep -h "linux.dell.com" /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null | grep -v "^#" || echo "None found"
echo ""
echo "APT update status:"
if apt-get update 2>&1 | grep -i "dell\|W:\|E:" | grep -v "Download is performed"; then
    echo "⚠️  Some warnings/errors remain"
else
    echo "✅ APT update completed successfully"
fi

echo ""
echo "=== Dell Repository Fixed ==="
echo "The Dell repository should now work without errors."
echo ""
echo "To verify Dell packages are available:"
echo "  apt-cache search openmanage"