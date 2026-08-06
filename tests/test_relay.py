"""
Tests for zero-decryption UDP relay protocol and server forwarding.
"""

import pytest
from pymesh.relay.protocol import RelayProtocol


def test_relay_protocol_encoding_decoding():
    src_id = "8d1c5e1234567890abcdef1234567890"
    dst_id = "9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
    encrypted_payload = b"\x04\x00\x00\x00WireGuardEncryptedDataBlock"

    frame = RelayProtocol.encode_frame(src_id, dst_id, encrypted_payload)
    assert frame.startswith(b"PYRELAY")

    decoded = RelayProtocol.decode_frame(frame)
    assert decoded is not None
    res_src, res_dst, res_payload = decoded

    assert res_src == src_id
    assert res_dst == dst_id
    assert res_payload == encrypted_payload
