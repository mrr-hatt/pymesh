"""
Daemon lifecycle manager and periodic controller synchronization loop.
"""

import asyncio
import logging
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pymesh.identity.node import NodeIdentity
from pymesh.protocol.messages import NetworkConfigResponse, HeartbeatRequest
from pymesh.networking.wireguard import WireGuardManager
from pymesh.networking.interfaces import InterfaceManager
from pymesh.networking.routes import RouteManager
from pymesh.networking.dns import MagicDNSServer
from pymesh.discovery.nat import NATDetector
from pymesh.discovery.endpoints import EndpointHarvester
from .state import DaemonState

logger = logging.getLogger("pymesh.daemon")


class DaemonLifecycle:
    """Manages node daemon lifecycle, background sync, and networking interfaces."""

    def __init__(self, config_dir: Path = Path("/etc/pymesh")):
        self.config_dir = config_dir
        self.state = DaemonState()
        self.wg_manager = WireGuardManager("pymesh0")
        self.if_manager = InterfaceManager("pymesh0")
        self.route_manager = RouteManager("pymesh0")
        self.dns_server = MagicDNSServer("127.0.0.1", 5353)
        self._running = False

    def load_identity(self) -> Optional[NodeIdentity]:
        paths = [
            self.config_dir / "identity.json",
            Path.home() / ".config" / "pymesh" / "identity.json",
            Path("/etc/pymesh/identity.json"),
        ]
        for path in paths:
            if path.exists():
                self.state.identity = NodeIdentity.load(path)
                return self.state.identity
        return None

    async def start(self) -> None:
        self._running = True
        self.state.is_running = True
        logger.info("Starting PyMesh daemon...")

        # Initialize identity
        identity = self.load_identity()
        if not identity:
            logger.warning("No node identity found. Run 'pymesh join <url>' first.")
            return

        # Initialize WireGuard interface
        self.wg_manager.create_interface(identity.listen_port)
        self.wg_manager.configure_interface(identity.wg_private_key, identity.listen_port)

        # Detect NAT type
        self.state.nat_type = await NATDetector.detect_nat_type()
        logger.info(f"Detected NAT Type: {self.state.nat_type}")

        # Start Magic DNS
        try:
            await self.dns_server.start()
        except Exception as e:
            logger.warning(f"Could not start Magic DNS on 5353: {e}")

        # Sync loop
        asyncio.create_task(self._sync_loop())

    async def _sync_loop(self) -> None:
        while self._running:
            try:
                await self.sync_with_controller()
            except Exception as e:
                logger.error(f"Sync error: {e}")
            await asyncio.sleep(15)

    async def sync_with_controller(self) -> None:
        identity = self.state.identity
        if not identity or not identity.controller_url:
            return

        # Harvest candidate endpoints
        endpoints = await EndpointHarvester.get_candidate_endpoints(identity.listen_port)

        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Send heartbeat
            hb_req = HeartbeatRequest(
                node_id=identity.node_id,
                endpoints=endpoints,
                nat_type=self.state.nat_type,
            )
            hb_url = f"{identity.controller_url.rstrip('/')}/api/v1/nodes/{identity.node_id}/heartbeat"
            await client.post(hb_url, json=hb_req.model_dump())

            # 2. Fetch latest network config
            cfg_url = f"{identity.controller_url.rstrip('/')}/api/v1/network/config?node_id={identity.node_id}"
            resp = await client.get(cfg_url)
            if resp.status_code == 200:
                config = NetworkConfigResponse.model_validate(resp.json())
                self.state.config = config
                self.state.peers = config.peers
                self.state.last_sync = datetime.now(timezone.utc).isoformat()

                # Check for automatic subnet re-allocation from controller
                if identity.mesh_ipv4 != config.mesh_ipv4 or identity.mesh_ipv6 != config.mesh_ipv6:
                    logger.info(f"Subnet re-allocated by controller: New IPv4 = {config.mesh_ipv4}, New IPv6 = {config.mesh_ipv6}. Re-addressing local TUN interface pymesh0.")
                    identity.mesh_ipv4 = config.mesh_ipv4
                    identity.mesh_ipv6 = config.mesh_ipv6
                    id_path = self.config_dir / "identity.json"
                    try:
                        identity.save(id_path)
                    except Exception:
                        pass

                self.if_manager.assign_addresses(config.mesh_ipv4, config.mesh_ipv6)

                # Sync WireGuard peers
                peer_dicts = []
                dns_records = {}
                for p in config.peers:
                    ep = p.endpoints[0] if p.endpoints else None
                    peer_dicts.append({
                        "public_key": p.public_key,
                        "allowed_ips": p.allowed_ips,
                        "endpoint": ep,
                        "persistent_keepalive": p.persistent_keepalive,
                    })
                    dns_records[p.hostname] = p.mesh_ipv4

                self.wg_manager.sync_peers(peer_dicts)
                self.dns_server.update_records(dns_records)

                # Sync /etc/hosts for instant Chrome browser resolution
                try:
                    from pymesh.networking.hosts import HostsManager
                    HostsManager.sync_hosts_file(dns_records)
                except Exception as h_err:
                    logger.debug(f"Hosts sync note: {h_err}")

                # Apply advertised routes
                for r in config.routes:
                    if r.get("via_node_id") != identity.node_id:
                        self.route_manager.add_subnet_route(r["prefix"])

    async def stop(self) -> None:
        self._running = False
        self.state.is_running = False
        self.dns_server.stop()
        try:
            from pymesh.networking.hosts import HostsManager
            HostsManager.remove_hosts_file()
        except Exception:
            pass
        self.if_manager.bring_down()
        logger.info("PyMesh daemon stopped.")
