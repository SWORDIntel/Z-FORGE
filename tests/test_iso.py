#!/usr/bin/env python3
# z-forge/tests/test_iso.py - ISO testing script

"""
ISO Testing Framework
Tests the generated ISO in various configurations
"""

import subprocess
import tempfile
import time
from pathlib import Path
import libvirt

def test_uefi_boot(iso_path: str):
    """Test UEFI boot in QEMU"""

    print("[*] Testing UEFI boot...")

    # Create UEFI vars file
    with tempfile.NamedTemporaryFile(suffix='.fd', delete=False) as vars_file:
        subprocess.run([
            "cp", "/usr/share/OVMF/OVMF_VARS.fd", vars_file.name
        ], check=True)

        cmd = [
            "qemu-system-x86_64",
            "-m", "4096",
            "-smp", "2",
            "-enable-kvm",
            "-drive", f"if=pflash,format=raw,readonly,file=/usr/share/OVMF/OVMF_CODE.fd",
            "-drive", f"if=pflash,format=raw,file={vars_file.name}",
            "-cdrom", iso_path,
            "-boot", "d",
            "-display", "vnc=:1",
            "-monitor", "stdio"
        ]

        proc = subprocess.Popen(cmd)
        print("[*] UEFI VM started on VNC :1")
        print("[*] Connect with: vncviewer localhost:1")
        print("[*] Press Enter to stop VM...")
        input()
        proc.terminate()

def test_bios_boot(iso_path: str):
    """Test BIOS boot in QEMU"""

    print("[*] Testing BIOS boot...")

    cmd = [
        "qemu-system-x86_64",
        "-m", "4096",
        "-smp", "2",
        "-enable-kvm",
        "-cdrom", iso_path,
        "-boot", "d",
        "-display", "vnc=:2",
        "-monitor", "stdio"
    ]

    proc = subprocess.Popen(cmd)
    print("[*] BIOS VM started on VNC :2")
    print("[*] Connect with: vncviewer localhost:2")
    print("[*] Press Enter to stop VM...")
    input()
    proc.terminate()

def main():
    """Main test runner"""

    iso_path = "zforge-proxmox-v3.iso"

    if not Path(iso_path).exists():
        print(f"[!] ISO not found: {iso_path}")
        return

    print("Z-Forge ISO Testing Framework")
    print("=============================")
    print("")

    while True:
        print("\nSelect test:")
        print("1. Test UEFI boot")
        print("2. Test BIOS boot")
        print("3. Run automated tests")
        print("4. Exit")

        choice = input("\nChoice: ")

        if choice == "1":
            test_uefi_boot(iso_path)
        elif choice == "2":
            test_bios_boot(iso_path)
        elif choice == "3":
            print("[*] Automated tests not yet implemented")
        elif choice == "4":
            break
        else:
            print("[!] Invalid choice")

if __name__ == "__main__":
    main()
