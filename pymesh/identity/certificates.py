"""
Cryptographic certificates and signatures for PyMesh authentication tokens and network configuration.
"""

import base64
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def sign_payload(private_key_b64: str, data: bytes) -> str:
    """Signs bytes payload with an Ed25519 private key, returning base64 signature."""
    priv_bytes = base64.b64decode(private_key_b64)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
    signature = private_key.sign(data)
    return base64.b64encode(signature).decode("utf-8")


def verify_signature(public_key_b64: str, signature_b64: str, data: bytes) -> bool:
    """Verifies Ed25519 signature against data."""
    try:
        pub_bytes = base64.b64decode(public_key_b64)
        sig_bytes = base64.b64decode(signature_b64)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(sig_bytes, data)
        return True
    except Exception:
        return False
