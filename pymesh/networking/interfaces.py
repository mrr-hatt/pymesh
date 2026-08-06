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
        success = False
        try:
            from pyroute2 import IPRoute
            with IPRoute() as ipr:
                idx = ipr.link_lookup(ifname=self.interface_name)
                if idx:
                    dev_idx = idx[0]
                    # Assign IPv4 (/10 CGNAT mask)
                    try:
                        ipr.addr("add", index=dev_idx, address=ipv4_address, mask=10)
                    except Exception as addr_err:
                        if "File exists" not in str(addr_err) and getattr(addr_err, 'errno', None) != 17:
                            logger.debug(f"IPv4 addr add note: {addr_err}")

                    # Assign IPv6 (/48 ULA mask) if present
                    if ipv6_address:
                        try:
                            ipr.addr("add", index=dev_idx, address=ipv6_address, mask=48)
                        except Exception as addr_err:
                            if "File exists" not in str(addr_err) and getattr(addr_err, 'errno', None) != 17:
                                logger.debug(f"IPv6 addr add note: {addr_err}")

                    # Bring link UP
                    ipr.link("set", index=dev_idx, state="up")
                    logger.info(f"Assigned {ipv4_address} to {self.interface_name} and set UP")
                    success = True
        except Exception as e:
            logger.warning(f"pyroute2 interface setup note: {e}")

        if not success:
            # Fallback to ip CLI tool
            import subprocess
            try:
                subprocess.run(["ip", "addr", "add", f"{ipv4_address}/10", "dev", self.interface_name], check=False, stderr=subprocess.DEVNULL)
                if ipv6_address:
                    subprocess.run(["ip", "addr", "add", f"{ipv6_address}/48", "dev", self.interface_name], check=False, stderr=subprocess.DEVNULL)
                subprocess.run(["ip", "link", "set", "dev", self.interface_name, "up"], check=False, stderr=subprocess.DEVNULL)
                logger.info(f"Assigned {ipv4_address} via ip CLI to {self.interface_name} and set UP")
                return True
            except Exception as cli_err:
                logger.warning(f"ip CLI setup error: {cli_err}")
                return False

        return True

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
