"""
Tests for Cisco Packet Tracer style Web Admin site & passkey authentication.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from controller.app import app
from pymesh.controller.web import ADMIN_PASSKEY


@pytest.mark.asyncio
async def test_web_admin_passkey_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # GET /net/login
        login_res = await client.get("/net/login")
        assert login_res.status_code == 200
        assert "Network Interface" in login_res.text

        # Invalid passkey POST
        invalid_res = await client.post("/net/login", data={"passkey": "INVALID_KEY"})
        assert invalid_res.status_code == 401

        # Valid passkey POST
        valid_res = await client.post("/net/login", data={"passkey": ADMIN_PASSKEY}, follow_redirects=False)
        assert valid_res.status_code == 302
        assert "pymesh_session" in valid_res.cookies

        # GET /net/dashboard with session cookie
        dash_res = await client.get("/net/dashboard", cookies=valid_res.cookies)
        assert dash_res.status_code == 200
        assert "Network Interface" in dash_res.text
