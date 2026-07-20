"""Fail-closed canonicality authority validation for Development Artifacts."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import yaml
from jsonschema import FormatChecker, ValidationError, validators
from referencing import Registry, Resource


DEVELOPMENT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = DEVELOPMENT_ROOT / "schemas"
REGISTRY_PATH = DEVELOPMENT_ROOT / "shared/artifact-canonicality-registry.yaml"

RESERVED_CANDIDATE_FIELDS = {
    "status",
    "canonical",
    "canonical_status",
    "canonical_decision",
    "canonicality_authority",
    "authority_identity",
    "accepted",
    "locked",
    "passed",
    "artifact_written",
    "workflow_status",
}


@dataclass(frozen=True)
class CanonicalityValidationResult:
    status: str
    reason_code: str
    canonical_decision: str | None = None
    decision_record_id: str | None = None


def canonical_record_hash(record: Mapping[str, Any], hash_field: str) -> str:
    """Return the shared canonical SHA-256 identity for an immutable record."""
    envelope = {key: value for key, value in record.items() if key != hash_field}
    encoded = json.dumps(
        envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_validators() -> tuple[dict[str, Any], dict[str, Any]]:
    names = (
        "canonicality-common.schema.yaml",
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
    validators_by_name: dict[str, Any] = {}
    for name, schema in schemas.items():
        cls = validators.validator_for(schema)
        cls.check_schema(schema)
        validators_by_name[name] = cls(
            schema, registry=resources, format_checker=format_checker
        )
    return schemas, validators_by_name


def load_canonicality_contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    """Load and validate the registry and all structural contracts."""
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
            continue
        if "not_applicable" in authority_types:
            raise ValueError("not_applicable cannot be combined with an authority")
        if not canonicality["required_authority_binding"] or not contracts:
            raise ValueError("canonical decisions require authority contracts")
        contract_types = {item["authority_type"] for item in contracts}
        contract_decisions = {
            decision for item in contracts for decision in item["allowed_decisions"]
        }
        if contract_types != authority_types or contract_decisions != allowed_decisions:
            raise ValueError("canonicality registry summary differs from its contracts")


def _result(
    status: str,
    reason_code: str,
    *,
    decision: str | None = None,
    record_id: str | None = None,
) -> CanonicalityValidationResult:
    return CanonicalityValidationResult(status, reason_code, decision, record_id)


def validate_candidate(candidate: Mapping[str, Any]) -> CanonicalityValidationResult:
    """Validate Candidate identity without deriving a canonical decision."""
    forbidden = RESERVED_CANDIDATE_FIELDS.intersection(candidate)
    if forbidden:
        return _result("invalid", "candidate_canonical_field_forbidden")
    try:
        registry, schema_validators = load_canonicality_contracts()
        schema_validators["artifact-candidate.schema.yaml"].validate(candidate)
    except (ValidationError, ValueError, OSError, yaml.YAMLError):
        return _result("invalid", "candidate_schema_invalid")
    artifact_type = candidate["artifact_type"]
    if artifact_type not in registry["artifact_types"]:
        return _result("blocked", "artifact_type_unregistered")
    contract = registry["artifact_types"][artifact_type]
    if candidate["generated_by"] not in contract["candidate_generators"]:
        return _result("blocked", "candidate_generator_not_allowed")
    if candidate["artifact_lifecycle_status"] not in contract["artifact_lifecycle_statuses"]:
        return _result("blocked", "artifact_lifecycle_status_not_allowed")
    return _result("valid", "candidate_valid")


def _context_valid(context: Mapping[str, Any]) -> bool:
    required = {
        "candidate_id",
        "candidate_payload_hash",
        "subject_binding",
        "material_context_hash",
        "checked_snapshot_hash",
        "verified_authority_record_hash",
        "verified_authority_source",
        "verified_actor_identity",
        "effective_authority_record_ids",
        "revoked_authority_record_ids",
    }
    return (
        set(context) == required
        and isinstance(context["effective_authority_record_ids"], (list, tuple, set))
        and isinstance(context["revoked_authority_record_ids"], (list, tuple, set))
    )


def validate_canonicality_authority(
    candidate: Mapping[str, Any],
    decision_record: Mapping[str, Any],
    authority_record: Mapping[str, Any],
    current_context: Mapping[str, Any],
    *,
    existing_decision_records: Mapping[str, str] | None = None,
) -> CanonicalityValidationResult:
    """Validate and derive one canonical decision without mutating Candidate or State."""
    candidate_result = validate_candidate(candidate)
    if candidate_result.status != "valid":
        return candidate_result
    try:
        registry, schema_validators = load_canonicality_contracts()
        schema_validators["canonicality-decision-record.schema.yaml"].validate(decision_record)
        schema_validators["canonicality-authority-record.schema.yaml"].validate(authority_record)
    except (ValidationError, ValueError, OSError, yaml.YAMLError):
        return _result("invalid", "authority_record_schema_invalid")
    if not _context_valid(current_context):
        return _result("invalid", "current_context_invalid")

    calculated_authority_hash = canonical_record_hash(
        authority_record, "authority_record_hash"
    )
    if calculated_authority_hash != authority_record["authority_record_hash"]:
        return _result("invalid", "authority_record_integrity_invalid")
    if current_context["verified_authority_record_hash"] != calculated_authority_hash:
        return _result("blocked", "authority_record_not_trusted")
    calculated_decision_hash = canonical_record_hash(decision_record, "decision_record_hash")
    if calculated_decision_hash != decision_record["decision_record_hash"]:
        return _result("invalid", "decision_record_integrity_invalid")
    existing = existing_decision_records or {}
    existing_hash = existing.get(decision_record["decision_record_id"])
    if existing_hash is not None and existing_hash != calculated_decision_hash:
        return _result("blocked", "decision_record_id_conflict")

    artifact_type = candidate["artifact_type"]
    type_contract = registry["artifact_types"][artifact_type]
    canonicality = type_contract["canonicality"]
    if canonicality["authority_types"] == ["not_applicable"]:
        return _result("blocked", "canonicality_not_applicable")

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
    if (
        reference["authority_record_id"] != authority_record["authority_record_id"]
        or reference["authority_record_hash"] != authority_record["authority_record_hash"]
    ):
        return _result("blocked", "authority_reference_mismatch")

    matching_contracts = [
        item
        for item in canonicality["contracts"]
        if item["authority_type"] == authority_record["authority_type"]
        and item["authority_source"] == authority_record["authority_source"]
        and authority_record["action_type"] in item["action_types"]
        and decision in item["allowed_decisions"]
    ]
    if not matching_contracts:
        return _result("blocked", "authority_source_not_allowed")
    if current_context["verified_authority_source"] != authority_record["authority_source"]:
        return _result("blocked", "authority_source_identity_mismatch")
    if authority_record["authority_type"] == "human_action":
        actor = authority_record["actor_identity"]
        if not isinstance(actor, Mapping) or actor.get("verified") is not True:
            return _result("blocked", "human_actor_identity_invalid")
        if current_context["verified_actor_identity"] != actor:
            return _result("blocked", "human_actor_identity_mismatch")
    else:
        if authority_record["actor_identity"] is not None:
            return _result("blocked", "non_human_actor_identity_forbidden")
        if current_context["verified_actor_identity"] is not None:
            return _result("blocked", "non_human_actor_identity_forbidden")

    if authority_record["status"] != "effective":
        return _result("blocked", "authority_revoked")
    authority_id = authority_record["authority_record_id"]
    if authority_id in current_context["revoked_authority_record_ids"]:
        return _result("blocked", "authority_revoked")
    if authority_id not in current_context["effective_authority_record_ids"]:
        return _result("blocked", "authority_stale")
    if current_context["candidate_id"] != candidate["candidate_id"]:
        return _result("blocked", "current_candidate_identity_mismatch")
    if current_context["candidate_payload_hash"] != candidate["payload_hash"]:
        return _result("blocked", "current_candidate_hash_mismatch")
    if current_context["subject_binding"] != candidate["subject_binding"]:
        return _result("blocked", "current_subject_binding_mismatch")
    if current_context["material_context_hash"] != authority_record["material_context_hash"]:
        return _result("blocked", "authority_material_context_stale")
    if authority_record["authority_type"] in {"workflow_guard", "source_agent_decision"}:
        if current_context["checked_snapshot_hash"] != authority_record["checked_snapshot_hash"]:
            return _result("blocked", "authority_snapshot_mismatch")

    return _result(
        "valid",
        "canonicality_authority_valid",
        decision=decision,
        record_id=decision_record["decision_record_id"],
    )
