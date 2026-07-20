"""Closed, interface-first Development Artifact security-scan contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Protocol

import yaml
from jsonschema import FormatChecker, ValidationError, validators
from referencing import Registry, Resource

from canonicality_authority import canonical_record_hash
from source_binding import (
    SourceBindingAuthority, validate_candidate_source_binding_with_authority,
    validate_source_binding_structure,
)


DEVELOPMENT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = DEVELOPMENT_ROOT / "schemas"
POLICY_PATH = DEVELOPMENT_ROOT / "shared/development-security-policy-registry.yaml"
_ACTIONS = ("candidate_revision_required", "false_positive_confirmed", "policy_decision_required")


@dataclass(frozen=True)
class SecurityScanResult:
    scan_status: str
    completed_checks: tuple[Mapping[str, str], ...]
    reason_codes: tuple[str, ...]
    safe_locations: Mapping[str, Any]
    review_requirement: Mapping[str, Any]
    scan_started_at: str
    scan_completed_at: str


class DevelopmentSecurityScanner(Protocol):
    """Future scanner engine boundary; exact bytes are scanned without normalization."""

    def scan(
        self, candidate_identity: Mapping[str, Any], exact_payload_bytes: bytes,
    ) -> SecurityScanResult:
        ...


class SecurityScanAuthority(ABC):
    """Test-only comparison contract; never accepted by a production entrypoint."""

    @abstractmethod
    def resolve_scan_evidence(self, scan_evidence_id: str) -> Mapping[str, Any] | None:
        ...

    @abstractmethod
    def resolve_test_scan_proof(self, scan_evidence_id: str) -> "TestSecurityScanProof | None":
        ...


@dataclass(frozen=True)
class TestSecurityScanProof:
    """Test-only proof shape; it is not a production attestation or mint capability."""

    scanner_id: str
    scanner_version: str
    security_policy_version: str
    artifact_type_policy_version: str
    payload_hash: str
    scan_evidence_id: str
    scan_evidence_hash: str
    scan_started_at: str
    scan_completed_at: str
    test_adapter_identity: str


@dataclass(frozen=True)
class SecurityScanValidationResult:
    status: str
    reason_code: str
    scan_evidence: Mapping[str, Any] | None = None
    authority_kind: str = field(default="none", repr=False, compare=False)


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _contracts() -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    names = (
        "revision-domains.schema.yaml", "canonicality-common.schema.yaml",
        "source-binding.schema.yaml", "artifact-candidate.schema.yaml",
        "development-security-policy-registry.schema.yaml",
        "development-security-scan-evidence.schema.yaml",
        "development-security-scan-binding.schema.yaml",
    )
    schemas = {name: _load_yaml(SCHEMA_ROOT / name) for name in names}
    resources = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    checked: dict[str, Any] = {}
    for name, schema in schemas.items():
        cls = validators.validator_for(schema)
        cls.check_schema(schema)
        checked[name] = cls(schema, registry=resources, format_checker=FormatChecker())
    policy = _load_yaml(POLICY_PATH)
    checked["development-security-policy-registry.schema.yaml"].validate(policy)
    _validate_policy_semantics(policy)
    return policy, checked


def _validate_policy_semantics(policy: Mapping[str, Any]) -> None:
    artifact_registry = _load_yaml(DEVELOPMENT_ROOT / "shared/artifact-canonicality-registry.yaml")
    if set(policy["artifact_type_policies"]) != set(artifact_registry["artifact_types"]):
        raise ValueError("security policy must cover the closed Artifact registry")
    reasons = policy["reason_code_vocabulary"]
    for code, record in reasons.items():
        expected = {
            "contextual": {"review_required"},
            "hard_block": {"blocked"},
            "operational_unknown": {"unknown"},
        }[record["classification"]]
        if set(record["allowed_scan_statuses"]) != expected:
            raise ValueError(f"reason/status mismatch: {code}")


def evidence_hash(evidence: Mapping[str, Any]) -> str:
    return canonical_record_hash(_thaw(evidence), "evidence_hash")


def _location_key(location: Mapping[str, Any]) -> tuple[Any, ...]:
    kind = location["location_type"]
    if kind == "section_id":
        return (kind, location["section_id"])
    if kind == "field_path":
        return (kind, *location["field_path"])
    return (kind, location["start_line"], location["end_line"])


def _canonicalize_result(result: SecurityScanResult) -> dict[str, Any]:
    checks = sorted((dict(item) for item in result.completed_checks), key=lambda item: item["check_id"])
    reasons = sorted(result.reason_codes)
    locations = dict(result.safe_locations)
    if locations.get("state") == "present":
        locations["locations"] = sorted(
            (dict(item) for item in locations["locations"]), key=_location_key,
        )
    review = dict(result.review_requirement)
    if review.get("state") == "human_review_required":
        review["allowed_action_types"] = sorted(review["allowed_action_types"])
        review["reason_codes"] = sorted(review["reason_codes"])
    return {
        "scan_status": result.scan_status, "completed_checks": checks,
        "reason_codes": reasons, "safe_locations": locations,
        "review_requirement": review, "scan_started_at": result.scan_started_at,
        "scan_completed_at": result.scan_completed_at,
    }


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _effective_checks(policy: Mapping[str, Any], artifact_type: str) -> set[str]:
    return set(policy["global_required_checks"]) | set(
        policy["artifact_type_policies"][artifact_type]["required_checks"]
    )


def _semantic_error(evidence: Mapping[str, Any], policy: Mapping[str, Any]) -> str | None:
    if evidence["security_policy_version"] not in policy["accepted_security_policy_versions"]:
        return "security_scan_policy_mismatch"
    type_policy = policy["artifact_type_policies"].get(evidence["artifact_type"])
    if not type_policy or evidence["artifact_type_policy_version"] != type_policy["artifact_type_policy_version"]:
        return "security_scan_policy_mismatch"
    scanner = {"scanner_id": evidence["scanner_id"], "scanner_version": evidence["scanner_version"]}
    if scanner not in policy["allowed_scanners"]:
        return "security_scan_authority_invalid"
    if evidence["source_binding"]["binding_type"] not in type_policy["accepted_source_binding_variants"]:
        return "security_scan_source_binding_mismatch"
    checks = evidence["completed_checks"]
    if checks != sorted(checks, key=lambda item: item["check_id"]):
        return "security_scan_completed_checks_invalid"
    ids = [item["check_id"] for item in checks]
    if len(ids) != len(set(ids)) or set(ids) != _effective_checks(policy, evidence["artifact_type"]):
        return "security_scan_completed_checks_invalid"
    reasons = evidence["reason_codes"]
    if reasons != sorted(reasons) or len(reasons) != len(set(reasons)):
        return "security_scan_findings_invalid"
    vocabulary = policy["reason_code_vocabulary"]
    if any(code not in vocabulary or evidence["scan_status"] not in vocabulary[code]["allowed_scan_statuses"] for code in reasons):
        return "security_scan_findings_invalid"
    locations = evidence["safe_locations"]
    if locations.get("state") == "present":
        listed = locations["locations"]
        if listed != sorted(listed, key=_location_key):
            return "security_scan_safe_locations_invalid"
        if any(item.get("location_type") == "line_range" and item["start_line"] > item["end_line"] for item in listed):
            return "security_scan_safe_locations_invalid"
        allowed_paths = {
            tuple(path) for path in type_policy["allowed_security_scan_field_paths"]
        }
        if any(
            item.get("location_type") == "field_path"
            and tuple(item["field_path"]) not in allowed_paths
            for item in listed
        ):
            return "security_scan_field_path_unregistered"
    review = evidence["review_requirement"]
    status = evidence["scan_status"]
    completed = all(item["completion_status"] == "completed" for item in checks)
    if status in {"pass", "review_required", "blocked"} and not completed:
        return "security_scan_status_invalid"
    if status == "pass" and not (
        not reasons and locations == {"state": "none"} and review == {"state": "not_required"}
    ):
        return "security_scan_status_invalid"
    if status == "review_required" and not (
        reasons and locations.get("state") == "present"
        and review.get("state") == "human_review_required"
        and review.get("allowed_action_types") == sorted(_ACTIONS)
        and review.get("reason_codes") == reasons
    ):
        return "security_scan_status_invalid"
    if status == "blocked" and not reasons:
        return "security_scan_status_invalid"
    if status in {"blocked", "unknown"} and review != {"state": "not_required"}:
        return "security_scan_status_invalid"
    if status == "unknown" and not reasons:
        return "security_scan_status_invalid"
    if status == "unknown" and completed:
        # A registered operational-unknown reason is itself proof of unavailable safety evidence.
        if not all(vocabulary[code]["classification"] == "operational_unknown" for code in reasons):
            return "security_scan_status_invalid"
    if _parse_time(evidence["scan_started_at"]) > _parse_time(evidence["scan_completed_at"]):
        return "security_scan_timestamp_invalid"
    return None


def validate_scan_evidence_structure(evidence: Mapping[str, Any]) -> SecurityScanValidationResult:
    try:
        policy, checked = _contracts()
        checked["development-security-scan-evidence.schema.yaml"].validate(evidence)
    except (ValidationError, ValueError, OSError, yaml.YAMLError, KeyError, TypeError):
        return SecurityScanValidationResult("invalid", "security_scan_schema_invalid")
    source = validate_source_binding_structure(evidence["source_binding"])
    if source.status != "valid":
        return SecurityScanValidationResult("invalid", "security_scan_source_binding_mismatch")
    semantic = _semantic_error(evidence, policy)
    if semantic:
        return SecurityScanValidationResult("invalid", semantic)
    if evidence_hash(evidence) != evidence["evidence_hash"]:
        return SecurityScanValidationResult("invalid", "security_scan_evidence_hash_mismatch")
    return SecurityScanValidationResult("valid", "security_scan_structure_valid", evidence)


def _candidate_mismatch(evidence: Mapping[str, Any], candidate: Mapping[str, Any]) -> str | None:
    for field, reason in (
        ("artifact_type", "security_scan_artifact_type_mismatch"),
        ("logical_artifact_id", "security_scan_logical_artifact_id_mismatch"),
        ("payload_hash", "security_scan_payload_hash_mismatch"),
        ("payload_format", "security_scan_payload_format_mismatch"),
    ):
        if evidence[field] != candidate.get(field):
            return reason
    if evidence["source_binding"] != candidate.get("source_binding"):
        return "security_scan_source_binding_mismatch"
    return None


def validate_scan_evidence_with_authority_for_test(
    evidence: Mapping[str, Any], candidate: Mapping[str, Any], authority: SecurityScanAuthority | Any,
) -> SecurityScanValidationResult:
    structural = validate_scan_evidence_structure(evidence)
    if structural.status != "valid":
        return structural
    mismatch = _candidate_mismatch(evidence, candidate)
    if mismatch:
        return SecurityScanValidationResult("blocked", mismatch)
    if not isinstance(authority, SecurityScanAuthority):
        return SecurityScanValidationResult("invalid", "security_scan_authority_required")
    try:
        trusted = authority.resolve_scan_evidence(evidence["scan_evidence_id"])
        proof = authority.resolve_test_scan_proof(evidence["scan_evidence_id"])
    except Exception:
        return SecurityScanValidationResult("invalid", "security_scan_authority_invalid")
    if trusted is None or not isinstance(proof, TestSecurityScanProof):
        return SecurityScanValidationResult("blocked", "security_scan_execution_not_found")
    trusted_validation = validate_scan_evidence_structure(trusted)
    if trusted_validation.status != "valid" or dict(trusted) != dict(evidence):
        return SecurityScanValidationResult("blocked", "security_scan_authority_invalid")
    expected_proof = TestSecurityScanProof(
        evidence["scanner_id"], evidence["scanner_version"], evidence["security_policy_version"],
        evidence["artifact_type_policy_version"], evidence["payload_hash"],
        evidence["scan_evidence_id"], evidence["evidence_hash"],
        evidence["scan_started_at"], evidence["scan_completed_at"], proof.test_adapter_identity,
    )
    if not proof.test_adapter_identity or proof != expected_proof:
        return SecurityScanValidationResult("blocked", "security_scan_authority_invalid")
    return SecurityScanValidationResult(
        "valid", "security_scan_test_authority_valid", _freeze(_thaw(evidence)), "test",
    )


def validate_scan_evidence_production(
    evidence: Mapping[str, Any], candidate: Mapping[str, Any],
) -> SecurityScanValidationResult:
    # Resolve at the composition boundary so the installed production source
    # authority and its validator always belong to the same loaded module.
    from source_binding import validate_candidate_source_binding_production
    source = validate_candidate_source_binding_production(candidate)
    if source.status != "valid":
        return SecurityScanValidationResult("blocked", "security_scan_unknown")
    structural = validate_scan_evidence_structure(evidence)
    if structural.status != "valid":
        return structural
    mismatch = _candidate_mismatch(evidence, candidate)
    if mismatch:
        return SecurityScanValidationResult("blocked", mismatch)
    from development_security_scan_trusted_adapter import validate_installed_production_scan_evidence
    if not validate_installed_production_scan_evidence(evidence):
        return SecurityScanValidationResult("blocked", "security_scan_production_authority_required")
    snapshot = _freeze(_thaw(evidence))
    if evidence_hash(snapshot) != snapshot["evidence_hash"]:
        return SecurityScanValidationResult("invalid", "security_scan_evidence_snapshot_invalid")
    return SecurityScanValidationResult(
        "valid", "security_scan_production_authority_valid", snapshot, "production",
    )


def build_scan_evidence_for_test(
    candidate: Mapping[str, Any], exact_payload_bytes: bytes, scan_evidence_id: str,
    scanner_identity: Mapping[str, str], security_policy_version: str,
    artifact_type_policy_version: str, result: SecurityScanResult,
    source_authority: SourceBindingAuthority,
) -> SecurityScanValidationResult:
    try:
        _, checked = _contracts()
        checked["artifact-candidate.schema.yaml"].validate(candidate)
    except (ValidationError, ValueError, OSError, yaml.YAMLError, KeyError, TypeError):
        return SecurityScanValidationResult("invalid", "security_scan_candidate_invalid")
    source = validate_candidate_source_binding_with_authority(candidate, source_authority)
    if source.status != "valid":
        return SecurityScanValidationResult("blocked", "security_scan_source_binding_mismatch")
    if hashlib.sha256(exact_payload_bytes).hexdigest() != candidate.get("payload_hash"):
        return SecurityScanValidationResult("blocked", "security_scan_payload_hash_mismatch")
    try:
        canonical = _canonicalize_result(result)
    except (KeyError, TypeError, ValueError):
        return SecurityScanValidationResult("invalid", "security_scan_result_invalid")
    evidence: dict[str, Any] = {
        "scan_evidence_schema_version": "1.0", "scan_evidence_id": scan_evidence_id,
        "scanner_id": scanner_identity["scanner_id"], "scanner_version": scanner_identity["scanner_version"],
        "security_policy_version": security_policy_version,
        "artifact_type_policy_version": artifact_type_policy_version,
        "artifact_type": candidate["artifact_type"], "logical_artifact_id": candidate["logical_artifact_id"],
        "payload_hash": candidate["payload_hash"], "payload_format": candidate["payload_format"],
        "source_binding": candidate["source_binding"], **canonical,
    }
    evidence["evidence_hash"] = evidence_hash(evidence)
    return validate_scan_evidence_structure(evidence)


def _derive_binding_from_production_snapshot(
    validated: SecurityScanValidationResult,
) -> tuple[Mapping[str, Any] | None, str]:
    if (
        validated.status != "valid" or validated.authority_kind != "production"
        or validated.scan_evidence is None
    ):
        return None, "security_scan_binding_invalid"
    evidence = validated.scan_evidence
    if evidence_hash(evidence) != evidence["evidence_hash"]:
        return None, "security_scan_evidence_snapshot_invalid"
    if evidence["scan_status"] != "pass":
        return None, {
            "review_required": "security_scan_review_required",
            "blocked": "security_scan_blocked", "unknown": "security_scan_unknown",
        }[evidence["scan_status"]]
    binding = {
        "scan_evidence_id": evidence["scan_evidence_id"],
        "scan_evidence_hash": evidence["evidence_hash"],
        "scanned_payload_hash": evidence["payload_hash"],
        "security_policy_version": evidence["security_policy_version"],
        "artifact_type_policy_version": evidence["artifact_type_policy_version"],
        "scan_status": "pass", "final_security_decision": "automatic_pass",
        "human_review_binding": {"state": "not_required"},
    }
    _, checked = _contracts()
    try:
        checked["development-security-scan-binding.schema.yaml"].validate(binding)
    except ValidationError:
        return None, "security_scan_binding_invalid"
    return binding, "security_scan_binding_valid"


def validate_and_derive_development_security_scan_binding_production(
    candidate: Mapping[str, Any], exact_payload_bytes: bytes, evidence: Mapping[str, Any],
) -> tuple[Mapping[str, Any] | None, str]:
    """Production mint: installed authorities are internal and cannot be injected."""
    if hashlib.sha256(exact_payload_bytes).hexdigest() != candidate.get("payload_hash"):
        return None, "security_scan_payload_hash_mismatch"
    validated = validate_scan_evidence_production(evidence, candidate)
    if validated.status != "valid":
        return None, validated.reason_code
    return _derive_binding_from_production_snapshot(validated)


def derive_development_security_scan_binding(
    validated: SecurityScanValidationResult,
) -> tuple[Mapping[str, Any] | None, str]:
    """Deprecated generic entrypoint: no generic/test result may mint a production binding."""
    return None, "security_scan_binding_derivation_not_allowed"


def validate_security_scan_binding_structure(binding: Mapping[str, Any]) -> str:
    try:
        _, checked = _contracts()
        checked["development-security-scan-binding.schema.yaml"].validate(binding)
    except (ValidationError, ValueError, OSError, yaml.YAMLError):
        return "security_scan_binding_invalid"
    return "security_scan_binding_structure_valid"


def validate_development_security_scan_binding(binding: Mapping[str, Any]) -> str:
    """Backward-compatible structural-only alias; it does not establish eligibility."""
    return validate_security_scan_binding_structure(binding)
