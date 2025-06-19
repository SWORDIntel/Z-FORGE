#!/bin/bash
# setup-calamares-modules.sh
# Script to set up all required Calamares modules

echo "====== Setting up Calamares modules ======"

# Define all modules
ALL_MODULES="zfspooldetect zfsrootselect zfsbootloader proxmoxconfig zforgefinalize securityhardening telemetryconsent telemetryjob"

# General modules directory for Calamares itself is usually `calamares/modules`
# The main calamares directory should exist at the root where this script is run.
if [ ! -d "calamares" ]; then
    echo "[!] ERROR: 'calamares' directory not found in current location. Please run from the project root."
    exit 1
fi
mkdir -p calamares/modules

# Create module.desc files and copy Python scripts
for module in $ALL_MODULES; do
    MODULE_BUILDER_DIR="builder/modules/$module" # Source from builder
    MODULE_CALAMARES_DIR="calamares/modules/$module" # Target in calamares structure

    echo "--- Processing module: $module ---"

    if [ ! -d "$MODULE_BUILDER_DIR" ]; then
        echo "[!] ERROR: Builder source directory $MODULE_BUILDER_DIR not found. Skipping $module."
        continue
    fi

    # Target directory for Calamares module files (main.py, module.desc, .qml etc.)
    # This directory should already contain the module.desc created in previous steps.
    if [ ! -d "$MODULE_CALAMARES_DIR" ]; then
        echo "[!] WARNING: Target Calamares module directory $MODULE_CALAMARES_DIR does not exist. It should have been pre-created with a module.desc."
        # As a safety, create it, but module.desc will be missing unless handled specifically.
        mkdir -p "$MODULE_CALAMARES_DIR"
        echo "[+] Ensured target directory $MODULE_CALAMARES_DIR exists."
    fi

    # Verify module.desc exists (should have been manually created)
    if [ ! -f "$MODULE_CALAMARES_DIR/module.desc" ]; then
        echo "[!] ERROR: module.desc for $module not found in $MODULE_CALAMARES_DIR. This is required."
        # Optionally, could create a fallback generic one here, but it's better to ensure it's correct.
        # For this script, we'll assume it must exist.
    else
        echo "[+] Verified module.desc exists for $module."
    fi

    # Copy main.py
    src_main_py="$MODULE_BUILDER_DIR/main.py"
    dest_main_py="$MODULE_CALAMARES_DIR/main.py"
    if [ -f "$src_main_py" ]; then
        cp "$src_main_py" "$dest_main_py"
        chmod +x "$dest_main_py" # Python scripts often need to be executable
        echo "[+] Copied main.py for $module to $dest_main_py and made it executable"
    else
        echo "[!] ERROR: Source file $src_main_py not found for $module. This module may not function."
    fi

    # Copy __init__.py if it exists
    src_init_py="$MODULE_BUILDER_DIR/__init__.py"
    dest_init_py="$MODULE_CALAMARES_DIR/__init__.py"
    if [ -f "$src_init_py" ]; then
        cp "$src_init_py" "$dest_init_py"
        echo "[+] Copied __init__.py for $module to $dest_init_py"
    fi

    # Specific handling for telemetryconsent QML file
    if [ "$module" == "telemetryconsent" ]; then
        src_qml_file="$MODULE_BUILDER_DIR/ui_telemetryconsent.qml"
        dest_qml_file="$MODULE_CALAMARES_DIR/ui_telemetryconsent.qml"
        if [ -f "$src_qml_file" ]; then
            cp "$src_qml_file" "$dest_qml_file"
            echo "[+] Copied ui_telemetryconsent.qml for $module to $dest_qml_file"
        else
            echo "[!] ERROR: Source QML file $src_qml_file not found for $module."
        fi
    fi
done

echo ""
echo "[+] Calamares modules setup complete!"
echo "    Python scripts and QML files (if any) should now be in place in their respective calamares/modules/ subdirectories."
echo ""
