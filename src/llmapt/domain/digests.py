"""Canonical SHA-256 helpers used by manifests and evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping


def digest_bytes(payload: bytes) -> str:
    """Return a lowercase SHA-256 hex digest."""

    return hashlib.sha256(payload).hexdigest()


def digest_text(value: str) -> str:
    return digest_bytes(value.encode("utf-8"))


def digest_mapping(values: Mapping[str, str | int | float | bool]) -> str:
    """Hash a mapping using stable JSON ordering and separators."""

    encoded = json.dumps(
        dict(values),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return digest_bytes(encoded)
