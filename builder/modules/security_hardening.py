# security_hardening.py

#!/usr/bin/env python3
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from tqdm import tqdm

class SecurityHardening:
    """
    Applies system-level hardening:
      - SSH lockdown
      - kernel sysctl tweaks
      - unattended-upgrades
      - minimal services
    Config keys:
      - ssh_disable_root: bool
      - sysctl: dict of key→value
      - services_disable: [ "avahi-daemon", ... ]
    """

    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    def _run(self, cmd):
        try:
            self.logger.debug(f"Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {e}")
            sys.exit(1)

    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        self.logger.info("=== SecurityHardening start ===")
        resume = resume_data or {}
        result = {"completed_steps": []}

        tasks = ["ssh_hardening", "apply_sysctl", "unattended_upgrades", "disable_services"]
        for task in tqdm(tasks, desc="Harden→"):
            if task in resume:
                self.logger.info(f"Skipping {task}")
                continue

            if task == "ssh_hardening" and self.config.get("ssh_disable_root", True):
                cfg = "/etc/ssh/sshd_config"
                self._run(["sed", "-i",
                           "s/^#*PermitRootLogin .*/PermitRootLogin no/",
                           cfg])
                self.logger.info("Disabled SSH root login.")
            elif task == "apply_sysctl":
                for key, val in self.config.get("sysctl", {}).items():
                    self._run(["sysctl", "-w", f"{key}={val}"])
                Path("/etc/sysctl.d/99-hardening.conf").write_text(
                    "\n".join(f"{k} = {v}" for k,v in self.config.get("sysctl", {}).items())
                )
                self._run(["sysctl", "--system"])
                self.logger.info("Applied sysctl settings.")
            elif task == "unattended_upgrades":
                self._run(["apt-get", "update"])
                self._run(["apt-get", "install", "-y", "unattended-upgrades"])
                self._run(["dpkg-reconfigure", "-plow", "unattended-upgrades"])
                self.logger.info("Configured unattended-upgrades.")
            elif task == "disable_services":
                for svc in self.config.get("services_disable", []):
                    self._run(["systemctl", "disable", "--now", svc])
                    self.logger.info(f"Disabled service: {svc}")
            else:
                self.logger.debug(f"No action for task {task}")
            result["completed_steps"].append(task)

        self.logger.info("=== SecurityHardening complete ===")
        return result

