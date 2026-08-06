"""
Cryptographic key management for PyMesh (Ed25519 identity keys & WireGuard X25519 keys).
"""

import base64
from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives import serialization


class KeyManager:
    """Handles creation, loading, and encoding of Node identity and WireGuard keys."""

    @staticmethod
    def generate_ed25519_keypair() -> Tuple[str, str]:
        """Generates Ed25519 private/public keypair encoded in base64."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        priv_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        return (
            base64.b64encode(priv_bytes).decode("utf-8"),
            base64.b64encode(pub_bytes).decode("utf-8"),
        )

    @staticmethod
    def generate_wireguard_keypair() -> Tuple[str, str]:
        """Generates WireGuard (X25519) private/public keypair encoded in base64."""
        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()

        priv_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        return (
            base64.b64encode(priv_bytes).decode("utf-8"),
            base64.b64encode(pub_bytes).decode("utf-8"),
        )

    @staticmethod
    def derive_node_id(ed25519_public_key_b64: str) -> str:
        """Derives a deterministic 64-character Node ID from the Ed25519 public key."""
        import hashlib
        pub_bytes = base64.b64decode(ed25519_public_key_b64)
        return hashlib.sha256(pub_bytes).hexdigest()
