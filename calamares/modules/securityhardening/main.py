#!/usr/bin/env python3

import os
import subprocess
import re
import json # For lsblk parsing if needed by helpers, though not directly used in this version.
import libcalamares
from libcalamares import utils

# --- Configuration Constants ---
# Sysctl settings
BASELINE_SYSCTL_SETTINGS = {
    "fs.suid_dumpable": "0",
    "kernel.randomize_va_space": "2",
    "net.ipv4.tcp_syncookies": "1",
    "net.ipv4.rfc1337": "1", # Protects against time-wait assassination
    "net.ipv4.conf.all.rp_filter": "1",
    "net.ipv4.conf.default.rp_filter": "1",
    "net.ipv4.conf.all.accept_source_route": "0",
    "net.ipv4.conf.default.accept_source_route": "0",
    "net.ipv4.conf.all.accept_redirects": "0",
    "net.ipv4.conf.default.accept_redirects": "0",
    "net.ipv4.conf.all.secure_redirects": "0",
    "net.ipv4.conf.default.secure_redirects": "0",
    "net.ipv6.conf.all.accept_ra": "0", # Adjust if IPv6 RA is needed
    "net.ipv6.conf.default.accept_ra": "0",
    "net.ipv6.conf.all.accept_redirects": "0",
    "net.ipv6.conf.default.accept_redirects": "0",
    "net.ipv6.conf.all.accept_source_route": "0",
    "net.ipv6.conf.default.accept_source_route": "0",
}

SERVER_SYSCTL_SETTINGS = {
    "net.ipv4.icmp_echo_ignore_broadcasts": "1",
    "net.ipv4.icmp_ignore_bogus_error_responses": "1",
    # Add more server-specific sysctl settings if needed
}

# Kernel modules to blacklist
BLACKLISTED_MODULES = [
    "cramfs", "freevxfs", "jffs2", "hfs", "hfsplus",
    "squashfs", "udf", "usb_storage", "ieee1394", # FireWire, remove usb_storage if USB boot/install media needed post-hardening
    "dccp", "sctp", "rds", "tipc", # Uncommon network protocols
]

# SSHd settings to harden
SSHD_HARDENING_SETTINGS = {
    "PermitRootLogin": "no",
    "PasswordAuthentication": "no",
    "ChallengeResponseAuthentication": "no",
    "UsePAM": "yes", # Ensure PAM is used, common default
    "X11Forwarding": "no",
    "PrintMotd": "no", # Optional: some prefer it on
    "AllowAgentForwarding": "no",
    "PermitEmptyPasswords": "no",
    "MaxAuthTries": "3",
    "ClientAliveInterval": "300", # 5 minutes
    "ClientAliveCountMax": "2", # Effectively 10 minutes timeout for idle clients
    "LoginGraceTime": "60", # 1 minute
    "AllowTcpForwarding": "no",
    # "Ciphers": "aes256-ctr,aes192-ctr,aes128-ctr", # Example: Modern ciphers, might need adjustment
    # "MACs": "hmac-sha2-512,hmac-sha2-256", # Example: Modern MACs
    # "KexAlgorithms": "diffie-hellman-group-exchange-sha256", # Example: Modern KEX
}


def _chroot_exec(root_path: str, command_list: list, check_return: bool = True):
    """Executes a command in the chroot environment."""
    try:
        full_command = ["chroot", root_path] + command_list
        utils.debug(f"Executing chroot command: {' '.join(full_command)}")
        # Using target_env_call for better integration with Calamares environment if possible.
        # For now, direct chroot call if target_env_call is not straightforwardly available
        # or requires more setup for simple commands.
        # returncode = utils.target_env_call(command_list, root_path=root_path)
        # if check_return and returncode != 0:
        #     utils.error(f"Chroot command '{' '.join(command_list)}' failed with return code {returncode}")
        #     return False
        # return True

        result = subprocess.run(full_command, capture_output=True, text=True, check=check_return)
        if result.stdout:
            utils.debug(f"Chroot command stdout: {result.stdout.strip()}")
        if result.stderr:
            utils.warning(f"Chroot command stderr: {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        utils.error(f"Chroot command '{' '.join(command_list)}' failed: {e.stderr}")
        return False
    except FileNotFoundError:
        utils.error(f"Chroot command failed: chroot or '{command_list[0]}' not found in host system.")
        return False

def _modify_file_settings(filepath: str, settings: dict, comment_prefix: str = "#", separator: str = " "):
    """
    Modifies settings in a configuration file.
    If a setting key exists (commented or not), its line is replaced.
    If a setting key does not exist, it's appended to the file.
    """
    if not os.path.exists(filepath):
        utils.warning(f"File {filepath} not found. Skipping modifications.")
        return False

    utils.debug(f"Modifying settings in {filepath} with: {settings}")

    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
    except IOError as e:
        utils.error(f"Error reading {filepath}: {e}")
        return False

    new_lines = []
    settings_to_process = settings.copy()

    for line in lines:
        stripped_line = line.strip()
        processed_line = False
        for key, value in list(settings_to_process.items()):
            # Regex to match key, possibly commented, followed by optional space and value
            # Handles "Key Value", "#Key Value", "Key    Value"
            # Ensures that the key is followed by a space or end of line to avoid partial matches (e.g. "Key" matching "KeyMore")
            if re.match(rf"^\s*{re.escape(comment_prefix)}?\s*{re.escape(key)}(\s+.*|$)", stripped_line):
                new_lines.append(f"{key}{separator}{value}\n")
                utils.debug(f"Modified existing line for '{key}' to '{key}{separator}{value}' in {filepath}")
                del settings_to_process[key]
                processed_line = True
                break
        if not processed_line:
            new_lines.append(line)

    for key, value in settings_to_process.items():
        new_lines.append(f"{key}{separator}{value}\n")
        utils.debug(f"Appended new setting '{key}{separator}{value}' to {filepath}")

    try:
        with open(filepath, "w") as f:
            f.writelines(new_lines)
        utils.debug(f"Successfully wrote modifications to {filepath}")
        return True
    except IOError as e:
        utils.error(f"Error writing to {filepath}: {e}")
        return False

def _append_to_file_if_not_exists(filepath: str, content_to_add: list, ensure_newline_at_start=True):
    """Appends lines to a file if they don't already exist (simple string match)."""
    if not os.path.exists(os.path.dirname(filepath)):
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            utils.debug(f"Created directory for {filepath}")
        except OSError as e:
            utils.error(f"Failed to create directory for {filepath}: {e}")
            return False

    existing_content = []
    file_exists_before_write = os.path.exists(filepath)
    if file_exists_before_write:
        try:
            with open(filepath, "r") as f:
                existing_content = [line.strip() for line in f.readlines()]
        except IOError as e:
            utils.error(f"Error reading {filepath}: {e}")
            return False

    lines_to_append = [line for line in content_to_add if line.strip() not in existing_content]

    if lines_to_append:
        try:
            with open(filepath, "a") as f:
                if ensure_newline_at_start and file_exists_before_write and (not existing_content or existing_content[-1] != ""):
                    f.write("\n")
                for line in lines_to_append:
                    f.write(line + "\n")
            utils.debug(f"Appended settings to {filepath}: {lines_to_append}")
        except IOError as e:
            utils.error(f"Error appending to {filepath}: {e}")
            return False
    else:
        utils.debug(f"All settings already present in {filepath} or no new settings to add. No changes made.")
    return True


# --- Baseline Profile Functions ---
def _set_default_umask(root_path: str):
    utils.log("Setting default umask to 027...")
    login_defs_path = os.path.join(root_path, "etc/login.defs")

    if not os.path.exists(login_defs_path):
        utils.warning(f"{login_defs_path} not found. Skipping umask setting.")
        return

    new_lines = []
    made_change = False
    umask_found_and_set = False

    try:
        with open(login_defs_path, "r") as f:
            lines = f.readlines()
    except IOError as e:
        utils.error(f"Error reading {login_defs_path}: {e}")
        return

    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith("UMASK"):
            if stripped_line == "UMASK           027" or stripped_line == "UMASK 027":
                umask_found_and_set = True # Already correct
            new_lines.append("UMASK           027\n") # Standardize format
            made_change = True
            utils.debug(f"Modified UMASK setting in {login_defs_path}")
        elif stripped_line.startswith("#UMASK"):
            new_lines.append("UMASK           027\n")
            made_change = True
            utils.debug(f"Uncommented and modified UMASK setting in {login_defs_path}")
        else:
            new_lines.append(line)

    if not umask_found_and_set and not any(l.strip().startswith("UMASK") for l in new_lines if not l.strip().startswith("#")): # If no active UMASK line was added
        new_lines.append("\nUMASK           027\n")
        made_change = True
        utils.debug(f"Appended UMASK 027 to {login_defs_path}")

    if made_change and not umask_found_and_set : # Only write if actual change occurred
        try:
            with open(login_defs_path, "w") as f:
                f.writelines(new_lines)
            utils.log("Successfully set default umask.")
        except IOError as e:
            utils.error(f"Error writing to {login_defs_path}: {e}")
    elif umask_found_and_set:
         utils.debug("UMASK already correctly configured as 027.")
    else:
        utils.debug("No change needed for UMASK or file write error occurred previously.")

def _harden_tmpfs(root_path: str):
    utils.log("Hardening tmpfs mounts (/tmp, /dev/shm)...")
    fstab_path = os.path.join(root_path, "etc/fstab")

    if not os.path.exists(fstab_path):
        utils.warning(f"{fstab_path} not found. Skipping tmpfs hardening.")
        return

    utils.debug("For tmpfs hardening, manual review of fstab or systemd mount units is often preferred for robustness.")
    utils.debug("This script will log intended actions for /tmp and /dev/shm if found, but not modify fstab directly yet.")
    # For example, to make /tmp noexec,nosuid,nodev:
    # Check if /tmp is a tmpfs mount. If so, add/modify options.
    # If /tmp is a separate partition, options are set there.
    # If systemd is used, consider creating /etc/systemd/system/tmp.mount.d/override.conf
    # with [Mount] Options=rw,nosuid,nodev,noexec,relatime
    # Similar for /dev/shm.
    # For now, only logging:
    utils.log("Placeholder: Would ensure /tmp and /dev/shm have nodev,nosuid,noexec options if they are tmpfs.")


def _apply_sysctl_settings(root_path: str, settings: dict, filename: str = "90-hardening.conf"):
    utils.log(f"Applying sysctl settings to {filename}...")
    sysctl_conf_d_path = os.path.join(root_path, "etc/sysctl.d")
    if not os.path.exists(sysctl_conf_d_path):
        try:
            os.makedirs(sysctl_conf_d_path)
            utils.debug(f"Created directory {sysctl_conf_d_path}")
        except OSError as e:
            utils.error(f"Failed to create {sysctl_conf_d_path}: {e}")
            return

    sysctl_conf_path = os.path.join(sysctl_conf_d_path, filename)
    lines_to_add = [f"{key} = {value}" for key, value in settings.items()]

    if _append_to_file_if_not_exists(sysctl_conf_path, lines_to_add):
        utils.log(f"Sysctl settings applied/updated in {sysctl_conf_path}.")
    else:
        utils.warning(f"Failed to apply all sysctl settings to {sysctl_conf_path}.")


def _blacklist_kernel_modules(root_path: str):
    utils.log("Blacklisting kernel modules...")
    modprobe_d_path = os.path.join(root_path, "etc/modprobe.d")
    if not os.path.exists(modprobe_d_path):
        try:
            os.makedirs(modprobe_d_path)
            utils.debug(f"Created directory {modprobe_d_path}")
        except OSError as e:
            utils.error(f"Failed to create {modprobe_d_path}: {e}")
            return

    blacklist_conf_path = os.path.join(modprobe_d_path, "90-hardening-blacklist.conf")
    lines_to_add = [f"blacklist {module}" for module in BLACKLISTED_MODULES]

    if _append_to_file_if_not_exists(blacklist_conf_path, lines_to_add):
        utils.log(f"Kernel module blacklist updated in {blacklist_conf_path}.")
    else:
        utils.warning(f"Failed to update kernel module blacklist at {blacklist_conf_path}.")


def apply_baseline_profile(root_path: str):
    utils.log("Applying Baseline Security Profile...")
    _set_default_umask(root_path)
    _harden_tmpfs(root_path)
    _apply_sysctl_settings(root_path, BASELINE_SYSCTL_SETTINGS, "90-baseline-hardening.conf")
    _blacklist_kernel_modules(root_path)
    utils.log("Baseline Security Profile application finished.")


# --- Server Profile Functions ---
def _harden_ssh_server(root_path: str):
    utils.log("Hardening SSH server (sshd_config)...")
    sshd_config_path = os.path.join(root_path, "etc/ssh/sshd_config")
    sshd_config_d_path = os.path.join(root_path, "etc/ssh/sshd_config.d")
    hardening_conf_filename = "90-hardening.conf"

    # Prefer placing overrides in sshd_config.d if it exists and is likely used
    # (OpenSSH usually includes "Include /etc/ssh/sshd_config.d/*.conf" by default)
    if os.path.isdir(sshd_config_d_path):
        hardening_conf_path = os.path.join(sshd_config_d_path, hardening_conf_filename)
        utils.debug(f"sshd_config.d directory exists. Writing hardening to {hardening_conf_path}")

        # Create a clean config file for our settings.
        # This avoids modifying existing files in sshd_config.d if we run this multiple times
        # or if other tools also place files there.
        try:
            with open(hardening_conf_path, "w") as f: # Overwrite this specific hardening file
                for key, value in SSHD_HARDENING_SETTINGS.items():
                    f.write(f"{key} {value}\n")
            utils.log(f"SSH hardening settings written to {hardening_conf_path}")
        except IOError as e:
            utils.error(f"Failed to write SSH hardening to {hardening_conf_path}: {e}")
        return

    # Fallback to modifying sshd_config directly if sshd_config.d doesn't exist
    if not os.path.exists(sshd_config_path):
        utils.warning("sshd_config not found, and no sshd_config.d directory. Skipping SSH server hardening.")
        return

    if _modify_file_settings(sshd_config_path, SSHD_HARDENING_SETTINGS, comment_prefix="#", separator=" "):
        utils.log("sshd_config hardened by direct modification.")
    else:
        utils.warning("Failed to harden sshd_config directly or no changes made.")


def _setup_ufw_firewall(root_path: str):
    utils.log("Setting up UFW firewall...")
    if not _chroot_exec(root_path, ["which", "ufw"], check_return=False): # Check if UFW command exists
        utils.log("UFW not found, attempting to install...")
        if not _chroot_exec(root_path, ["apt-get", "update", "-q"], check_return=False): # Suppress non-critical errors for update
            utils.warning("apt-get update potentially failed. Proceeding with UFW install attempt.")
        if not _chroot_exec(root_path, ["apt-get", "install", "-y", "ufw"]):
            utils.warning("Failed to install UFW. Firewall setup skipped.")
            return
        utils.log("UFW installed successfully.")

    _chroot_exec(root_path, ["ufw", "logging", "on"])
    _chroot_exec(root_path, ["ufw", "default", "deny", "incoming"])
    _chroot_exec(root_path, ["ufw", "default", "allow", "outgoing"])

    sshd_config_path = os.path.join(root_path, "etc/ssh/sshd_config")
    if os.path.exists(sshd_config_path):
        _chroot_exec(root_path, ["ufw", "allow", "ssh"])
        utils.log("UFW: Allowed SSH.")
    else:
        utils.debug("sshd_config not found, not explicitly allowing SSH in UFW by default.")

    # To enable UFW without interactive prompt:
    # One way is to echo 'y' | ufw enable, but that's tricky with chroot_exec.
    # Another is to modify /etc/ufw/ufw.conf to set ENABLED=yes
    ufw_conf_path = os.path.join(root_path, "etc/ufw/ufw.conf")
    if _modify_file_settings(ufw_conf_path, {"ENABLED": "yes"}, comment_prefix="#", separator="="):
         utils.log("UFW configured to be enabled on boot via ufw.conf.")
    else:
         utils.warning("Could not set UFW to enabled in ufw.conf. Manual 'ufw enable' might be needed post-install.")
    # Alternatively, if systemd is present and ufw service is standard:
    # _chroot_exec(root_path, ["systemctl", "enable", "ufw"])
    # _chroot_exec(root_path, ["systemctl", "start", "ufw"]) # Start if live changes needed
    utils.log("UFW basic rules configured. It should be enabled on next boot.")

def apply_server_profile(root_path: str):
    utils.log("Applying Server Security Profile...")
    apply_baseline_profile(root_path)

    _harden_ssh_server(root_path)
    _setup_ufw_firewall(root_path)
    _apply_sysctl_settings(root_path, SERVER_SYSCTL_SETTINGS, "91-server-hardening.conf")

    utils.log("Server Security Profile application finished.")

def run():
    utils.log("Starting Security Hardening module...")

    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    if not root_mount_point :
        utils.debug("rootMountPoint not found in globalStorage. Trying to use '/' for testing (NOT FOR PRODUCTION).")
        # This is a fallback for testing outside Calamares.
        # In a real Calamares environment, rootMountPoint should always be set by partitioning.
        # If Calamares runs this module before partitioning (e.g. in initramfs with no target yet),
        # this module should not run or should detect that state.
        # For safety in production, if rootMountPoint is '/', it's the live system.
        # This module should operate on the TARGET system.
        # A Calamares job module typically runs after partitioning and mounting the target.
        utils.critical("rootMountPoint is not set. This module must run after target system is mounted.")
        return libcalamares.JobResult.ERROR # Critical error if no target

    if root_mount_point == "/":
        utils.critical("rootMountPoint is '/', which means live system. Hardening should apply to target. Aborting.")
        return libcalamares.JobResult.ERROR

    if not os.path.isabs(root_mount_point):
        utils.critical(f"rootMountPoint '{root_mount_point}' is not an absolute path.")
        return libcalamares.JobResult.ERROR
    if not os.path.isdir(root_mount_point):
        utils.critical(f"rootMountPoint '{root_mount_point}' does not exist or is not a directory.")
        return libcalamares.JobResult.ERROR

    profile = libcalamares.globalstorage.value("security_hardening_profile")
    if not profile:
        profile = "none"
        utils.warning("security_hardening_profile not found in globalstorage, defaulting to 'none'.")

    utils.log(f"Selected security hardening profile: {profile} on target {root_mount_point}")

    if profile == "baseline":
        apply_baseline_profile(root_mount_point)
    elif profile == "server":
        apply_server_profile(root_mount_point)
    elif profile == "none":
        utils.log("No security hardening profile selected. Skipping.")
    else:
        utils.warning(f"Unknown security hardening profile: {profile}. Skipping.")
        return libcalamares.JobResult.OK # Or WARNING, not necessarily an error for unknown profile string.

    utils.log("Security Hardening module finished successfully.")
    return libcalamares.JobResult.OK
