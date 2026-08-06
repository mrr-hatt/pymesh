"""
Local and remote endpoint discovery and candidate harvesting.
"""

import socket
import asyncio
from typing import List
from .stun import STUNClient


class EndpointHarvester:
    """Discovers local network interface addresses and public STUN endpoints."""

    @staticmethod
    async def get_candidate_endpoints(listen_port: int = 51820) -> List[str]:
        candidates = []

        # 1. Discover local network interfaces
        try:
            hostname = socket.gethostname()
            addrs = socket.getaddrinfo(hostname, None)
            for addr in addrs:
                ip = addr[4][0]
                if not ip.startswith("127.") and not ip.startswith("100.64.") and ":" not in ip:
                    ep = f"{ip}:{listen_port}"
                    if ep not in candidates:
                        candidates.append(ep)
        except Exception:
            pass

        # 2. STUN reflexive candidate
        stun_res = await STUNClient.get_mapped_address()
        if stun_res:
            pub_ip, pub_port = stun_res
            ep = f"{pub_ip}:{pub_port}"
            if ep not in candidates:
                candidates.append(ep)

        return candidates
