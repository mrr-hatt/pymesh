"""
Mesh IP address allocation for IPv4 (100.64.0.0/10) and IPv6 (fd00:mesh::/48).
"""

import ipaddress
from typing import Set, Tuple


class IPAllocator:
    """Manages subnet IP allocations for registered mesh nodes."""

    def __init__(
        self,
        ipv4_cidr: str = "100.64.0.0/10",
        ipv6_cidr: str = "fd00:7079:6d65::/48",
    ):
        self.ipv4_net = ipaddress.IPv4Network(ipv4_cidr, strict=False)
        self.ipv6_net = ipaddress.IPv6Network(ipv6_cidr, strict=False)

    def allocate(self, allocated_v4: Set[str], allocated_v6: Set[str]) -> Tuple[str, str]:
        """Allocates the next available IPv4 and IPv6 address."""
        # Reserved: network address (.0) and controller (.1)
        next_v4 = None
        for host in self.ipv4_net.hosts():
            host_str = str(host)
            if host_str == str(self.ipv4_net.network_address) or host_str.endswith(".1"):
                continue
            if host_str not in allocated_v4:
                next_v4 = host_str
                break

        if not next_v4:
            raise RuntimeError("IPv4 subnet exhaustion in mesh pool.")

        # Derive IPv6 from IPv4 host offset
        host_int = int(ipaddress.IPv4Address(next_v4)) - int(self.ipv4_net.network_address)
        v6_host = self.ipv6_net.network_address + host_int
        next_v6 = str(v6_host)

        return next_v4, next_v6
