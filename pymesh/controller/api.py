"""
FastAPI REST controller routes for PyMesh.
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from pymesh.storage.database import DatabaseManager
from pymesh.storage.models import NodeModel, ACLRule, SubnetRoute
from pymesh.protocol.messages import (
    NodeRegistrationRequest,
    NodeRegistrationResponse,
    NetworkConfigResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    ACLRuleModel,
    SubnetRouteModel,
)
from .nodes import NodeManager
from .peers import PeerManager
from .auth import AuthManager

router = APIRouter(prefix="/api/v1")
db_manager = DatabaseManager()


async def get_db():
    async for session in db_manager.get_session():
        yield session


@router.post("/auth/join")
async def create_join_token(
    description: str = "CLI Join Token",
    db: AsyncSession = Depends(get_db),
):
    token = await AuthManager.create_token(db, description=description)
    return {"token": token, "auth_url": f"/join?token={token}"}


@router.post("/nodes/register", response_model=NodeRegistrationResponse)
async def register_node(
    req: NodeRegistrationRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    # Optional token verification if provided
    if authorization and authorization.startswith("Bearer "):
        token_str = authorization.split(" ", 1)[1]
        valid = await AuthManager.validate_token(db, token_str)
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid or expired join token")

    node = await NodeManager.register_node(db, req)
    return NodeRegistrationResponse(
        node_id=node.id,
        hostname=node.hostname,
        mesh_ipv4=node.mesh_ipv4,
        mesh_ipv6=node.mesh_ipv6,
        wireguard_public_key=node.wireguard_public_key,
        network_name="pymesh",
    )


@router.get("/nodes", response_model=List[dict])
async def list_nodes(db: AsyncSession = Depends(get_db)):
    nodes = await NodeManager.list_nodes(db)
    return [
        {
            "id": n.id,
            "hostname": n.hostname,
            "mesh_ipv4": n.mesh_ipv4,
            "mesh_ipv6": n.mesh_ipv6,
            "wireguard_public_key": n.wireguard_public_key,
            "listen_port": n.listen_port,
            "os": n.os,
            "version": n.version,
            "online": n.online,
            "nat_type": n.nat_type,
            "last_seen": n.last_seen.isoformat() if n.last_seen else None,
            "endpoints": n.endpoints,
            "tags": n.tags,
        }
        for n in nodes
    ]


@router.get("/nodes/{node_id}")
async def get_node(node_id: str, db: AsyncSession = Depends(get_db)):
    node = await NodeManager.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return {
        "id": node.id,
        "hostname": node.hostname,
        "mesh_ipv4": node.mesh_ipv4,
        "mesh_ipv6": node.mesh_ipv6,
        "wireguard_public_key": node.wireguard_public_key,
        "listen_port": node.listen_port,
        "os": node.os,
        "version": node.version,
        "online": node.online,
        "nat_type": node.nat_type,
        "last_seen": node.last_seen.isoformat() if node.last_seen else None,
        "endpoints": node.endpoints,
        "tags": node.tags,
    }


@router.delete("/nodes/{node_id}")
async def delete_node(node_id: str, db: AsyncSession = Depends(get_db)):
    stmt = delete(NodeModel).where(NodeModel.id == node_id)
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Node not found")
    return {"status": "deleted", "id": node_id}


@router.get("/network/config", response_model=NetworkConfigResponse)
async def get_network_config(
    node_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        config = await PeerManager.build_network_config(db, node_id)
        return config
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/nodes/{node_id}/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(
    node_id: str,
    req: HeartbeatRequest,
    db: AsyncSession = Depends(get_db),
):
    node = await NodeManager.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    node.online = True
    node.last_seen = datetime.now(timezone.utc)
    node.nat_type = req.nat_type
    if req.endpoints:
        node.endpoints = req.endpoints

    await db.commit()
    return HeartbeatResponse(status="ok", peers_changed=False)


@router.get("/acl", response_model=List[ACLRuleModel])
async def list_acls(db: AsyncSession = Depends(get_db)):
    stmt = select(ACLRule)
    res = await db.execute(stmt)
    rules = res.scalars().all()
    return [
        ACLRuleModel(
            id=r.id,
            source=r.source,
            destination=r.destination,
            action=r.action,
            ports=r.ports or [],
            protocols=r.protocols or [],
        )
        for r in rules
    ]


@router.put("/acl", response_model=ACLRuleModel)
async def create_acl_rule(rule: ACLRuleModel, db: AsyncSession = Depends(get_db)):
    import uuid
    rule_id = rule.id or f"acl-{uuid.uuid4().hex[:8]}"
    db_rule = ACLRule(
        id=rule_id,
        network_id="net-pymesh",
        source=rule.source,
        destination=rule.destination,
        action=rule.action,
        ports=rule.ports,
        protocols=rule.protocols,
    )
    db.add(db_rule)
    await db.commit()
    return ACLRuleModel(
        id=db_rule.id,
        source=db_rule.source,
        destination=db_rule.destination,
        action=db_rule.action,
        ports=db_rule.ports,
        protocols=db_rule.protocols,
    )


@router.get("/routes", response_model=List[SubnetRouteModel])
async def list_routes(db: AsyncSession = Depends(get_db)):
    stmt = select(SubnetRoute)
    res = await db.execute(stmt)
    routes = res.scalars().all()
    return [
        SubnetRouteModel(
            id=r.id,
            prefix=r.prefix,
            via_node_id=r.via_node_id,
            advertised_by=r.advertised_by,
            enabled=r.enabled,
        )
        for r in routes
    ]


@router.post("/routes", response_model=SubnetRouteModel)
async def add_route(route: SubnetRouteModel, db: AsyncSession = Depends(get_db)):
    import uuid
    route_id = route.id or f"route-{uuid.uuid4().hex[:8]}"
    db_route = SubnetRoute(
        id=route_id,
        network_id="net-pymesh",
        prefix=route.prefix,
        via_node_id=route.via_node_id,
        advertised_by=route.advertised_by,
        enabled=route.enabled,
    )
    db.add(db_route)
    await db.commit()
    return SubnetRouteModel(
        id=db_route.id,
        prefix=db_route.prefix,
        via_node_id=db_route.via_node_id,
        advertised_by=db_route.advertised_by,
        enabled=db_route.enabled,
    )


@router.delete("/routes/{route_id}")
async def delete_route(route_id: str, db: AsyncSession = Depends(get_db)):
    stmt = delete(SubnetRoute).where(SubnetRoute.id == route_id)
    await db.execute(stmt)
    await db.commit()
    return {"status": "deleted", "id": route_id}


@router.put("/network/subnet")
async def update_network_subnet(
    ipv4_prefix: str,
    ipv6_prefix: Optional[str] = "fd00:7079:6d65::/48",
    db: AsyncSession = Depends(get_db),
):
    from pymesh.controller.allocator import IPAllocator
    from pymesh.storage.models import Network

    if not IPAllocator.validate_cidr(ipv4_prefix, ipv6_prefix):
        raise HTTPException(status_code=400, detail="Invalid IPv4 or IPv6 CIDR prefix syntax.")

    network = await NodeManager.get_or_create_network(db, "pymesh")
    network.ipv4_prefix = ipv4_prefix
    if ipv6_prefix:
        network.ipv6_prefix = ipv6_prefix

    nodes = await NodeManager.list_nodes(db, network.id)
    allocator = IPAllocator(ipv4_prefix, ipv6_prefix or "fd00:7079:6d65::/48")

    allocated_v4 = set()
    allocated_v6 = set()

    for node in nodes:
        v4, v6 = allocator.allocate(allocated_v4, allocated_v6)
        node.mesh_ipv4 = v4
        node.mesh_ipv6 = v6
        allocated_v4.add(v4)
        allocated_v6.add(v6)

    await db.commit()
    return {
        "status": "updated",
        "ipv4_prefix": ipv4_prefix,
        "ipv6_prefix": ipv6_prefix,
        "nodes_reallocated": len(nodes),
    }


# --- TLD Publishing Endpoints ---

@router.post("/tld/publish")
async def publish_tld(
    name: str = Query(..., help="TLD name (e.g. cr, mesh, priv)"),
    description: str = Query("Official TLD", help="TLD description"),
    publisher_info: str = Query("Primary CR Server", help="Publisher details"),
    db: AsyncSession = Depends(get_db),
):
    from pymesh.dns.tld import TLDManager
    from pymesh.storage.models import TLDRegistry

    if not TLDManager.validate_tld_name(name):
        raise HTTPException(
            status_code=400,
            detail="Invalid TLD name syntax. Must be 2-24 standard lowercase characters/hyphens (e.g. .cr, .mesh).",
        )

    clean_name = TLDManager.clean_tld(name)
    stmt = select(TLDRegistry).where(TLDRegistry.name == clean_name)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if not existing:
        tld_entry = TLDRegistry(
            name=clean_name,
            description=description,
            publisher_info=publisher_info,
            publisher_node_id="cr-primary",
        )
        db.add(tld_entry)
    else:
        existing.description = description
        existing.publisher_info = publisher_info

    await db.commit()
    return {
        "status": "published",
        "tld": f".{clean_name}",
        "registry_url": f"http://registry.{clean_name}",
        "description": description,
    }


@router.get("/tld")
async def list_tlds(db: AsyncSession = Depends(get_db)):
    from pymesh.storage.models import TLDRegistry

    stmt = select(TLDRegistry)
    res = await db.execute(stmt)
    tlds = res.scalars().all()
    return [
        {
            "name": f".{t.name}",
            "description": t.description,
            "publisher_info": t.publisher_info,
            "publisher_node_id": t.publisher_node_id,
            "registry_url": f"http://registry.{t.name}",
        }
        for t in tlds
    ]


# --- CR Federation Endpoints ---

@router.post("/cr/handshake")
async def cr_handshake(payload: dict, db: AsyncSession = Depends(get_db)):
    from pymesh.storage.models import FederatedController

    target_url = payload.get("url", "").rstrip("/")
    if not target_url:
        raise HTTPException(status_code=400, detail="Missing CR server URL")

    stmt = select(FederatedController).where(FederatedController.url == target_url)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if not existing:
        cr_peer = FederatedController(
            id=payload.get("controller_id", "cr-remote"),
            url=target_url,
            hostname=payload.get("hostname", "Remote-CR"),
            public_key=payload.get("public_key", "pubkey"),
            status="PEERED",
        )
        db.add(cr_peer)
    else:
        existing.status = "PEERED"

    await db.commit()
    return {
        "status": "peered",
        "controller_id": "cr-local",
        "hostname": "CR-Bootnode-Local",
        "public_key": "local_pubkey",
    }


@router.post("/cr/peer")
async def peer_cr_controller(url: str = Query(...), db: AsyncSession = Depends(get_db)):
    from pymesh.controller.federation import FederationManager

    local_info = {
        "id": "cr-primary",
        "hostname": "CR-Primary",
        "url": "http://localhost:8000",
        "public_key": "local_cr_pubkey",
    }
    result = await FederationManager.peer_controller(db, url, local_info)
    return {"status": "peered", "target_url": url, "result": result}


@router.get("/cr/peers")
async def list_cr_peers(db: AsyncSession = Depends(get_db)):
    from pymesh.controller.federation import FederationManager

    peers = await FederationManager.list_peers(db)
    return peers
