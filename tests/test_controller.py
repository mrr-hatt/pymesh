"""
Async integration tests for FastAPI PyMesh Controller API endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from controller.app import app


@pytest.mark.asyncio
async def test_root_and_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json()["service"] == "PyMesh Controller"

        # Create join token
        token_resp = await client.post("/api/v1/auth/join?description=TestToken")
        assert token_resp.status_code == 200
        assert "token" in token_resp.json()


@pytest.mark.asyncio
async def test_node_registration_and_peers():
    from pymesh.identity.keys import KeyManager
    _, pub_key = KeyManager.generate_wireguard_keypair()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Register Node 1
        reg_req = {
            "hostname": "test-pc-1",
            "public_key": pub_key,
            "listen_port": 51820,
            "os": "linux",
            "version": "0.1.0",
        }
        res1 = await client.post("/api/v1/nodes/register", json=reg_req)
        assert res1.status_code == 200
        node1 = res1.json()
        assert node1["mesh_ipv4"] == "100.64.0.2"

        # Register Node 2
        _, pub_key_2 = KeyManager.generate_wireguard_keypair()
        reg_req_2 = {
            "hostname": "test-vps-2",
            "public_key": pub_key_2,
            "listen_port": 51820,
        }
        res2 = await client.post("/api/v1/nodes/register", json=reg_req_2)
        assert res2.status_code == 200
        node2 = res2.json()
        assert node2["mesh_ipv4"] == "100.64.0.3"

        # Query Config for Node 1
        cfg_res = await client.get(f"/api/v1/network/config?node_id={node1['node_id']}")
        assert cfg_res.status_code == 200
        cfg = cfg_res.json()
        assert len(cfg["peers"]) == 1
        assert cfg["peers"][0]["node_id"] == node2["node_id"]
        assert cfg["peers"][0]["hostname"] == "test-vps-2"
