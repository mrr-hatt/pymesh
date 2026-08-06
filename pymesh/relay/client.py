"""
Relay Client transport helper for fallback routing when P2P NAT punch fails.
"""

import socket
import asyncio
import logging
from typing import Optional, Tuple
from .protocol import RelayProtocol

logger = logging.getLogger("pymesh.relay.client")


class RelayClient:
    """Sends framed UDP packets through a PyMesh relay server."""

    def __init__(self, relay_endpoint: str, self_node_id: str):
        self.relay_endpoint = relay_endpoint
        self.self_node_id = self_node_id

    async def send_relayed_packet(self, dst_node_id: str, payload: bytes) -> bool:
        try:
            if ":" not in self.relay_endpoint:
                return False
            host, port_str = self.relay_endpoint.rsplit(":", 1)
            port = int(port_str)

            frame = RelayProtocol.encode_frame(self.self_node_id, dst_node_id, payload)

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(frame, (host, port))
            sock.close()
            return True
        except Exception as e:
            logger.warning(f"Failed sending packet via relay {self.relay_endpoint}: {e}")
            return False
