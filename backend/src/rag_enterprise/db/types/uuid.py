"""UUIDv7 generation per RFC 9562."""

from __future__ import annotations

import secrets
import time
import uuid


def generate_uuid7() -> uuid.UUID:
    """Generate a time-ordered UUIDv7 identifier.

    UUIDv7 provides better PostgreSQL B-tree locality than UUIDv4 while remaining
    globally unique without database sequences.
    """
    timestamp_ms = int(time.time() * 1000)
    uuid_bytes = bytearray(16)
    uuid_bytes[0:6] = timestamp_ms.to_bytes(6, "big")

    random_bytes = secrets.token_bytes(10)
    uuid_bytes[6] = (random_bytes[0] & 0x0F) | 0x70
    uuid_bytes[7] = random_bytes[1]
    uuid_bytes[8] = (random_bytes[2] & 0x3F) | 0x80
    uuid_bytes[9:16] = random_bytes[3:10]

    return uuid.UUID(bytes=bytes(uuid_bytes))
