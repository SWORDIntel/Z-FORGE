#!/bin/bash
#
# Critical Calamares Installer Fixes
# UltraThink Agent Fix Implementation v8.0
#

echo "==========================================="
echo "CALAMARES CRITICAL FIX SCRIPT"
echo "==========================================="
echo "This script will fix critical issues in the Calamares installer"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Backup function
backup_file() {
    local file="$1"
    if [ -f "$file" ]; then
        cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
        echo "  Backed up: $file"
    fi
}

echo "============================================"
echo "CREATING MISSING CRITICAL MODULES"
echo "============================================"

# Fix 1: Create missing ZFS pool detection module
echo -e "\n${GREEN}Creating zfspooldetect module...${NC}"
mkdir -p calamares/modules/zfspooldetect

cat > calamares/modules/zfspooldetect/main.py << 'EOF'
#!/usr/bin/env python3
"""
ZFS Pool Detection Module for Calamares
Detects existing ZFS pools on the system
"""

import subprocess
import json
from typing import Dict, List, Optional

class ZfspooldetectJob:
    """Calamares job for detecting ZFS pools"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.pools = []
        
    def detect_pools(self) -> List[Dict]:
        """Detect all ZFS pools on the system"""
        pools = []
        
        try:
            # Get list of pools
            result = subprocess.run(
                ['zpool', 'list', '-H', '-o', 'name,size,alloc,free,health'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 5:
                            pools.append({
                                'name': parts[0],
                                'size': parts[1],
                                'allocated': parts[2],
                                'free': parts[3],
                                'health': parts[4]
                            })
            
            # Get detailed pool information
            for pool in pools:
                self._get_pool_details(pool)
                
        except Exception as e:
            print(f"Error detecting pools: {e}")
            
        return pools
    
    def _get_pool_details(self, pool: Dict) -> None:
        """Get detailed information about a pool"""
        try:
            # Get pool properties
            result = subprocess.run(
                ['zpool', 'get', 'all', pool['name'], '-H'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                properties = {}
                for line in result.stdout.strip().split('\n'):
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        properties[parts[1]] = parts[2]
                pool['properties'] = properties
                
            # Get datasets in pool
            result = subprocess.run(
                ['zfs', 'list', '-H', '-r', '-o', 'name,used,avail,mountpoint', pool['name']],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                datasets = []
                for line in result.stdout.strip().split('\n'):
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        datasets.append({
                            'name': parts[0],
                            'used': parts[1],
                            'available': parts[2],
                            'mountpoint': parts[3]
                        })
                pool['datasets'] = datasets
                
        except Exception as e:
            print(f"Error getting pool details: {e}")
    
    def run(self) -> Optional[str]:
        """Main execution method for Calamares"""
        try:
            self.pools = self.detect_pools()
            
            # Store detected pools for other modules
            import libcalamares
            libcalamares.globalstorage.insert("zfsPools", self.pools)
            
            print(f"Detected {len(self.pools)} ZFS pools")
            for pool in self.pools:
                print(f"  - {pool['name']}: {pool['size']} ({pool['health']})")
            
            return None  # Success
            
        except Exception as e:
            return f"Failed to detect ZFS pools: {str(e)}"

# Module metadata
def main():
    """Entry point for testing"""
    job = ZfspooldetectJob({})
    pools = job.detect_pools()
    print(f"Found {len(pools)} pools")
    for pool in pools:
        print(f"  {pool}")

if __name__ == "__main__":
    main()
EOF

echo -e "${GREEN}✅ Created zfspooldetect module${NC}"

# Fix 2: Create ZFS bootloader module
echo -e "\n${GREEN}Creating zfsbootloader module...${NC}"
mkdir -p calamares/modules/zfsbootloader

cat > calamares/modules/zfsbootloader/main.py << 'EOF'
#!/usr/bin/env python3
"""
ZFS Bootloader Configuration Module for Calamares
Configures bootloader for ZFS root systems
"""

import os
import subprocess
from typing import Dict, Optional

class ZfsbootloaderJob:
    """Calamares job for configuring ZFS bootloader"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.root_pool = config.get('rootPool', 'rpool')
        self.boot_device = config.get('bootDevice', '/dev/sda')
        
    def configure_grub_zfs(self) -> bool:
        """Configure GRUB for ZFS boot"""
        try:
            # Update GRUB configuration for ZFS
            grub_config = """
# ZFS Boot Configuration
GRUB_CMDLINE_LINUX="root=ZFS={pool}/ROOT/debian"
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_TERMINAL=console
""".format(pool=self.root_pool)
            
            # Write GRUB defaults
            grub_defaults = "/target/etc/default/grub"
            if os.path.exists(grub_defaults):
                with open(grub_defaults, 'a') as f:
                    f.write(grub_config)
            
            # Install GRUB to boot device
            subprocess.run([
                'chroot', '/target',
                'grub-install', self.boot_device
            ], check=True)
            
            # Update GRUB configuration
            subprocess.run([
                'chroot', '/target',
                'update-grub'
            ], check=True)
            
            return True
            
        except Exception as e:
            print(f"Error configuring GRUB: {e}")
            return False
    
    def configure_zfs_initramfs(self) -> bool:
        """Configure initramfs for ZFS"""
        try:
            # Ensure ZFS is included in initramfs
            initramfs_config = "/target/etc/initramfs-tools/modules"
            if os.path.exists(os.path.dirname(initramfs_config)):
                with open(initramfs_config, 'a') as f:
                    f.write("\n# ZFS modules\n")
                    f.write("zfs\n")
            
            # Update initramfs
            subprocess.run([
                'chroot', '/target',
                'update-initramfs', '-u', '-k', 'all'
            ], check=True)
            
            return True
            
        except Exception as e:
            print(f"Error configuring initramfs: {e}")
            return False
    
    def configure_systemd_boot(self) -> bool:
        """Configure systemd-boot for ZFS (UEFI systems)"""
        try:
            # Check if system is UEFI
            if not os.path.exists('/sys/firmware/efi'):
                return True  # Skip for BIOS systems
            
            # Create systemd-boot entry
            entry_config = """
title   Debian GNU/Linux
linux   /vmlinuz
initrd  /initrd.img
options root=ZFS={pool}/ROOT/debian rw quiet splash
""".format(pool=self.root_pool)
            
            entry_file = "/target/boot/efi/loader/entries/debian.conf"
            os.makedirs(os.path.dirname(entry_file), exist_ok=True)
            
            with open(entry_file, 'w') as f:
                f.write(entry_config)
            
            return True
            
        except Exception as e:
            print(f"Error configuring systemd-boot: {e}")
            return False
    
    def run(self) -> Optional[str]:
        """Main execution method for Calamares"""
        try:
            print("Configuring bootloader for ZFS...")
            
            # Configure GRUB
            if not self.configure_grub_zfs():
                return "Failed to configure GRUB for ZFS"
            
            # Configure initramfs
            if not self.configure_zfs_initramfs():
                return "Failed to configure initramfs for ZFS"
            
            # Configure systemd-boot if UEFI
            if not self.configure_systemd_boot():
                return "Failed to configure systemd-boot"
            
            print("ZFS bootloader configuration complete")
            return None  # Success
            
        except Exception as e:
            return f"Failed to configure ZFS bootloader: {str(e)}"

# Module metadata
def main():
    """Entry point for testing"""
    job = ZfsbootloaderJob({'rootPool': 'rpool', 'bootDevice': '/dev/sda'})
    print("ZFS bootloader module initialized")

if __name__ == "__main__":
    main()
EOF

echo -e "${GREEN}✅ Created zfsbootloader module${NC}"

# Fix 3: Create other missing module stubs
echo -e "\n${GREEN}Creating other missing modules...${NC}"

for module in proxmoxconfig securityhardening telemetryconsent zforgefinalize; do
    mkdir -p calamares/modules/$module
    
    # Capitalize first letter for class name
    class_name="${module^}Job"
    
    cat > calamares/modules/$module/main.py << EOF
#!/usr/bin/env python3
"""
${module^} Module for Calamares
Auto-generated stub - implement functionality as needed
"""

from typing import Dict, Optional

class ${class_name}:
    """Calamares job for ${module}"""
    
    def __init__(self, config: Dict):
        self.config = config
        
    def run(self) -> Optional[str]:
        """Main execution method for Calamares"""
        try:
            print(f"Running ${module} module")
            # TODO: Implement module functionality
            
            return None  # Success
            
        except Exception as e:
            return f"Failed in ${module}: {str(e)}"

def main():
    """Entry point for testing"""
    job = ${class_name}({})
    result = job.run()
    if result:
        print(f"Error: {result}")
    else:
        print("${module} completed successfully")

if __name__ == "__main__":
    main()
EOF
    
    echo -e "  ${GREEN}✅ Created ${module} module${NC}"
done

echo ""
echo "============================================"
echo "FIXING CLASS NAMING CONVENTIONS"
echo "============================================"

# Fix 4: Correct class naming in existing modules
echo -e "\n${YELLOW}Fixing class names to match Calamares conventions...${NC}"

for module in gpupassthrough hardwarehealth networkconfig postinstall \
              storagelayout zfsenhancedconfig zfsrichconfig zfsrootselect; do
    
    module_file="calamares/modules/$module/main.py"
    if [ -f "$module_file" ]; then
        backup_file "$module_file"
        
        # Create correct class name (capitalize first letter, add Job suffix)
        class_name="${module^}Job"
        
        # Replace various class naming patterns
        sed -i "s/class [A-Za-z]*Module:/class ${class_name}:/g" "$module_file"
        sed -i "s/class [A-Za-z]*Module(/class ${class_name}(/g" "$module_file"
        sed -i "s/class ${module^}:/class ${class_name}:/g" "$module_file"
        
        echo -e "  ${GREEN}✅ Fixed class naming in ${module}${NC}"
    fi
done

echo ""
echo "============================================"
echo "CREATING GUI FRAMEWORK CONVERTER"
echo "============================================"

# Fix 5: Create a converter script for GTK to Qt
cat > calamares/convert_gtk_to_qt.py << 'EOF'
#!/usr/bin/env python3
"""
GTK to Qt Converter for Calamares Modules
Converts GTK-based GUI code to Qt for Calamares compatibility
"""

import os
import re
from pathlib import Path

def convert_gtk_to_qt(file_path):
    """Convert GTK code to Qt in a Python file"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if file uses GTK
    if 'gi.repository' not in content and 'Gtk' not in content:
        return False
    
    print(f"Converting {file_path}...")
    
    # Replace imports
    replacements = [
        # GTK imports to Qt
        (r"import gi\ngi\.require_version\('Gtk', '3\.0'\)\nfrom gi\.repository import Gtk",
         "from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QCheckBox, QLineEdit, QTextEdit, QGroupBox\nfrom PyQt5.QtCore import Qt, pyqtSignal"),
        
        # Common GTK to Qt widget replacements
        (r"Gtk\.Window", "QWidget"),
        (r"Gtk\.VBox", "QVBoxLayout"),
        (r"Gtk\.HBox", "QHBoxLayout"),
        (r"Gtk\.Label", "QLabel"),
        (r"Gtk\.Button", "QPushButton"),
        (r"Gtk\.Entry", "QLineEdit"),
        (r"Gtk\.TextView", "QTextEdit"),
        (r"Gtk\.ComboBoxText", "QComboBox"),
        (r"Gtk\.CheckButton", "QCheckBox"),
        (r"Gtk\.Box", "QGroupBox"),
        
        # Method replacements
        (r"\.pack_start\([^)]+\)", ".addWidget"),
        (r"\.show_all\(\)", ".show()"),
        (r"\.set_text\(", ".setText("),
        (r"\.get_text\(\)", ".text()"),
        (r"\.connect\('clicked',", ".clicked.connect("),
        (r"\.set_active\(", ".setChecked("),
        (r"\.get_active\(\)", ".isChecked()"),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # Backup original file
    backup_path = f"{file_path}.gtk_backup"
    os.rename(file_path, backup_path)
    
    # Write converted file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"  Converted and backed up to {backup_path}")
    return True

def main():
    """Convert all GTK modules to Qt"""
    modules_dir = Path("modules")
    converted_count = 0
    
    for module_dir in modules_dir.iterdir():
        if module_dir.is_dir():
            for py_file in module_dir.glob("*.py"):
                if convert_gtk_to_qt(py_file):
                    converted_count += 1
    
    print(f"\nConverted {converted_count} files from GTK to Qt")

if __name__ == "__main__":
    main()
EOF

echo -e "${GREEN}✅ Created GTK to Qt converter script${NC}"
echo "  Run: python3 calamares/convert_gtk_to_qt.py"

echo ""
echo "============================================"
echo "CREATING INTEGRATION TEST"
echo "============================================"

# Create integration test
cat > calamares/test_integration.py << 'EOF'
#!/usr/bin/env python3
"""
Calamares Module Integration Test
Tests all modules can be loaded and initialized
"""

import sys
import os
from pathlib import Path

def test_module(module_name):
    """Test a single module"""
    try:
        # Add module to path
        module_path = Path(f"modules/{module_name}")
        sys.path.insert(0, str(module_path))
        
        # Import module
        import main
        
        # Check for correct class
        class_name = f"{module_name.capitalize()}Job"
        if hasattr(main, class_name):
            # Try to instantiate
            job_class = getattr(main, class_name)
            job = job_class({})
            print(f"  ✅ {module_name}: OK (class {class_name} found)")
            return True
        else:
            print(f"  ❌ {module_name}: Class {class_name} not found")
            return False
            
    except Exception as e:
        print(f"  ❌ {module_name}: {str(e)}")
        return False
    finally:
        # Remove from path
        if str(module_path) in sys.path:
            sys.path.remove(str(module_path))

def main():
    """Test all modules"""
    print("Testing Calamares Module Integration")
    print("=" * 40)
    
    modules = [
        'gpupassthrough', 'hardwarehealth', 'networkconfig', 'postinstall',
        'storagelayout', 'zfsenhancedconfig', 'zfsrichconfig', 'zfsrootselect',
        'zfspooldetect', 'zfsbootloader', 'proxmoxconfig', 'securityhardening',
        'telemetryconsent', 'zforgefinalize'
    ]
    
    passed = 0
    failed = 0
    
    for module in modules:
        if test_module(module):
            passed += 1
        else:
            failed += 1
    
    print("=" * 40)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ All modules can be loaded!")
        return 0
    else:
        print(f"❌ {failed} modules have issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

echo -e "${GREEN}✅ Created integration test${NC}"

echo ""
echo "============================================"
echo "VERIFICATION"
echo "============================================"

# Verify fixes
echo -e "\n${YELLOW}Verifying fixes...${NC}"

# Check if modules were created
for module in zfspooldetect zfsbootloader proxmoxconfig \
              securityhardening telemetryconsent zforgefinalize; do
    if [ -f "calamares/modules/$module/main.py" ]; then
        echo -e "  ${GREEN}✅ ${module} module exists${NC}"
    else
        echo -e "  ${RED}❌ ${module} module missing${NC}"
    fi
done

# Test the integration
echo -e "\n${YELLOW}Running integration test...${NC}"
cd calamares && python3 test_integration.py
cd ..

echo ""
echo "============================================"
echo "FIX SUMMARY"
echo "============================================"
echo ""
echo -e "${GREEN}Completed:${NC}"
echo "  ✅ Created 6 missing critical modules"
echo "  ✅ Fixed class naming conventions"
echo "  ✅ Created GTK to Qt converter"
echo "  ✅ Created integration test suite"
echo ""
echo -e "${YELLOW}Still Required:${NC}"
echo "  ⚠️ Run GTK to Qt converter: python3 calamares/convert_gtk_to_qt.py"
echo "  ⚠️ Implement module logic in stub modules"
echo "  ⚠️ Add comprehensive error handling"
echo "  ⚠️ Create unit tests for each module"
echo ""
echo "Next steps:"
echo "  1. cd calamares && python3 convert_gtk_to_qt.py"
echo "  2. ./test_calamares_installer.sh"
echo "  3. Implement remaining module functionality"
echo ""
echo "Fix script completed at: $(date)"
echo "==========================================="