"""
Peer mapping and network config builder for PyMesh controller.
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pymesh.storage.models import NodeModel, SubnetRoute
from pymesh.protocol.messages import PeerConfig, NetworkConfigResponse


class PeerManager:
    @staticmethod
    async def build_network_config(
        session: AsyncSession,
        node_id: str,
    ) -> NetworkConfigResponse:
        stmt_target = select(NodeModel).where(NodeModel.id == node_id)
        res_target = await session.execute(stmt_target)
        target_node = res_target.scalar_one_or_none()

        if not target_node:
            raise ValueError(f"Node {node_id} not found.")

        # Query all active peers in the same network
        stmt_peers = select(NodeModel).where(
            NodeModel.network_id == target_node.network_id,
            NodeModel.id != node_id,
        )
        res_peers = await session.execute(stmt_peers)
        other_nodes = res_peers.scalars().all()

        # Query advertised subnet routes
        stmt_routes = select(SubnetRoute).where(
            SubnetRoute.network_id == target_node.network_id,
            SubnetRoute.enabled == True,
        )
        res_routes = await session.execute(stmt_routes)
        routes = res_routes.scalars().all()

        route_map = {}
        for r in routes:
            route_map.setdefault(r.via_node_id, []).append(r.prefix)

        peer_configs: List[PeerConfig] = []
        for p in other_nodes:
            allowed_ips = [f"{p.mesh_ipv4}/32", f"{p.mesh_ipv6}/128"]
            # Append routed subnets advertised by this peer
            if p.id in route_map:
                allowed_ips.extend(route_map[p.id])

            peer_configs.append(
                PeerConfig(
                    node_id=p.id,
                    hostname=p.hostname,
                    public_key=p.wireguard_public_key,
                    mesh_ipv4=p.mesh_ipv4,
                    mesh_ipv6=p.mesh_ipv6,
                    allowed_ips=allowed_ips,
                    endpoints=p.endpoints or [],
                    persistent_keepalive=25,
                )
            )

        formatted_routes = [
            {
                "id": r.id,
                "prefix": r.prefix,
                "via_node_id": r.via_node_id,
                "advertised_by": r.advertised_by,
            }
            for r in routes
        ]

        return NetworkConfigResponse(
            node_id=target_node.id,
            mesh_ipv4=target_node.mesh_ipv4,
            mesh_ipv6=target_node.mesh_ipv6,
            peers=peer_configs,
            routes=formatted_routes,
            dns_domain="mesh",
        )
