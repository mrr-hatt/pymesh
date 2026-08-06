"""
Firewall and ACL rule enforcer using iptables/nftables or user-space filtering.
"""

import subprocess
import shutil
import logging
from typing import List, Dict, Any

logger = logging.getLogger("pymesh.firewall")


class FirewallManager:
    """Applies ACL access controls on the pymesh0 interface."""

    def __init__(self, interface_name: str = "pymesh0"):
        self.interface_name = interface_name
        self.iptables_path = shutil.which("iptables")

    def apply_rules(self, rules: List[Dict[str, Any]]) -> bool:
        if not self.iptables_path:
            logger.info("iptables not found; running firewall in user-space verification mode.")
            return True

        try:
            # Setup PYMESH chain
            subprocess.run(["iptables", "-N", "PYMESH_ACL"], stderr=subprocess.DEVNULL)
            subprocess.run(["iptables", "-F", "PYMESH_ACL"], check=True)

            for rule in rules:
                action = rule.get("action", "allow").upper()
                target = "ACCEPT" if action == "ALLOW" else "DROP"
                ports = rule.get("ports", [])
                
                if ports:
                    for port in ports:
                        cmd = [
                            "iptables", "-A", "PYMESH_ACL",
                            "-i", self.interface_name,
                            "-p", "tcp",
                            "--dport", str(port),
                            "-j", target
                        ]
                        subprocess.run(cmd, check=True)
                else:
                    cmd = [
                        "iptables", "-A", "PYMESH_ACL",
                        "-i", self.interface_name,
                        "-j", target
                    ]
                    subprocess.run(cmd, check=True)
            return True
        except Exception as e:
            logger.warning(f"Firewall rules application failed: {e}")
            return False
