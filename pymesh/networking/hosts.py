"""
System /etc/hosts manager for 100% browser resolution of .cr, .mesh, and custom TLDs.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("pymesh.hosts")

HOSTS_PATH = Path("/etc/hosts")
SECTION_START = "# BEGIN PYMESH DNS"
SECTION_END = "# END PYMESH DNS"


class HostsManager:
    """Manages PyMesh domain mappings inside /etc/hosts for instant system & browser DNS resolution."""

    @staticmethod
    def sync_hosts_file(records: Dict[str, str], active_tlds: List[str] = None) -> bool:
        """
        Injects PyMesh node hostnames and registry.tld entries into /etc/hosts.
        """
        if not HOSTS_PATH.exists():
            return False

        tlds = active_tlds or ["cr", "mesh"]
        tld_cleans = [t.lstrip(".").lower() for t in tlds]

        # Generate PyMesh hosts lines
        pymesh_lines = [SECTION_START]

        # Group domains by IP
        ip_map: Dict[str, List[str]] = {}
        for hostname, ip in records.items():
            h_clean = hostname.lower()
            if ip not in ip_map:
                ip_map[ip] = []

            ip_map[ip].append(h_clean)
            for tld in tld_cleans:
                ip_map[ip].append(f"{h_clean}.{tld}")

        # Add registry.tld mappings to controller IP (or default 100.64.0.1)
        controller_ip = "100.64.0.1"
        for ip, host_list in ip_map.items():
            if ip.endswith(".1") or "controller" in host_list:
                controller_ip = ip
                break

        if controller_ip not in ip_map:
            ip_map[controller_ip] = []

        for tld in tld_cleans:
            reg_domain = f"registry.{tld}"
            if reg_domain not in ip_map[controller_ip]:
                ip_map[controller_ip].append(reg_domain)

        for ip, domains in ip_map.items():
            unique_domains = sorted(list(set(domains)))
            if unique_domains:
                pymesh_lines.append(f"{ip}\t{' '.join(unique_domains)}")

        pymesh_lines.append(SECTION_END)
        new_block = "\n".join(pymesh_lines) + "\n"

        try:
            content = HOSTS_PATH.read_text()
            if SECTION_START in content and SECTION_END in content:
                # Replace existing section
                pattern = re.escape(SECTION_START) + r".*?" + re.escape(SECTION_END) + r"\n?"
                updated_content = re.sub(pattern, new_block, content, flags=re.DOTALL)
            else:
                # Append section
                updated_content = content.rstrip() + "\n\n" + new_block

            HOSTS_PATH.write_text(updated_content)
            logger.info("Successfully updated /etc/hosts with PyMesh TLD records")
            return True
        except PermissionError:
            logger.debug("Insufficient privileges to update /etc/hosts directly (run with sudo for full system DNS injection)")
            return False
        except Exception as e:
            logger.warning(f"Error writing to /etc/hosts: {e}")
            return False

    @staticmethod
    def remove_hosts_file() -> bool:
        """Removes PyMesh entries from /etc/hosts upon daemon shutdown."""
        if not HOSTS_PATH.exists():
            return False
        try:
            content = HOSTS_PATH.read_text()
            if SECTION_START in content and SECTION_END in content:
                pattern = re.escape(SECTION_START) + r".*?" + re.escape(SECTION_END) + r"\n?"
                updated_content = re.sub(pattern, "", content, flags=re.DOTALL)
                HOSTS_PATH.write_text(updated_content)
                logger.info("Cleaned up PyMesh entries from /etc/hosts")
            return True
        except Exception:
            return False
