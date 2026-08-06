"""
Node management logic for PyMesh controller.
"""

from datetime import datetime, timezone
from typing import List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pymesh.storage.models import NodeModel, Network
from pymesh.protocol.messages import NodeRegistrationRequest
from pymesh.identity.keys import KeyManager
from .allocator import IPAllocator


class NodeManager:
    @staticmethod
    async def get_or_create_network(session: AsyncSession, network_name: str = "pymesh") -> Network:
        stmt = select(Network).where(Network.name == network_name)
        result = await session.execute(stmt)
        net = result.scalar_one_or_none()
        if not net:
            net_id = f"net-{network_name}"
            net = Network(id=net_id, name=network_name)
            session.add(net)
            await session.commit()
            await session.refresh(net)
        return net

    @staticmethod
    async def register_node(
        session: AsyncSession,
        req: NodeRegistrationRequest,
        network_name: str = "pymesh",
    ) -> NodeModel:
        network = await NodeManager.get_or_create_network(session, network_name)

        # Query existing allocated IPs
        stmt_ips = select(NodeModel.mesh_ipv4, NodeModel.mesh_ipv6).where(NodeModel.network_id == network.id)
        res_ips = await session.execute(stmt_ips)
        existing = res_ips.all()
        allocated_v4: Set[str] = {r[0] for r in existing if r[0]}
        allocated_v6: Set[str] = {r[1] for r in existing if r[1]}

        allocator = IPAllocator(network.ipv4_prefix, network.ipv6_prefix)

        node_id = KeyManager.derive_node_id(req.public_key)

        # Check if node already registered
        stmt_node = select(NodeModel).where(NodeModel.id == node_id)
        res_node = await session.execute(stmt_node)
        existing_node = res_node.scalar_one_or_none()

        if existing_node:
            existing_node.hostname = req.hostname
            existing_node.wireguard_public_key = req.public_key
            existing_node.listen_port = req.listen_port
            existing_node.os = req.os
            existing_node.version = req.version
            existing_node.endpoints = req.endpoints
            existing_node.tags = req.tags
            existing_node.online = True
            existing_node.last_seen = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(existing_node)
            return existing_node

        v4, v6 = allocator.allocate(allocated_v4, allocated_v6)

        new_node = NodeModel(
            id=node_id,
            network_id=network.id,
            hostname=req.hostname,
            mesh_ipv4=v4,
            mesh_ipv6=v6,
            wireguard_public_key=req.public_key,
            identity_public_key=req.public_key,
            listen_port=req.listen_port,
            os=req.os,
            version=req.version,
            endpoints=req.endpoints,
            tags=req.tags,
            online=True,
            last_seen=datetime.now(timezone.utc),
        )
        session.add(new_node)
        await session.commit()
        await session.refresh(new_node)
        return new_node

    @staticmethod
    async def get_node(session: AsyncSession, node_id: str) -> Optional[NodeModel]:
        stmt = select(NodeModel).where(NodeModel.id == node_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_nodes(session: AsyncSession, network_id: Optional[str] = None) -> List[NodeModel]:
        stmt = select(NodeModel)
        if network_id:
            stmt = stmt.where(NodeModel.network_id == network_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())
