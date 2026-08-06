"""
Linux TUN interface IP address configuration and lifecycle.
"""

import logging
from typing import Optional

logger = logging.getLogger("pymesh.interfaces")


class InterfaceManager:
    """Configures interface addresses and link status."""

    def __init__(self, interface_name: str = "pymesh0"):
        self.interface_name = interface_name

    def assign_addresses(self, ipv4_address: str, ipv6_address: Optional[str] = None) -> bool:
        try:
            from pyroute2 import IPRoute
            with IPRoute() as ipr:
                idx = ipr.link_lookup(ifname=self.interface_name)
                if not idx:
                    logger.warning(f"Interface {self.interface_name} not found.")
                    return False
                dev_idx = idx[0]

                # Assign IPv4 (/10 CGNAT mask)
                ipr.addr("add", index=dev_idx, address=ipv4_address, mask=10)

                # Assign IPv6 (/48 ULA mask) if present
                if ipv6_address:
                    ipr.addr("add", index=dev_idx, address=ipv6_address, mask=48)

                # Bring link UP
                ipr.link("set", index=dev_idx, state="up")
                logger.info(f"Assigned {ipv4_address} to {self.interface_name} and set UP")
                return True
        except Exception as e:
            logger.warning(f"Unable to set interface address ({e}) - continuing in user-space mode.")
            return False

    def bring_down(self) -> bool:
        try:
            from pyroute2 import IPRoute
            with IPRoute() as ipr:
                idx = ipr.link_lookup(ifname=self.interface_name)
                if idx:
                    ipr.link("set", index=idx[0], state="down")
                    return True
        except Exception as e:
            logger.warning(f"Unable to bring interface down: {e}")
        return False
