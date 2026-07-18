"""Fail-closed, atomic validator for Development Harness Execute State patches."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from jsonschema import validators
from referencing import Registry, Resource


class ExecutionStatePatchError(ValueError):
    pass


EXACT_ALLOWLISTS = {
    "inspect-execution-context": {
        "/state", "/execution/current_skill", "/execution/context/artifact",
        "/execution/context/repository_revision", "/execution/context/design_lock_revision",
    },
    "implement": {
        "/state", "/execution/current_skill", "/execution/implementation/artifact",
        "/execution/implementation/revision", "/execution/implementation/changed_files",
        "/execution/implementation/snapshot_hash",
    },
    "review-implementation": {
        "/state", "/execution/current_skill", "/review/latest_result",
        "/review/latest_artifact", "/review/implementation_revision",
        "/review/reviewed_snapshot_hash",
    },
    "apply-scope-fix": {
        "/state", "/execution/current_skill", "/execution/implementation/artifact",
        "/execution/implementation/revision", "/execution/implementation/changed_files",
        "/execution/implementation/snapshot_hash",
    },
    "run-release-gate": {
        "/state", "/execution/current_skill", "/release_gate/result",
        "/release_gate/artifact", "/release_gate/implementation_revision",
        "/release_gate/checked_snapshot_hash", "/release_gate/secret_scan",
        "/release_gate/privacy_scan", "/release_gate/raw_source_scan",
    },
    "create-repository-publish-handoff": {
        "/state", "/execution/current_skill", "/repository_publish/handoff_reference",
        "/repository_publish/invocation_request_reference",
        "/repository_publish/repository_publish_run_id", "/repository_publish/status",
    },
}
COLLECTION_ALLOWLISTS = ("/warnings", "/blocking_issues")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ExecutionStatePatchError(message)


def _unresolved_issues(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [issue for issue in state["blocking_issues"] if issue["status"] in {"open", "resolving"}]


def _validate_entry_guard(
    guard: str, state: dict[str, Any], previous_state: str, *, interface_owned: bool = False
) -> None:
    """Validate semantic entry conditions. Runtime is the condition source of truth."""
    execution = state["execution"]
    implementation = execution["implementation"]
    review = state["review"]
    gate = state["release_gate"]
    publish = state["repository_publish"]
    unresolved = _unresolved_issues(state)

    if guard == "execution_started":
        return
    if guard == "execution_context_ready":
        context = execution["context"]
        _require(all(context[key] is not None for key in
                     ("artifact", "repository_revision", "design_lock_revision")),
                 "execution context is incomplete")
        _require(state["design_lock"]["status"] == "aligned", "Design Lock is not aligned")
        _require(not unresolved, "unresolved Blocking Issue prevents context readiness")
        return
    if guard == "implementation_completed":
        _require(implementation["artifact"] is not None, "implementation artifact is required")
        _require(implementation["revision"] is not None, "implementation revision is required")
        _require(bool(implementation["changed_files"]), "changed files must not be empty")
        _require(implementation["snapshot_hash"] is not None, "implementation snapshot hash is required")
        return
    if guard in {"changes_required", "review_accepted"}:
        expected = "changes_required" if guard == "changes_required" else "accepted"
        _require(review["latest_result"] == expected, f"review result must be {expected}")
        _require(review["latest_artifact"] is not None, "review artifact is required")
        _require(review["implementation_revision"] == implementation["revision"],
                 "review and implementation revisions differ")
        _require(review["reviewed_snapshot_hash"] == implementation["snapshot_hash"],
                 "review and implementation snapshot hashes differ")
        if guard == "review_accepted":
            _require(not unresolved, "unresolved Blocking Issue prevents review acceptance")
        return
    if guard == "fixing":
        count = execution["fix_cycle"]["attempt_count"]
        maximum = execution["fix_cycle"]["maximum_attempts"]
        _require(0 < count < maximum, "fix attempt count is outside the fixing range")
        if interface_owned:
            _require(previous_state in {"changes_required", "release_gate_failed"},
                     "fixing has an invalid source State")
        return
    if guard == "release_gate_failed":
        _require(gate["result"] == "failed", "Release Gate result must be failed")
        _require(gate["artifact"] is not None, "Release Gate artifact is required")
        _require(gate["implementation_revision"] == implementation["revision"],
                 "Release Gate and implementation revisions differ")
        _require(gate["checked_snapshot_hash"] is not None, "checked snapshot hash is required")
        scans = (gate["secret_scan"], gate["privacy_scan"], gate["raw_source_scan"])
        _require(any(scan == "failed" for scan in scans),
                 "failed Release Gate requires at least one failed scan")
        return
    if guard in {"release_gate_passed", "repository_publish_handoff_ready", "development_completed"}:
        _require(review["latest_result"] == "accepted", "accepted Review is required")
        _require(gate["result"] == "passed", "Release Gate result must be passed")
        _require(gate["artifact"] is not None, "Release Gate artifact is required")
        _require(gate["implementation_revision"] == implementation["revision"],
                 "Release Gate and implementation revisions differ")
        _require(review["implementation_revision"] == implementation["revision"],
                 "Review and implementation revisions differ")
        _require(gate["checked_snapshot_hash"] == review["reviewed_snapshot_hash"] == implementation["snapshot_hash"],
                 "Implementation, Review, and Release Gate hashes differ")
        _require(all(gate[key] == "passed" for key in
                     ("secret_scan", "privacy_scan", "raw_source_scan")),
                 "all Release Gate scans must be passed")
        _require(not unresolved, "unresolved Blocking Issue prevents Release Gate completion")
        if guard in {"repository_publish_handoff_ready", "development_completed"}:
            _require(publish["handoff_reference"] is not None, "handoff reference is required")
            _require(publish["invocation_request_reference"] is not None,
                     "invocation request reference is required")
            _require(publish["repository_publish_run_id"] is not None,
                     "Repository Publish run ID is required")
            _require(publish["status"] == "invocation_requested",
                     "Repository Publish invocation must be requested")
        if guard == "development_completed":
            _require(interface_owned and previous_state == "repository_publish_handoff_ready",
                     "development completion requires the handoff-ready Interface action")
        return
    if guard == "blocked":
        _require(bool(unresolved), "blocked State requires an unresolved Blocking Issue")
        return
    if guard == "aborted":
        _require(previous_state == "blocked" and bool(state["blocking_issues"]),
                 "aborted State requires an explicit blocking reason")
        return
    raise ExecutionStatePatchError(f"unknown entry guard: {guard}")


ENTRY_GUARDS = {
    "execution_started", "execution_context_ready", "implementation_completed",
    "changes_required", "fixing", "review_accepted", "release_gate_failed",
    "release_gate_passed", "repository_publish_handoff_ready", "development_completed",
    "blocked", "aborted",
}
INTERFACE_ACTIONS = {"increment_fix_attempt", "complete_execution"}


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_contracts() -> tuple[Any, Any, dict[str, Any]]:
    development = Path(__file__).resolve().parents[1]
    state_schema = _load_yaml(development / "schemas/execution-state.schema.yaml")
    patch_schema = _load_yaml(development / "shared/state-patch.schema.yaml")
    blocking_schema = _load_yaml(development / "shared/blocking-issue.schema.yaml")
    workflow = _load_yaml(development / "interfaces/execute/workflow.yaml")
    resources = [state_schema, patch_schema, blocking_schema]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in resources
    )
    state_cls = validators.validator_for(state_schema)
    patch_cls = validators.validator_for(patch_schema)
    for schema, cls in ((state_schema, state_cls), (patch_schema, patch_cls)):
        cls.check_schema(schema)
    return state_cls(state_schema, registry=registry), patch_cls(patch_schema, registry=registry), workflow


def _tokens(pointer: str) -> list[str]:
    if pointer in {"", "/"}:
        raise ExecutionStatePatchError("root replacement is forbidden")
    if not pointer.startswith("/"):
        raise ExecutionStatePatchError("invalid JSON Pointer")
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]


def _allowed(skill_id: str, path: str) -> bool:
    if path in EXACT_ALLOWLISTS.get(skill_id, set()):
        return True
    return any(path == prefix or path.startswith(prefix + "/") for prefix in COLLECTION_ALLOWLISTS)


def _parent(document: Any, pointer: str) -> tuple[Any, str]:
    tokens = _tokens(pointer)
    current = document
    for token in tokens[:-1]:
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError) as error:
                raise ExecutionStatePatchError(f"path does not exist: {pointer}") from error
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            raise ExecutionStatePatchError(f"path does not exist: {pointer}")
    return current, tokens[-1]


def _apply_operation(document: Any, operation: dict[str, Any]) -> None:
    parent, token = _parent(document, operation["path"])
    op = operation["op"]
    if isinstance(parent, list):
        if token == "-" and op == "add":
            parent.append(deepcopy(operation["value"]))
            return
        try:
            index = int(token)
        except ValueError as error:
            raise ExecutionStatePatchError("invalid array index") from error
        if op == "add":
            if index < 0 or index > len(parent):
                raise ExecutionStatePatchError("array index out of range")
            parent.insert(index, deepcopy(operation["value"]))
        elif 0 <= index < len(parent):
            if op == "replace":
                parent[index] = deepcopy(operation["value"])
            else:
                parent.pop(index)
        else:
            raise ExecutionStatePatchError("array index out of range")
        return
    if not isinstance(parent, dict):
        raise ExecutionStatePatchError("operation parent is not a container")
    if op == "add":
        parent[token] = deepcopy(operation["value"])
    elif token not in parent:
        raise ExecutionStatePatchError(f"path does not exist: {operation['path']}")
    elif op == "replace":
        parent[token] = deepcopy(operation["value"])
    else:
        del parent[token]


_MISSING = object()


def _read(document: Any, pointer: str) -> Any:
    current = document
    for token in _tokens(pointer):
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError):
                return _MISSING
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            return _MISSING
    return current


def _postcondition_holds(document: Any, condition: dict[str, Any]) -> bool:
    actual = _read(document, condition["path"])
    expected = condition.get("value", _MISSING)
    checks = {
        "equals": actual is not _MISSING and actual == expected,
        "not_equals": actual is _MISSING or actual != expected,
        "exists": actual is not _MISSING,
        "not_exists": actual is _MISSING,
        "not_null": actual is not _MISSING and actual is not None,
        "empty": actual is not _MISSING and actual in (None, "", [], {}),
        "not_empty": actual is not _MISSING and actual not in (None, "", [], {}),
    }
    return checks[condition["type"]]


def validate_and_apply_execution_patch(
    current_state: dict[str, Any], patch_document: dict[str, Any], invoked_skill: str
) -> dict[str, Any]:
    """Return a validated new State; current_state is never mutated."""
    state_validator, patch_validator, workflow = load_contracts()
    state_validator.validate(current_state)
    current_name = current_state["state"]
    if current_name not in workflow["states"]:
        raise ExecutionStatePatchError("current State is absent from Execute Workflow")
    state_contract = workflow["states"][current_name]
    current_guard = state_contract.get("entry_guard")
    if current_guard is None:
        raise ExecutionStatePatchError("current State has no entry guard")
    # `fixing` always validates its persisted counter range. Its source-State
    # condition is additionally validated only when the Interface enters it.
    _validate_entry_guard(current_guard, current_state, current_name)
    if "interface_action" in state_contract:
        raise ExecutionStatePatchError("Interface Action State rejects Skill patches")
    primary_skill = state_contract.get("primary_skill")
    if primary_skill != invoked_skill:
        raise ExecutionStatePatchError("invoked Skill is not the current State's primary Skill")
    patch_validator.validate(patch_document)
    patch = patch_document["patch"]
    if patch["target"] != "execution-state" or patch["source"]["interface"] != "execute":
        raise ExecutionStatePatchError("patch target/source is not Execute State")
    if patch["source"]["skill_id"] != invoked_skill:
        raise ExecutionStatePatchError("Skill ID does not match invoked Skill")
    if invoked_skill not in EXACT_ALLOWLISTS:
        raise ExecutionStatePatchError("unknown Execute Skill")
    if patch["expected"]["revision"] != current_state["revision"]:
        raise ExecutionStatePatchError("expected revision mismatch")
    if patch["expected"]["workflow_state"] != current_state["state"]:
        raise ExecutionStatePatchError("expected workflow state mismatch")
    for operation in patch["operations"]:
        path = operation["path"]
        if path == "/revision" or path.startswith("/revision/"):
            raise ExecutionStatePatchError("Skill may not modify revision")
        if not _allowed(invoked_skill, path):
            raise ExecutionStatePatchError(f"path is outside Skill allowlist: {path}")
    candidate = deepcopy(current_state)
    for operation in patch["operations"]:
        _apply_operation(candidate, operation)
    candidate["revision"] = current_state["revision"] + 1
    transition = patch["requested_transition"]
    if transition is not None:
        if transition["from"] != current_state["state"]:
            raise ExecutionStatePatchError("requested transition source mismatch")
        transitions = state_contract.get("transitions", {})
        if transition["to"] not in transitions.values():
            raise ExecutionStatePatchError("requested transition is not allowed")
        if candidate["state"] != transition["to"]:
            raise ExecutionStatePatchError("candidate State does not match transition destination")
    elif candidate["state"] != current_state["state"]:
        raise ExecutionStatePatchError("State changed without requested transition")
    state_validator.validate(candidate)
    if not all(_postcondition_holds(candidate, condition) for condition in patch["postconditions"]):
        raise ExecutionStatePatchError("postcondition failed")
    guard = workflow["states"][candidate["state"]].get("entry_guard")
    if guard is None:
        raise ExecutionStatePatchError("destination State has no entry guard")
    _validate_entry_guard(guard, candidate, current_name)
    return candidate


def _fix_attempt_issue(state_name: str, count: int, issues: list[dict[str, Any]]) -> dict[str, Any]:
    numeric_ids = [int(issue["id"].split("-", 1)[1]) for issue in issues
                   if issue.get("id", "").startswith("BI-") and issue["id"][3:].isdigit()]
    issue_id = f"BI-{max([8999, *numeric_ids]) + 1:04d}"
    return {
        "id": issue_id, "code": "FIX_ATTEMPT_LIMIT_REACHED",
        "title": "Fix attempt limit reached", "category": "workflow", "severity": "high",
        "source": {"interface": "execute", "skill_id": None, "phase": state_name},
        "description": "The Execute fix-cycle attempt limit was reached.",
        "evidence": {"references": [], "observed": [f"attempt_count reached {count}."],
                     "expected": ["A Review acceptance before the maximum attempt count."]},
        "violated_invariants": [], "affected_artifacts": [],
        "resolution": {"required_action": "request_human_decision", "responsible_role": "human",
                       "resumable": False, "resume_condition": "A human selects a recovery action."},
        "status": "open", "created_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None, "extensions": {},
    }


def apply_interface_action(current_state: dict[str, Any], action: str) -> dict[str, Any]:
    """Apply a named Interface action atomically; callers never select its destination."""
    state_validator, _, workflow = load_contracts()
    if action not in INTERFACE_ACTIONS:
        raise ExecutionStatePatchError(f"unsupported Interface action: {action}")
    state_validator.validate(current_state)
    previous_state = current_state["state"]
    if previous_state not in workflow["states"]:
        raise ExecutionStatePatchError("current State is absent from Execute Workflow")
    state_contract = workflow["states"][previous_state]
    current_guard = state_contract.get("entry_guard")
    if current_guard is None:
        raise ExecutionStatePatchError("current State has no entry guard")
    _validate_entry_guard(current_guard, current_state, previous_state)
    if state_contract.get("interface_action") != action:
        raise ExecutionStatePatchError("action is not owned by the current Execute State")
    candidate = deepcopy(current_state)
    if action == "increment_fix_attempt":
        cycle = candidate["execution"]["fix_cycle"]
        new_count = cycle["attempt_count"] + 1
        if new_count > cycle["maximum_attempts"]:
            raise ExecutionStatePatchError("fix attempt limit was already reached")
        cycle["attempt_count"] = new_count
        if new_count < cycle["maximum_attempts"]:
            transition_name = "attempts_available"
        else:
            transition_name = "attempt_limit_reached"
            candidate["blocking_issues"].append(
                _fix_attempt_issue(previous_state, new_count, candidate["blocking_issues"])
            )
    elif action == "complete_execution":
        transition_name = "development_completed"
    transitions = state_contract.get("transitions", {})
    if transition_name not in transitions:
        raise ExecutionStatePatchError("Interface action transition is absent from Workflow")
    destination = transitions[transition_name]
    candidate["state"] = destination
    candidate["revision"] = current_state["revision"] + 1
    guard = workflow["states"][destination].get("entry_guard")
    if guard is None:
        raise ExecutionStatePatchError("destination State has no entry guard")
    _validate_entry_guard(guard, candidate, previous_state, interface_owned=True)
    state_validator.validate(candidate)
    return candidate
