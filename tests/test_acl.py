"""
Tests for ACLEngine policy filtering rules.
"""

import pytest
from pymesh.controller.acl import ACLEngine


def test_acl_default_allow_when_empty():
    engine = ACLEngine([])
    src = {"hostname": "dev-pc", "tags": ["developers"]}
    dst = {"hostname": "prod-db", "tags": ["database"]}

    assert engine.is_allowed(src, dst, port=5432) is True


def test_acl_group_and_port_matching():
    rules = [
        {
            "source": "group:developers",
            "destination": "group:servers",
            "ports": [22, 443],
            "action": "allow",
        },
        {
            "source": "group:developers",
            "destination": "node:prod-db",
            "ports": [5432],
            "action": "allow",
        },
    ]

    engine = ACLEngine(rules)

    dev_node = {"hostname": "dev-pc", "tags": ["developers"]}
    server_node = {"hostname": "vps-de", "tags": ["servers"]}
    db_node = {"hostname": "prod-db", "tags": ["database"]}

    # Allowed SSH / HTTPS to server
    assert engine.is_allowed(dev_node, server_node, port=22) is True
    assert engine.is_allowed(dev_node, server_node, port=443) is True
    # Disallowed port 8080 to server
    assert engine.is_allowed(dev_node, server_node, port=8080) is False

    # Allowed DB connection
    assert engine.is_allowed(dev_node, db_node, port=5432) is True
    assert engine.is_allowed(dev_node, db_node, port=22) is False
