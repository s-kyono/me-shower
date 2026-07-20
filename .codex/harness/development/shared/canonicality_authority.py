"""Fail-closed canonicality authority validation for Development Artifacts."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml
from jsonschema import FormatChecker, ValidationError, validators
from referencing import Registry, Resource

from source_binding import (
    SourceBindingAuthority, validate_candidate_source_binding_production,
    validate_candidate_source_binding_with_authority,
)


DEVELOPMENT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = DEVELOPMENT_ROOT / "schemas"
REGISTRY_PATH = DEVELOPMENT_ROOT / "shared/artifact-canonicality-registry.yaml"

RESERVED_CANDIDATE_FIELDS = {
    "status", "canonical", "canonical_status", "canonical_decision",
    "canonicality_authority", "authority_identity", "accepted", "locked",
    "passed", "artifact_written", "workflow_status",
    "revision", "artifact_revision", "new_artifact_revision",
    "target_artifact_revision", "revision_path_segment", "content_hash",
}
PAYLOAD_CANONICAL_FIELDS = {
    "canonical", "canonical_status", "canonical_decision", "canonicality_authority",
    "authority_identity", "approval_status", "submitted_by", "submitted_at",
    "actor_identity",
}
PAYLOAD_FORBIDDEN_REVISION_FIELDS = {
    "revision", "artifact_revision", "new_artifact_revision",
    "target_artifact_revision", "revision_path_segment",
}
CANONICAL_VALUES = {
    "accepted", "rejected", "deferred", "locked", "passed", "failed",
    "changes_required", "blocked", "granted", "continued", "revoked",
}
TYPE_CANONICAL_VALUES = {
    "plan": {"accepted"},
    "adr": {"accepted", "rejected", "deferred"},
    "design_lock": {"locked"},
    "implementation_review": {"accepted", "changes_required", "blocked"},
    "release_gate": {"passed", "failed", "blocked"},
    "authorization_grant": {"granted"},
    "authorization_continuation": {"continued"},
    "authorization_revocation": {"revoked"},
}
_TRUST_TOKEN = object()


@dataclass(frozen=True)
class CanonicalityValidationResult:
    status: str
    reason_code: str
    canonical_decision: str | None = None
    decision_record_id: str | None = None


@dataclass(frozen=True)
class TrustedCanonicalityContext:
    """Opaque resolver output; public validation APIs never accept raw mappings."""

    candidate_id: str
    candidate_payload_hash: str
    trusted_candidate_generator: Mapping[str, Any] | None
    subject_binding: Mapping[str, Any] | None
    material_context_hash: str
    checked_snapshot_hash: str | None
    verified_authority_record_hash: str
    verified_authority_source: Mapping[str, Any] | None
    verified_actor_identity: Mapping[str, Any] | None
    effective_authority_record_ids: frozenset[str]
    revoked_authority_record_ids: frozenset[str]
    existing_decision_records: Mapping[str, str] | None
    existing_authority_records: Mapping[str, str] | None
    _token: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._token is not _TRUST_TOKEN:
            raise TypeError("trusted canonicality context must be resolver-issued")

class TrustedCanonicalityContextResolver(ABC):
    """Trusted adapter boundary for State, identity, and immutable record indexes."""

    @abstractmethod
    def resolve_candidate(self, candidate_id: str) -> TrustedCanonicalityContext | None:
        """Resolve trusted Candidate execution and current-subject facts."""

    @abstractmethod
    def resolve_canonicality(
        self, candidate_id: str, authority_record_id: str
    ) -> TrustedCanonicalityContext | None:
        """Resolve trusted authority facts and immutable ID indexes."""

    @staticmethod
    def _mint_context(**facts: Any) -> TrustedCanonicalityContext:
        """Adapter-only constructor for facts obtained from trusted stores."""
        for name in (
            "trusted_candidate_generator", "subject_binding",
            "verified_authority_source",
            "verified_actor_identity", "existing_decision_records",
            "existing_authority_records",
        ):
            value = facts.get(name)
            if value is not None:
                facts[name] = MappingProxyType(dict(value))
        for name in ("effective_authority_record_ids", "revoked_authority_record_ids"):
            facts[name] = frozenset(facts[name])
        return TrustedCanonicalityContext(_token=_TRUST_TOKEN, **facts)


def canonical_record_hash(record: Mapping[str, Any], hash_field: str) -> str:
    envelope = {key: value for key, value in record.items() if key != hash_field}
    encoded = json.dumps(
        envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_validators() -> tuple[dict[str, Any], dict[str, Any]]:
    names = (
        "revision-domains.schema.yaml",
        "canonicality-common.schema.yaml", "source-binding.schema.yaml",
        "artifact-candidate.schema.yaml",
        "canonicality-authority-record.schema.yaml",
        "canonicality-decision-record.schema.yaml",
        "artifact-canonicality-registry.schema.yaml",
    )
    schemas = {name: _load_yaml(SCHEMA_ROOT / name) for name in names}
    resources = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    format_checker = FormatChecker()
    result: dict[str, Any] = {}
    for name, schema in schemas.items():
        cls = validators.validator_for(schema)
        cls.check_schema(schema)
        result[name] = cls(schema, registry=resources, format_checker=format_checker)
    return schemas, result


def load_canonicality_contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    _, schema_validators = _load_validators()
    registry = _load_yaml(REGISTRY_PATH)
    schema_validators["artifact-canonicality-registry.schema.yaml"].validate(registry)
    _validate_registry_semantics(registry)
    return registry, schema_validators


def _validate_registry_semantics(registry: Mapping[str, Any]) -> None:
    for registry_key, contract in registry["artifact_types"].items():
        if registry_key != contract["artifact_type"]:
            raise ValueError("canonicality registry key/type mismatch")
        canonicality = contract["canonicality"]
        authority_types = set(canonicality["authority_types"])
        allowed_decisions = set(canonicality["allowed_decisions"])
        contracts = canonicality["contracts"]
        if authority_types == {"not_applicable"}:
            if canonicality["required_authority_binding"] or allowed_decisions or contracts:
                raise ValueError("not_applicable canonicality contract is inconsistent")
            if contract["subject_binding_policy"] != "optional":
                raise ValueError("not_applicable subject binding must be optional")
            continue
        if "not_applicable" in authority_types:
            raise ValueError("not_applicable cannot be combined with an authority")
        if contract["subject_binding_policy"] != "required":
            raise ValueError("canonical decisions require a bound subject")
        if not canonicality["required_authority_binding"] or not contracts:
            raise ValueError("canonical decisions require authority contracts")
        contract_types = {item["authority_type"] for item in contracts}
        contract_decisions = {
            decision for item in contracts for decision in item["allowed_decisions"]
        }
        if contract_types != authority_types or contract_decisions != allowed_decisions:
            raise ValueError("canonicality registry summary differs from its contracts")


def _result(
    status: str, reason_code: str, *, decision: str | None = None,
    record_id: str | None = None,
) -> CanonicalityValidationResult:
    return CanonicalityValidationResult(status, reason_code, decision, record_id)


def _payload_metadata(payload_bytes: bytes, payload_format: str) -> Mapping[str, Any] | None:
    try:
        text = payload_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("unsupported payload encoding") from exc
    if payload_format == "yaml":
        metadata = yaml.safe_load(text)
        if metadata is None:
            return {}
        if not isinstance(metadata, Mapping):
            raise ValueError("YAML payload must be a mapping")
        return metadata
    if payload_format != "markdown":
        raise ValueError("unsupported payload format")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise ValueError("unterminated YAML front matter") from exc
    metadata = yaml.safe_load("\n".join(lines[1:end]))
    if metadata is None:
        return {}
    if not isinstance(metadata, Mapping):
        raise ValueError("front matter must be a mapping")
    return metadata


def _contains_canonical_payload_field(
    value: Any, artifact_type: str, parent_key: str | None = None
) -> bool:
    type_values = TYPE_CANONICAL_VALUES.get(artifact_type, set())
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).lower()
            if key in PAYLOAD_CANONICAL_FIELDS:
                return True
            if key in PAYLOAD_FORBIDDEN_REVISION_FIELDS:
                return True
            if key == "status" and isinstance(child, str) and (
                child.lower() in CANONICAL_VALUES or child.lower() in type_values
            ):
                return True
            if (key in CANONICAL_VALUES or key in type_values) and child is True:
                return True
            if key == "approval" and isinstance(child, Mapping):
                submitted = child.get("submitted")
                if submitted is True or child.get("status") in CANONICAL_VALUES:
                    return True
            if _contains_canonical_payload_field(child, artifact_type, key):
                return True
    elif isinstance(value, list):
        return any(
            _contains_canonical_payload_field(item, artifact_type, parent_key)
            for item in value
        )
    return False


def _trusted_context_from_resolver(
    resolver: TrustedCanonicalityContextResolver | Any,
    candidate_id: str,
    authority_record_id: str | None = None,
) -> TrustedCanonicalityContext | None:
    if not isinstance(resolver, TrustedCanonicalityContextResolver):
        return None
    try:
        context = (
            resolver.resolve_candidate(candidate_id)
            if authority_record_id is None
            else resolver.resolve_canonicality(candidate_id, authority_record_id)
        )
    except Exception:
        return None
    return context if isinstance(context, TrustedCanonicalityContext) else None


def _validate_candidate_with_context(
    candidate: Mapping[str, Any], payload_bytes: bytes | None,
    context: TrustedCanonicalityContext | None,
    source_authority: SourceBindingAuthority | None = None,
) -> CanonicalityValidationResult:
    if payload_bytes is None or not isinstance(payload_bytes, bytes):
        return _result("invalid", "candidate_payload_required")
    if context is None:
        return _result("blocked", "trusted_context_required")
    forbidden = RESERVED_CANDIDATE_FIELDS.intersection(candidate)
    if forbidden:
        return _result("invalid", "candidate_canonical_field_forbidden")
    try:
        registry, schema_validators = load_canonicality_contracts()
        schema_validators["artifact-candidate.schema.yaml"].validate(candidate)
    except (ValidationError, ValueError, OSError, yaml.YAMLError):
        return _result("invalid", "candidate_schema_invalid")
    source_result = (
        validate_candidate_source_binding_with_authority(candidate, source_authority)
        if source_authority is not None
        else validate_candidate_source_binding_production(candidate)
    )
    if source_result.status != "valid":
        return _result(source_result.status, source_result.reason_code)
    if hashlib.sha256(payload_bytes).hexdigest() != candidate["payload_hash"]:
        return _result("blocked", "candidate_payload_hash_mismatch")
    try:
        metadata = _payload_metadata(payload_bytes, candidate["payload_format"])
    except (ValueError, yaml.YAMLError):
        return _result("invalid", "candidate_payload_invalid")
    if _contains_canonical_payload_field(metadata, candidate["artifact_type"]):
        return _result("blocked", "candidate_payload_contains_canonical_field")
    artifact_type = candidate["artifact_type"]
    if artifact_type not in registry["artifact_types"]:
        return _result("blocked", "artifact_type_unregistered")
    contract = registry["artifact_types"][artifact_type]
    if candidate["generated_by"] not in contract["candidate_generators"]:
        return _result("blocked", "candidate_generator_not_allowed")
    if context.trusted_candidate_generator is None:
        return _result("blocked", "trusted_candidate_generator_missing")
    if context.trusted_candidate_generator != candidate["generated_by"]:
        return _result("blocked", "candidate_generator_identity_mismatch")
    if candidate["artifact_lifecycle_status"] not in contract["artifact_lifecycle_statuses"]:
        return _result("blocked", "artifact_lifecycle_status_not_allowed")
    if context.candidate_id != candidate["candidate_id"]:
        return _result("blocked", "current_candidate_identity_mismatch")
    if context.candidate_payload_hash != candidate["payload_hash"]:
        return _result("blocked", "current_candidate_hash_mismatch")
    if contract["subject_binding_policy"] == "required":
        bindings = (candidate["subject_binding"], context.subject_binding)
        if any(not item or item.get("binding_type") != "bound" for item in bindings):
            return _result("blocked", "subject_binding_required")
    if context.subject_binding != candidate["subject_binding"]:
        return _result("blocked", "current_subject_binding_mismatch")
    return _result("valid", "candidate_valid")


def validate_candidate(
    candidate: Mapping[str, Any], payload_bytes: bytes | None,
    context_resolver: TrustedCanonicalityContextResolver | Any,
) -> CanonicalityValidationResult:
    context = _trusted_context_from_resolver(context_resolver, candidate.get("candidate_id", ""))
    return _validate_candidate_with_context(candidate, payload_bytes, context)


def validate_candidate_for_test(
    candidate: Mapping[str, Any], payload_bytes: bytes | None,
    context_resolver: TrustedCanonicalityContextResolver | Any,
    source_authority: SourceBindingAuthority,
) -> CanonicalityValidationResult:
    context = _trusted_context_from_resolver(context_resolver, candidate.get("candidate_id", ""))
    return _validate_candidate_with_context(candidate, payload_bytes, context, source_authority)


def _validate_canonicality_authority(
    candidate: Mapping[str, Any], payload_bytes: bytes | None,
    decision_record: Mapping[str, Any], authority_record: Mapping[str, Any],
    context_resolver: TrustedCanonicalityContextResolver | Any,
    source_authority: SourceBindingAuthority | None = None,
) -> CanonicalityValidationResult:
    authority_id = authority_record.get("authority_record_id", "")
    context = _trusted_context_from_resolver(
        context_resolver, candidate.get("candidate_id", ""), authority_id
    )
    candidate_result = _validate_candidate_with_context(
        candidate, payload_bytes, context, source_authority,
    )
    if candidate_result.status != "valid":
        return candidate_result
    assert context is not None
    if context.existing_decision_records is None:
        return _result("invalid", "decision_record_index_required")
    if context.existing_authority_records is None:
        return _result("invalid", "authority_record_index_required")
    try:
        registry, schema_validators = load_canonicality_contracts()
        schema_validators["canonicality-decision-record.schema.yaml"].validate(decision_record)
        schema_validators["canonicality-authority-record.schema.yaml"].validate(authority_record)
    except (ValidationError, ValueError, OSError, yaml.YAMLError):
        return _result("invalid", "canonicality_record_schema_invalid")

    authority_hash = canonical_record_hash(authority_record, "authority_record_hash")
    if authority_hash != authority_record["authority_record_hash"]:
        return _result("invalid", "authority_record_integrity_invalid")
    existing_authority_hash = context.existing_authority_records.get(authority_id)
    if existing_authority_hash is not None and existing_authority_hash != authority_hash:
        return _result("blocked", "authority_record_id_conflict")
    if context.verified_authority_record_hash != authority_hash:
        return _result("blocked", "authority_record_not_trusted")
    decision_hash = canonical_record_hash(decision_record, "decision_record_hash")
    if decision_hash != decision_record["decision_record_hash"]:
        return _result("invalid", "decision_record_integrity_invalid")
    existing_decision_hash = context.existing_decision_records.get(
        decision_record["decision_record_id"]
    )
    if existing_decision_hash is not None and existing_decision_hash != decision_hash:
        return _result("blocked", "decision_record_id_conflict")

    artifact_type = candidate["artifact_type"]
    type_contract = registry["artifact_types"][artifact_type]
    canonicality = type_contract["canonicality"]
    if canonicality["authority_types"] == ["not_applicable"]:
        return _result("blocked", "canonicality_not_applicable")
    bindings = (
        candidate["subject_binding"], authority_record["subject_binding"],
        decision_record["subject_binding"], context.subject_binding,
    )
    if type_contract["subject_binding_policy"] == "required" and any(
        not item or item.get("binding_type") != "bound" for item in bindings
    ):
        return _result("blocked", "subject_binding_required")

    identity_fields = ("artifact_type", "logical_artifact_id", "candidate_id")
    if any(decision_record[field] != candidate[field] for field in identity_fields):
        return _result("blocked", "decision_candidate_identity_mismatch")
    if any(authority_record[field] != candidate[field] for field in identity_fields):
        return _result("blocked", "authority_candidate_identity_mismatch")
    if decision_record["candidate_payload_hash"] != candidate["payload_hash"]:
        return _result("blocked", "decision_candidate_hash_mismatch")
    if authority_record["candidate_payload_hash"] != candidate["payload_hash"]:
        return _result("blocked", "authority_candidate_hash_mismatch")
    if decision_record["subject_binding"] != candidate["subject_binding"]:
        return _result("blocked", "decision_subject_binding_mismatch")
    if authority_record["subject_binding"] != candidate["subject_binding"]:
        return _result("blocked", "authority_subject_binding_mismatch")

    decision = decision_record["canonical_decision"]
    if decision not in canonicality["allowed_decisions"]:
        return _result("blocked", "canonical_decision_not_allowed")
    if authority_record["canonical_decision"] != decision:
        return _result("blocked", "authority_decision_mismatch")
    if decision_record["authority_type"] != authority_record["authority_type"]:
        return _result("blocked", "authority_type_mismatch")
    reference = decision_record["authority_reference"]
    if reference != {
        "authority_record_id": authority_id,
        "authority_record_hash": authority_record["authority_record_hash"],
    }:
        return _result("blocked", "authority_reference_mismatch")

    matching = [
        item for item in canonicality["contracts"]
        if item["authority_type"] == authority_record["authority_type"]
        and item["authority_source"] == authority_record["authority_source"]
        and authority_record["action_type"] in item["action_types"]
        and decision in item["allowed_decisions"]
    ]
    if not matching:
        return _result("blocked", "authority_source_not_allowed")
    if context.verified_authority_source is None:
        return _result("blocked", "trusted_authority_source_missing")
    if context.verified_authority_source != authority_record["authority_source"]:
        return _result("blocked", "authority_source_identity_mismatch")
    if authority_record["authority_type"] == "human_action":
        actor = authority_record["actor_identity"]
        if context.verified_actor_identity is None:
            return _result("blocked", "trusted_actor_identity_missing")
        if context.verified_actor_identity != actor:
            return _result("blocked", "human_actor_identity_mismatch")
    elif authority_record["actor_identity"] is not None or context.verified_actor_identity is not None:
        return _result("blocked", "non_human_actor_identity_forbidden")

    if authority_record["status"] != "effective":
        return _result("blocked", "authority_revoked")
    if authority_id in context.revoked_authority_record_ids:
        return _result("blocked", "authority_revoked")
    if authority_id not in context.effective_authority_record_ids:
        return _result("blocked", "authority_stale")
    if context.material_context_hash != authority_record["material_context_hash"]:
        return _result("blocked", "authority_material_context_stale")
    if authority_record["authority_type"] in {"workflow_guard", "source_agent_decision"}:
        if context.checked_snapshot_hash != authority_record["checked_snapshot_hash"]:
            return _result("blocked", "authority_snapshot_mismatch")

    return _result(
        "valid", "canonicality_authority_valid", decision=decision,
        record_id=decision_record["decision_record_id"],
    )


def validate_canonicality_authority(
    candidate: Mapping[str, Any], payload_bytes: bytes | None,
    decision_record: Mapping[str, Any], authority_record: Mapping[str, Any],
    context_resolver: TrustedCanonicalityContextResolver | Any,
) -> CanonicalityValidationResult:
    """Production entrypoint with internally fixed source provenance authority."""
    return _validate_canonicality_authority(
        candidate, payload_bytes, decision_record, authority_record, context_resolver,
    )


def validate_canonicality_authority_for_test(
    candidate: Mapping[str, Any], payload_bytes: bytes | None,
    decision_record: Mapping[str, Any], authority_record: Mapping[str, Any],
    context_resolver: TrustedCanonicalityContextResolver | Any,
    source_authority: SourceBindingAuthority,
) -> CanonicalityValidationResult:
    """Test-only composition entrypoint; never used by production interfaces."""
    return _validate_canonicality_authority(
        candidate, payload_bytes, decision_record, authority_record,
        context_resolver, source_authority,
    )
