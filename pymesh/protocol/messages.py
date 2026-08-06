"""
Pydantic protocol message models for PyMesh.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class NodeRegistrationRequest(BaseModel):
    hostname: str
    public_key: str
    listen_port: int = 51820
    os: str = "linux"
    version: str = "0.1.0"
    endpoints: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class NodeRegistrationResponse(BaseModel):
    node_id: str
    hostname: str
    mesh_ipv4: str
    mesh_ipv6: str
    wireguard_public_key: str
    controller_public_key: Optional[str] = None
    network_name: str = "pymesh"


class PeerConfig(BaseModel):
    node_id: str
    hostname: str
    public_key: str
    mesh_ipv4: str
    mesh_ipv6: str
    allowed_ips: List[str]
    endpoints: List[str]
    persistent_keepalive: int = 25
    relay_endpoint: Optional[str] = None


class NetworkConfigResponse(BaseModel):
    node_id: str
    mesh_ipv4: str
    mesh_ipv6: str
    peers: List[PeerConfig]
    routes: List[dict] = Field(default_factory=list)
    dns_domain: str = "mesh"


class HeartbeatRequest(BaseModel):
    node_id: str
    endpoints: List[str] = Field(default_factory=list)
    nat_type: str = "unknown"
    rx_bytes: int = 0
    tx_bytes: int = 0


class HeartbeatResponse(BaseModel):
    status: str = "ok"
    peers_changed: bool = False
    peers: Optional[List[PeerConfig]] = None


class ACLRuleModel(BaseModel):
    id: Optional[str] = None
    source: str
    destination: str
    action: str = "allow"
    ports: List[int] = Field(default_factory=list)
    protocols: List[str] = Field(default_factory=list, json_schema_extra={"example": ["tcp", "udp"]})


class SubnetRouteModel(BaseModel):
    id: Optional[str] = None
    prefix: str
    via_node_id: str
    advertised_by: str
    enabled: bool = True


class DiagnosticReport(BaseModel):
    ipv4_status: str = "OK"
    ipv6_status: str = "OK"
    udp_status: str = "OK"
    nat_type: str = "Unknown"
    direct_p2p: str = "Possible"
    stun_status: str = "OK"
    relay_status: str = "Available"
    peers_status: List[dict] = Field(default_factory=list)
