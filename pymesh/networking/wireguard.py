"""
WireGuard interface manager abstraction (pyroute2 / wg CLI / Dry-run fallback).
"""

import subprocess
import shutil
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger("pymesh.wireguard")


class WireGuardManager:
    """Manages WireGuard devices, keys, peers, and persistent keepalives."""

    def __init__(self, interface_name: str = "pymesh0"):
        self.interface_name = interface_name
        self._dry_run = False

    def create_interface(self, listen_port: int = 51820) -> bool:
        """Creates the WireGuard netlink interface if privileges allow."""
        try:
            from pyroute2 import IPRoute
            with IPRoute() as ipr:
                if not ipr.link_lookup(ifname=self.interface_name):
                    ipr.link("add", ifname=self.interface_name, kind="wireguard")
                    logger.info(f"Created WireGuard interface {self.interface_name}")
                return True
        except Exception as e:
            logger.debug(f"pyroute2 link creation note: {e}")

        # Fallback to ip link tool
        try:
            res = subprocess.run(["ip", "link", "add", "dev", self.interface_name, "type", "wireguard"], capture_output=True)
            if res.returncode == 0 or "File exists" in res.stderr.decode():
                logger.info(f"Created interface {self.interface_name} via ip CLI")
                return True
        except Exception as e:
            logger.warning(f"Unable to create interface: {e}")

        self._dry_run = True
        return False

    def configure_interface(
        self,
        private_key_b64: str,
        listen_port: int = 51820,
    ) -> bool:
        """Sets the private key and listen port for the WireGuard interface."""
        if self._dry_run:
            logger.info(f"[Dry-run] Configured {self.interface_name} port {listen_port}")
            return True

        # Try pyroute2
        try:
            from pyroute2 import WireGuard
            wg = WireGuard()
            wg.set(
                self.interface_name,
                private_key=private_key_b64,
                listen_port=listen_port,
            )
            return True
        except Exception as e:
            logger.debug(f"pyroute2 wg configure note: {e}")

        # Fallback to wg CLI tool
        if shutil.which("wg"):
            import tempfile
            import os
            try:
                with tempfile.NamedTemporaryFile("w", delete=False) as tf:
                    tf.write(private_key_b64)
                    key_file = tf.name

                subprocess.run(
                    ["wg", "set", self.interface_name, "listen-port", str(listen_port), "private-key", key_file],
                    check=True,
                    stderr=subprocess.DEVNULL,
                )
                os.unlink(key_file)
                logger.info(f"Configured {self.interface_name} key and port via wg CLI")
                return True
            except Exception as cli_err:
                logger.warning(f"wg CLI configure failed: {cli_err}")

        self._dry_run = True
        return True

    def sync_peers(self, peers: List[Dict[str, Any]]) -> bool:
        """
        Synchronizes peer definitions onto the WireGuard interface.
        Each dict in peers has: public_key, allowed_ips, endpoint (optional), persistent_keepalive (optional).
        """
        if self._dry_run:
            logger.info(f"[Dry-run] Synced {len(peers)} peers on {self.interface_name}")
            return True

        # 1. Try wg CLI tool first if available (most reliable across distros)
        if shutil.which("wg"):
            try:
                for p in peers:
                    pubkey = p["public_key"]
                    allowed_ips = ",".join(p.get("allowed_ips", [])) or "0.0.0.0/0"
                    cmd = ["wg", "set", self.interface_name, "peer", pubkey, "allowed-ips", allowed_ips]
                    
                    if p.get("endpoint"):
                        cmd.extend(["endpoint", str(p["endpoint"])])
                    
                    keepalive = p.get("persistent_keepalive", 25)
                    cmd.extend(["persistent-keepalive", str(keepalive)])
                    
                    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
                logger.info(f"Synced {len(peers)} peers via wg CLI")
                return True
            except Exception as cli_err:
                logger.warning(f"wg CLI peer sync note: {cli_err}")

        # 2. Try pyroute2
        try:
            from pyroute2 import WireGuard
            wg = WireGuard()
            wg_peers = []
            for p in peers:
                peer_dict = {
                    "public_key": p["public_key"],
                    "allowed_ips": p.get("allowed_ips", []),
                    "persistent_keepalive": p.get("persistent_keepalive", 25),
                }
                if p.get("endpoint"):
                    ep = p["endpoint"]
                    if ":" in ep:
                        host, port = ep.rsplit(":", 1)
                        peer_dict["endpoint"] = {"addr": host, "port": int(port)}
                wg_peers.append(peer_dict)

            wg.set(self.interface_name, peer=wg_peers)
            return True
        except Exception as e:
            logger.warning(f"Failed syncing WireGuard peers via pyroute2: {e}")
            return False

    def add_peer(
        self,
        public_key: str,
        allowed_ips: List[str],
        endpoint: Optional[str] = None,
        persistent_keepalive: int = 25,
    ) -> bool:
        return self.sync_peers(
            [
                {
                    "public_key": public_key,
                    "allowed_ips": allowed_ips,
                    "endpoint": endpoint,
                    "persistent_keepalive": persistent_keepalive,
                }
            ]
        )

    def remove_peer(self, public_key: str) -> bool:
        if self._dry_run:
            return True

        if shutil.which("wg"):
            try:
                subprocess.run(["wg", "set", self.interface_name, "peer", public_key, "remove"], check=True, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                pass

        try:
            from pyroute2 import WireGuard
            wg = WireGuard()
            wg.set(
                self.interface_name,
                peers=[{"public_key": public_key, "flags": 1}],
            )
            return True
        except Exception as e:
            logger.warning(f"Failed removing peer {public_key}: {e}")
            return False
