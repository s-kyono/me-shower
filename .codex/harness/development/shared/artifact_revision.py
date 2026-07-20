"""Trusted, create-only Artifact revision allocation contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import yaml
from jsonschema import FormatChecker, ValidationError, validators
from referencing import Registry, Resource


DEVELOPMENT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = DEVELOPMENT_ROOT / "schemas"
ARTIFACT_REGISTRY_PATH = DEVELOPMENT_ROOT / "shared/artifact-canonicality-registry.yaml"
MAX_REVISION = 999_999_999
FORBIDDEN_CANDIDATE_REVISION_FIELDS = {
    "revision", "artifact_revision", "new_artifact_revision",
    "target_artifact_revision", "revision_path_segment", "content_hash",
}
_ADAPTER_TOKEN = object()


@dataclass(frozen=True)
class ArtifactRevisionAllocationResult:
    status: str
    reason_code: str
    allocation_record: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class TrustedArtifactRevisionContext:
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
    context_snapshot_hash: str
    _adapter_token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._adapter_token is not _ADAPTER_TOKEN:
            raise TypeError("trusted Artifact revision context must be adapter-issued")


class TrustedArtifactRevisionResolver(ABC):
    @abstractmethod
    def resolve_revision_context(
        self, artifact_type: str, logical_artifact_id: str, allocation_record_id: str
    ) -> TrustedArtifactRevisionContext | None:
        """Resolve trusted allocation State; filesystem observations are not accepted."""


def _canonical_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def allocation_record_hash(record: Mapping[str, Any]) -> str:
    return _canonical_hash({k: v for k, v in record.items() if k != "allocation_record_hash"})


def revision_evidence_hash(evidence: Mapping[str, Any]) -> str:
    return _canonical_hash({k: v for k, v in evidence.items() if k != "revision_evidence_hash"})


def allocation_request_fingerprint(request: Mapping[str, Any]) -> str:
    fields = (
        "allocation_schema_version", "allocation_record_id", "requested_by",
        "artifact_type", "logical_artifact_id", "candidate_id", "candidate_revision",
        "candidate_payload_hash", "candidate_identity_hash", "expected_latest",
        "revision_binding",
    )
    return _canonical_hash({name: request[name] for name in fields})


def candidate_identity_hash(candidate: Mapping[str, Any]) -> str:
    return _canonical_hash(candidate)


def context_snapshot_hash(facts: Mapping[str, Any]) -> str:
    return _canonical_hash(facts)


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    names = (
        "revision-domains.schema.yaml", "canonicality-common.schema.yaml",
        "artifact-candidate.schema.yaml", "artifact-revision-allocation-request.schema.yaml",
        "artifact-revision-allocation-record.schema.yaml", "artifact-revision-evidence.schema.yaml",
        "artifact-canonicality-registry.schema.yaml",
    )
    schemas = {name: _load_yaml(SCHEMA_ROOT / name) for name in names}
    resources = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    result: dict[str, Any] = {}
    for name, schema in schemas.items():
        cls = validators.validator_for(schema)
        cls.check_schema(schema)
        result[name] = cls(schema, registry=resources, format_checker=FormatChecker())
    registry = _load_yaml(ARTIFACT_REGISTRY_PATH)
    result["artifact-canonicality-registry.schema.yaml"].validate(registry)
    return registry, result


def _result(status: str, reason: str, record: Mapping[str, Any] | None = None):
    return ArtifactRevisionAllocationResult(status, reason, record)


def _resolve_context(resolver: Any, artifact_type: str, logical_id: str, allocation_id: str):
    try:
        from artifact_revision_trusted_adapter import ProductionArtifactRevisionResolver
    except ImportError:
        return None
    if type(resolver) is not ProductionArtifactRevisionResolver:
        return None
    try:
        value = resolver.resolve_revision_context(artifact_type, logical_id, allocation_id)
    except Exception:
        return None
    return value if isinstance(value, TrustedArtifactRevisionContext) else None


def _validate_binding(request: Mapping[str, Any], candidate: Mapping[str, Any], registry_entry: Mapping[str, Any]) -> str | None:
    supplied = request["revision_binding"]
    contract = registry_entry["revision_binding"]
    if supplied.get("binding_type") != contract["binding_type"]:
        return "revision_binding_variant_mismatch"
    expected_keys = {"binding_type", *contract["required_bindings"]}
    if set(supplied) != expected_keys:
        return "revision_binding_required"
    owned = set(contract["owned_revision_domains"])
    if "decision_revision" in owned and "decision_revision" not in supplied:
        return "revision_binding_required"
    if "authorization_revision" in owned and "authorization_revision" not in supplied:
        return "revision_binding_required"
    subject = candidate.get("subject_binding", {})
    if contract["binding_type"] == "plan_subject" and (
        subject.get("binding_type") != "bound"
        or subject.get("subject_type") != "plan"
        or supplied["subject_plan_logical_artifact_id"] != subject.get("subject_id")
        or supplied["subject_revision"] != subject.get("subject_revision")
        or supplied["subject_content_hash"] != subject.get("subject_hash")
    ):
        return "revision_binding_invalid"
    if contract["binding_type"] == "implementation_subject" and (
        subject.get("binding_type") != "bound"
        or subject.get("subject_type") != "implementation"
        or supplied["subject_implementation_logical_artifact_id"] != subject.get("subject_id")
        or supplied["implementation_revision"] != subject.get("subject_revision")
        or supplied["repository_snapshot_hash"] != subject.get("subject_hash")
    ):
        return "revision_binding_invalid"
    return None


def _record_fingerprint(record: Mapping[str, Any]) -> str:
    request_view = {
        "allocation_schema_version": record["allocation_schema_version"],
        "allocation_record_id": record["allocation_record_id"],
        "requested_by": record["allocated_by"],
        "artifact_type": record["artifact_type"],
        "logical_artifact_id": record["logical_artifact_id"],
        "candidate_id": record["candidate_id"],
        "candidate_revision": record["candidate_revision"],
        "candidate_payload_hash": record["candidate_payload_hash"],
        "candidate_identity_hash": record["candidate_identity_hash"],
        "expected_latest": record["expected_latest"],
        "revision_binding": record["revision_binding"],
    }
    return allocation_request_fingerprint(request_view)


def _valid_revision(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_REVISION


def _validate_context(context, artifact_type, logical_id, validators_by_name) -> str | None:
    if context.artifact_type != artifact_type or context.logical_artifact_id != logical_id:
        return "revision_series_identity_mismatch"
    snapshot = {
        "artifact_type": context.artifact_type,
        "logical_artifact_id": context.logical_artifact_id,
        "series_state": context.series_state,
        "latest_artifact_revision": context.latest_artifact_revision,
        "latest_content_hash": context.latest_content_hash,
        "reserved_artifact_revisions": sorted(context.reserved_artifact_revisions),
        "existing_revision_index": {str(k): dict(v) for k, v in context.existing_revision_index.items()},
        "existing_allocation_records": {k: dict(v) for k, v in context.existing_allocation_records.items()},
        "trusted_allocator_identity": dict(context.trusted_allocator_identity),
        "allocated_at": context.allocated_at,
    }
    if context_snapshot_hash(snapshot) != context.context_snapshot_hash:
        return "revision_context_provenance_invalid"
    if any(not _valid_revision(item) for item in context.reserved_artifact_revisions):
        return "revision_policy_limit_exceeded"

    records_by_revision: dict[int, Mapping[str, Any]] = {}
    for record_id, record in context.existing_allocation_records.items():
        try:
            validators_by_name["artifact-revision-allocation-record.schema.yaml"].validate(dict(record))
        except ValidationError:
            return "existing_allocation_record_invalid"
        if (record_id != record["allocation_record_id"]
                or allocation_record_hash(record) != record["allocation_record_hash"]
                or _record_fingerprint(record) != record["allocation_request_fingerprint"]):
            return "existing_allocation_record_invalid"
        if record["artifact_type"] != artifact_type or record["logical_artifact_id"] != logical_id:
            return "revision_context_inconsistent"
        record_revision = record["allocated_artifact_revision"]
        if record_revision in records_by_revision and records_by_revision[record_revision]["allocation_record_hash"] != record["allocation_record_hash"]:
            return "revision_context_inconsistent"
        records_by_revision[record_revision] = record

    for key, evidence in context.existing_revision_index.items():
        if not _valid_revision(key):
            return "revision_policy_limit_exceeded"
        try:
            validators_by_name["artifact-revision-evidence.schema.yaml"].validate(dict(evidence))
        except ValidationError:
            return "revision_evidence_schema_invalid"
        if revision_evidence_hash(evidence) != evidence["revision_evidence_hash"]:
            return "revision_evidence_integrity_invalid"
        if (evidence["artifact_type"], evidence["logical_artifact_id"], evidence["artifact_revision"]) != (artifact_type, logical_id, key):
            return "revision_evidence_series_mismatch"
        record = context.existing_allocation_records.get(evidence["allocation_record_id"])
        if record is None or record["allocation_record_hash"] != evidence["allocation_record_hash"]:
            return "revision_evidence_allocation_mismatch"
        if record["allocated_artifact_revision"] != key or any(
            record[name] != evidence[name] for name in (
                "candidate_id", "candidate_revision", "candidate_payload_hash", "candidate_identity_hash"
            )
        ):
            return "revision_evidence_allocation_mismatch"

    persisted = set(context.existing_revision_index)
    if persisted & context.reserved_artifact_revisions:
        return "revision_reservation_conflict"
    for revision_number, record in records_by_revision.items():
        if revision_number not in persisted and revision_number not in context.reserved_artifact_revisions:
            return "revision_context_inconsistent"

    if context.series_state == "absent":
        if any((context.latest_artifact_revision is not None, context.latest_content_hash is not None,
                persisted, context.reserved_artifact_revisions, context.existing_allocation_records)):
            return "revision_context_inconsistent"
    elif context.series_state == "present":
        if not _valid_revision(context.latest_artifact_revision) or not persisted:
            return "revision_context_inconsistent"
        latest = max(persisted)
        if latest != context.latest_artifact_revision:
            return "revision_index_latest_mismatch"
        if context.existing_revision_index[latest]["content_hash"] != context.latest_content_hash:
            return "revision_index_content_hash_mismatch"
        if any(item <= latest for item in context.reserved_artifact_revisions):
            return "revision_reservation_conflict"
    else:
        return "revision_context_inconsistent"
    return None


def allocate_artifact_revision(candidate, allocation_request, revision_resolver):
    forbidden = FORBIDDEN_CANDIDATE_REVISION_FIELDS.intersection(candidate)
    if forbidden:
        return _result("invalid", "candidate_artifact_revision_forbidden")
    try:
        registry, schemas = _load_contracts()
        schemas["artifact-candidate.schema.yaml"].validate(candidate)
    except (ValidationError, ValueError, OSError, yaml.YAMLError, KeyError):
        return _result("invalid", "revision_allocation_schema_invalid")
    artifact_type_hint = allocation_request.get("artifact_type")
    entry_hint = registry["artifact_types"].get(artifact_type_hint)
    if entry_hint is not None and isinstance(allocation_request.get("revision_binding"), Mapping):
        binding_error = _validate_binding(allocation_request, candidate, entry_hint)
        if binding_error:
            return _result("blocked", binding_error)
    try:
        schemas["artifact-revision-allocation-request.schema.yaml"].validate(allocation_request)
    except ValidationError:
        return _result("invalid", "revision_allocation_schema_invalid")
    if allocation_request_fingerprint(allocation_request) != allocation_request["allocation_request_fingerprint"]:
        return _result("invalid", "allocation_request_fingerprint_mismatch")

    artifact_type = allocation_request["artifact_type"]
    logical_id = allocation_request["logical_artifact_id"]
    entry = registry["artifact_types"].get(artifact_type)
    if entry is None:
        return _result("blocked", "revision_series_unregistered")
    if candidate["artifact_type"] != artifact_type or candidate["logical_artifact_id"] != logical_id:
        return _result("blocked", "revision_series_identity_mismatch")
    if (candidate["candidate_id"], candidate["candidate_revision"], candidate["payload_hash"], candidate_identity_hash(candidate)) != (
        allocation_request["candidate_id"], allocation_request["candidate_revision"],
        allocation_request["candidate_payload_hash"], allocation_request["candidate_identity_hash"]
    ):
        return _result("blocked", "revision_candidate_identity_mismatch")

    context = _resolve_context(revision_resolver, artifact_type, logical_id, allocation_request["allocation_record_id"])
    if context is None:
        return _result("invalid", "revision_context_provenance_invalid")
    context_error = _validate_context(context, artifact_type, logical_id, schemas)
    if context_error:
        return _result("invalid", context_error)
    registry_allocator = registry["revision_allocation"]["allowed_allocator"]
    if allocation_request["requested_by"] != registry_allocator:
        return _result("blocked", "revision_allocator_registry_mismatch")
    if context.trusted_allocator_identity != registry_allocator:
        return _result("blocked", "revision_allocator_registry_mismatch")

    existing = context.existing_allocation_records.get(allocation_request["allocation_record_id"])
    if existing is not None:
        if existing["allocation_request_fingerprint"] != allocation_request["allocation_request_fingerprint"]:
            return _result("blocked", "allocation_record_id_conflict")
        target = existing["allocated_artifact_revision"]
        evidence = context.existing_revision_index.get(target)
        if evidence is not None and evidence["candidate_identity_hash"] != candidate_identity_hash(candidate):
            return _result("blocked", "artifact_revision_content_conflict")
        return _result("idempotent_allocation", "allocation_record_idempotent", existing)

    expected = allocation_request["expected_latest"]
    if expected["state"] == "absent":
        if context.series_state != "absent":
            return _result("blocked", "expected_latest_absent_but_series_exists")
    else:
        if context.series_state != "present":
            return _result("blocked", "expected_latest_present_but_series_absent")
        if expected["artifact_revision"] != context.latest_artifact_revision:
            return _result("blocked", "expected_latest_revision_mismatch")
        if expected["content_hash"] != context.latest_content_hash:
            return _result("blocked", "expected_latest_content_hash_mismatch")

    highest = max({context.latest_artifact_revision or 0, *context.reserved_artifact_revisions})
    if highest >= MAX_REVISION:
        return _result("blocked", "revision_policy_limit_exceeded")
    target = highest + 1
    collision = context.existing_revision_index.get(target)
    if collision is not None:
        if collision["candidate_identity_hash"] == candidate_identity_hash(candidate):
            return _result("idempotent_revision_candidate", "artifact_revision_same_candidate_identity")
        return _result("blocked", "artifact_revision_content_conflict")

    observed = {"state": "absent"} if context.series_state == "absent" else {
        "state": "present", "artifact_revision": context.latest_artifact_revision,
        "content_hash": context.latest_content_hash,
    }
    record = {
        "allocation_schema_version": "1.0", "allocation_record_id": allocation_request["allocation_record_id"],
        "artifact_type": artifact_type, "logical_artifact_id": logical_id,
        "allocated_artifact_revision": target, "expected_latest": dict(expected), "observed_latest": observed,
        "candidate_id": candidate["candidate_id"], "candidate_revision": candidate["candidate_revision"],
        "candidate_payload_hash": candidate["payload_hash"], "candidate_identity_hash": candidate_identity_hash(candidate),
        "revision_binding": dict(allocation_request["revision_binding"]),
        "allocation_request_fingerprint": allocation_request["allocation_request_fingerprint"],
        "allocation_status": "allocated", "allocated_by": dict(context.trusted_allocator_identity),
        "allocated_at": context.allocated_at, "allocation_record_hash": "0" * 64,
    }
    record["allocation_record_hash"] = allocation_record_hash(record)
    try:
        schemas["artifact-revision-allocation-record.schema.yaml"].validate(record)
    except ValidationError:
        return _result("invalid", "allocation_record_invalid")
    return _result("allocated", "artifact_revision_allocated", record)
