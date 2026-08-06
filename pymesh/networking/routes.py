"""
Linux kernel routing table manager for PyMesh subnet routers and exit nodes.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger("pymesh.routes")


class RouteManager:
    """Manages kernel IP routes via PyRoute2."""

    def __init__(self, interface_name: str = "pymesh0"):
        self.interface_name = interface_name

    def add_subnet_route(self, destination_subnet: str) -> bool:
        """Adds a kernel route redirecting destination_subnet traffic through pymesh0."""
        try:
            from pyroute2 import IPRoute
            with IPRoute() as ipr:
                idx = ipr.link_lookup(ifname=self.interface_name)
                if not idx:
                    return False
                dev_idx = idx[0]
                ipr.route("add", dst=destination_subnet, oif=dev_idx)
                logger.info(f"Added route {destination_subnet} via {self.interface_name}")
                return True
        except Exception as e:
            logger.warning(f"Failed to add route {destination_subnet}: {e}")
            return False

    def remove_subnet_route(self, destination_subnet: str) -> bool:
        try:
            from pyroute2 import IPRoute
            with IPRoute() as ipr:
                idx = ipr.link_lookup(ifname=self.interface_name)
                if not idx:
                    return False
                dev_idx = idx[0]
                ipr.route("del", dst=destination_subnet, oif=dev_idx)
                return True
        except Exception as e:
            logger.warning(f"Failed to remove route {destination_subnet}: {e}")
            return False
