"""
NAT Behavior Classifier and type detector.
"""

import asyncio
from typing import Tuple, Optional
from .stun import STUNClient, DEFAULT_STUN_SERVERS


class NATType:
    OPEN = "Open Internet"
    FULL_CONE = "Full Cone NAT"
    RESTRICTED = "Restricted Cone NAT"
    PORT_RESTRICTED = "Port Restricted Cone NAT"
    SYMMETRIC = "Symmetric NAT"
    BLOCKED = "UDP Blocked"
    UNKNOWN = "Unknown"


class NATDetector:
    """Classifies host NAT filtering and mapping behavior."""

    @staticmethod
    async def detect_nat_type() -> str:
        res1 = await STUNClient.get_mapped_address(DEFAULT_STUN_SERVERS[0][0], DEFAULT_STUN_SERVERS[0][1])
        if not res1:
            return NATType.BLOCKED

        ip1, port1 = res1

        res2 = await STUNClient.get_mapped_address(DEFAULT_STUN_SERVERS[1][0], DEFAULT_STUN_SERVERS[1][1])
        if not res2:
            return NATType.RESTRICTED

        ip2, port2 = res2

        if ip1 != ip2 or port1 != port2:
            # Different external mapping per target server -> Symmetric NAT
            return NATType.SYMMETRIC
        else:
            # Consistent mapping across target servers -> Cone NAT
            return NATType.FULL_CONE
