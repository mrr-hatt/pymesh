"""
Magic DNS resolver server for *.mesh domains.
"""

import asyncio
import logging
from typing import Dict, Optional

logger = logging.getLogger("pymesh.dns")


class MagicDNSProtocol(asyncio.DatagramProtocol):
    """Simple UDP DNS Server protocol responding to A/AAAA queries for .mesh domains."""

    def __init__(self, records: Dict[str, str]):
        self.records = records
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        try:
            response = self._build_dns_response(data)
            if response:
                self.transport.sendto(response, addr)
        except Exception as e:
            logger.debug(f"DNS resolution error for {addr}: {e}")

    def _build_dns_response(self, query: bytes) -> bytes:
        # Elementary DNS header response construction
        if len(query) < 12:
            return b""
        
        transaction_id = query[:2]
        flags = b"\x81\x80" # Standard query response, no error
        qdcount = query[4:6]
        ancount = b"\x00\x01" # 1 answer
        nscount = b"\x00\x00"
        arcount = b"\x00\x00"

        header = transaction_id + flags + qdcount + ancount + nscount + arcount

        # Extract queried domain name
        offset = 12
        labels = []
        while offset < len(query):
            length = query[offset]
            if length == 0:
                offset += 1
                break
            labels.append(query[offset + 1 : offset + 1 + length].decode("ascii", errors="ignore"))
            offset += 1 + length

        qtype = query[offset : offset + 2]
        qclass = query[offset + 2 : offset + 4]
        question_section = query[12 : offset + 4]

        domain_name = ".".join(labels).lower()
        ip_str = self.records.get(domain_name)
        if not ip_str:
            # Check without trailing domain if needed
            short_name = labels[0] if labels else ""
            ip_str = self.records.get(short_name)

        if not ip_str:
            # NXDOMAIN response
            flags = b"\x81\x83"
            return transaction_id + flags + qdcount + b"\x00\x00" + nscount + arcount + question_section

        # Answer block: name pointer (0xc00c), Type A (1), Class IN (1), TTL (60s), RDLENGTH (4), RDATA
        import ipaddress
        ip_bytes = ipaddress.IPv4Address(ip_str).packed
        answer = b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04" + ip_bytes

        return header + question_section + answer


class MagicDNSServer:
    """Manages Magic DNS server lifecycle."""

    def __init__(self, bind_host: str = "127.0.0.1", bind_port: int = 5353):
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.records: Dict[str, str] = {}
        self.transport = None

    def update_records(self, new_records: Dict[str, str], active_tlds: Optional[list] = None):
        self.records.clear()
        tld_list = active_tlds or ["mesh", "cr"]

        for k, v in new_records.items():
            k_clean = k.lower()
            self.records[k_clean] = v

            # Map across all active TLDs (e.g. node.cr, node.mesh)
            for tld in tld_list:
                tld_clean = tld.lstrip(".").lower()
                self.records[f"{k_clean}.{tld_clean}"] = v
                # Add registry.tld mapping to controller IP if controller present
                if k_clean == "controller" or v.endswith(".1"):
                    self.records[f"registry.{tld_clean}"] = v

    async def start(self):
        loop = asyncio.get_running_loop()
        bound = False

        # Attempt port 53 first (standard DNS), fallback to 5353
        for port in [53, self.bind_port]:
            try:
                self.transport, _ = await loop.create_datagram_endpoint(
                    lambda: MagicDNSProtocol(self.records),
                    local_addr=(self.bind_host, port),
                )
                self.bind_port = port
                logger.info(f"Magic DNS server listening on udp://{self.bind_host}:{port}")
                bound = True
                break
            except Exception as e:
                logger.debug(f"Could not bind UDP DNS to port {port}: {e}")

        if not bound:
            logger.warning("Could not bind Magic DNS server to port 53 or 5353.")

        self._configure_system_resolver()

    def _configure_system_resolver(self):
        """Integrates local DNS resolver with systemd-resolved for system & browser queries."""
        import subprocess
        import shutil

        if shutil.which("resolvectl"):
            try:
                subprocess.run(
                    ["resolvectl", "dns", "pymesh0", f"{self.bind_host}:{self.bind_port}"],
                    check=False,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    ["resolvectl", "domain", "pymesh0", "~mesh", "~cr"],
                    check=False,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("Configured systemd-resolved DNS routes for PyMesh TLDs")
            except Exception as e:
                logger.debug(f"systemd-resolved config note: {e}")

    def stop(self):
        if self.transport:
            self.transport.close()
            logger.info("Magic DNS server stopped.")
