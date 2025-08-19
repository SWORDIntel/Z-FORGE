# Non-Interactive Installation Fixes

This document describes the fixes implemented to handle common interactive prompts during package installation in the Z-FORGE build process.

## Overview

The `NonInteractiveFixes` module ensures that the entire build process can run without user interaction by pre-configuring packages that commonly prompt for input.

## Common Issues Fixed

### 1. Locale Configuration
- **Issue**: "cannot change locale (en_US.utf8): No such file or directory"
- **Fix**: Install locales package and generate en_US.UTF-8 locale
- **Implementation**: Added to ZFS build module

### 2. Debconf Frontend
- **Issue**: Various packages prompt for configuration
- **Fix**: Set DEBIAN_FRONTEND=noninteractive
- **Configuration**:
  ```
  debconf/frontend: Noninteractive
  debconf/priority: critical
  ```

### 3. APT Configuration
- **Issue**: APT prompts for confirmations
- **Fix**: Configure APT to assume yes and handle config files automatically
- **Options**:
  - `--force-confdef`: Keep default for new config files
  - `--force-confold`: Keep old config files when upgrading
  - Disable fancy progress bars that can hang

### 4. Service Starts During Installation
- **Issue**: Services try to start during package installation
- **Fix**: Create `/usr/sbin/policy-rc.d` that exits with code 101
- **Effect**: Prevents all service starts during build

### 5. Package-Specific Configurations

#### GRUB
- Pre-configures installation device (/dev/sda)
- Sets default kernel command line options

#### Postfix
- Sets to "No configuration" mode
- Avoids mail server configuration prompts

#### Timezone (tzdata)
- Default: UTC
- Creates proper /etc/localtime symlink

#### Keyboard Configuration
- Default: US English layout
- Model: Generic 105-key PC

#### OpenSSH Server
- Disables root login by default
- Enables password authentication

#### MySQL/MariaDB
- Sets empty root password
- Avoids password prompts during installation

#### Display Managers (SDDM/GDM/LightDM)
- Pre-selects SDDM as default
- Avoids display manager selection dialog

#### Unattended Upgrades
- Disabled by default
- Prevents automatic update configuration prompts

### 6. Console Setup
- Character set: UTF-8
- Font: TerminusBold 16

## Usage

The module is automatically executed after Debootstrap and before package installation begins. It:

1. Configures debconf for non-interactive mode
2. Sets up APT with appropriate options
3. Creates policy-rc.d to prevent service starts
4. Pre-seeds all common package configurations
5. Sets environment variables for child processes

## Adding New Fixes

To add fixes for additional packages:

1. Identify the debconf questions:
   ```bash
   debconf-show packagename
   ```

2. Add pre-seeding in the appropriate method:
   ```python
   def _configure_newpackage(self):
       config = """
packagename questionname type value
"""
       # Apply configuration
   ```

3. Test the fix in a clean chroot environment

## Environment Variables

The module sets:
- `DEBIAN_FRONTEND=noninteractive`
- `DEBCONF_NONINTERACTIVE_SEEN=true`

These are inherited by all child processes during the build.

## Common Packages That May Need Fixes

If you encounter prompts from these packages, they may need configuration:
- Samba (workgroup name)
- Kerberos (default realm)
- LDAP (base DN)
- Prometheus Node Exporter (arguments)
- Docker (storage driver)
- LXD (bridge configuration)

## Testing

To test if a package will prompt:
```bash
DEBIAN_FRONTEND=noninteractive apt-get install -y packagename
```

If it still prompts, it needs debconf pre-seeding.

## Benefits

1. Fully automated builds
2. Consistent configuration across builds
3. No hanging on user prompts
4. Faster build times
5. Suitable for CI/CD pipelines

## Notes

- Some packages may still output warnings about non-interactive mode
- Services will need to be properly configured after installation
- The policy-rc.d file is removed during the finalization phase