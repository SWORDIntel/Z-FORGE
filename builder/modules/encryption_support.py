# encryption_support.py

#!/usr/bin/env python3
import logging
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Dict, Optional

from tqdm import tqdm

class EncryptionSupport:
    """
    Sets up full-disk encryption using ZFS native encryption or LUKS+ZFS.
    Expects self.config to include:
      - method: "zfs-native" or "luks"
      - luks_device: "/dev/sdaX"      # if method=="luks"
      - luks_name: "cryptroot"
      - zpool_name: "rpool"
      - zfs_datasets: ["tank", "tank/home", ...]
    """

    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

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

        # Step 2: Perform encryption setup
        steps = []
        method = self.config.get("method", "zfs-native")
        if method == "zfs-native":
            steps = ["create_pool", "enable_encryption", "create_datasets"]
        else:
            steps = ["setup_luks", "open_luks", "create_pool", "create_datasets"]

        for step in tqdm(steps, desc="Encrypt→", unit="step"):
            if step in resume:
                self.logger.info(f"Skipping {step}, marked complete in resume_data.")
                continue

            if step == "setup_luks":
                dev = self.config["luks_device"]
                name = self.config["luks_name"]
                self._run(["cryptsetup", "luksFormat", "--type", "luks2", dev])
                self._run(["cryptsetup", "open", dev, name])
                self.logger.info("LUKS container formatted and opened.")
            elif step == "open_luks":
                # already opened by setup_luks
                pass
            elif step == "create_pool":
                pool = self.config["zpool_name"]
                target = ("/dev/mapper/" + self.config["luks_name"]) if method!="zfs-native" else self.config["zpool_device"]
                self._run(["zpool", "create", "-o", "feature@encryption=enabled", pool, target])
                self.logger.info(f"ZFS pool {pool} created with encryption enabled.")
            elif step == "enable_encryption":
                pool = self.config["zpool_name"]
                self._run(["zfs", "set", "encryption=on", pool])
                self.logger.info(f"Encryption enabled on existing pool {pool}.")
            elif step == "create_datasets":
                pool = self.config["zpool_name"]
                for ds in self.config.get("zfs_datasets", []):
                    full = f"{pool}/{ds}"
                    self._run(["zfs", "create", "-o", "mountpoint=/" + ds, full])
                    self.logger.info(f"Created dataset {full}.")
            else:
                self.logger.warning(f"Unknown step: {step}")
            result["completed_steps"].append(step)

        self.logger.info("=== EncryptionSupport complete ===")
        return result

