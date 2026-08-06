"""
UDP Hole Punching coordinator and direct P2P reachability checker.
"""

import socket
import asyncio
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger("pymesh.punching")


class HolePuncher:
    """Orchestrates outbound UDP hole punching bursts to establish direct P2P stateful NAT mappings."""

    @staticmethod
    async def punch_hole(
        local_port: int,
        target_endpoints: List[str],
        duration_seconds: float = 3.0,
    ) -> Optional[str]:
        """
        Sends simultaneous UDP probe bursts to target_endpoints to open NAT firewall mappings.
        Returns the reachable endpoint if connection confirmed.
        """
        if not target_endpoints:
            return None

        loop = asyncio.get_running_loop()
        probe_msg = b"PYMESH_P2P_PROBE"

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", local_port))
        except Exception:
            pass
        sock.setblocking(False)

        reachable_endpoint = None

        def datagram_received(data, addr):
            nonlocal reachable_endpoint
            if data == probe_msg or data.startswith(b"PYMESH"):
                ep_str = f"{addr[0]}:{addr[1]}"
                if not reachable_endpoint:
                    reachable_endpoint = ep_str

        class PunchProtocol(asyncio.DatagramProtocol):
            def datagram_received(self, data, addr):
                datagram_received(data, addr)

        transport, _ = await loop.create_datagram_endpoint(
            lambda: PunchProtocol(),
            sock=sock,
        )

        try:
            start_time = loop.time()
            while loop.time() - start_time < duration_seconds and not reachable_endpoint:
                for ep in target_endpoints:
                    try:
                        if ":" in ep:
                            ip, p = ep.rsplit(":", 1)
                            transport.sendto(probe_msg, (ip, int(p)))
                    except Exception:
                        pass
                await asyncio.sleep(0.3)

            return reachable_endpoint
        finally:
            transport.close()
