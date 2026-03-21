from __future__ import annotations

from .schemas import JobQueueSpec

QUEUE_PREFIX = "jobs:queue:"
GROUP_PREFIX = "jobs:group:"
STATE_PREFIX = "jobs:state:"
LEASE_PREFIX = "jobs:lease:"
DEDUPE_PREFIX = "jobs:dedupe:"


def build_queue_key(spec: JobQueueSpec) -> str:
    return f"{QUEUE_PREFIX}{spec.domain}"


def build_consumer_group(spec: JobQueueSpec) -> str:
    return f"{GROUP_PREFIX}{spec.domain}"


def build_state_key(spec: JobQueueSpec, job_id: str) -> str:
    return f"{STATE_PREFIX}{spec.domain}:{job_id}"


def build_lease_key(spec: JobQueueSpec, job_id: str) -> str:
    return f"{LEASE_PREFIX}{spec.domain}:{job_id}"


def build_dedupe_key(spec: JobQueueSpec, job_id: str, kind: str) -> str:
    return f"{DEDUPE_PREFIX}{spec.domain}:{job_id}:{kind}"


__all__ = [
    "build_consumer_group",
    "build_dedupe_key",
    "build_lease_key",
    "build_queue_key",
    "build_state_key",
]
