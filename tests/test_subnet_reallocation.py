"""
Tests for dynamic subnet CIDR re-allocation and validation.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from controller.app import app
from pymesh.controller.allocator import IPAllocator


def test_cidr_validation():
    assert IPAllocator.validate_cidr("100.64.0.0/10") is True
    assert IPAllocator.validate_cidr("10.200.0.0/16", "fd00:7079:6d65::/48") is True
    assert IPAllocator.validate_cidr("invalid/cidr") is False
    assert IPAllocator.validate_cidr("999.999.999.999/10") is False


@pytest.mark.asyncio
async def test_subnet_reallocation_api():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Invalid CIDR request -> 400 Bad Request
        res_invalid = await client.put("/api/v1/network/subnet?ipv4_prefix=invalid_cidr")
        assert res_invalid.status_code == 400

        # Valid CIDR update -> 200 OK
        res_valid = await client.put("/api/v1/network/subnet?ipv4_prefix=10.200.0.0/16")
        assert res_valid.status_code == 200
        data = res_valid.json()
        assert data["status"] == "updated"
        assert data["ipv4_prefix"] == "10.200.0.0/16"
