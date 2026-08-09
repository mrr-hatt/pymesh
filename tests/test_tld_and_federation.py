"""
Tests for TLD validation, registry.tld HTML rendering, and CR federation.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from controller.app import app
from pymesh.dns.tld import TLDManager


def test_tld_name_validation():
    # Valid TLD names
    assert TLDManager.validate_tld_name("cr") is True
    assert TLDManager.validate_tld_name(".mesh") is True
    assert TLDManager.validate_tld_name("priv-net") is True

    # Invalid / absurd names -> False
    assert TLDManager.validate_tld_name("connectmetoyouservernetwork") is False # > 24 chars
    assert TLDManager.validate_tld_name("a") is False # < 2 chars
    assert TLDManager.validate_tld_name("com") is False # reserved standard TLD
    assert TLDManager.validate_tld_name("-invalid-") is False # leading hyphen


def test_tld_html_rendering():
    nodes = [{"hostname": "SV1", "mesh_ipv4": "100.64.0.3", "mesh_ipv6": "fd00:7079:6d65::3"}]
    html = TLDManager.render_registry_html("cr", "Official CR Publisher Info", nodes)
    assert "Top-Level Domain Registry: .cr" in html
    assert "Official CR Publisher Info" in html
    assert "SV1.cr" in html


@pytest.mark.asyncio
async def test_tld_api_routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Invalid TLD publish -> 400 Bad Request
        res_inv = await client.post("/api/v1/tld/publish?name=connectmetoyouservernetwork")
        assert res_inv.status_code == 400

        # Valid TLD publish -> 200 OK
        res_pub = await client.post("/api/v1/tld/publish?name=cr&description=Official+CR+Domain&publisher_info=Root+CR")
        assert res_pub.status_code == 200
        data = res_pub.json()
        assert data["tld"] == ".cr"
        assert "registry.cr" in data["registry_url"]

        # GET /api/v1/tld
        res_list = await client.get("/api/v1/tld")
        assert res_list.status_code == 200
        tlds = res_list.json()
        assert any(t["name"] == ".cr" for t in tlds)

        # GET /registry/cr HTML landing page
        res_reg = await client.get("/registry/cr")
        assert res_reg.status_code == 200
        assert "Top-Level Domain Registry: .cr" in res_reg.text


@pytest.mark.asyncio
async def test_cr_federation_api_routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Handshake
        handshake_payload = {
            "controller_id": "cr-node-2",
            "hostname": "CR-Germany",
            "url": "http://cr2.example.com:8000",
            "public_key": "pubkey_cr2",
        }
        res_hs = await client.post("/api/v1/cr/handshake", json=handshake_payload)
        assert res_hs.status_code == 200
        assert res_hs.json()["status"] == "peered"

        # List CR peers
        res_peers = await client.get("/api/v1/cr/peers")
        assert res_peers.status_code == 200
        peers = res_peers.json()
        assert any(p["url"] == "http://cr2.example.com:8000" for p in peers)
