#!/usr/bin/env python3
"""
Fix module class names to match what the module loader expects
"""

import re
from pathlib import Path

# Mapping of files to class name changes
fixes = {
    "builder/modules/zfs_compression_optimizer.py": {
        "old": "class ZFSCompressionOptimizer:",
        "new": "class ZfsCompressionOptimizer:"
    },
    "builder/modules/zfs_encryption.py": {
        "old": "class ZFSEncryption:",
        "new": "class ZfsEncryption:"
    },
    "builder/modules/zfs_pool_config.py": {
        "old": "class ZFSPoolConfig:",
        "new": "class ZfsPoolConfig:"
    },
    "builder/modules/zfsbootmenu_install.py": {
        "old": "class ZFSBootMenuInstall:",
        "new": "class ZfsbootmenuInstall:"
    }
}

project_root = Path(__file__).parent.parent

for file_path, fix in fixes.items():
    full_path = project_root / file_path
    if full_path.exists():
        content = full_path.read_text()
        if fix["old"] in content:
            new_content = content.replace(fix["old"], fix["new"])
            full_path.write_text(new_content)
            print(f"✅ Fixed {file_path}")
        else:
            print(f"⚠️ Pattern not found in {file_path}")
    else:
        print(f"❌ File not found: {file_path}")

print("\nDone! All class names should now match the module loader expectations.")