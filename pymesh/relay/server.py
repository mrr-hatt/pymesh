"""
Async zero-decryption encrypted UDP relay server.
"""

import asyncio
import logging
from typing import Dict, Tuple
from .protocol import RelayProtocol

logger = logging.getLogger("pymesh.relay.server")


class RelayServerProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.node_endpoints: Dict[str, Tuple[str, int]] = {}
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        logger.info("Relay server datagram listener ready.")

    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        decoded = RelayProtocol.decode_frame(data)
        if not decoded:
            return

        src_id, dst_id, payload = decoded

        # Update source node's active endpoint
        self.node_endpoints[src_id] = addr

        # Forward framed packet to dst_id if known
        dst_addr = self.node_endpoints.get(dst_id)
        if dst_addr:
            # Re-forward payload frame to target destination node
            self.transport.sendto(data, dst_addr)
        else:
            logger.debug(f"Relay packet dropped: target node {dst_id} not connected to relay.")


class RelayServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 51830):
        self.host = host
        self.port = port
        self.transport = None

    async def start(self):
        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: RelayServerProtocol(),
            local_addr=(self.host, self.port),
        )
        logger.info(f"PyMesh Relay server running on udp://{self.host}:{self.port}")

    def stop(self):
        if self.transport:
            self.transport.close()
            logger.info("Relay server stopped.")
