#!/usr/bin/env python3
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

class FirewallSetup:
    """
    Configures a secure firewall using nftables.
    """

    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.chroot_path = self.workspace / "chroot"

    def _run_chroot_command(self, cmd, check=True):
        chrooted_cmd = ["chroot", str(self.chroot_path)] + cmd
        result = subprocess.run(chrooted_cmd, check=check, capture_output=True, text=True)
        if result.returncode != 0 and check:
            self.logger.error(f"Command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
        return result

    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Dict] = None) -> Dict:
        self.logger.info("=== FirewallSetup start ===")

        firewall_config = self.config.get("firewall_config", {})
        if not firewall_config.get("enabled", False):
            self.logger.info("Firewall setup is disabled in the build configuration. Skipping.")
            return {'status': 'skipped'}

        try:
            self.logger.info("Installing nftables...")
            self._run_chroot_command(["apt-get", "install", "-y", "nftables"])

            self.logger.info("Generating nftables ruleset...")
            ruleset = self._generate_ruleset(firewall_config)

            ruleset_path = self.chroot_path / "etc" / "nftables.conf"
            with open(ruleset_path, "w") as f:
                f.write(ruleset)

            self.logger.info("Enabling nftables service...")
            self._run_chroot_command(["systemctl", "enable", "nftables"])

            self.logger.info("=== FirewallSetup complete ===")
            return {'status': 'success'}

        except Exception as e:
            self.logger.error(f"FirewallSetup failed: {e}")
            return {'status': 'error', 'error': str(e)}

    def _generate_ruleset(self, config: Dict) -> str:

        allowed_tcp = config.get("allowed_tcp_ports", [22])
        allowed_udp = config.get("allowed_udp_ports", [])

        rules = [
            "#!/usr/sbin/nft -f",
            "flush ruleset",
            "",
            "table inet filter {",
            "    chain input {",
            "        type filter hook input priority 0; policy drop;",
            "",
            "        # Allow loopback traffic",
            "        iif lo accept",
            "",
            "        # Allow established and related connections",
            "        ct state {established, related} accept",
            "",
        ]

        if allowed_tcp:
            rules.append(f"        tcp dport {{ {', '.join(map(str, allowed_tcp))} }} accept")
        if allowed_udp:
            rules.append(f"        udp dport {{ {', '.join(map(str, allowed_udp))} }} accept")

        rules.extend([
            "    }",
            "    chain forward {",
            "        type filter hook forward priority 0; policy drop;",
            "    }",
            "    chain output {",
            "        type filter hook output priority 0; policy accept;",
            "    }",
            "}",
        ])

        return "\n".join(rules)
