"""
Tests for WireGuardManager configuration and dry-run fallback.
"""

import pytest
from pymesh.networking.wireguard import WireGuardManager
from pymesh.identity.keys import KeyManager


def test_wireguard_manager_dryrun():
    wg = WireGuardManager("pymesh_test0")
    _, pub_key = KeyManager.generate_wireguard_keypair()
    priv_key, _ = KeyManager.generate_wireguard_keypair()

    assert wg.configure_interface(priv_key, listen_port=51820) is True
    assert wg.add_peer(pub_key, ["100.64.0.3/32"], "51.1.2.3:51820") is True
    assert wg.remove_peer(pub_key) is True
