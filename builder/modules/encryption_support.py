#!/usr/bin/env python3

import os
import logging
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional

from tqdm import tqdm

class EncryptionSupport:
    """
    Sets up full-disk encryption using ZFS native encryption or LUKS+ZFS,
    and optionally encrypts a separate boot pool if the environment var
    `Encrypt_boot` (or config["encrypt_boot"]) is set to true.

    Expects self.config to include:
      - method: "zfs-native" or "luks"
      - luks_device: "/dev/sdaX"       # if method=="luks"
      - luks_name: "cryptroot"
      - zpool_name: "rpool"
      - zfs_datasets: ["tank", "tank/home", ...]
      - boot_pool_name: "bpool"        # if encrypt_boot
      - boot_pool_device: "/dev/sdaY" # if encrypt_boot
      - encrypt_boot: bool (optional, overrides env var)
    """

    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        # Determine whether to encrypt a separate boot pool
        env_flag = os.getenv("Encrypt_boot", "false").lower() in ("1", "true", "yes")
        self.encrypt_boot = config.get("encrypt_boot", env_flag)

        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s %(message)s")

    def _run(self, cmd, **kwargs):
        """Helper to run a shell command with retries."""
        for attempt in range(1, 4):
            try:
                self.logger.debug(f"Running: {' '.join(cmd)} (attempt {attempt})")
                subprocess.run(cmd, check=True, **kwargs)
                return
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Command failed: {e}. Retrying...")
        self.logger.error(f"Command {' '.join(cmd)} failed after 3 attempts.")
        sys.exit(1)

    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        self.logger.info("=== EncryptionSupport start ===")
        resume = resume_data or {}
        result = {"completed_steps": []}

        # Step 1: Ensure required binaries exist
        for binary in ["zfs", "zpool", "cryptsetup"]:
            if not shutil.which(binary):
                self.logger.error(f"Required binary not found: {binary}")
                sys.exit(1)
        result["completed_steps"].append("check_binaries")
        self.logger.info("All required binaries present.")

        # Build list of steps
        steps = []
        if self.encrypt_boot:
            steps.append("create_boot_pool")

        method = self.config.get("method", "zfs-native")
        if method == "zfs-native":
            steps += ["create_pool", "enable_encryption", "create_datasets"]
        else:
            steps += ["setup_luks", "open_luks", "create_pool", "create_datasets"]

        for step in tqdm(steps, desc="Encrypt→", unit="step"):
            if step in resume:
                self.logger.info(f"Skipping {step}, already done.")
                continue

            if step == "create_boot_pool":
                # Create an encrypted ZFS boot pool
                bname = self.config["boot_pool_name"]
                bdev = self.config["boot_pool_device"]
                self._run([
                    "zpool", "create",
                    "-o", "feature@encryption=enabled",
                    "-o", "encryption=on",
                    "-o", "keyformat=passphrase",
                    "-o", "keylocation=prompt",
                    bname, bdev
                ])
                self.logger.info(f"Encrypted boot pool {bname} created on {bdev}.")

            elif step == "setup_luks":
                dev = self.config["luks_device"]
                name = self.config["luks_name"]
                self._run(["cryptsetup", "luksFormat", "--type", "luks2", dev])
                self._run(["cryptsetup", "open", dev, name])
                self.logger.info("LUKS container formatted and opened.")

            elif step == "open_luks":
                # Already opened by setup_luks, this step might be redundant in the list,
                # but it serves as a placeholder for a resume point if needed.
                pass

            elif step == "create_pool":
                pool = self.config["zpool_name"]
                target = (("/dev/mapper/" + self.config["luks_name"])
                                if method != "zfs-native"
                                else self.config["zpool_device"])
                self._run([
                    "zpool", "create",
                    "-o", "feature@encryption=enabled",
                    pool, target
                ])
                self.logger.info(f"ZFS pool {pool} created with encryption enabled.")

            elif step == "enable_encryption":
                pool = self.config["zpool_name"]
                self._run(["zfs", "set", "encryption=on", pool])
                self.logger.info(f"Encryption enabled on existing pool {pool}.")

            elif step == "create_datasets":
                pool = self.config["zpool_name"]
                for ds in self.config.get("zfs_datasets", []):
                    full = f"{pool}/{ds}"
                    self._run([
                        "zfs", "create",
                        "-o", "mountpoint=/" + ds,
                        full
                    ])
                    self.logger.info(f"Created dataset {full}.")
            else:
                self.logger.warning(f"Unknown step: {step}")

            result["completed_steps"].append(step)

        self.logger.info("=== EncryptionSupport complete ===")
        return result
