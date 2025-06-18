#!/bin/bash
# z-forge-init.sh - Project structure creation

echo "[*] Creating Z-Forge V3 project structure..."

# Create directory hierarchy
mkdir -p z-forge/{
    builder/{core,modules,templates,utils},
    calamares/modules/{
        zforge_hardware,
        zforge_partitioning,
        zforge_install,
        zforge_bootloader,
        zforge_recovery
    },
    scripts/{build,security,testing},
    config/templates,
    iso/overlay/{etc,usr/share/zforge},
    tests/{unit,integration,fixtures},
    docs
}

# Initialize as git repository
cd z-forge
git init
git config user.name "John"
git config user.email "john@zforge.local"

echo "[+] Project structure created successfully"
