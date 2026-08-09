"""
CR-to-CR Controller Federation Manager for multi-controller bootnode mesh.
"""

import httpx
import logging
import uuid
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from pymesh.storage.models import FederatedController, NodeModel, TLDRegistry

logger = logging.getLogger("pymesh.federation")


class FederationManager:
    """Manages Controller-to-Controller (CR) peer federation and registry synchronization."""

    @staticmethod
    async def peer_controller(db: AsyncSession, target_url: str, local_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initiates CR-to-CR mutual peering handshake with a remote controller server.
        Exchanges public keys, hostnames, and registers federated bootnode trust.
        """
        target_clean = target_url.rstrip("/")
        handshake_url = f"{target_clean}/api/v1/cr/handshake"

        payload = {
            "controller_id": local_info.get("id", "cr-primary"),
            "hostname": local_info.get("hostname", "CR-Bootnode"),
            "url": local_info.get("url", "http://localhost:8000"),
            "public_key": local_info.get("public_key", "cr_pubkey_placeholder"),
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(handshake_url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"CR federation handshake failed with {target_url}: {resp.text}")
            
            peer_data = resp.json()

        # Check if already registered
        stmt = select(FederatedController).where(FederatedController.url == target_clean)
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        if not existing:
            cr_peer = FederatedController(
                id=f"cr-{uuid.uuid4().hex[:12]}",
                url=target_clean,
                hostname=peer_data.get("hostname", "Remote-CR"),
                public_key=peer_data.get("public_key", "pubkey"),
                status="PEERED",
            )
            db.add(cr_peer)
        else:
            existing.status = "PEERED"

        await db.commit()
        logger.info(f"Successfully federated CR controller with {target_clean}")
        return peer_data

    @staticmethod
    async def list_peers(db: AsyncSession) -> List[Dict[str, Any]]:
        stmt = select(FederatedController)
        res = await db.execute(stmt)
        peers = res.scalars().all()
        return [
            {
                "id": p.id,
                "url": p.url,
                "hostname": p.hostname,
                "status": p.status,
                "last_synced": p.last_synced.isoformat() if p.last_synced else None,
            }
            for p in peers
        ]
