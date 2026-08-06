"""
Daemon local runtime state container.
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from pymesh.identity.node import NodeIdentity
from pymesh.protocol.messages import NetworkConfigResponse, PeerConfig


class DaemonState(BaseModel):
    is_running: bool = False
    identity: Optional[NodeIdentity] = None
    config: Optional[NetworkConfigResponse] = None
    peers: List[PeerConfig] = Field(default_factory=list)
    nat_type: str = "Unknown"
    last_sync: Optional[str] = None
    rx_bytes: int = 0
    tx_bytes: int = 0
