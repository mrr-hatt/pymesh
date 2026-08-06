"""
PyMesh zero-decryption UDP relay framing protocol.
"""

import struct
from typing import Optional, Tuple

# Header layout: Magic (7 bytes) + Src Node ID (32 bytes) + Dst Node ID (32 bytes) + Payload Len (2 bytes) = 73 bytes
RELAY_MAGIC = b"PYRELAY"
HEADER_LEN = 73


class RelayProtocol:
    """Encodes and decodes encrypted UDP relay frames."""

    @staticmethod
    def encode_frame(src_node_id: str, dst_node_id: str, payload: bytes) -> bytes:
        src_bytes = src_node_id[:32].ljust(32, "\x00").encode("ascii")
        dst_bytes = dst_node_id[:32].ljust(32, "\x00").encode("ascii")
        payload_len = len(payload)
        header = RELAY_MAGIC + src_bytes + dst_bytes + struct.pack(">H", payload_len)
        return header + payload

    @staticmethod
    def decode_frame(data: bytes) -> Optional[Tuple[str, str, bytes]]:
        if len(data) < HEADER_LEN:
            return None

        magic = data[:7]
        if magic != RELAY_MAGIC:
            return None

        src_node_id = data[7:39].decode("ascii", errors="ignore").rstrip("\x00")
        dst_node_id = data[39:71].decode("ascii", errors="ignore").rstrip("\x00")
        payload_len = struct.unpack(">H", data[71:73])[0]

        payload = data[HEADER_LEN : HEADER_LEN + payload_len]
        return (src_node_id, dst_node_id, payload)
