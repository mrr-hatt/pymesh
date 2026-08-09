"""
Standalone Authoritative & Upstream Recursive DNS Server for PyMesh.
Resolves custom TLDs (*.cr, *.mesh, registry.*) and proxies regular internet domains.
"""

import asyncio
import socket
import logging
import ipaddress
import httpx
from typing import Dict, Optional, Tuple

logger = logging.getLogger("pymesh.dns.server")

UPSTREAM_DNS = ("1.1.1.1", 53)


class DNSQueryParser:
    """Zero-dependency RFC 1035 DNS Packet Encoder / Decoder."""

    @staticmethod
    def parse_domain_name(data: bytes, offset: int = 12) -> Tuple[str, int]:
        """Extracts domain name string from DNS query packet."""
        labels = []
        curr = offset
        while curr < len(data):
            length = data[curr]
            if length == 0:
                curr += 1
                break
            # Handle DNS pointer compression (0xc0)
            if (length & 0xC0) == 0xC0:
                curr += 2
                break
            labels.append(data[curr + 1 : curr + 1 + length].decode("ascii", errors="ignore"))
            curr += 1 + length

        domain = ".".join(labels).lower()
        return domain, curr

    @staticmethod
    def build_a_response(query_data: bytes, domain_name: str, target_ip: str) -> bytes:
        """Constructs an RFC 1035 Type A DNS response packet."""
        if len(query_data) < 12:
            return b""

        transaction_id = query_data[:2]
        flags = b"\x81\x80"  # Standard response, no error
        qdcount = query_data[4:6]
        ancount = b"\x00\x01"  # 1 answer
        nscount = b"\x00\x00"
        arcount = b"\x00\x00"

        header = transaction_id + flags + qdcount + ancount + nscount + arcount

        # Find end of question section
        _, q_end = DNSQueryParser.parse_domain_name(query_data, 12)
        question_section = query_data[12 : q_end + 4]  # include qtype (2 bytes) + qclass (2 bytes)

        # Answer section
        ip_bytes = ipaddress.IPv4Address(target_ip).packed
        # Name pointer (0xc00c), Type A (1), Class IN (1), TTL 30s (0x1e), RDLENGTH 4, RDATA
        answer = b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x1e\x00\x04" + ip_bytes

        return header + question_section + answer


class PyMeshDNSServerProtocol(asyncio.DatagramProtocol):
    """UDP Datagram protocol for PyMesh DNS Server."""

    def __init__(self, dns_server: "PyMeshDNSServer"):
        self.dns_server = dns_server
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        asyncio.create_task(self._process_query(data, addr))

    async def _process_query(self, data: bytes, addr):
        try:
            if len(data) < 12:
                return

            domain, _ = DNSQueryParser.parse_domain_name(data, 12)
            if not domain:
                return

            target_ip = await self.dns_server.resolve_custom_tld(domain)
            if target_ip:
                # Custom PyMesh TLD match!
                response = DNSQueryParser.build_a_response(data, domain, target_ip)
                if response and self.transport:
                    self.transport.sendto(response, addr)
                    logger.info(f"DNS resolved [CUSTOM TLD] {domain} -> {target_ip} for {addr[0]}")
            else:
                # Recursive query to upstream DNS (1.1.1.1)
                upstream_resp = await self.dns_server.forward_upstream(data)
                if upstream_resp and self.transport:
                    self.transport.sendto(upstream_resp, addr)
        except Exception as e:
            logger.debug(f"DNS query error from {addr}: {e}")


class PyMeshDNSServer:
    """
    High-performance PyMesh DNS Server.
    Resolves custom TLD domains (*.cr, *.mesh, registry.*) and proxies upstream queries.
    """

    def __init__(self, bind_host: str = "0.0.0.0", bind_port: int = 53, controller_url: str = "http://localhost:8000"):
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.controller_url = controller_url.rstrip("/")
        self.records_cache: Dict[str, str] = {}
        self.transport = None

    async def resolve_custom_tld(self, domain: str) -> Optional[str]:
        """Checks if domain matches a custom TLD or PyMesh node hostname."""
        d_clean = domain.lower().strip(".")

        # Direct cache lookup
        if d_clean in self.records_cache:
            return self.records_cache[d_clean]

        # Fetch live records from controller
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                # 1. Fetch nodes
                nodes_res = await client.get(f"{self.controller_url}/api/v1/nodes")
                if nodes_res.status_code == 200:
                    nodes = nodes_res.json()
                    for n in nodes:
                        h = n["hostname"].lower()
                        ip = n["mesh_ipv4"]
                        self.records_cache[h] = ip
                        self.records_cache[f"{h}.cr"] = ip
                        self.records_cache[f"{h}.mesh"] = ip

                # 2. Fetch TLDs
                tld_res = await client.get(f"{self.controller_url}/api/v1/tld")
                if tld_res.status_code == 200:
                    tlds = tld_res.json()
                    from urllib.parse import urlparse
                    ctrl_host = urlparse(self.controller_url).hostname
                    if not ctrl_host or ctrl_host in ("localhost", "127.0.0.1", "0.0.0.0"):
                        ctrl_ip = "100.64.0.1"
                    else:
                        ctrl_ip = ctrl_host

                    for t in tlds:
                        clean_t = t["name"].lstrip(".").lower()
                        self.records_cache[f"registry.{clean_t}"] = ctrl_ip
                        self.records_cache[f"registry"] = ctrl_ip
        except Exception as e:
            logger.debug(f"DNS controller fetch note: {e}")

        return self.records_cache.get(d_clean)

    async def process_query_data(self, data: bytes) -> bytes:
        """Processes raw binary DNS query packet and returns DNS response packet."""
        if len(data) < 12:
            return b""

        domain, _ = DNSQueryParser.parse_domain_name(data, 12)
        if not domain:
            return b""

        target_ip = await self.resolve_custom_tld(domain)
        if target_ip:
            response = DNSQueryParser.build_a_response(data, domain, target_ip)
            if response:
                return response

        upstream_resp = await self.forward_upstream(data)
        return upstream_resp or b""

    async def forward_upstream(self, query_data: bytes) -> Optional[bytes]:
        """Forwards standard internet query (e.g. google.com) to upstream DNS (1.1.1.1:53)."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        class UpstreamClientProtocol(asyncio.DatagramProtocol):
            def datagram_received(self, data, addr):
                if not future.done():
                    future.set_result(data)

            def error_received(self, exc):
                if not future.done():
                    future.set_result(None)

        try:
            transport, _ = await loop.create_datagram_endpoint(
                UpstreamClientProtocol,
                remote_addr=UPSTREAM_DNS,
            )
            transport.sendto(query_data)
            response = await asyncio.wait_for(future, timeout=3.0)
            transport.close()
            return response
        except Exception:
            return None

    async def start(self):
        """Starts the PyMesh DNS Server on UDP port 53 (or configured fallback port)."""
        loop = asyncio.get_running_loop()
        bound = False

        ports_to_try = [self.bind_port] if self.bind_port != 53 else [53, 5353, 5300]
        for port in ports_to_try:
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if hasattr(socket, "SO_REUSEPORT"):
                    try:
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                    except Exception:
                        pass
                sock.bind((self.bind_host, port))
                self.transport, _ = await loop.create_datagram_endpoint(
                    lambda: PyMeshDNSServerProtocol(self),
                    sock=sock,
                )
                self.bind_port = port
                logger.info(f"PyMesh DNS Server active on udp://{self.bind_host}:{port}")
                bound = True
                break
            except Exception as e:
                if sock:
                    sock.close()
                logger.debug(f"Could not bind UDP DNS port {port}: {e}")

        if not bound:
            logger.warning(f"Could not bind PyMesh DNS Server on any port near {self.bind_port}.")

    def stop(self):
        if self.transport:
            self.transport.close()
            logger.info("PyMesh DNS Server stopped.")


def run_dns_server(host: str = "0.0.0.0", port: int = 53, controller_url: str = "http://localhost:8000"):
    """CLI entrypoint for running standalone PyMesh DNS Server."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    srv = PyMeshDNSServer(host, port, controller_url)

    async def main_async():
        await srv.start()
        print(f"\n========================================================")
        print(f" PyMesh DNS Server Active on UDP {host}:{port}")
        print(f" Custom TLDs: .cr, .mesh, registry.cr, registry.mesh")
        print(f" Upstream DNS: 1.1.1.1 (Cloudflare)")
        print(f"========================================================\n")
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            srv.stop()
            print("\nPyMesh DNS Server stopped.")

    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        srv.stop()
        print("\nPyMesh DNS Server stopped.")


if __name__ == "__main__":
    import sys
    ctrl_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    p = int(sys.argv[2]) if len(sys.argv) > 2 else 53
    run_dns_server(port=p, controller_url=ctrl_url)
