"""Pre-allocation Development Artifact Write Request contract."""
from __future__ import annotations

from base64 import b64decode, b64encode
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml
from jsonschema import FormatChecker, ValidationError, validators
from referencing import Registry, Resource

from artifact_identity import is_valid_logical_id, validate_revision_scoped_logical_id
from canonicality_authority import canonical_record_hash
from development_security_scan import (
    SecurityScanAuthority,
    validate_scan_evidence_with_authority_for_test,
    validate_security_scan_binding_structure,
)
from source_binding import (
    SourceBindingAuthority,
    validate_candidate_source_binding_with_authority,
    validate_source_binding_structure,
)


DEVELOPMENT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = DEVELOPMENT_ROOT / "schemas"
REGISTRY_PATH = DEVELOPMENT_ROOT / "shared/artifact-canonicality-registry.yaml"
FORBIDDEN_FIELDS = frozenset({
    "artifact_revision", "revision", "revision_number",
    "revision_scoped_logical_artifact_id", "allocation_id", "target_path",
    "repository_path", "absolute_path", "extension", "revision_path_segment",
    "path_policy_result", "artifact_reference", "writer_status",
    "persistence_status", "temporary_path", "filesystem_handle",
})


@dataclass(frozen=True)
class WriteRequestValidationResult:
    status: str
    reason_code: str
    write_request: Mapping[str, Any] | None = None
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
        return [_thaw(child) for child in value]
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _contracts() -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    names = (
        "revision-domains.schema.yaml", "canonicality-common.schema.yaml",
        "source-binding.schema.yaml", "artifact-candidate.schema.yaml",
        "development-security-scan-binding.schema.yaml",
        "artifact-write-request.schema.yaml",
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
    return _load_yaml(REGISTRY_PATH), checked


def encode_payload(exact_payload_bytes: bytes) -> Mapping[str, str]:
    if not isinstance(exact_payload_bytes, bytes):
        raise TypeError("write_request_payload_bytes_required")
    return {"encoding": "base64", "data": b64encode(exact_payload_bytes).decode("ascii")}


def decode_payload(payload: Mapping[str, Any]) -> bytes:
    if not isinstance(payload, Mapping) or set(payload) != {"encoding", "data"}:
        raise ValueError("write_request_payload_invalid")
    if payload.get("encoding") != "base64" or not isinstance(payload.get("data"), str):
        raise ValueError("write_request_payload_invalid")
    try:
        decoded = b64decode(payload["data"], validate=True)
    except Exception as exc:
        raise ValueError("write_request_payload_invalid") from exc
    if b64encode(decoded).decode("ascii") != payload["data"]:
        raise ValueError("write_request_payload_invalid")
    return decoded


def request_fingerprint(request: Mapping[str, Any]) -> str:
    envelope = {
        key: _thaw(request[key]) for key in (
            "request_schema_version", "artifact_type", "logical_artifact_id",
            "payload_format", "payload_hash", "subject_binding", "expected_latest",
            "source_binding", "development_security_scan_binding",
        )
    }
    return canonical_record_hash(envelope, "request_fingerprint")


def _payload_valid(exact: bytes, payload_format: str) -> bool:
    try:
        text = exact.decode("utf-8")
        if payload_format == "yaml":
            yaml.safe_load(text)
        elif payload_format != "markdown":
            return False
    except (UnicodeDecodeError, yaml.YAMLError):
        return False
    return True


def _identity_error(candidate: Mapping[str, Any], registry: Mapping[str, Any]) -> str | None:
    artifact_type = candidate.get("artifact_type")
    entry = registry["artifact_types"].get(artifact_type)
    if entry is None:
        return "write_request_artifact_type_unregistered"
    logical_id = candidate.get("logical_artifact_id")
    if not is_valid_logical_id(logical_id):
        return "write_request_logical_artifact_id_invalid"
    policy = entry["path_policy"]
    if candidate.get("payload_format") != policy["canonical_format"]:
        return "write_request_payload_format_mismatch"
    subject = candidate.get("subject_binding")
    variant = policy["subject_binding_variant"]
    if variant == "none":
        if subject != {"binding_type": "none"}:
            return "write_request_subject_binding_mismatch"
    else:
        if not isinstance(subject, Mapping) or subject.get("binding_type") != "bound":
            return "write_request_subject_binding_mismatch"
        if subject.get("subject_type") != variant:
            return "write_request_subject_binding_mismatch"
    mode = policy["logical_series_identity"]
    if mode == "subject_id_revision" and not validate_revision_scoped_logical_id(
        logical_id, subject.get("subject_id"), subject.get("subject_revision"),
    ):
        return "write_request_logical_series_identity_mismatch"
    if mode == "subject_id" and logical_id != subject.get("subject_id"):
        return "write_request_logical_series_identity_mismatch"
    return None


def validate_write_request_structure(request: Mapping[str, Any]) -> WriteRequestValidationResult:
    if not isinstance(request, Mapping) or FORBIDDEN_FIELDS.intersection(request):
        return WriteRequestValidationResult("invalid", "write_request_schema_invalid")
    try:
        plain = _thaw(request)
        registry, checked = _contracts()
        checked["artifact-write-request.schema.yaml"].validate(plain)
        exact = decode_payload(plain["payload"])
    except (ValidationError, ValueError, OSError, yaml.YAMLError, KeyError, TypeError):
        return WriteRequestValidationResult("invalid", "write_request_schema_invalid")
    if hashlib.sha256(exact).hexdigest() != plain["payload_hash"]:
        return WriteRequestValidationResult("invalid", "write_request_payload_hash_mismatch")
    if not _payload_valid(exact, plain["payload_format"]):
        return WriteRequestValidationResult("invalid", "write_request_payload_format_invalid")
    identity = _identity_error(plain, registry)
    if identity:
        return WriteRequestValidationResult("blocked", identity)
    source = validate_source_binding_structure(plain["source_binding"])
    if source.status != "valid":
        return WriteRequestValidationResult("invalid", source.reason_code)
    security = validate_security_scan_binding_structure(
        plain["development_security_scan_binding"]
    )
    if security != "security_scan_binding_structure_valid":
        return WriteRequestValidationResult("invalid", "write_request_security_binding_invalid")
    binding = plain["development_security_scan_binding"]
    if binding["scanned_payload_hash"] != plain["payload_hash"]:
        return WriteRequestValidationResult("blocked", "write_request_security_payload_mismatch")
    if not (
        binding["scan_status"] == "pass"
        and binding["final_security_decision"] == "automatic_pass"
        and binding["human_review_binding"] == {"state": "not_required"}
    ):
        return WriteRequestValidationResult("blocked", "write_request_final_decision_not_allowed")
    if request_fingerprint(plain) != plain["request_fingerprint"]:
        return WriteRequestValidationResult("invalid", "write_request_fingerprint_mismatch")
    return WriteRequestValidationResult("valid", "write_request_structure_valid", request)


def _candidate_error(
    request: Mapping[str, Any], candidate: Mapping[str, Any], exact_payload_bytes: bytes,
) -> str | None:
    for field in ("artifact_type", "logical_artifact_id", "payload_format", "payload_hash", "subject_binding", "source_binding"):
        if request[field] != candidate.get(field):
            return f"write_request_candidate_{field}_mismatch"
    if decode_payload(request["payload"]) != exact_payload_bytes:
        return "write_request_candidate_payload_mismatch"
    if hashlib.sha256(exact_payload_bytes).hexdigest() != candidate.get("payload_hash"):
        return "write_request_candidate_payload_mismatch"
    return None


def _assemble(
    candidate: Mapping[str, Any], exact_payload_bytes: bytes,
    expected_latest: Mapping[str, Any], request_id: str, idempotency_key: str,
    security_binding: Mapping[str, Any], authority_kind: str,
) -> WriteRequestValidationResult:
    request: dict[str, Any] = {
        "request_schema_version": "1.0", "request_id": request_id,
        "idempotency_key": idempotency_key, "request_fingerprint": "0" * 64,
        "artifact_type": candidate["artifact_type"],
        "logical_artifact_id": candidate["logical_artifact_id"],
        "payload": encode_payload(exact_payload_bytes),
        "payload_format": candidate["payload_format"], "payload_hash": candidate["payload_hash"],
        "subject_binding": _thaw(candidate["subject_binding"]),
        "expected_latest": _thaw(expected_latest),
        "source_binding": _thaw(candidate["source_binding"]),
        "development_security_scan_binding": _thaw(security_binding),
    }
    request["request_fingerprint"] = request_fingerprint(request)
    structural = validate_write_request_structure(request)
    if structural.status != "valid":
        return structural
    snapshot = _freeze(request)
    return WriteRequestValidationResult(
        "valid", f"write_request_{authority_kind}_valid", snapshot, authority_kind,
    )


def build_write_request_production(
    *, candidate: Mapping[str, Any], exact_payload_bytes: bytes,
    expected_latest: Mapping[str, Any], request_id: str, idempotency_key: str,
    scan_evidence: Mapping[str, Any],
) -> WriteRequestValidationResult:
    """Production mint; all authority selection is internal."""
    try:
        registry, checked = _contracts()
        checked["artifact-candidate.schema.yaml"].validate(candidate)
    except (ValidationError, ValueError, OSError, yaml.YAMLError, KeyError, TypeError):
        return WriteRequestValidationResult("invalid", "write_request_candidate_invalid")
    if _identity_error(candidate, registry):
        return WriteRequestValidationResult("blocked", _identity_error(candidate, registry))
    from source_binding import validate_candidate_source_binding_production as validate_source_production
    source = validate_source_production(candidate)
    if source.status != "valid":
        return WriteRequestValidationResult("blocked", "write_request_source_authority_required")
    from development_security_scan import (
        validate_and_derive_development_security_scan_binding_production as derive_security_production,
    )
    binding, reason = derive_security_production(
        candidate, exact_payload_bytes, scan_evidence,
    )
    if binding is None:
        return WriteRequestValidationResult("blocked", reason)
    return _assemble(
        candidate, exact_payload_bytes, expected_latest, request_id, idempotency_key,
        binding, "production",
    )


def build_write_request_for_test(
    *, candidate: Mapping[str, Any], exact_payload_bytes: bytes,
    expected_latest: Mapping[str, Any], request_id: str, idempotency_key: str,
    scan_evidence: Mapping[str, Any], source_authority: SourceBindingAuthority,
    scan_authority: SecurityScanAuthority,
) -> WriteRequestValidationResult:
    """Internal/test entrypoint; its result is never production eligible."""
    try:
        registry, checked = _contracts()
        checked["artifact-candidate.schema.yaml"].validate(candidate)
    except (ValidationError, ValueError, OSError, yaml.YAMLError, KeyError, TypeError):
        return WriteRequestValidationResult("invalid", "write_request_candidate_invalid")
    identity = _identity_error(candidate, registry)
    if identity:
        return WriteRequestValidationResult("blocked", identity)
    source = validate_candidate_source_binding_with_authority(candidate, source_authority)
    if source.status != "valid":
        return WriteRequestValidationResult("blocked", "write_request_source_authority_required")
    validated = validate_scan_evidence_with_authority_for_test(scan_evidence, candidate, scan_authority)
    if validated.status != "valid" or validated.scan_evidence is None:
        return WriteRequestValidationResult("blocked", validated.reason_code)
    evidence = validated.scan_evidence
    if evidence["scan_status"] != "pass":
        return WriteRequestValidationResult("blocked", "write_request_final_decision_not_allowed")
    binding = {
        "scan_evidence_id": evidence["scan_evidence_id"],
        "scan_evidence_hash": evidence["evidence_hash"],
        "scanned_payload_hash": evidence["payload_hash"],
        "security_policy_version": evidence["security_policy_version"],
        "artifact_type_policy_version": evidence["artifact_type_policy_version"],
        "scan_status": "pass", "final_security_decision": "automatic_pass",
        "human_review_binding": {"state": "not_required"},
    }
    return _assemble(
        candidate, exact_payload_bytes, expected_latest, request_id, idempotency_key,
        binding, "test",
    )


def validate_write_request_authority_production(
    request: Mapping[str, Any], *, candidate: Mapping[str, Any],
    exact_payload_bytes: bytes, scan_evidence: Mapping[str, Any],
) -> WriteRequestValidationResult:
    structural = validate_write_request_structure(request)
    if structural.status != "valid":
        return structural
    try:
        registry, checked = _contracts()
        checked["artifact-candidate.schema.yaml"].validate(_thaw(candidate))
    except (ValidationError, ValueError, OSError, yaml.YAMLError, KeyError, TypeError):
        return WriteRequestValidationResult("invalid", "write_request_candidate_invalid")
    identity = _identity_error(candidate, registry)
    if identity:
        return WriteRequestValidationResult("blocked", identity)
    try:
        mismatch = _candidate_error(request, candidate, exact_payload_bytes)
    except (KeyError, TypeError, ValueError):
        return WriteRequestValidationResult("invalid", "write_request_candidate_invalid")
    if mismatch:
        return WriteRequestValidationResult("blocked", mismatch)
    from source_binding import validate_candidate_source_binding_production as validate_source_production
    source = validate_source_production(candidate)
    if source.status != "valid":
        return WriteRequestValidationResult("blocked", "write_request_source_authority_required")
    from development_security_scan import (
        validate_and_derive_development_security_scan_binding_production as derive_security_production,
    )
    binding, reason = derive_security_production(
        candidate, exact_payload_bytes, scan_evidence,
    )
    if binding is None or dict(binding) != dict(request["development_security_scan_binding"]):
        return WriteRequestValidationResult("blocked", reason if binding is None else "write_request_security_binding_mismatch")
    snapshot = _freeze(_thaw(request))
    if request_fingerprint(snapshot) != snapshot["request_fingerprint"]:
        return WriteRequestValidationResult("invalid", "write_request_snapshot_invalid")
    return WriteRequestValidationResult(
        "valid", "write_request_production_authority_valid", snapshot, "production",
    )


class WriteRequestLocalIndex:
    """Single-threaded test utility; never a production authority or persistent store."""

    def __init__(self) -> None:
        self._by_request_id: dict[str, Mapping[str, Any]] = {}
        self._by_idempotency_key: dict[str, Mapping[str, Any]] = {}

    def record(self, request: Mapping[str, Any]) -> str:
        validated = validate_write_request_structure(request)
        if validated.status != "valid":
            return validated.reason_code
        snapshot = _freeze(_thaw(request))
        for key, index in (
            (request["request_id"], self._by_request_id),
            (request["idempotency_key"], self._by_idempotency_key),
        ):
            previous = index.get(key)
            if previous is not None and previous != snapshot:
                return "write_request_identity_conflict"
        existing = request["request_id"] in self._by_request_id
        self._by_request_id[request["request_id"]] = snapshot
        self._by_idempotency_key[request["idempotency_key"]] = snapshot
        return "write_request_idempotent" if existing else "write_request_recorded"
