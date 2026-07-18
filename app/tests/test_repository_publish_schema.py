from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest
import yaml
from jsonschema import validators
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / ".codex/harness/development/schemas"
SHARED_DIR = ROOT / ".codex/harness/development/shared"
AGENT_SHARED_DIR = ROOT / ".codex/agents/repository-publish/shared"
TOOL_PATH = ROOT / ".codex/tools/repository_snapshot/build_snapshot.py"
SPEC = importlib.util.spec_from_file_location("repository_snapshot_schema", TOOL_PATH)
assert SPEC and SPEC.loader
snapshot_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot_tool)


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


SCHEMAS = [
    load(SCHEMA_DIR / "execution-state.schema.yaml"),
    load(SCHEMA_DIR / "repository-publish-handoff.schema.yaml"),
    load(SHARED_DIR / "blocking-issue.schema.yaml"),
    load(AGENT_SHARED_DIR / "agent-invocation-result.schema.yaml"),
]
REGISTRY = Registry().with_resources(
    (schema["$id"], Resource.from_contents(schema)) for schema in SCHEMAS
)


def validator(schema_name: str):
    schema = next(item for item in SCHEMAS if item["title"] == schema_name)
    cls = validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema, registry=REGISTRY)


HASH = "a" * 64


def valid_handoff():
    run_id = snapshot_tool.repository_publish_run_id("owner/repo", "main", "feature/x", HASH, 1)
    return {
        "schema_version": "1.0", "target_agent": "repository-publish", "handoff_revision": 1,
        "repository_publish_run_id": run_id,
        "release_gate": {"status": "passed", "artifact_path": "artifacts/RELEASE_GATE.md",
                         "design_lock_revision": 2, "implementation_revision": 3,
                         "reviewed_diff_hash": HASH, "checked_diff_hash": HASH},
        "repository": {"id": "owner/repo", "base_branch": "main", "working_branch": "feature/x"},
        "publish_scope": {"included_paths": ["src/example.py"], "excluded_paths": [],
                          "expected_changed_files": ["src/example.py"]},
        "commit": {"message": "Add example", "summary": "Adds example."},
        "pull_request": {"title": "Add example", "body_context": {"summary": "Adds example.",
                         "implementation": ["Added example"], "validation": ["pytest passed"],
                         "known_constraints": [], "warnings": [],
                         "references": ["artifacts/RELEASE_GATE.md"]}, "draft": True},
        "blocking_issues": [], "warnings": [],
        "next_action": {"type": "invoke_agent", "target": "repository-publish",
                        "handoff_reference": "artifacts/repository-publish-handoff.yaml",
                        "repository_publish_run_id": run_id, "automatic": True,
                        "requires_human_confirmation": False,
                        "on_invocation_failure": "invocation_failed",
                        "deduplication_key": "repository_publish_run_id"},
    }


def valid_execution_state(handoff):
    return {
        "schema_version": "1.0", "epic": "EPIC-1", "state": "development_completed", "revision": 4,
        "design_lock": {"status": "aligned", "path": "DESIGN_LOCK.md", "revision": 2},
        "execution": {"current_skill": None, "changed_files": ["src/example.py"],
                      "fix_cycle": {"attempt_count": 0, "maximum_attempts": 5}},
        "review": {"latest_result": "accepted", "latest_artifact": "REVIEW.md"},
        "release_gate": {"result": "passed", "artifact": "RELEASE_GATE.md", "secret_scan": "passed",
                         "privacy_scan": "passed", "raw_source_scan": "passed"},
        "downstream": {"agent": "repository-publish", "handoff_reference": "handoff.yaml",
                       "run_id": handoff["repository_publish_run_id"], "status": "invocation_requested",
                       "result_reference": None, "next_action": handoff["next_action"]},
        "blocking_issues": [], "warnings": [], "extensions": {},
    }


def test_draft_2020_12_schemas_refs_and_valid_samples() -> None:
    for schema in SCHEMAS:
        validators.validator_for(schema).check_schema(schema)
    handoff = valid_handoff()
    validator("Repository Publish Handoff").validate(handoff)
    snapshot_tool.validate_handoff_cross_fields(handoff)
    validator("Development Harness Execution State").validate(valid_execution_state(handoff))


@pytest.mark.parametrize("mutation", [
    lambda value: value["release_gate"].update(status="failed"),
    lambda value: value.pop("commit"),
    lambda value: value.update(unknown=True),
    lambda value: value["blocking_issues"].append({"code": "BLOCKED"}),
    lambda value: value["publish_scope"].update(included_paths=[]),
])
def test_handoff_schema_rejects_invalid_samples(mutation) -> None:
    value = valid_handoff()
    mutation(value)
    with pytest.raises(ValidationError):
        validator("Repository Publish Handoff").validate(value)


@pytest.mark.parametrize("mutation", [
    lambda value: value["repository"].update(working_branch="main"),
    lambda value: value["release_gate"].update(checked_diff_hash="b" * 64),
])
def test_runtime_guards_reject_cross_field_mismatch(mutation) -> None:
    value = valid_handoff()
    mutation(value)
    validator("Repository Publish Handoff").validate(value)
    with pytest.raises(snapshot_tool.SnapshotError):
        snapshot_tool.validate_handoff_cross_fields(value)


def test_execution_schema_rejects_unknown_state_and_field() -> None:
    handoff = valid_handoff()
    state = valid_execution_state(handoff)
    state["state"] = "completed"
    with pytest.raises(ValidationError):
        validator("Development Harness Execution State").validate(state)
    state = valid_execution_state(handoff)
    state["downstream"]["commit_sha"] = "0" * 40
    with pytest.raises(ValidationError):
        validator("Development Harness Execution State").validate(state)


def test_router_owned_invocation_result_success_and_failure() -> None:
    invocation_validator = validator("Repository Publish Agent Invocation Result")
    base = {"schema_version": "1.0", "target_agent": "repository-publish",
            "repository_publish_run_id": "rpr-" + "a" * 64, "handoff_reference": "handoff.yaml",
            "result_reference": None}
    invocation_validator.validate({**base, "status": "invoked", "error_code": None})
    invocation_validator.validate({**base, "status": "invocation_failed", "error_code": "AGENT_START_FAILED"})
    with pytest.raises(ValidationError):
        invocation_validator.validate({**base, "status": "invocation_failed", "error_code": None})
