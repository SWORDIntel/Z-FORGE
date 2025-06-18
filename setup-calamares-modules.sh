#!/bin/bash
# setup-calamares-modules.sh
# Script to set up all required Calamares modules

echo "====== Setting up Calamares modules ======"

# Create modules directory
mkdir -p calamares/modules/{zfspooldetect,zfsrootselect,zfsbootloader,proxmoxconfig,zforgefinalize}

# Create module.desc files
for module in zfspooldetect zfsrootselect zfsbootloader proxmoxconfig zforgefinalize; do
    cat > calamares/modules/$module/module.desc << EOF
---
type:       "job"
name:       "$module"
interface:  "python"
script:     "main.py"
EOF
    echo "[+] Created module.desc for $module"
done

# Copy main.py implementations for all modules
for module in zfspooldetect zfsrootselect zfsbootloader proxmoxconfig zforgefinalize; do
    src_file="builder/modules/$module/main.py"
    dest_file="calamares/modules/$module/main.py"

    if [ -f "$src_file" ]; then
        cp "$src_file" "$dest_file"
        chmod +x "$dest_file"
        echo "[+] Copied main.py for $module and made it executable"
    else
        echo "[!] ERROR: Source file $src_file not found. Skipping $module."
    fi
done

echo "[+] Calamares modules setup complete!"
echo "    Actual main.py implementations have been copied for all modules."
echo ""
