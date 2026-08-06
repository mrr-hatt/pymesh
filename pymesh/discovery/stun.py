"""
Async STUN client (RFC 5389 / RFC 3489) for public reflexive IP and UDP port discovery.
"""

import socket
import asyncio
import os
import struct
import logging
from typing import Tuple, Optional

logger = logging.getLogger("pymesh.stun")

# Default public STUN servers for fallback
DEFAULT_STUN_SERVERS = [
    ("stun.l.google.com", 19302),
    ("stun1.l.google.com", 19302),
    ("stun2.l.google.com", 19302),
]

STUN_BINDING_REQUEST = 0x0001
MAGIC_COOKIE = 0x2112A442


class STUNClient:
    """Async STUN client discovery."""

    @staticmethod
    async def get_mapped_address(
        host: str = "stun.l.google.com",
        port: int = 19302,
        timeout: float = 3.0,
    ) -> Optional[Tuple[str, int]]:
        """Performs a STUN Binding Request and returns (public_ip, public_port)."""
        try:
            loop = asyncio.get_running_loop()
            
            # Construct STUN Header (20 bytes)
            # Msg Type (2), Length (2), Magic Cookie (4), Transaction ID (12)
            trans_id = os.urandom(12)
            msg_length = 0
            header = struct.pack(">HHIIII", STUN_BINDING_REQUEST, msg_length, MAGIC_COOKIE,
                                 struct.unpack(">I", trans_id[0:4])[0],
                                 struct.unpack(">I", trans_id[4:8])[0],
                                 struct.unpack(">I", trans_id[8:12])[0])

            # Resolve server address
            infos = await loop.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_DGRAM)
            if not infos:
                return None
            target_addr = infos[0][4]

            # Datagram transport
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setblocking(False)
            sock.sendto(header, target_addr)

            # Wait for response
            fut = loop.create_future()

            def data_received(data, addr):
                if not fut.done():
                    fut.set_result(data)

            class STUNProtocol(asyncio.DatagramProtocol):
                def datagram_received(self, data, addr):
                    data_received(data, addr)

            transport, _ = await loop.create_datagram_endpoint(
                lambda: STUNProtocol(),
                sock=sock,
            )

            try:
                data = await asyncio.wait_for(fut, timeout=timeout)
                return STUNClient._parse_stun_response(data, trans_id)
            finally:
                transport.close()

        except Exception as e:
            logger.debug(f"STUN discovery failed for {host}:{port}: {e}")
            return None

    @staticmethod
    def _parse_stun_response(data: bytes, trans_id: bytes) -> Optional[Tuple[str, int]]:
        if len(data) < 20:
            return None

        msg_type, msg_len = struct.unpack(">HH", data[:4])
        magic = struct.unpack(">I", data[4:8])[0]

        offset = 20
        while offset < len(data):
            if offset + 4 > len(data):
                break
            attr_type, attr_len = struct.unpack(">HH", data[offset:offset+4])
            offset += 4
            if offset + attr_len > len(data):
                break
            
            attr_data = data[offset:offset+attr_len]
            offset += (attr_len + 3) & ~3 # 4-byte aligned

            # XOR-MAPPED-ADDRESS (0x0020)
            if attr_type == 0x0020 and len(attr_data) >= 8:
                family = attr_data[1]
                if family == 0x01: # IPv4
                    xor_port = struct.unpack(">H", attr_data[2:4])[0]
                    port = xor_port ^ (MAGIC_COOKIE >> 16)
                    xor_ip = struct.unpack(">I", attr_data[4:8])[0]
                    ip_int = xor_ip ^ MAGIC_COOKIE
                    ip = socket.inet_ntoa(struct.pack(">I", ip_int))
                    return (ip, port)

            # MAPPED-ADDRESS (0x0001)
            elif attr_type == 0x0001 and len(attr_data) >= 8:
                family = attr_data[1]
                if family == 0x01: # IPv4
                    port = struct.unpack(">H", attr_data[2:4])[0]
                    ip = socket.inet_ntoa(attr_data[4:8])
                    return (ip, port)

        return None
