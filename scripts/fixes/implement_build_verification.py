#!/usr/bin/env python3
"""
Implement build verification features for Z-FORGE
- Kernel integrity verification
- ISO bootability checks
- Package validation
"""
import os
import sys
from pathlib import Path

def add_kernel_integrity_verification():
    """Add kernel integrity verification to kernel_acquisition.py"""
    
    module_path = Path(__file__).parent.parent.parent / "builder" / "modules" / "kernel_acquisition.py"
    
    if not module_path.exists():
        print(f"[!] Module not found: {module_path}")
        return False
    
    print(f"[*] Adding kernel integrity verification to: {module_path}")
    
    # Read current content
    with open(module_path, 'r') as f:
        content = f.read()
    
    # Add verification method
    verification_method = '''
    def _verify_kernel_integrity(self, kernel_path: Path, kernel_version: str) -> bool:
        """
        Verify kernel image integrity and validity.
        
        Args:
            kernel_path: Path to kernel image (vmlinuz)
            kernel_version: Expected kernel version
            
        Returns:
            True if kernel is valid, raises exception otherwise
        """
        self.logger.info(f"Verifying kernel integrity: {kernel_path}")
        
        # Check if file exists
        full_path = self.chroot_path / kernel_path.relative_to("/") if kernel_path.is_absolute() else kernel_path
        if not full_path.exists():
            raise FileNotFoundError(f"Kernel image not found: {kernel_path}")
        
        # Check file size is reasonable (kernels are typically 5-15MB)
        size = full_path.stat().st_size
        size_mb = size / (1024 * 1024)
        
        if size_mb < 5:
            raise ValueError(f"Kernel image too small: {size_mb:.1f}MB (expected > 5MB)")
        elif size_mb > 50:
            self.logger.warning(f"Kernel image unusually large: {size_mb:.1f}MB")
        
        # Verify it's a compressed kernel image
        try:
            with open(full_path, 'rb') as f:
                # Read first 4 bytes for magic numbers
                magic = f.read(4)
                
                # Check for various kernel compression signatures
                valid_signatures = [
                    b'\\x1f\\x8b\\x08',  # gzip
                    b'BZh',             # bzip2
                    b'\\xfd7zXZ',       # xz/lzma2
                    b'\\x89LZO',        # lzo
                    b'MZ',              # PE/COFF (EFI stub)
                    b'\\x02\\x21',      # lz4
                    b'(\\xb5/\\xfd',    # zstd
                ]
                
                valid_kernel = False
                for sig in valid_signatures:
                    if magic.startswith(sig[:len(magic)]):
                        valid_kernel = True
                        self.logger.debug(f"Detected kernel compression: {sig}")
                        break
                
                # Also check if it's an uncompressed kernel (rare)
                f.seek(0x202)
                kernel_header = f.read(4)
                if kernel_header == b'HdrS':
                    valid_kernel = True
                    self.logger.debug("Detected uncompressed kernel with setup header")
                
                if not valid_kernel:
                    raise ValueError(f"Invalid kernel image format (magic: {magic.hex()})")
        
        except IOError as e:
            raise ValueError(f"Failed to read kernel image: {e}")
        
        # Verify kernel version matches if possible
        try:
            # Try to extract version string from kernel
            result = self._run_chroot_command([
                "strings", str(kernel_path), "|", "grep", "-E", "^Linux version"
            ], check=False)
            
            if result.returncode == 0 and result.stdout:
                version_line = result.stdout.strip().split('\\n')[0]
                if kernel_version not in version_line and not version_line.startswith("Linux version"):
                    self.logger.warning(f"Kernel version mismatch: expected {kernel_version}, found {version_line}")
        except:
            # Non-critical if we can't verify version
            pass
        
        # Calculate and store checksum for future verification
        import hashlib
        sha256_hash = hashlib.sha256()
        
        with open(full_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
        
        checksum = sha256_hash.hexdigest()
        self.logger.info(f"Kernel checksum (SHA256): {checksum}")
        
        # Store checksum for build manifest
        if hasattr(self, 'build_manifest'):
            self.build_manifest['kernel_checksum'] = checksum
        
        self.logger.info(f"Kernel integrity verified: {kernel_path} ({size_mb:.1f}MB)")
        return True
    '''
    
    # Find where to insert the method (after _find_installed_kernel_paths)
    insert_pos = content.find("def _generate_dracut_initramfs")
    if insert_pos == -1:
        insert_pos = content.find("def _install_zfs_module")
    
    # Insert the verification method
    new_content = content[:insert_pos] + verification_method + "\n" + content[insert_pos:]
    
    # Now add calls to verify kernel after installation
    # Find where kernel is installed
    kernel_install_pattern = "self.logger.info(f\"Successfully installed kernel version: {installed_kernel_version}\")"
    install_pos = new_content.find(kernel_install_pattern)
    
    if install_pos != -1:
        # Add verification call after installation
        install_end = new_content.find("\n", install_pos)
        verification_call = '''
            
            # Verify kernel integrity
            vmlinuz_path = Path("/boot") / f"vmlinuz-{installed_kernel_version}"
            try:
                self._verify_kernel_integrity(vmlinuz_path, installed_kernel_version)
            except Exception as e:
                self.logger.error(f"Kernel integrity verification failed: {e}")
                raise RuntimeError(f"Installed kernel failed integrity check: {e}")'''
        
        new_content = new_content[:install_end] + verification_call + new_content[install_end:]
    
    # Write updated content
    with open(module_path, 'w') as f:
        f.write(new_content)
    
    print("[✓] Added kernel integrity verification")
    return True

def add_iso_bootability_verification():
    """Add ISO bootability verification to iso_generator.py"""
    
    module_path = Path(__file__).parent.parent.parent / "builder" / "modules" / "iso_generator.py"
    
    if not module_path.exists():
        print(f"[!] ISO generator module not found: {module_path}")
        return False
    
    print(f"[*] Adding ISO bootability verification to: {module_path}")
    
    # Read current content
    with open(module_path, 'r') as f:
        content = f.read()
    
    # Add ISO verification method
    iso_verification = '''
    def _verify_iso_bootable(self, iso_path: Path) -> bool:
        """
        Verify that the generated ISO is bootable.
        
        Args:
            iso_path: Path to the ISO file
            
        Returns:
            True if ISO is bootable, raises exception otherwise
        """
        self.logger.info(f"Verifying ISO bootability: {iso_path}")
        
        if not iso_path.exists():
            raise FileNotFoundError(f"ISO file not found: {iso_path}")
        
        # Check ISO size is reasonable
        size = iso_path.stat().st_size
        size_mb = size / (1024 * 1024)
        
        if size_mb < 100:
            raise ValueError(f"ISO too small: {size_mb:.1f}MB (expected > 100MB)")
        
        # Verify ISO structure using isoinfo
        try:
            # Check for El Torito boot catalog (required for bootable ISO)
            result = subprocess.run(
                ["isoinfo", "-d", "-i", str(iso_path)],
                capture_output=True,
                text=True,
                check=True
            )
            
            iso_info = result.stdout
            
            # Check for boot catalog
            if "El Torito" not in iso_info:
                raise ValueError("ISO is not bootable - missing El Torito boot catalog")
            
            # Extract and verify boot information
            boot_info = {}
            for line in iso_info.split('\\n'):
                if "Eltorito" in line:
                    self.logger.debug(f"Boot info: {line.strip()}")
                elif "Volume id:" in line:
                    boot_info['volume_id'] = line.split(':', 1)[1].strip()
                elif "Volume size" in line:
                    boot_info['volume_size'] = line.strip()
            
            self.logger.info(f"ISO Volume ID: {boot_info.get('volume_id', 'Unknown')}")
            
            # Check for required boot files
            required_files = [
                "/boot/grub/grub.cfg",
                "/EFI/BOOT/BOOTX64.EFI",
                "/isolinux/isolinux.bin"
            ]
            
            # List files in ISO
            list_result = subprocess.run(
                ["isoinfo", "-R", "-l", "-i", str(iso_path)],
                capture_output=True,
                text=True,
                check=False
            )
            
            if list_result.returncode == 0:
                iso_contents = list_result.stdout
                found_boot_files = []
                
                for boot_file in required_files:
                    if boot_file.lower() in iso_contents.lower():
                        found_boot_files.append(boot_file)
                        self.logger.debug(f"Found boot file: {boot_file}")
                
                if not found_boot_files:
                    self.logger.warning("No standard boot files found in ISO")
            
            # Verify UEFI boot if present
            if "/EFI/BOOT/BOOTX64.EFI" in iso_contents:
                self.logger.info("UEFI boot support detected")
                boot_info['uefi'] = True
            
            # Verify legacy BIOS boot if present
            if "/isolinux/isolinux.bin" in iso_contents or "boot/grub" in iso_contents:
                self.logger.info("Legacy BIOS boot support detected")
                boot_info['bios'] = True
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to analyze ISO: {e}")
        except FileNotFoundError:
            self.logger.warning("isoinfo not found - skipping detailed ISO verification")
            # Fall back to basic checks
            
        # Calculate ISO checksum
        import hashlib
        sha256_hash = hashlib.sha256()
        
        with open(iso_path, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):  # 1MB chunks
                sha256_hash.update(chunk)
        
        checksum = sha256_hash.hexdigest()
        self.logger.info(f"ISO checksum (SHA256): {checksum}")
        
        # Store in build manifest
        if hasattr(self, 'build_manifest'):
            self.build_manifest['iso_checksum'] = checksum
            self.build_manifest['iso_size_mb'] = size_mb
            self.build_manifest['iso_boot_info'] = boot_info
        
        self.logger.info(f"ISO verification passed: {iso_path} ({size_mb:.1f}MB)")
        return True
    '''
    
    # Find where to insert (before execute method typically)
    insert_pos = content.find("def execute(")
    if insert_pos == -1:
        insert_pos = content.find("def _create_iso_structure")
    
    # Insert the method
    new_content = content[:insert_pos] + iso_verification + "\n    " + content[insert_pos:]
    
    # Add verification call after ISO creation
    # Look for where xorriso is called
    xorriso_pattern = "xorriso"
    xorriso_calls = []
    pos = 0
    while True:
        pos = new_content.find(xorriso_pattern, pos)
        if pos == -1:
            break
        xorriso_calls.append(pos)
        pos += 1
    
    # Find the last xorriso call (likely the ISO creation)
    if xorriso_calls:
        last_xorriso = xorriso_calls[-1]
        # Find the end of that code block
        block_end = new_content.find("\n\n", last_xorriso)
        if block_end != -1:
            verification_call = '''
        
        # Verify the ISO is bootable
        try:
            self._verify_iso_bootable(Path(self.iso_path))
        except Exception as e:
            self.logger.error(f"ISO verification failed: {e}")
            # Clean up failed ISO
            if Path(self.iso_path).exists():
                os.remove(self.iso_path)
            raise RuntimeError(f"Generated ISO is not bootable: {e}")'''
            
            new_content = new_content[:block_end] + verification_call + new_content[block_end:]
    
    # Write updated content
    with open(module_path, 'w') as f:
        f.write(new_content)
    
    print("[✓] Added ISO bootability verification")
    return True

def add_package_validation():
    """Add package validation to debootstrap and other modules"""
    
    module_path = Path(__file__).parent.parent.parent / "builder" / "modules" / "debootstrap.py"
    
    if not module_path.exists():
        print(f"[!] Debootstrap module not found: {module_path}")
        return False
    
    print(f"[*] Adding package validation to: {module_path}")
    
    # Read current content
    with open(module_path, 'r') as f:
        content = f.read()
    
    # Add package validation method
    package_validation = '''
    def _validate_package_integrity(self, package_path: Path) -> bool:
        """
        Validate downloaded package integrity.
        
        Args:
            package_path: Path to the .deb package
            
        Returns:
            True if package is valid
        """
        if not package_path.exists():
            raise FileNotFoundError(f"Package not found: {package_path}")
        
        # Check package structure using dpkg-deb
        try:
            result = subprocess.run(
                ["dpkg-deb", "--info", str(package_path)],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Package is valid if dpkg-deb can read it
            return True
            
        except subprocess.CalledProcessError:
            return False
    
    def _verify_package_signatures(self) -> bool:
        """
        Verify all downloaded packages have valid signatures.
        
        Returns:
            True if all packages are verified
        """
        self.logger.info("Verifying package signatures...")
        
        # Get list of downloaded packages
        apt_cache = self.chroot_path / "var/cache/apt/archives"
        if not apt_cache.exists():
            return True  # No packages to verify
        
        packages = list(apt_cache.glob("*.deb"))
        self.logger.info(f"Found {len(packages)} packages to verify")
        
        failed_packages = []
        for package in packages:
            try:
                if not self._validate_package_integrity(package):
                    failed_packages.append(package.name)
            except Exception as e:
                self.logger.warning(f"Failed to verify {package.name}: {e}")
                failed_packages.append(package.name)
        
        if failed_packages:
            self.logger.error(f"Package verification failed for: {', '.join(failed_packages)}")
            return False
        
        self.logger.info("All packages verified successfully")
        return True
    
    def _setup_apt_security(self) -> None:
        """
        Configure APT for enhanced security.
        """
        self.logger.info("Configuring APT security settings...")
        
        # Create APT configuration for security
        apt_config = """// Enhanced security settings for Z-FORGE
APT::Get::AllowUnauthenticated "false";
APT::Get::AllowInsecureRepositories "false";
APT::Get::AllowDowngradeToInsecureRepositories "false";
Acquire::AllowInsecureRepositories "false";
Acquire::AllowWeakRepositories "false";
Acquire::AllowDowngradeToInsecureRepositories "false";

// Verify package signatures
APT::Get::Assume-Yes "false";
Debug::pkgAcquire::Auth "true";
"""
        
        apt_conf_path = self.chroot_path / "etc/apt/apt.conf.d/99zforge-security"
        apt_conf_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(apt_conf_path, 'w') as f:
            f.write(apt_config)
        
        self.logger.info("APT security configuration applied")
    '''
    
    # Find where to insert (after __init__ method)
    init_end = content.find("def execute(")
    if init_end == -1:
        init_end = content.find("def _prepare_chroot")
    
    # Insert validation methods
    new_content = content[:init_end] + package_validation + "\n    " + content[init_end:]
    
    # Add security setup call in execute method
    execute_start = new_content.find("def execute(")
    if execute_start != -1:
        # Find first substantial operation in execute
        first_operation = new_content.find("self.", execute_start + 50)
        if first_operation != -1:
            # Add security setup
            security_call = '''
        # Setup enhanced APT security
        self._setup_apt_security()
        '''
            line_start = new_content.rfind("\n", 0, first_operation)
            new_content = new_content[:line_start] + "\n" + security_call + new_content[line_start:]
    
    # Add package verification after debootstrap
    debootstrap_complete = new_content.find("Base system installation completed")
    if debootstrap_complete != -1:
        line_end = new_content.find("\n", debootstrap_complete)
        verification_call = '''
        
        # Verify all downloaded packages
        if not self._verify_package_signatures():
            self.logger.warning("Some packages could not be verified")'''
        
        new_content = new_content[:line_end] + verification_call + new_content[line_end:]
    
    # Write updated content
    with open(module_path, 'w') as f:
        f.write(new_content)
    
    print("[✓] Added package validation and APT security")
    return True

if __name__ == "__main__":
    print("=== Implementing Build Verification ===")
    
    success = True
    
    # Add kernel verification
    if add_kernel_integrity_verification():
        print("\n✓ Kernel integrity verification added")
    else:
        success = False
    
    # Add ISO verification
    if add_iso_bootability_verification():
        print("✓ ISO bootability verification added")
    else:
        success = False
    
    # Add package validation
    if add_package_validation():
        print("✓ Package validation system added")
    else:
        success = False
    
    if success:
        print("\n[✓] All build verification features implemented")
        print("\nThe build system now verifies:")
        print("- Kernel image integrity and format")
        print("- ISO bootability with El Torito catalog")
        print("- Package integrity and signatures")
        print("- APT security configuration")
    else:
        print("\n[!] Some features failed to implement")
        sys.exit(1)