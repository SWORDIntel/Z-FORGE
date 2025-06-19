## Calamares Integration for SecurityHardening Module

### 1. Calamares Sequence Integration

The `securityhardening` module is designed as a Calamares "job" module. It should be placed in the `exec` sequence of a Calamares process, typically within a phase that runs after the target system's root filesystem has been set up and packages have been installed, but before final cleanup or user-visible post-install configuration steps.

**Recommended Placement:**

*   **Phase:** `postinstall` or a custom "configure" phase.
*   **Order:**
    *   After modules that install the base system, kernel, and essential packages.
    *   After user creation modules (e.g., `users`).
    *   Before modules that might finalize the system or reboot (e.g., `finished`).
    *   It's generally good practice to run it before modules that might start services that would be affected by the hardening (e.g., starting sshd before it's hardened, though systemd would restart it with new config on next boot).

**Example (YAML sequence file, e.g., `settings.conf` or a branded sequence file):**

```yaml
modules:
  - welcome
  - partition
  # ... other modules ...
  - mount
  - unpackfs
  - machineid
  - fstab
  - localecfg
  - users
  - networkcfg # Or similar network configuration module
  # ... other configuration modules ...
  - grubcfg
  - bootloader

jobs: # "exec" sequence in settings.conf
  # ... other jobs ...
  -ดูแลsystem # Example from some Calamares setups for early chroot tasks
  - packages
  - services-systemd # Configure services before hardening them
  - securityhardening # <--- PLACE MODULE HERE
  # ... other jobs like displaymanager, initramfscfg ...
  - umount
  - finished
```

**Note:** The exact name of phases and the sequence can vary depending on the specific Calamares branding and configuration being used. The key is to run it on the fully installed but not yet finalized system.

### 2. `security_hardening_profile` Propagation to GlobalStorage

The `securityhardening` module relies on a value in `libcalamares.globalstorage` to determine which profile to apply ("baseline", "server", or "none"). This value should originate from a configuration file, typically the `build_spec.yml` used to define the ISO build.

**Mechanism:**

1.  **`build_spec.yml` Configuration:**
    Add a key to your `build_spec.yml` (or equivalent ISO build configuration file) to specify the desired security profile. For example:

    ```yaml
    # In your build_spec.yml
    # ... other build specifications ...
    branding:
      installer_product_name: "My Custom OS"

    custom_settings:
      security_profile: "server" # Options: "baseline", "server", "none"
    # ...
    ```

2.  **Early Python Module to Load Settings:**
    An early-running Calamares Python module needs to read this value from the `build_spec.yml` (which must be accessible within the live ISO environment, e.g., copied to `/etc/calamares/build_spec.yml` or a known path) and insert it into `libcalamares.globalstorage`.

    *   This could be a new, dedicated Python module (e.g., `buildspec_loader`) running in an early "prepare" or "init" phase.
    *   Alternatively, an existing early module like `environment` (if it's a Python module in your setup) or a custom welcome module could be augmented.

    **Example code snippet for such a module's `run()` function:**

    ```python
    import libcalamares
    import yaml # PyYAML must be available in Calamares' Python environment
    import os

    BUILD_SPEC_PATH = "/etc/calamares/build_spec.yml" # Example path

    def run():
        profile = "none" # Default if not found or error
        try:
            if os.path.exists(BUILD_SPEC_PATH):
                with open(BUILD_SPEC_PATH, "r") as f:
                    spec = yaml.safe_load(f)

                # Adjust path according to your build_spec.yml structure
                profile = spec.get("custom_settings", {}).get("security_profile", "none")
                libcalamares.utils.debug(f"Loaded security_profile from build_spec: {profile}")
            else:
                libcalamares.utils.warning(f"{BUILD_SPEC_PATH} not found. Defaulting security_profile to 'none'.")
        except Exception as e:
            libcalamares.utils.error(f"Error loading security_profile from {BUILD_SPEC_PATH}: {e}. Defaulting to 'none'.")

        libcalamares.globalstorage.insert("security_hardening_profile", profile)
        libcalamares.utils.log(f"security_hardening_profile set in globalstorage: {profile}")

        return None # No job result for non-job modules typically
    ```

    This loader module should be placed very early in the Calamares sequence, before any modules that might depend on the `security_hardening_profile` value (though in this case, only the `securityhardening` job module itself needs it).

By following these integration steps, the `securityhardening` module can be effectively incorporated into the Calamares installation process, and its behavior can be controlled via the ISO's build specification.
