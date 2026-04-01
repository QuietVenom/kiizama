from __future__ import annotations

import hashlib

RATE_LIMIT_KEY_PREFIX = "rl:v1"


def hash_subject(subject: str) -> str:
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()[:32]


def build_rate_limit_key(*, policy_name: str, subject: str) -> str:
    return f"{RATE_LIMIT_KEY_PREFIX}:{policy_name}:{hash_subject(subject)}"


def build_rate_limit_sequence_key(*, policy_name: str, subject: str) -> str:
    return f"{build_rate_limit_key(policy_name=policy_name, subject=subject)}:seq"
