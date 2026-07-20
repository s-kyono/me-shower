"""Immutable, raw-content-free Candidate source provenance bindings."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml
from jsonschema import FormatChecker, ValidationError, validators
from referencing import Registry, Resource

from artifact_identity import validate_revision_scoped_logical_id


DEVELOPMENT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = DEVELOPMENT_ROOT / "schemas"
GENERATION_FINGERPRINT_SCHEMA_VERSION = "1.0"
GENERATION_INPUT_POLICY_VERSION = "generation-input-v1"
GENERATION_INPUT_DOMAIN = "development-artifact-generation-input"
SNAPSHOT_POLICY_VERSION = "repository-snapshot-v1"
FORBIDDEN_FIELDS = {
    "raw_source", "raw_source_content", "raw_transcript", "raw_tool_output",
    "original_input", "prompt", "content", "secret", "credential", "absolute_path",
    "latest", "current", "status", "branch", "diff", "file_content", "human_note",
}


@dataclass(frozen=True)
class SourceBindingValidationResult:
    status: str
    reason_code: str
    source_binding: Mapping[str, Any] | None = None


class SourceBindingAuthority(ABC):
    """Composition-boundary authority; it returns an already verified immutable binding."""

    @abstractmethod
    def resolve_source_binding(
        self, generator_identity: Mapping[str, str], generator_execution_id: str,
    ) -> Mapping[str, Any] | None:
        """Resolve exactly one binding for one registered generator execution."""

    @abstractmethod
    def supports_binding_type(self, binding_type: str) -> bool:
        """Confirm the installed authority independently verifies this provenance variant."""

    @abstractmethod
    def resolve_generation_execution_evidence(
        self, generator_identity: Mapping[str, str], generator_execution_id: str,
    ) -> "GenerationExecutionEvidence | None":
        """Resolve safe immutable inputs used to recompute a generated-only fingerprint."""


@dataclass(frozen=True)
class GenerationExecutionEvidence:
    generator_identity: Mapping[str, str]
    generator_execution_id: str
    generation_input_fingerprint_schema_version: str
    generation_input_policy_version: str
    generation_input_domain: str
    safe_immutable_input_hashes: tuple[str, ...]


class SourceBindingExecutionIndex:
    """Single-threaded test utility; never a production trust primitive."""

    def __init__(self) -> None:
        self.__records: dict[tuple[str, str, str], dict[str, Any]] = {}

    @staticmethod
    def key(binding: Mapping[str, Any]) -> tuple[str, str, str]:
        identity = binding["generator_identity"]
        return identity["source_id"], identity["source_version"], binding["generator_execution_id"]

    def record(self, binding: Mapping[str, Any]) -> str:
        key = self.key(binding)
        previous = self.__records.get(key)
        if previous is not None:
            if previous != binding:
                return "source_binding_execution_conflict"
            return "source_binding_execution_idempotent"
        validation = validate_source_binding_structure(binding)
        if validation.status != "valid":
            return validation.reason_code
        self.__records[key] = json.loads(json.dumps(binding))
        return "source_binding_execution_recorded"

    def resolve(self, generator_identity: Mapping[str, str], execution_id: str) -> Mapping[str, Any] | None:
        key = generator_identity["source_id"], generator_identity["source_version"], execution_id
        value = self.__records.get(key)
        return json.loads(json.dumps(value)) if value is not None else None


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generation_input_fingerprint(
    generator_identity: Mapping[str, str], generator_execution_id: str,
    safe_input_hashes: Sequence[str],
) -> str:
    """Hash only registered safe immutable input hashes, never their source bytes."""
    envelope = {
        "generation_input_fingerprint_schema_version": GENERATION_FINGERPRINT_SCHEMA_VERSION,
        "generation_input_policy_version": GENERATION_INPUT_POLICY_VERSION,
        "generation_input_domain": GENERATION_INPUT_DOMAIN,
        "generator_identity": dict(generator_identity),
        "generator_execution_id": generator_execution_id,
        "safe_input_hashes": sorted(safe_input_hashes),
    }
    return _canonical_hash(envelope)


def source_reference_set_hash(references: Sequence[Mapping[str, Any]]) -> str:
    """Commit only to the canonical immutable source Artifact Reference set."""
    return _canonical_hash(list(references))


def source_binding_hash(binding: Mapping[str, Any]) -> str:
    """Commit to generator, execution, variant, and all variant provenance facts."""
    return _canonical_hash({key: value for key, value in binding.items() if key != "source_binding_hash"})


def _series_key(series: Mapping[str, Any]) -> tuple[Any, ...]:
    kind = series["identity_type"]
    if kind == "logical_id":
        return (kind, series["logical_artifact_id"])
    if kind == "subject_id":
        return (kind, series["subject_type"], series["subject_id"])
    return (kind, series["subject_type"], series["subject_id"], series["subject_revision"])


def _reference_identity_key(reference: Mapping[str, Any]) -> tuple[Any, ...]:
    return (reference["artifact_type"], _series_key(reference["logical_series"]), reference["artifact_revision"])


def _reference_sort_key(reference: Mapping[str, Any]) -> tuple[Any, ...]:
    return _reference_identity_key(reference) + (reference["logical_artifact_id"], reference["content_hash"])


def _logical_series_matches(reference: Mapping[str, Any]) -> bool:
    series = reference["logical_series"]
    kind = series["identity_type"]
    if kind == "logical_id":
        return reference["logical_artifact_id"] == series["logical_artifact_id"]
    if kind == "subject_id":
        return reference["logical_artifact_id"] == series["subject_id"]
    return validate_revision_scoped_logical_id(
        reference["logical_artifact_id"], series["subject_id"], series["subject_revision"],
    )


def canonicalize_source_references(
    references: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    canonical = sorted((dict(item) for item in references), key=_reference_sort_key)
    seen: dict[tuple[Any, ...], str] = {}
    for item in canonical:
        identity = _reference_identity_key(item)
        previous = seen.get(identity)
        if previous is not None:
            if previous != item["content_hash"]:
                return None, "source_binding_artifact_reference_conflict"
            return None, "source_binding_reference_duplicate"
        seen[identity] = item["content_hash"]
    return canonical, None


def _load_validator():
    names = ("revision-domains.schema.yaml", "canonicality-common.schema.yaml", "source-binding.schema.yaml")
    schemas = {name: yaml.safe_load((SCHEMA_ROOT / name).read_text(encoding="utf-8")) for name in names}
    resources = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    schema = schemas["source-binding.schema.yaml"]
    cls = validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema, registry=resources, format_checker=FormatChecker())


def _has_forbidden_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(key in FORBIDDEN_FIELDS or _has_forbidden_field(child) for key, child in value.items())
    if isinstance(value, (list, tuple)):
        return any(_has_forbidden_field(item) for item in value)
    return False


def validate_source_binding_structure(
    binding: Mapping[str, Any], expected_generator_identity: Mapping[str, Any] | None = None,
) -> SourceBindingValidationResult:
    if not isinstance(binding, Mapping) or _has_forbidden_field(binding):
        return SourceBindingValidationResult("invalid", "source_binding_forbidden_field")
    try:
        _load_validator().validate(binding)
    except (ValidationError, ValueError, OSError, yaml.YAMLError, KeyError, TypeError):
        return SourceBindingValidationResult("invalid", "source_binding_schema_invalid")
    if expected_generator_identity is not None and binding["generator_identity"] != expected_generator_identity:
        return SourceBindingValidationResult("blocked", "source_binding_generator_identity_mismatch")
    if binding["binding_type"] == "artifact_references":
        references = binding["source_references"]
        if any(not _logical_series_matches(item) for item in references):
            return SourceBindingValidationResult("blocked", "source_binding_logical_series_mismatch")
        canonical, conflict = canonicalize_source_references(references)
        if conflict:
            return SourceBindingValidationResult("blocked", conflict)
        if references != canonical:
            return SourceBindingValidationResult("invalid", "source_binding_reference_order_invalid")
        if source_reference_set_hash(references) != binding["source_reference_set_hash"]:
            return SourceBindingValidationResult("invalid", "source_binding_reference_set_integrity_invalid")
    if source_binding_hash(binding) != binding["source_binding_hash"]:
        return SourceBindingValidationResult("invalid", "source_binding_integrity_invalid")
    return SourceBindingValidationResult("valid", "source_binding_structure_valid", binding)


def validate_source_binding_authority(
    binding: Mapping[str, Any], authority: SourceBindingAuthority | Any,
) -> SourceBindingValidationResult:
    structural = validate_source_binding_structure(binding)
    if structural.status != "valid":
        return structural
    if not isinstance(authority, SourceBindingAuthority):
        return SourceBindingValidationResult("invalid", "source_binding_authority_required")
    try:
        supported = authority.supports_binding_type(binding["binding_type"])
    except Exception:
        supported = False
    if not supported:
        reason = (
            "source_binding_artifact_reference_unverified"
            if binding["binding_type"] == "artifact_references"
            else "source_binding_authority_invalid"
        )
        return SourceBindingValidationResult("blocked", reason)
    if binding["binding_type"] == "generated_only":
        try:
            evidence = authority.resolve_generation_execution_evidence(
                binding["generator_identity"], binding["generator_execution_id"],
            )
        except Exception:
            evidence = None
        if not isinstance(evidence, GenerationExecutionEvidence):
            return SourceBindingValidationResult("blocked", "source_binding_fingerprint_evidence_missing")
        if evidence.generator_identity != binding["generator_identity"] or evidence.generator_execution_id != binding["generator_execution_id"]:
            return SourceBindingValidationResult("blocked", "source_binding_provenance_mismatch")
        if evidence.generation_input_fingerprint_schema_version != GENERATION_FINGERPRINT_SCHEMA_VERSION:
            return SourceBindingValidationResult("blocked", "source_binding_fingerprint_policy_mismatch")
        if evidence.generation_input_policy_version != GENERATION_INPUT_POLICY_VERSION:
            return SourceBindingValidationResult("blocked", "source_binding_fingerprint_policy_mismatch")
        if evidence.generation_input_domain != GENERATION_INPUT_DOMAIN:
            return SourceBindingValidationResult("blocked", "source_binding_fingerprint_domain_mismatch")
        safe_hashes = evidence.safe_immutable_input_hashes
        if len(safe_hashes) != len(set(safe_hashes)) or any(
            not isinstance(item, str) or len(item) != 64 or any(ch not in "0123456789abcdef" for ch in item)
            for item in safe_hashes
        ):
            return SourceBindingValidationResult("invalid", "source_binding_fingerprint_evidence_invalid")
        expected_fingerprint = generation_input_fingerprint(
            evidence.generator_identity, evidence.generator_execution_id, safe_hashes,
        )
        if expected_fingerprint != binding["generation_input_fingerprint"]:
            return SourceBindingValidationResult("blocked", "source_binding_fingerprint_mismatch")
    try:
        trusted = authority.resolve_source_binding(
            binding["generator_identity"], binding["generator_execution_id"],
        )
    except Exception:
        return SourceBindingValidationResult("invalid", "source_binding_authority_invalid")
    if trusted is None:
        return SourceBindingValidationResult("blocked", "source_binding_execution_not_found")
    trusted_result = validate_source_binding_structure(trusted, binding["generator_identity"])
    if trusted_result.status != "valid":
        return SourceBindingValidationResult("invalid", "source_binding_authority_invalid")
    if dict(trusted) != dict(binding):
        return SourceBindingValidationResult("blocked", "source_binding_provenance_mismatch")
    return SourceBindingValidationResult("valid", "source_binding_authority_valid", binding)


def validate_source_binding(
    binding: Mapping[str, Any], expected_generator_identity: Mapping[str, Any] | None = None,
) -> SourceBindingValidationResult:
    """Backward-compatible name for structural/integrity validation only."""
    return validate_source_binding_structure(binding, expected_generator_identity)


def validate_candidate_source_binding_with_authority(
    candidate: Mapping[str, Any], authority: SourceBindingAuthority | Any,
) -> SourceBindingValidationResult:
    structural = validate_source_binding_structure(
        candidate.get("source_binding", {}), candidate.get("generated_by"),
    )
    if structural.status != "valid":
        return structural
    return validate_source_binding_authority(candidate["source_binding"], authority)


def validate_candidate_source_binding_production(
    candidate: Mapping[str, Any],
) -> SourceBindingValidationResult:
    """Production entrypoint: callers cannot inject an authority object."""
    try:
        from source_binding_trusted_adapter import (
            PRODUCTION_SOURCE_PROVENANCE_AUTHORITY,
            ProductionSourceProvenanceResolver,
        )
    except ImportError:
        return SourceBindingValidationResult("invalid", "source_binding_production_authority_required")
    if type(PRODUCTION_SOURCE_PROVENANCE_AUTHORITY) is not ProductionSourceProvenanceResolver:
        return SourceBindingValidationResult("invalid", "source_binding_production_authority_required")
    result = validate_candidate_source_binding_with_authority(
        candidate, PRODUCTION_SOURCE_PROVENANCE_AUTHORITY,
    )
    if result.reason_code in {
        "source_binding_authority_required", "source_binding_authority_invalid",
        "source_binding_execution_not_found", "source_binding_fingerprint_evidence_missing",
    }:
        return SourceBindingValidationResult(
            "blocked", "source_binding_production_authority_required",
        )
    return result


def build_generated_only_binding(
    generator_identity: Mapping[str, str], execution_id: str, safe_input_hashes: Sequence[str],
) -> dict[str, Any]:
    binding: dict[str, Any] = {
        "source_binding_schema_version": "1.0", "binding_type": "generated_only",
        "generator_identity": dict(generator_identity), "generator_execution_id": execution_id,
        "generation_input_fingerprint_schema_version": GENERATION_FINGERPRINT_SCHEMA_VERSION,
        "generation_input_policy_version": GENERATION_INPUT_POLICY_VERSION,
        "generation_input_domain": GENERATION_INPUT_DOMAIN,
        "generation_input_fingerprint": generation_input_fingerprint(
            generator_identity, execution_id, safe_input_hashes,
        ),
    }
    binding["source_binding_hash"] = source_binding_hash(binding)
    return binding


def build_artifact_references_binding(
    generator_identity: Mapping[str, str], execution_id: str,
    references: Sequence[Mapping[str, Any]],
) -> SourceBindingValidationResult:
    canonical, conflict = canonicalize_source_references(references)
    if conflict:
        return SourceBindingValidationResult("blocked", conflict)
    binding: dict[str, Any] = {
        "source_binding_schema_version": "1.0", "binding_type": "artifact_references",
        "generator_identity": dict(generator_identity), "generator_execution_id": execution_id,
        "source_references": canonical,
        "source_reference_set_hash": source_reference_set_hash(canonical or []),
    }
    binding["source_binding_hash"] = source_binding_hash(binding)
    result = validate_source_binding_structure(binding)
    return result if result.status != "valid" else SourceBindingValidationResult("valid", "source_binding_built", binding)


def build_repository_snapshot_binding(
    generator_identity: Mapping[str, str], execution_id: str,
    repository_identity: Mapping[str, str], snapshot_hash: str,
) -> dict[str, Any]:
    binding: dict[str, Any] = {
        "source_binding_schema_version": "1.0", "binding_type": "repository_snapshot",
        "generator_identity": dict(generator_identity), "generator_execution_id": execution_id,
        "repository_identity": dict(repository_identity),
        "snapshot_kind": "canonical_worktree_snapshot",
        "snapshot_policy_version": SNAPSHOT_POLICY_VERSION,
        "repository_snapshot_hash": snapshot_hash,
    }
    binding["source_binding_hash"] = source_binding_hash(binding)
    return binding
