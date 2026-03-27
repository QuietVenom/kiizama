from __future__ import annotations

import uuid

from uuid6 import uuid7


def generate_uuid7() -> uuid.UUID:
    return uuid.UUID(str(uuid7()))


__all__ = ["generate_uuid7"]
