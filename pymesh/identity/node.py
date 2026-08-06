"""
Node identity persistence and local machine state representation.
"""

import json
import socket
import os
import sys
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field
from .keys import KeyManager


class NodeIdentity(BaseModel):
    node_id: str
    hostname: str
    identity_private_key: str
    identity_public_key: str
    wg_private_key: str
    wg_public_key: str
    mesh_ipv4: Optional[str] = None
    mesh_ipv6: Optional[str] = None
    controller_url: Optional[str] = None
    auth_token: Optional[str] = None
    listen_port: int = 51820
    os: str = sys.platform
    version: str = "0.1.0"
    endpoints: List[str] = Field(default_factory=list)

    @classmethod
    def create_new(cls, hostname: Optional[str] = None, listen_port: int = 51820) -> "NodeIdentity":
        if not hostname:
            hostname = socket.gethostname()

        id_priv, id_pub = KeyManager.generate_ed25519_keypair()
        wg_priv, wg_pub = KeyManager.generate_wireguard_keypair()
        node_id = KeyManager.derive_node_id(id_pub)

        return cls(
            node_id=node_id,
            hostname=hostname,
            identity_private_key=id_priv,
            identity_public_key=id_pub,
            wg_private_key=wg_priv,
            wg_public_key=wg_pub,
            listen_port=listen_port,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(self.model_dump_json(indent=2))
        os.chmod(path, 0o600)

    @classmethod
    def load(cls, path: Path) -> "NodeIdentity":
        with open(path, "r") as f:
            data = json.load(f)
        return cls.model_validate(data)
