"""Composition boundary for verified revision-store snapshots."""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Mapping

from artifact_revision import (
    TrustedArtifactRevisionContext, TrustedArtifactRevisionResolver,
    _ADAPTER_TOKEN, context_snapshot_hash,
)


@dataclass(frozen=True)
class VerifiedRevisionStoreSnapshot:
    artifact_type: str
    logical_artifact_id: str
    series_state: str
    latest_artifact_revision: int | None
    latest_content_hash: str | None
    reserved_artifact_revisions: frozenset[int]
    existing_revision_index: Mapping[int, Mapping[str, Any]]
    existing_allocation_records: Mapping[str, Mapping[str, Any]]
    trusted_allocator_identity: Mapping[str, Any]
    allocated_at: str


class ProductionArtifactRevisionResolver(TrustedArtifactRevisionResolver):
    """Exact production composition adapter; arbitrary resolver subclasses are rejected."""
    def __init__(self, snapshot: VerifiedRevisionStoreSnapshot):
        if type(snapshot) is not VerifiedRevisionStoreSnapshot:
            raise TypeError("verified revision store snapshot required")
        self.__snapshot = snapshot

    def resolve_revision_context(self, artifact_type, logical_artifact_id, allocation_record_id):
        snapshot = self.__snapshot
        revision_index = MappingProxyType({k: MappingProxyType(deepcopy(dict(v))) for k, v in snapshot.existing_revision_index.items()})
        allocation_index = MappingProxyType({k: MappingProxyType(deepcopy(dict(v))) for k, v in snapshot.existing_allocation_records.items()})
        facts = {
            "artifact_type": snapshot.artifact_type,
            "logical_artifact_id": snapshot.logical_artifact_id,
            "series_state": snapshot.series_state,
            "latest_artifact_revision": snapshot.latest_artifact_revision,
            "latest_content_hash": snapshot.latest_content_hash,
            "reserved_artifact_revisions": sorted(snapshot.reserved_artifact_revisions),
            "existing_revision_index": {str(k): dict(v) for k, v in revision_index.items()},
            "existing_allocation_records": {k: dict(v) for k, v in allocation_index.items()},
            "trusted_allocator_identity": dict(snapshot.trusted_allocator_identity),
            "allocated_at": snapshot.allocated_at,
        }
        return TrustedArtifactRevisionContext(
            artifact_type=snapshot.artifact_type,
            logical_artifact_id=snapshot.logical_artifact_id,
            series_state=snapshot.series_state,
            latest_artifact_revision=snapshot.latest_artifact_revision,
            latest_content_hash=snapshot.latest_content_hash,
            reserved_artifact_revisions=frozenset(snapshot.reserved_artifact_revisions),
            existing_revision_index=revision_index,
            existing_allocation_records=allocation_index,
            trusted_allocator_identity=MappingProxyType(dict(snapshot.trusted_allocator_identity)),
            allocated_at=snapshot.allocated_at,
            context_snapshot_hash=context_snapshot_hash(facts),
            _adapter_token=_ADAPTER_TOKEN,
        )
