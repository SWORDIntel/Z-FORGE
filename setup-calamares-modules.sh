#!/bin/bash
# setup-calamares-modules.sh - Initialize Calamares module structure

echo "[*] Setting up Calamares custom modules..."

# Create module directories
mkdir -p calamares/modules/{
    zfspooldetect,
    zfsrootselect,
    zfsbootloader,
    proxmoxconfig,
    zforgefinalize
}/

# Create module.desc files for each module
for module in zfspooldetect zfsrootselect zfsbootloader proxmoxconfig zforgefinalize; do
    cat > calamares/modules/$module/module.desc << EOF
---
type:       "job"
name:       "$module"
interface:  "python"
requires:   []
script:     "main.py"
EOF
done

echo "[+] Calamares module structure created"
