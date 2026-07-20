"""Deterministic, repository-relative Development Artifact Path Policy."""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from string import Formatter
from typing import Any, Mapping

import yaml
from jsonschema import FormatChecker, ValidationError, validators
from referencing import Registry, Resource

from artifact_identity import (
    MAX_REVISION, build_revision_scoped_logical_id, format_revision_token,
    is_valid_logical_id,
)


DEVELOPMENT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = DEVELOPMENT_ROOT / "schemas"
REGISTRY_PATH = DEVELOPMENT_ROOT / "shared/artifact-canonicality-registry.yaml"
ARTIFACT_ROOT = PurePosixPath(".codex/harness/development/artifacts")
REVISION_SEGMENT_RE = re.compile(r"^r[0-9]{4,}$", re.ASCII)
ALLOWED_TOKENS = {
    "logical_id", "artifact_revision", "subject_decision_id",
    "subject_plan_id", "subject_implementation_id", "subject_revision",
}
FIXED_PATH_NAMES = {"PLAN.md", "DESIGN_LOCK.md", "REVIEW.md", "RELEASE_GATE.md", "ADR.md"}
FORMAT_EXTENSIONS = {"markdown": ".md", "json": ".json"}
ID_TOKENS = {"logical_id", "subject_decision_id", "subject_plan_id", "subject_implementation_id"}
REVISION_TOKEN_SEGMENTS = {
    "{artifact_revision}.md", "{artifact_revision}.json",
    "record-{artifact_revision}.json", "review-{artifact_revision}.md",
    "validation-{artifact_revision}.json", "lock-{artifact_revision}.md",
    "readiness-{artifact_revision}.json", "gate-{artifact_revision}.md",
    "request-{artifact_revision}.json", "handoff-{artifact_revision}.json",
    "grant-{artifact_revision}.json", "continuation-{artifact_revision}.json",
    "revocation-{artifact_revision}.json", "plan-{subject_revision}",
    "implementation-{subject_revision}",
}


@dataclass(frozen=True)
class PathPolicyResult:
    status: str
    reason_code: str
    path_derivation: Mapping[str, Any] | None = None


def _result(status: str, reason: str, record=None) -> PathPolicyResult:
    return PathPolicyResult(status, reason, record)


def _canonical_hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def derivation_record_hash(record: Mapping[str, Any]) -> str:
    return _canonical_hash({k: v for k, v in record.items() if k != "derivation_record_hash"})


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_contracts():
    names = (
        "revision-domains.schema.yaml", "canonicality-common.schema.yaml",
        "artifact-canonicality-registry.schema.yaml",
        "artifact-path-derivation-request.schema.yaml",
        "artifact-path-derivation-result.schema.yaml",
    )
    schemas = {name: _load_yaml(SCHEMA_ROOT / name) for name in names}
    resources = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    )
    compiled = {}
    for name, schema in schemas.items():
        cls = validators.validator_for(schema)
        cls.check_schema(schema)
        compiled[name] = cls(schema, registry=resources, format_checker=FormatChecker())
    registry = _load_yaml(REGISTRY_PATH)
    compiled["artifact-canonicality-registry.schema.yaml"].validate(registry)
    reason = validate_path_policy_registry(registry)
    if reason:
        raise ValueError(reason)
    return registry, compiled


def is_valid_path_id(value: Any) -> bool:
    return is_valid_logical_id(value)


def revision_segment(value: Any) -> str:
    try:
        segment = format_revision_token(value)
    except ValueError as error:
        raise ValueError("path_policy_artifact_revision_invalid") from error
    if REVISION_SEGMENT_RE.fullmatch(segment) is None:
        raise ValueError("path_policy_pattern_invalid")
    return segment


def _pattern_tokens(pattern: str) -> list[str] | None:
    try:
        parsed = list(Formatter().parse(pattern))
    except ValueError:
        return None
    tokens = []
    for literal, field_name, format_spec, conversion in parsed:
        if "\\" in literal or "\x00" in literal or "{" in literal or "}" in literal or format_spec or conversion:
            return None
        if field_name is not None:
            if field_name not in ALLOWED_TOKENS:
                return None
            tokens.append(field_name)
    return tokens


def _pattern_structure_valid(pattern: str, tokens: list[str]) -> bool:
    segments = pattern.split("/")
    if not segments or any(not segment or segment in {".", ".."} for segment in segments):
        return False
    for segment in segments:
        segment_tokens = _pattern_tokens(segment)
        if segment_tokens is None:
            return False
        if not segment_tokens:
            if re.fullmatch(r"[a-z0-9-]+", segment) is None:
                return False
        elif len(segment_tokens) != 1:
            return False
        elif segment_tokens[0] in ID_TOKENS:
            if segment != "{" + segment_tokens[0] + "}":
                return False
        elif segment not in REVISION_TOKEN_SEGMENTS:
            return False
    return Counter(tokens)["artifact_revision"] == 1


def _safe_relative_path(value: str) -> str | None:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return "path_policy_backslash_forbidden"
    if value.startswith("/") or PurePosixPath(value).is_absolute():
        return "path_policy_absolute_path_forbidden"
    segments = value.split("/")
    if any(segment == "" for segment in segments):
        return "path_policy_empty_segment_forbidden"
    if any(segment in {".", ".."} for segment in segments):
        return "path_policy_traversal_forbidden"
    path = PurePosixPath(value)
    try:
        path.relative_to(ARTIFACT_ROOT)
    except ValueError:
        return "path_policy_outside_artifact_root"
    if path.name in FIXED_PATH_NAMES:
        return "path_policy_fixed_path_forbidden"
    return None


def _representative_values(identifier="sample", revision="r0001") -> dict[str, str]:
    return {
        "logical_id": identifier, "artifact_revision": revision,
        "subject_decision_id": identifier, "subject_plan_id": identifier,
        "subject_implementation_id": identifier, "subject_revision": revision,
    }


def validate_path_policy_registry(registry: Mapping[str, Any]) -> str | None:
    top = registry.get("path_policy", {})
    if top.get("artifact_root") != ARTIFACT_ROOT.as_posix() or top.get("accepted_versions") != ["path-policy-v1"]:
        return "path_policy_pattern_invalid"
    rendered_paths: dict[tuple[str, str], set[str]] = {}
    patterns: set[str] = set()
    if len(registry.get("artifact_types", {})) != 15:
        return "path_policy_artifact_type_unregistered"
    for artifact_type, entry in registry["artifact_types"].items():
        policy = entry.get("path_policy", {})
        pattern = policy.get("path_pattern")
        tokens = _pattern_tokens(pattern) if isinstance(pattern, str) else None
        if tokens is None or not tokens or not _pattern_structure_valid(pattern, tokens) or policy.get("path_policy_version") not in top["accepted_versions"]:
            return "path_policy_pattern_invalid"
        if any(token in {"status", "hash", "timestamp", "actor"} for token in tokens):
            return "path_policy_pattern_invalid"
        if policy.get("canonical_format") not in FORMAT_EXTENSIONS or FORMAT_EXTENSIONS[policy["canonical_format"]] != policy.get("extension"):
            return "path_policy_format_mismatch"
        variant = policy.get("subject_binding_variant")
        series_mode = policy.get("logical_series_identity")
        required_tokens = {
            "none": set(), "decision": {"subject_decision_id"},
            "plan": {"subject_plan_id", "subject_revision"},
            "implementation": {"subject_implementation_id", "subject_revision"},
        }.get(variant)
        if required_tokens is None or series_mode not in {"logical_id", "subject_id", "subject_id_revision"}:
            return "path_policy_subject_binding_variant_mismatch"
        expected_tokens = required_tokens | {"artifact_revision"}
        if series_mode == "logical_id":
            expected_tokens.add("logical_id")
        contract_tokens = policy.get("path_pattern_contract", {}).get("required_tokens", {})
        if Counter(tokens) != Counter(expected_tokens) or contract_tokens != {token: 1 for token in expected_tokens}:
            return "path_policy_subject_binding_variant_mismatch"
        if pattern in patterns:
            return "path_policy_pattern_collision"
        patterns.add(pattern)
        identifiers = ("a", "a-a", "sample", "sample-a", "a-sample", "x", "x-x", "a" * 64)
        revisions = ("r0001", "r9999", "r10000", f"r{MAX_REVISION}")
        for identifier in identifiers:
            for revision in revisions:
                key = (identifier, revision)
                rendered = f"{ARTIFACT_ROOT}/{pattern.format_map(_representative_values(identifier, revision))}"
                if _safe_relative_path(rendered):
                    return "path_policy_pattern_invalid"
                paths = rendered_paths.setdefault(key, set())
                if rendered in paths:
                    return "path_policy_pattern_collision"
                paths.add(rendered)
        if artifact_type != entry.get("artifact_type"):
            return "path_policy_artifact_type_unregistered"
    return None


def _logical_series(request: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    mode = policy["logical_series_identity"]
    binding = request["subject_binding"]
    if mode == "logical_id":
        return {"identity_type": "logical_id", "logical_artifact_id": request["logical_artifact_id"]}
    subject_type = binding["binding_type"]
    subject_key = {
        "decision": "subject_decision_id", "plan": "subject_plan_id",
        "implementation": "subject_implementation_id",
    }[subject_type]
    series = {"identity_type": mode, "subject_type": subject_type, "subject_id": binding[subject_key]}
    if mode == "subject_id_revision":
        series["subject_revision"] = binding["subject_revision"]
    return series


def _render_values(request: Mapping[str, Any], variant: str) -> dict[str, str]:
    values = {
        "logical_id": request["logical_artifact_id"],
        "artifact_revision": revision_segment(request["artifact_revision"]),
    }
    binding = request["subject_binding"]
    if variant == "decision":
        values["subject_decision_id"] = binding["subject_decision_id"]
        values["subject_revision"] = revision_segment(binding["subject_revision"])
    elif variant == "plan":
        values["subject_plan_id"] = binding["subject_plan_id"]
        values["subject_revision"] = revision_segment(binding["subject_revision"])
    elif variant == "implementation":
        values["subject_implementation_id"] = binding["subject_implementation_id"]
        values["subject_revision"] = revision_segment(binding["subject_revision"])
    return values


def derive_artifact_path(request: Mapping[str, Any]) -> PathPolicyResult:
    try:
        registry, schemas = _load_contracts()
        schemas["artifact-path-derivation-request.schema.yaml"].validate(request)
    except (ValidationError, ValueError, OSError, yaml.YAMLError):
        return _result("invalid", "path_derivation_request_invalid")
    artifact_type = request["artifact_type"]
    entry = registry["artifact_types"].get(artifact_type)
    if entry is None:
        return _result("blocked", "path_policy_artifact_type_unregistered")
    policy = entry["path_policy"]
    if request["path_policy_version"] != policy["path_policy_version"]:
        return _result("blocked", "path_policy_version_unregistered")
    if not is_valid_path_id(request["logical_artifact_id"]):
        return _result("blocked", "path_policy_logical_id_invalid")
    binding = request["subject_binding"]
    variant = policy["subject_binding_variant"]
    if binding.get("binding_type") != variant:
        return _result("blocked", "path_policy_subject_binding_variant_mismatch")
    for name, value in binding.items():
        if name.endswith("_id") and not is_valid_path_id(value):
            return _result("blocked", "path_policy_subject_identity_invalid")
    series_mode = policy["logical_series_identity"]
    if series_mode != "logical_id":
        subject_id_key = {"decision": "subject_decision_id", "plan": "subject_plan_id", "implementation": "subject_implementation_id"}[variant]
        expected_logical_id = binding[subject_id_key]
        if series_mode == "subject_id_revision":
            try:
                expected_logical_id = build_revision_scoped_logical_id(
                    expected_logical_id, binding["subject_revision"],
                )
            except ValueError:
                return _result("blocked", "path_policy_logical_series_identity_mismatch")
        if request["logical_artifact_id"] != expected_logical_id:
            return _result("blocked", "path_policy_logical_series_identity_mismatch")
    try:
        values = _render_values(request, variant)
        tokens = _pattern_tokens(policy["path_pattern"])
        if tokens is None or not set(tokens).issubset(values):
            return _result("invalid", "path_policy_pattern_invalid")
        repository_path = f"{ARTIFACT_ROOT}/{policy['path_pattern'].format_map(values)}"
    except (KeyError, ValueError):
        return _result("invalid", "path_policy_artifact_revision_invalid")
    path_error = _safe_relative_path(repository_path)
    if path_error:
        return _result("blocked", path_error)
    record = {
        "path_derivation_schema_version": "1.0",
        "path_policy_version": request["path_policy_version"],
        "artifact_type": artifact_type, "logical_artifact_id": request["logical_artifact_id"],
        "logical_series": _logical_series(request, policy),
        "artifact_revision": request["artifact_revision"], "subject_binding": dict(binding),
        "payload_format": policy["canonical_format"], "extension": policy["extension"],
        "repository_path": repository_path, "derivation_record_hash": "0" * 64,
    }
    record["derivation_record_hash"] = derivation_record_hash(record)
    try:
        schemas["artifact-path-derivation-result.schema.yaml"].validate(record)
    except ValidationError:
        return _result("invalid", "path_derivation_record_invalid")
    return _result("valid", "path_derived", record)


def validate_path_derivation_record(record: Mapping[str, Any]) -> PathPolicyResult:
    try:
        _, schemas = _load_contracts()
        schemas["artifact-path-derivation-result.schema.yaml"].validate(record)
    except (ValidationError, ValueError, OSError, yaml.YAMLError):
        return _result("invalid", "path_derivation_record_integrity_invalid")
    if derivation_record_hash(record) != record["derivation_record_hash"]:
        return _result("invalid", "path_derivation_record_integrity_invalid")
    request = {name: record[name] for name in (
        "path_policy_version", "artifact_type", "logical_artifact_id", "artifact_revision", "subject_binding"
    )}
    derived = derive_artifact_path(request)
    if derived.status != "valid" or dict(derived.path_derivation) != dict(record):
        return _result("blocked", "path_policy_claimed_path_mismatch")
    return _result("valid", "path_derivation_record_valid", record)


def validate_derived_artifact_path(request: Mapping[str, Any], claimed_repository_path: str) -> PathPolicyResult:
    error = _safe_relative_path(claimed_repository_path)
    if error:
        return _result("blocked", error)
    derived = derive_artifact_path(request)
    if derived.status != "valid":
        return derived
    if derived.path_derivation["repository_path"] != claimed_repository_path:
        return _result("blocked", "path_policy_claimed_path_mismatch")
    return _result("valid", "path_policy_claimed_path_valid", derived.path_derivation)
