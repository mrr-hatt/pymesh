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
            logger.warning(f"Unable to create interface via pyroute2 ({e}), falling back to dry-run mode.")
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
            logger.warning(f"Failed setting WireGuard config via pyroute2: {e}")
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

            wg.set(self.interface_name, peer_flags=0, peers=wg_peers)
            return True
        except Exception as e:
            logger.warning(f"Failed syncing WireGuard peers via pyroute2 ({e}).")
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
        try:
            from pyroute2 import WireGuard
            wg = WireGuard()
            wg.set(
                self.interface_name,
                peers=[{"public_key": public_key, "flags": 1}], # WGPEER_F_REMOVE_ME = 1
            )
            return True
        except Exception as e:
            logger.warning(f"Failed removing peer {public_key}: {e}")
            return False
