## Calamares Integration for Telemetry Modules (`telemetryconsent` and `telemetryjob`)

This document outlines how to integrate the `telemetryconsent` (view module) and `telemetryjob` (job module) into a Calamares-based installer.

### 1. `telemetryconsent` (View Module) Integration

The `telemetryconsent` module is a **view module** responsible for displaying UI to the user to obtain their consent for telemetry data collection.

**Recommended Placement:**

*   **Sequence Type:** `show` (or `showFirst` / `preinstall` if your Calamares configuration uses such phases for early UI steps).
*   **Order:** It should appear relatively early in the installation sequence, typically:
    *   After initial setup like `welcome`, `locale`, `keyboard`.
    *   Before system-altering operations like `partition`, `unpackfs`.
    *   The goal is to get consent before any data that might be part of telemetry is generated or any significant installation actions are taken.

**Example (YAML sequence file, e.g., `settings.conf` or a branded sequence file):**

```yaml
# Example 'show' sequence (often part of 'settings.conf' or specific branding sequence files)
# The exact structure (e.g., 'show' vs 'views') can vary.

# For settings.conf style:
# show: [ welcome, locale, keyboard, telemetryconsent, network, partition, ... ]

# For YAML sequence file style (e.g. mybrand.conf):
# ---
# # ... other settings ...
# viewsequence:
#   - # Phase 1: Initial Setup
#     name: "prepare"
#     # List of modules for this phase
#     modules:
#       - name: "welcome"
#       - name: "locale"         # Locale selection
#       - name: "keyboard"       # Keyboard configuration
#       - name: "telemetryconsent" # <--- TELEMETRY CONSENT UI MODULE
#       - name: "network"        # Network configuration
#       - name: "partition"      # Partitioning
#       # ... other view modules ...
#   - # Phase 2: User Setup & Summary
#     name: "configure"
#     modules:
#       - name: "users"          # User creation
#       - name: "summary"        # Installation summary
# # ...
```

The `telemetryconsent` module, upon being left (user clicks "Next"), will store the consent state (`True` or `False`) into `libcalamares.globalstorage["telemetry_consent_given"]`.

### 2. `telemetryjob` (Job Module) Integration

The `telemetryjob` module is a **job module** responsible for collecting and submitting telemetry data if consent was given.

**Recommended Placement:**

*   **Sequence Type:** `exec` (or `jobs` if your Calamares configuration uses that key).
*   **Order:** This module should run very late in the installation process.
    *   Ideally, it runs after all other installation and configuration tasks are complete.
    *   It should run regardless of whether the installation succeeded or failed, if the goal is to collect data about the installation process itself (success/failure state, duration, errors encountered if any). Calamares job modules run sequentially, and a failure in a prior job typically stops the sequence for subsequent *critical* jobs. Non-critical jobs might still run.
    *   Consider placing it after the `finished` module or as one of the very last jobs in the `postinstall` or `cleanup` phase.

**Example (YAML sequence file):**

```yaml
# Example 'jobs' sequence (often part of 'settings.conf' or specific branding sequence files)

# For settings.conf style:
# exec: {อินเทอร์เน็ต: [ ... ], prepare: [ ... ], install: [ ..., grubcfg, initramfs, ... ], postinstall: [ ..., securityhardening, telemetryjob ], cleanup: [ umount ] }

# For YAML sequence file style (e.g. mybrand.conf):
# ---
# # ... other settings ...
# execute:
#   # ... other phases and jobs ...
#   - phase: "postinstall"
#     jobs:
#       - module: "machineid" # Ensure machine ID is set if needed for anonymization
#       - module: "fstab"
#       - module: "localecfg"
#       - module: "users"
#       - module: "networkcfg"
#       - module: "services-systemd"
#       - module: "grubcfg"
#       - module: "bootloader"
#       - module: "securityhardening"
#       - module: "telemetryjob"   # <--- TELEMETRY SUBMISSION JOB
#       # Potentially other cleanup jobs
#   - phase: "cleanup"
#     jobs:
#       - module: "umount"
# # ...
```

The `telemetryjob` module will read `libcalamares.globalstorage["telemetry_consent_given"]`. If `True`, it will proceed with data collection and submission using the configured endpoint URL.

### 3. `telemetry_endpoint_url` Propagation to GlobalStorage

The `telemetryjob` module requires an endpoint URL to submit the collected data. This URL should be configurable per ISO build.

**Mechanism:**

1.  **`build_spec.yml` Configuration:**
    Add a key to your `build_spec.yml` (or equivalent ISO build configuration file) to specify the telemetry endpoint URL.

    ```yaml
    # In your build_spec.yml
    # ... other build specifications ...
    custom_settings:
      security_profile: "server"
      telemetry_endpoint_url: "https://your-telemetry-server.example.com/api/submit"
    # ...
    ```

2.  **Early Python Module to Load Settings (Reiteration):**
    As described for `security_hardening_profile`, an early-running Calamares Python module (e.g., `buildspec_loader` or an enhanced `environment` module) should read this value from the `build_spec.yml`.

    **Example code snippet for the loader module's `run()` function (extending previous example):**

    ```python
    import libcalamares
    import yaml
    import os

    BUILD_SPEC_PATH = "/etc/calamares/build_spec.yml" # Example path

    def run():
        # ... (loading for security_hardening_profile) ...

        telemetry_url = None
        try:
            if os.path.exists(BUILD_SPEC_PATH):
                with open(BUILD_SPEC_PATH, "r") as f:
                    spec = yaml.safe_load(f)

                telemetry_url = spec.get("custom_settings", {}).get("telemetry_endpoint_url")
                if telemetry_url:
                    libcalamares.utils.debug(f"Loaded telemetry_endpoint_url from build_spec: {telemetry_url}")
                else:
                    libcalamares.utils.warning("telemetry_endpoint_url not found in build_spec.")
            else:
                libcalamares.utils.warning(f"{BUILD_SPEC_PATH} not found. Telemetry endpoint URL not set.")
        except Exception as e:
            libcalamares.utils.error(f"Error loading telemetry_endpoint_url from {BUILD_SPEC_PATH}: {e}.")

        if telemetry_url:
            libcalamares.globalstorage.insert("telemetry_endpoint_url", telemetry_url)
            libcalamares.utils.log(f"telemetry_endpoint_url set in globalstorage: {telemetry_url}")
        else:
            # Store a None or empty string if not found, so telemetryjob can check existence
            libcalamares.globalstorage.insert("telemetry_endpoint_url", None)
            libcalamares.utils.log("telemetry_endpoint_url not configured.")

        return None
    ```
    This loader module ensures that `telemetry_endpoint_url` is available in `libcalamares.globalstorage` for the `telemetryjob` module to use. The `telemetryjob` should then check if this URL is valid before attempting any submission.

By following these integration steps, the `telemetryconsent` and `telemetryjob` modules can be effectively incorporated into the Calamares installation process, allowing for user consent and conditional data submission.
