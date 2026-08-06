"""
SQLAlchemy ORM models for PyMesh Controller database.
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Network(Base):
    __tablename__ = "networks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    ipv4_prefix: Mapped[str] = mapped_column(String(32), default="100.64.0.0/10")
    ipv6_prefix: Mapped[str] = mapped_column(String(64), default="fd00:7079:6d65::/48")
    dns_domain: Mapped[str] = mapped_column(String(64), default="mesh")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    nodes: Mapped[List["NodeModel"]] = relationship("NodeModel", back_populates="network")


class NodeModel(Base):
    __tablename__ = "nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    network_id: Mapped[str] = mapped_column(String(64), ForeignKey("networks.id"), nullable=False)
    hostname: Mapped[str] = mapped_column(String(128), nullable=False)
    mesh_ipv4: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    mesh_ipv6: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    wireguard_public_key: Mapped[str] = mapped_column(String(64), nullable=False)
    identity_public_key: Mapped[str] = mapped_column(String(64), nullable=False)
    listen_port: Mapped[int] = mapped_column(Integer, default=51820)
    os: Mapped[str] = mapped_column(String(64), default="linux")
    version: Mapped[str] = mapped_column(String(32), default="0.1.0")
    endpoints: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    online: Mapped[bool] = mapped_column(Boolean, default=True)
    nat_type: Mapped[str] = mapped_column(String(32), default="unknown")
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    network: Mapped["Network"] = relationship("Network", back_populates="nodes")


class SubnetRoute(Base):
    __tablename__ = "subnet_routes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    network_id: Mapped[str] = mapped_column(String(64), nullable=False)
    prefix: Mapped[str] = mapped_column(String(64), nullable=False)
    via_node_id: Mapped[str] = mapped_column(String(64), ForeignKey("nodes.id"), nullable=False)
    advertised_by: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ACLRule(Base):
    __tablename__ = "acl_rules"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    network_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False) # e.g. 'group:developers' or 'node:dev-pc' or '*'
    destination: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(16), default="allow")
    ports: Mapped[list] = mapped_column(JSON, default=list) # e.g. [22, 443]
    protocols: Mapped[list] = mapped_column(JSON, default=list) # e.g. ["tcp", "udp"]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    network_id: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(256), default="Join token")
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RelayNode(Base):
    __tablename__ = "relays"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(128), nullable=False)
    public_key: Mapped[str] = mapped_column(String(64), nullable=False)
    region: Mapped[str] = mapped_column(String(64), default="default")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
