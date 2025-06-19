# Calamares New Modules Documentation Outline

This document provides an outline for the user-facing documentation of the new `SecurityHardening` and `Telemetry` Calamares modules for the Z-Forge OS installer.

## 1. SecurityHardening Module

### 1.1. Overview

*   **Purpose:** The `SecurityHardening` module automatically applies a set of security best practices to the newly installed Z-Forge system. Its goal is to enhance the default security posture of the OS out-of-the-box.
*   **Type:** This is a Calamares "job" module, meaning it runs in the background during the installation process, typically after packages are installed but before the system is finalized.

### 1.2. Configuration

The behavior of the `SecurityHardening` module is controlled via a setting in the `build_spec.yml` file used to create the Z-Forge ISO.

*   **Key:** `security_hardening_profile` (expected under a `custom_settings` or similar top-level key).
*   **Available Profiles:**
    *   `baseline`: Applies a foundational set of security enhancements suitable for most desktop and server systems.
    *   `server`: Includes all `baseline` settings and adds further hardening measures typically recommended for server environments (e.g., more restrictive SSH, basic firewall).
    *   `none` (or omitting the key): Disables the module entirely. No security hardening tasks will be performed.

**Example `build_spec.yml` snippet:**

```yaml
custom_settings:
  security_hardening_profile: "server"
  # Other custom settings...
```

### 1.3. Features by Profile

#### 1.3.1. `baseline` Profile Features:

*   **Default Umask:** Sets a more restrictive default umask (e.g., 027) in `/etc/login.defs` to limit default file permissions for new files and directories.
*   **Basic Sysctl Hardening:** Applies common kernel parameter hardening via a configuration file in `/etc/sysctl.d/` (e.g., `90-baseline-hardening.conf`). This includes settings like:
    *   Disabling SUID core dumps (`fs.suid_dumpable=0`).
    *   Enabling Address Space Layout Randomization (`kernel.randomize_va_space=2`).
    *   Basic TCP/IP stack hardening (e.g., TCP SYN cookies, RP filter, disabling source routing/redirect acceptance).
*   **Tmpfs Hardening (Considerations):**
    *   Aims to secure shared memory (`/dev/shm`) and temporary file storage (`/tmp`) by applying options like `nodev`, `nosuid`, `noexec`.
    *   (Note: Direct modification of `/etc/fstab` is complex; this might be implemented via systemd mount unit drop-ins or by logging recommendations if direct modification is deemed too risky for an automated process).
*   **Kernel Module Blacklisting:** Prevents loading of unnecessary or potentially insecure kernel modules (e.g., uncommon filesystems, older protocols) by adding them to a blacklist file in `/etc/modprobe.d/` (e.g., `90-hardening-blacklist.conf`).

#### 1.3.2. `server` Profile Features:

Includes all features from the `baseline` profile, plus:

*   **SSHD Hardening:** Modifies `/etc/ssh/sshd_config` (or adds a configuration snippet in `/etc/ssh/sshd_config.d/`) to apply stricter SSH server settings:
    *   Disables root login (`PermitRootLogin no`).
    *   Disables password-based authentication (encouraging key-based auth) (`PasswordAuthentication no`).
    *   Disables challenge-response authentication.
    *   Disables X11 forwarding.
    *   Other settings like `MaxAuthTries`, `ClientAliveInterval`.
*   **UFW Firewall Setup:**
    *   Installs the `ufw` (Uncomplicated Firewall) package if not already present.
    *   Configures basic default rules: deny incoming traffic, allow outgoing traffic.
    *   Allows SSH traffic (typically on port 22/TCP) if an SSH server configuration is detected.
    *   Enables the UFW service.
*   **Stricter Sysctl Settings:** May apply additional server-focused kernel parameters via a separate file (e.g., `/etc/sysctl.d/91-server-hardening.conf`), such as ignoring ICMP broadcasts.

### 1.4. Logging

All actions performed by the `SecurityHardening` module, including file modifications and command executions, are logged to the main Calamares installation log. Users can review this log to see exactly which hardening steps were applied. Warnings or errors encountered during the process will also be logged.

---

## 2. Telemetry Modules (`TelemetryConsent` & `TelemetryJob`)

### 2.1. Overview

*   **Purpose:** The Telemetry modules allow users to optionally send anonymous system configuration and installation process data to the Z-Forge development team. This data is invaluable for understanding how Z-Forge is used, identifying common hardware configurations, pinpointing installation issues, and ultimately improving the operating system and installer.
*   **Key Principles:**
    *   **User Privacy:** Protecting user privacy is paramount.
    *   **Anonymization:** All collected data is designed to be anonymous. No personally identifiable information (PII) such as IP addresses, specific hostnames, or user file contents are collected. Unique IDs generated are for correlating a single report's data, not for tracking users.
    *   **Opt-In Consent:** Telemetry data is **only** sent if the user explicitly agrees by checking the consent box. It is opt-out by default.
    *   **Transparency:** The types of data collected are outlined below and should be detailed in a publicly accessible Privacy Policy.

### 2.2. Modules Involved

*   **`TelemetryConsent` (View Module):**
    *   This module presents a user interface screen during the early stages of installation.
    *   It clearly explains what telemetry is, why it's useful, and what kind of data is collected.
    *   It provides a checkbox for the user to give their explicit consent. By default, this checkbox is **unchecked** (opt-out).
    *   It includes a link to the project's Privacy Policy for more detailed information.
    *   The user's choice (consent given or not) is stored and respected by the `TelemetryJob` module.
*   **`TelemetryJob` (Job Module):**
    *   This module runs as a background task very late in the installation process (after success or failure is determined).
    *   It first checks if consent was given via the `TelemetryConsent` module.
    *   **If consent was given:** It collects the defined data points, constructs a JSON payload, and attempts to send it to a pre-configured telemetry endpoint URL.
    *   **If consent was NOT given:** The module does nothing and exits silently.
    *   The module is designed to fail silently (from the user's perspective) if there are network issues or problems sending the data, ensuring it does not disrupt the installation outcome.

### 2.3. Data Collected (Summary for User Documentation)

The following categories of anonymized data may be collected if consent is provided:

*   **Installation Report ID:** A randomly generated unique ID (`install_id`) for this specific installation report, used to group data from a single install. Not tied to a user or device long-term.
*   **ISO Version:** The version of the Z-Forge ISO being used.
*   **Calamares Version:** The version of the Calamares installer framework.
*   **Installation Status:** Whether the installation succeeded or failed. If failed, may include the general error message or module where failure occurred.
*   **Anonymized Hardware Profile:**
    *   Kernel Version.
    *   CPU: Anonymized model/family (e.g., "Intel(R)", "AMD") and core count.
    *   RAM: Total amount (e.g., in MB).
    *   Storage: For relevant disks (e.g., installation target), anonymized model/family, type (e.g., HDD, SSD, NVMe), and size. No partition layout details or filesystem contents.
    *   Display: Generally "Unknown" as it's hard to detect reliably in this phase.
    *   Network: Type of active network interface (e.g., ethernet, wifi).
*   **Configuration Choices (Anonymized):**
    *   Selected system language and locale (e.g., "en_US.UTF-8").
    *   Selected keyboard layout (e.g., "us").
    *   Selected timezone (e.g., "America/New_York").
    *   ZFS Configuration:
        *   Mode used (new pool or existing).
        *   If new pool: RAID type chosen (stripe, mirror, etc.).
        *   Whether ZFS encryption was enabled.
    *   Security Hardening Profile: Profile selected (baseline, server, none).
*   **Schema Version:** Version of the telemetry data structure itself.

**Important Reiteration:** No personally identifiable information (PII) such as specific IP addresses, MAC addresses, full hostnames, usernames, or contents of user files is ever collected or transmitted.
Users are encouraged to review the full (hypothetical) "Z-Forge Privacy Policy" and "Telemetry Data Schema" documents (link to be provided here) for complete transparency.

### 2.4. Configuration (for ISO Builders/Maintainers)

*   **Telemetry Endpoint URL:**
    *   The `TelemetryJob` module requires a URL to send the data to. This is configured in the `build_spec.yml` file for the ISO.
    *   Key: `telemetry_endpoint_url` (under `custom_settings` or similar).
    *   Example: `telemetry_endpoint_url: "https://telemetry.zforge.dev/submit"`
    *   This URL is read by an early Calamares module and placed into `libcalamares.globalstorage` for the `TelemetryJob` to use.
*   **User Consent Storage:**
    *   The `TelemetryConsent` module stores the user's choice as a boolean value in `libcalamares.globalstorage["telemetry_consent_given"]`.

### 2.5. Troubleshooting (Brief)

*   The `TelemetryJob` is designed to operate silently in the background and not interfere with the installation.
*   If data submission fails (e.g., due to network issues or server errors), it will be logged in the Calamares installation log (typically found in `/var/log/calamares/session.log` on the target system or available via the live session's log viewer). This is primarily for debugging by developers/maintainers.
*   The absence of telemetry data from an installation where consent was expected could indicate a network issue on the user's side or a problem reaching the telemetry server.
