"""
Tests for PyMesh cryptographic keys and identity generation.
"""

import pytest
from pathlib import Path
from pymesh.identity.keys import KeyManager
from pymesh.identity.node import NodeIdentity
from pymesh.identity.certificates import sign_payload, verify_signature


def test_key_generation():
    id_priv, id_pub = KeyManager.generate_ed25519_keypair()
    assert id_priv and id_pub

    wg_priv, wg_pub = KeyManager.generate_wireguard_keypair()
    assert wg_priv and wg_pub

    node_id = KeyManager.derive_node_id(id_pub)
    assert len(node_id) == 64


def test_node_identity_creation(tmp_path: Path):
    node = NodeIdentity.create_new(hostname="test-node")
    assert node.hostname == "test-node"
    assert node.node_id
    assert node.wg_public_key

    file_path = tmp_path / "identity.json"
    node.save(file_path)

    loaded = NodeIdentity.load(file_path)
    assert loaded.node_id == node.node_id
    assert loaded.hostname == "test-node"


def test_signatures():
    id_priv, id_pub = KeyManager.generate_ed25519_keypair()
    data = b"Hello PyMesh Network"

    sig = sign_payload(id_priv, data)
    assert verify_signature(id_pub, sig, data) is True
    assert verify_signature(id_pub, sig, b"Tampered data") is False
