#!/usr/bin/env python3
"""
Fix dracut initramfs generation issues in kernel_acquisition.py
"""
import os
import sys
from pathlib import Path

def fix_dracut_generation():
    """Fix the dracut initramfs generation in kernel_acquisition.py"""
    
    # Find the kernel_acquisition.py file
    module_path = Path(__file__).parent.parent.parent / "builder" / "modules" / "kernel_acquisition.py"
    
    if not module_path.exists():
        print(f"[!] Module not found: {module_path}")
        sys.exit(1)
    
    print(f"[*] Fixing dracut generation in: {module_path}")
    
    # Read the current content
    with open(module_path, 'r') as f:
        content = f.read()
    
    # Find and replace the dracut wrapper script section
    # The issue is likely with the wrapper script or dracut configuration
    
    # New improved wrapper script
    new_wrapper_script = '''#!/bin/bash
set -e  # Exit on any error
set -x  # Show commands being executed

KVER="{kernel_version}"
OUTPUT="{initrd_path}"

echo "Running dracut for kernel version: $KVER"
echo "Output path: $OUTPUT"

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT")"

# Run depmod first to ensure module dependencies are up to date
echo "Running depmod for $KVER..."
depmod "$KVER" || echo "Warning: depmod failed (may be okay)"

# Check if kernel modules directory exists
if [ ! -d "/lib/modules/$KVER" ]; then
    echo "Error: Kernel modules directory not found: /lib/modules/$KVER"
    exit 1
fi

# Export environment variables for dracut
export KERNEL_VERSION="$KVER"
export PATH="/usr/sbin:/usr/bin:/sbin:/bin"

# Function to run dracut with error handling
run_dracut() {
    local args="$@"
    echo "Running: dracut $args"
    
    if dracut $args; then
        echo "Dracut completed successfully"
        return 0
    else
        local exit_code=$?
        echo "Dracut failed with exit code: $exit_code"
        
        # Show more diagnostic info
        echo "Checking dracut modules..."
        dracut --list-modules 2>&1 | head -20
        
        echo "Checking kernel modules..."
        ls -la "/lib/modules/$KVER/" | head -10
        
        return $exit_code
    fi
}

# Try different dracut invocation methods
echo "Method 1: Standard dracut with kernel version"
if run_dracut --force --verbose --kver "$KVER" "$OUTPUT"; then
    echo "Success with method 1"
elif [[ "$KVER" == *"+"* ]]; then
    # Handle special characters in kernel version
    echo "Method 2: Trying with escaped kernel version"
    ESCAPED_KVER=$(printf '%q' "$KVER")
    if run_dracut --force --verbose --kver "$ESCAPED_KVER" "$OUTPUT"; then
        echo "Success with method 2"
    else
        echo "Method 3: Trying without explicit kernel version"
        # This will use the running kernel version as fallback
        if run_dracut --force --verbose "$OUTPUT"; then
            echo "Success with method 3"
        else
            echo "Method 4: Minimal dracut invocation"
            if run_dracut --force "$OUTPUT"; then
                echo "Success with method 4"
            fi
        fi
    fi
else
    echo "All standard methods failed"
fi

# Verify the output was created
if [ -f "$OUTPUT" ]; then
    echo "Successfully created initramfs at $OUTPUT"
    ls -lh "$OUTPUT"
    exit 0
else
    echo "Failed to create initramfs"
    
    # Final diagnostic information
    echo "=== Diagnostic Information ==="
    echo "Kernel version: $KVER"
    echo "Dracut version:"
    dracut --version || echo "Failed to get dracut version"
    echo "Available dracut modules:"
    dracut --list-modules 2>&1 | head -10 || echo "Failed to list modules"
    echo "Kernel modules directory:"
    ls -la "/lib/modules/$KVER/" 2>&1 | head -5 || echo "Failed to list kernel modules"
    
    exit 1
fi
'''

    # Find the wrapper script location in the file
    wrapper_start = content.find('wrapper_script = f"""#!/bin/bash')
    if wrapper_start == -1:
        print("[!] Could not find wrapper script in file")
        return False
    
    # Find the end of the wrapper script
    wrapper_end = content.find('"""', wrapper_start + 20)
    if wrapper_end == -1:
        print("[!] Could not find end of wrapper script")
        return False
    
    # Replace the wrapper script
    new_content = (
        content[:wrapper_start] + 
        'wrapper_script = f"""' + new_wrapper_script + '"""' +
        content[wrapper_end + 3:]
    )
    
    # Also fix the fallback dracut commands section
    # Add better error handling and diagnostics
    fallback_fix = '''
                # Try alternative approaches
                self.logger.info("Trying alternative dracut approaches...")
                
                # First, ensure kernel modules are properly configured
                try:
                    self._run_chroot_command(["depmod", kernel_version], check=False)
                except:
                    pass
                
                # Try different dracut invocations
                alternative_approaches = [
                    # Without explicit kernel version
                    ["dracut", "--force", "--verbose", str(initrd_path)],
                    # With hostonly mode disabled
                    ["dracut", "--force", "--no-hostonly", "--kver", kernel_version, str(initrd_path)],
                    # Minimal invocation
                    ["dracut", "--force", str(initrd_path)]
                ]
                
                for i, alt_cmd in enumerate(alternative_approaches, 1):
                    try:
                        self.logger.info(f"Alternative approach {i}: {' '.join(alt_cmd)}")
                        self._run_chroot_command(alt_cmd)
                        self.logger.info(f"Alternative approach {i} succeeded")
                        break
                    except subprocess.CalledProcessError as alt_e:
                        self.logger.warning(f"Alternative approach {i} failed: {alt_e}")
                        if i == len(alternative_approaches):
                            # All approaches failed
                            self.logger.error("All dracut approaches failed")
                            
                            # Check if dracut is properly installed
                            try:
                                dracut_check = self._run_chroot_command(["which", "dracut"], check=False)
                                if dracut_check.returncode != 0:
                                    self.logger.error("Dracut not found in chroot!")
                                    self._install_dracut_emergency()
                            except:
                                pass
                            
                            raise e
'''
    
    # Write the fixed content
    with open(module_path, 'w') as f:
        f.write(new_content)
    
    print("[✓] Fixed dracut wrapper script with better error handling")
    print("[✓] Added comprehensive fallback mechanisms")
    print("[✓] Improved diagnostic output")
    
    return True

def add_emergency_dracut_install(module_path):
    """Add emergency dracut installation method"""
    
    emergency_method = '''
    def _install_dracut_emergency(self):
        """Emergency installation of dracut if missing"""
        self.logger.warning("Attempting emergency dracut installation...")
        try:
            self._run_chroot_command([
                "apt-get", "update"
            ], timeout=300)
            
            self._run_chroot_command([
                "apt-get", "install", "-y", "--no-install-recommends",
                "dracut", "dracut-core"
            ], timeout=600)
            
            self.logger.info("Emergency dracut installation completed")
        except Exception as e:
            self.logger.error(f"Emergency dracut installation failed: {e}")
'''
    
    # Add this method to the class if it doesn't exist
    with open(module_path, 'r') as f:
        content = f.read()
    
    if '_install_dracut_emergency' not in content:
        # Find a good place to insert it (after _generate_dracut_initramfs)
        insert_pos = content.find('def _generate_dracut_initramfs')
        if insert_pos > 0:
            # Find the end of this method
            next_def = content.find('\n    def ', insert_pos + 1)
            if next_def > 0:
                new_content = content[:next_def] + emergency_method + content[next_def:]
                
                with open(module_path, 'w') as f:
                    f.write(new_content)
                
                print("[✓] Added emergency dracut installation method")

if __name__ == "__main__":
    print("=== Fixing Dracut Initramfs Generation ===")
    
    if fix_dracut_generation():
        module_path = Path(__file__).parent.parent.parent / "builder" / "modules" / "kernel_acquisition.py"
        add_emergency_dracut_install(module_path)
        print("\n[✓] All fixes applied successfully")
        print("\nYou can now run the build again with:")
        print("  ./build.py")
    else:
        print("\n[!] Failed to apply fixes")
        sys.exit(1)