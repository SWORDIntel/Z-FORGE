#!/usr/bin/env python3

import os
import subprocess
import json
import uuid
import datetime
import urllib.request
import urllib.error
import urllib.parse # Added for URL parsing
import socket # Added for DNS lookup
import re # For parsing command outputs

import libcalamares
from libcalamares import utils

# Configuration
TELEMETRY_SCHEMA_VERSION = "1.0.0"
DEFAULT_ISO_VERSION = "unknown_iso_version" # Fallback if not found
USER_AGENT = "ZForgeTelemetryClient/1.0"
REQUEST_TIMEOUT_SECONDS = 30 # Timeout for HTTP request

# Helper to get a value from globalstorage or return a default
def gs_get(key, default=None):
    val = libcalamares.globalstorage.value(key)
    return val if val is not None else default

def _chroot_exec(root_path: str, command_list: list, check_return: bool = True, universal_newlines=True):
    """Executes a command in the chroot environment, returns its stdout or None."""
    try:
        full_command = ["chroot", root_path] + command_list
        utils.debug(f"Executing chroot command: {' '.join(full_command)}")
        result = subprocess.run(full_command, capture_output=True, text=True, check=check_return, universal_newlines=universal_newlines)
        if result.stderr:
            utils.warning(f"Chroot command '{' '.join(command_list)}' stderr: {result.stderr.strip()}")
        return result.stdout.strip() if result.stdout else ""
    except subprocess.CalledProcessError as e:
        utils.error(f"Chroot command '{' '.join(command_list)}' failed: {e.stderr}")
        return None
    except FileNotFoundError:
        utils.error(f"Chroot command failed: chroot or '{command_list[0]}' not found in host system.")
        return None
    except Exception as e:
        utils.error(f"An unexpected error occurred with _chroot_exec for {' '.join(command_list)}: {e}")
        return None

def _check_url_availability(url_string: str) -> bool:
    """
    Checks basic network availability of the URL's hostname via DNS lookup.
    Returns True if DNS lookup succeeds, False otherwise.
    """
    if not url_string:
        return False
    try:
        parsed_url = urllib.parse.urlparse(url_string)
        hostname = parsed_url.hostname
        if not hostname:
            utils.warning(f"Could not parse hostname from URL: {url_string}")
            return False

        utils.debug(f"Attempting DNS lookup for hostname: {hostname}")
        socket.gethostbyname(hostname)
        utils.debug(f"DNS lookup successful for {hostname}.")
        return True
    except socket.gaierror as e: # getaddrinfo error (includes DNS failures)
        utils.warning(f"DNS lookup failed for hostname {hostname} from URL {url_string}: {e}")
        return False
    except Exception as e:
        utils.error(f"Unexpected error during URL availability check for {url_string}: {e}")
        return False

def _get_calamares_versions():
    """Gets Calamares version."""
    try:
        version = getattr(libcalamares, "VERSION_STRING", "unknown_calamares_version")
        return {"calamares_version": version}
    except Exception as e:
        utils.warning(f"Could not determine Calamares version: {e}")
        return {"calamares_version": "unknown_calamares_version"}

def _get_system_info(root_path: str):
    """Gathers anonymized system hardware information."""
    info = {}
    try:
        # Kernel
        kernel_raw = _chroot_exec(root_path, ["uname", "-r"])
        info["kernel_version"] = kernel_raw if kernel_raw else "unknown"

        # CPU
        cpu_info_raw = _chroot_exec(root_path, ["lscpu"])
        if cpu_info_raw:
            cpu_model_match = re.search(r"Model name:\s+(.+)", cpu_info_raw)
            if cpu_model_match:
                info["cpu_model_family"] = cpu_model_match.group(1).split()[0]
            cpu_cores_match = re.search(r"CPU\(s\):\s+(\d+)", cpu_info_raw)
            if cpu_cores_match:
                info["cpu_cores"] = int(cpu_cores_match.group(1))

        # RAM
        ram_info_raw = _chroot_exec(root_path, ["free", "-m"])
        if ram_info_raw:
            ram_total_match = re.search(r"Mem:\s+(\d+)", ram_info_raw)
            if ram_total_match:
                info["ram_total_mb"] = int(ram_total_match.group(1))

        # Storage
        storage_info_raw = _chroot_exec(root_path, ["lsblk", "-bJO", "path,type,size,model,tran", "--output-all", "--exclude", "7,1"])
        if storage_info_raw:
            try:
                storage_data = json.loads(storage_info_raw)
                info["storage_devices"] = []
                for device in storage_data.get("blockdevices", []):
                    if device.get("type") == "disk":
                        info["storage_devices"].append({
                            "type": device.get("tran", "unknown_tran"),
                            "model_family": device.get("model", "Unknown Model").split()[0] if device.get("model") else "Unknown",
                            "size_bytes": device.get("size", 0)
                        })
            except json.JSONDecodeError as e:
                utils.warning(f"Failed to parse storage lsblk JSON: {e}")

        info["display_resolution"] = "Unknown"

        net_info_raw = _chroot_exec(root_path, ["ip", "-o", "link", "show"])
        if net_info_raw:
            active_iface_match = re.search(r"\d+:\s+([a-zA-Z0-9]+)(?<!lo):\s+<[^>]*UP[^>]*>", net_info_raw)
            if active_iface_match:
                iface_name = active_iface_match.group(1)
                if iface_name.startswith("en") or iface_name.startswith("eth"):
                    info["network_type"] = "ethernet"
                elif iface_name.startswith("wl"):
                    info["network_type"] = "wifi"
                else:
                    info["network_type"] = "other"
            else:
                info["network_type"] = "none_active"
    except Exception as e:
        utils.error(f"Error gathering system info: {e}")
    return info

def _get_config_choices():
    choices = {}
    try:
        choices["language"] = gs_get("language", "unknown")
        choices["keyboard_layout"] = gs_get("keyboard_layout", "unknown")
        choices["timezone"] = gs_get("timezone", "unknown")
        choices["zfs_operation_mode"] = gs_get("zfs_operation_mode", "unknown")
        if choices["zfs_operation_mode"] == "new_pool":
            choices["zfs_new_pool_raid_type"] = gs_get("zfs_new_pool_raid_type", "unknown")
        choices["zfs_encryption_enabled"] = gs_get("zfs_encryption_enabled", False)
        choices["security_profile"] = gs_get("security_hardening_profile", "none")
    except Exception as e:
        utils.error(f"Error gathering config choices: {e}")
    return choices

def _get_installation_status():
    if libcalamares.globalstorage.value(" সবাইকে_বিদায়") is True: # Note: ' সবাইকে_বিদায়' is Bengali for "goodbye everyone"
        return {"status": "success", "error_details": None}
    else:
        error_message = gs_get("on_error_message", "Unknown error or installation incomplete.")
        return {"status": "failure", "error_details": str(error_message)}

def _build_json_payload(collected_data: dict):
    iso_version = gs_get("iso_version", DEFAULT_ISO_VERSION)
    payload = {
        "schema_version": TELEMETRY_SCHEMA_VERSION,
        "install_id": str(uuid.uuid4()),
        "iso_version": iso_version,
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "data": collected_data
    }
    try:
        return json.dumps(payload)
    except TypeError as e:
        utils.error(f"Could not serialize telemetry data to JSON: {e}")
        return None

def _send_telemetry(endpoint_url: str, json_data: str):
    utils.log(f"Attempting to send telemetry data to: {endpoint_url}")
    try:
        headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
        request = urllib.request.Request(endpoint_url, data=json_data.encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            response_body = response.read().decode('utf-8', errors='replace')
            if response.status >= 200 and response.status < 300:
                utils.log(f"Telemetry data successfully sent. Response: {response.status} {response_body[:200]}")
                return True
            else:
                utils.warning(f"Telemetry server responded with {response.status}: {response_body[:500]}")
                return False
    except urllib.error.HTTPError as e:
        utils.warning(f"HTTPError sending telemetry: {e.code} {e.reason} - {e.read().decode(errors='replace')[:500]}")
    except urllib.error.URLError as e:
        utils.warning(f"URLError sending telemetry: {e.reason}")
    except Exception as e:
        utils.error(f"Unexpected error sending telemetry: {e}")
    return False

def run():
    utils.log("Starting TelemetryJob module...")

    consent_given = gs_get("telemetry_consent_given", False)
    if not isinstance(consent_given, bool):
        utils.warning(f"telemetry_consent_given was not a boolean ({consent_given}), defaulting to False.")
        consent_given = False

    if not consent_given:
        utils.log("Telemetry consent not given. Exiting TelemetryJob.")
        return None

    endpoint_url = gs_get("telemetry_endpoint_url")
    if not endpoint_url or not endpoint_url.lower().startswith(('http://', 'https://')):
        utils.warning(f"Invalid or missing telemetry_endpoint_url: '{endpoint_url}'. Cannot send telemetry.")
        return None

    # Check URL availability via DNS lookup
    if not _check_url_availability(endpoint_url):
        # Logged in _check_url_availability, but we still proceed as per Task 1.3 (non-blocking)
        utils.warning(f"DNS lookup for telemetry endpoint {endpoint_url} failed or it might be unavailable. Will attempt to send anyway.")
    else:
        utils.log(f"Telemetry endpoint {endpoint_url} appears resolvable via DNS.")


    root_mount_point = gs_get("rootMountPoint")
    valid_root_mount_point = True
    if not root_mount_point or root_mount_point == "/":
        utils.error("rootMountPoint not valid for telemetry job. Some system info will be unavailable.")
        valid_root_mount_point = False
        root_mount_point = None # Ensure chroot commands are not attempted with invalid path

    all_data = {}
    all_data.update(_get_calamares_versions())
    if valid_root_mount_point:
        all_data["system_info"] = _get_system_info(root_mount_point)
    else:
        all_data["system_info"] = {"error": "rootMountPoint not available or invalid"}

    all_data["config_choices"] = _get_config_choices()
    all_data["installation_status"] = _get_installation_status()

    json_payload = _build_json_payload(all_data)

    if json_payload:
        if _send_telemetry(endpoint_url, json_payload):
            utils.log("TelemetryJob sending attempt finished.") # Success is logged in _send_telemetry
        else:
            utils.warning("TelemetryJob: Data sending attempt failed or was partially successful.")
    else:
        utils.error("TelemetryJob: Failed to build JSON payload. No data sent.")

    return None
