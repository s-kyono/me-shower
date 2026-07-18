from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest
import yaml
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / ".codex/harness/development/shared/execution_state_patch.py"
SPEC = importlib.util.spec_from_file_location("execution_state_patch", MODULE_PATH)
assert SPEC and SPEC.loader
patch_runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patch_runtime)

HASH_A = "a" * 64
HASH_B = "b" * 64
REVISION = "0" * 40
RUN_ID = "rpr-" + "c" * 64


def blocking_issue() -> dict:
    return {
        "id": "BI-1000", "code": "MANUAL_RECOVERY", "title": "Manual recovery required",
        "category": "human_decision", "severity": "high",
        "source": {"interface": "execute", "skill_id": None, "phase": "blocked"},
        "description": "A human must select a recovery action.",
        "evidence": {"references": [], "observed": ["Execution is blocked."], "expected": []},
        "violated_invariants": [], "affected_artifacts": [],
        "resolution": {"required_action": "request_human_decision", "responsible_role": "human",
                       "resumable": True, "resume_condition": "A valid recovery action is selected."},
        "status": "open", "created_at": "2026-07-18T00:00:00Z", "resolved_at": None,
        "extensions": {},
    }


def state(workflow_state: str = "execution_started") -> dict:
    return {
        "schema_version": "1.0", "epic": "EPIC-1", "state": workflow_state, "revision": 0,
        "design_lock": {"status": "aligned", "path": "DESIGN_LOCK.md", "revision": 1},
        "execution": {
            "current_skill": None,
            "context": {"artifact": None, "repository_revision": None, "design_lock_revision": None},
            "implementation": {"artifact": None, "revision": None, "changed_files": [], "snapshot_hash": None},
            "fix_cycle": {"attempt_count": 0, "maximum_attempts": 5},
        },
        "review": {"latest_result": None, "latest_artifact": None,
                   "implementation_revision": None, "reviewed_snapshot_hash": None},
        "release_gate": {"result": None, "artifact": None, "implementation_revision": None,
                         "checked_snapshot_hash": None, "secret_scan": None,
                         "privacy_scan": None, "raw_source_scan": None},
        "repository_publish": {"handoff_reference": None, "invocation_request_reference": None,
                               "repository_publish_run_id": None, "status": "not_ready"},
        "blocking_issues": [], "warnings": [], "extensions": {},
    }


def ready_for_implementation() -> dict:
    value = state("execution_context_ready")
    value["execution"]["context"] = {"artifact": "context.yaml", "repository_revision": REVISION,
                                       "design_lock_revision": 1}
    return value


def implemented(workflow_state: str = "implementation_completed", revision: int = 1, digest: str = HASH_A) -> dict:
    value = ready_for_implementation()
    value["state"] = workflow_state
    value["execution"]["implementation"] = {
        "artifact": f"implementation-{revision}.yaml", "revision": revision,
        "changed_files": ["src/example.py"], "snapshot_hash": digest,
    }
    return value


def reviewed(workflow_state: str = "review_accepted") -> dict:
    value = implemented(workflow_state)
    value["review"] = {"latest_result": "accepted", "latest_artifact": "REVIEW.md",
                       "implementation_revision": 1, "reviewed_snapshot_hash": HASH_A}
    return value


def changes_required(workflow_state: str = "changes_required", attempts: int = 0) -> dict:
    value = implemented(workflow_state)
    value["execution"]["fix_cycle"]["attempt_count"] = attempts
    value["review"] = {"latest_result": "changes_required", "latest_artifact": "REVIEW.md",
                       "implementation_revision": 1, "reviewed_snapshot_hash": HASH_A}
    return value


def gate_failed(attempts: int = 0) -> dict:
    value = reviewed("release_gate_failed")
    value["execution"]["fix_cycle"]["attempt_count"] = attempts
    value["release_gate"] = {"result": "failed", "artifact": "RELEASE_GATE.md",
                             "implementation_revision": 1, "checked_snapshot_hash": HASH_A,
                             "secret_scan": "failed", "privacy_scan": "passed",
                             "raw_source_scan": "passed"}
    return value


def patch(skill: str, current: dict, destination: str, operations: list[dict]) -> dict:
    return {
        "schema_version": "1.0",
        "patch": {
            "id": "SP-1000", "target": "execution-state",
            "expected": {"revision": current["revision"], "workflow_state": current["state"]},
            "source": {"interface": "execute", "skill_id": skill}, "intent": "test transition",
            "operations": operations + [{"op": "replace", "path": "/state", "value": destination}],
            "postconditions": [{"type": "equals", "path": "/state", "value": destination}],
            "requested_transition": {"from": current["state"], "to": destination},
            "risk": {"level": "low", "touches_human_approval": False, "touches_design_lock": False,
                     "touches_source_of_truth": False, "touches_persistence_boundary": False,
                     "touches_security_boundary": False},
            "extensions": {},
        },
    }


def apply(current: dict, document: dict, skill: str) -> dict:
    return patch_runtime.validate_and_apply_execution_patch(current, document, skill)


def test_inspect_execution_context_completed() -> None:
    current = state()
    result = apply(current, patch("inspect-execution-context", current, "execution_context_ready", [
        {"op": "replace", "path": "/execution/current_skill", "value": "inspect-execution-context"},
        {"op": "replace", "path": "/execution/context/artifact", "value": "context.yaml"},
        {"op": "replace", "path": "/execution/context/repository_revision", "value": REVISION},
        {"op": "replace", "path": "/execution/context/design_lock_revision", "value": 1},
    ]), "inspect-execution-context")
    assert result["state"] == "execution_context_ready" and result["revision"] == 1


def implementation_operations(revision: int = 1, digest: str = HASH_A, skill: str = "implement"):
    return [
        {"op": "replace", "path": "/execution/current_skill", "value": skill},
        {"op": "replace", "path": "/execution/implementation/artifact", "value": f"implementation-{revision}.yaml"},
        {"op": "replace", "path": "/execution/implementation/revision", "value": revision},
        {"op": "replace", "path": "/execution/implementation/changed_files", "value": ["src/example.py"]},
        {"op": "replace", "path": "/execution/implementation/snapshot_hash", "value": digest},
    ]


def test_implement_completed() -> None:
    current = ready_for_implementation()
    result = apply(current, patch("implement", current, "implementation_completed", implementation_operations()), "implement")
    assert result["execution"]["implementation"]["snapshot_hash"] == HASH_A


@pytest.mark.parametrize(("decision", "destination"), [("accepted", "review_accepted"),
                                                         ("changes_required", "changes_required")])
def test_review_results(decision: str, destination: str) -> None:
    current = implemented()
    document = patch("review-implementation", current, destination, [
        {"op": "replace", "path": "/execution/current_skill", "value": "review-implementation"},
        {"op": "replace", "path": "/review/latest_result", "value": decision},
        {"op": "replace", "path": "/review/latest_artifact", "value": "REVIEW.md"},
        {"op": "replace", "path": "/review/implementation_revision", "value": 1},
        {"op": "replace", "path": "/review/reviewed_snapshot_hash", "value": HASH_A},
    ])
    assert apply(current, document, "review-implementation")["review"]["latest_result"] == decision


def test_apply_scope_fix_completed() -> None:
    current = implemented("fixing")
    current["execution"]["fix_cycle"]["attempt_count"] = 1
    current["review"] = {"latest_result": "changes_required", "latest_artifact": "REVIEW.md",
                         "implementation_revision": 1, "reviewed_snapshot_hash": HASH_A}
    result = apply(current, patch("apply-scope-fix", current, "implementation_completed",
                                  implementation_operations(2, HASH_B, "apply-scope-fix")), "apply-scope-fix")
    assert result["execution"]["implementation"]["revision"] == 2
    assert result["review"]["latest_result"] == "changes_required"


@pytest.mark.parametrize("attempt_count", [0, 5, -1])
def test_persisted_fixing_rejects_invalid_attempt_count_atomically(attempt_count: int) -> None:
    current = changes_required("fixing", attempts=attempt_count)
    document = patch("apply-scope-fix", current, "implementation_completed",
                     implementation_operations(2, HASH_B, "apply-scope-fix"))
    assert_rejected_without_mutation(current, document, "apply-scope-fix")


@pytest.mark.parametrize(("decision", "destination"), [("passed", "release_gate_passed"),
                                                         ("failed", "release_gate_failed")])
def test_release_gate_results(decision: str, destination: str) -> None:
    current = reviewed()
    document = patch("run-release-gate", current, destination, [
        {"op": "replace", "path": "/execution/current_skill", "value": "run-release-gate"},
        {"op": "replace", "path": "/release_gate/result", "value": decision},
        {"op": "replace", "path": "/release_gate/artifact", "value": "RELEASE_GATE.md"},
        {"op": "replace", "path": "/release_gate/implementation_revision", "value": 1},
        {"op": "replace", "path": "/release_gate/checked_snapshot_hash", "value": HASH_A},
        {"op": "replace", "path": "/release_gate/secret_scan", "value":
         "passed" if decision == "passed" else "failed"},
        {"op": "replace", "path": "/release_gate/privacy_scan", "value": "passed"},
        {"op": "replace", "path": "/release_gate/raw_source_scan", "value": "passed"},
    ])
    assert apply(current, document, "run-release-gate")["release_gate"]["result"] == decision


def release_passed() -> dict:
    value = reviewed("release_gate_passed")
    value["release_gate"] = {"result": "passed", "artifact": "RELEASE_GATE.md",
                             "implementation_revision": 1, "checked_snapshot_hash": HASH_A,
                             "secret_scan": "passed", "privacy_scan": "passed", "raw_source_scan": "passed"}
    return value


def test_handoff_completed_and_development_completed() -> None:
    current = release_passed()
    handoff = patch("create-repository-publish-handoff", current, "repository_publish_handoff_ready", [
        {"op": "replace", "path": "/execution/current_skill", "value": "create-repository-publish-handoff"},
        {"op": "replace", "path": "/repository_publish/handoff_reference", "value": "handoff.yaml"},
        {"op": "replace", "path": "/repository_publish/invocation_request_reference", "value": "invocation.yaml"},
        {"op": "replace", "path": "/repository_publish/repository_publish_run_id", "value": RUN_ID},
        {"op": "replace", "path": "/repository_publish/status", "value": "invocation_requested"},
    ])
    ready = apply(current, handoff, "create-repository-publish-handoff")
    completed = patch_runtime.apply_interface_action(ready, "complete_execution")
    assert completed["state"] == "development_completed" and completed["revision"] == ready["revision"] + 1


def test_interface_transition_cannot_bypass_human_owned_transition() -> None:
    current = state("blocked")
    current["blocking_issues"] = [blocking_issue()]
    with pytest.raises(patch_runtime.ExecutionStatePatchError, match="not owned"):
        patch_runtime.apply_interface_action(current, "complete_execution")


def test_every_exact_allowlist_path_exists_in_execution_state() -> None:
    current = state()
    for paths in patch_runtime.EXACT_ALLOWLISTS.values():
        for path in paths:
            assert patch_runtime._read(current, path) is not patch_runtime._MISSING, path


def assert_rejected_without_mutation(current: dict, document: dict, skill: str) -> None:
    before = deepcopy(current)
    with pytest.raises((patch_runtime.ExecutionStatePatchError, ValidationError)):
        apply(current, document, skill)
    assert current == before


def test_expected_revision_workflow_and_skill_mismatch_are_atomic() -> None:
    current = ready_for_implementation()
    base = patch("implement", current, "implementation_completed", implementation_operations())
    wrong_revision = deepcopy(base); wrong_revision["patch"]["expected"]["revision"] = 99
    wrong_state = deepcopy(base); wrong_state["patch"]["expected"]["workflow_state"] = "fixing"
    wrong_skill = deepcopy(base); wrong_skill["patch"]["source"]["skill_id"] = "review-implementation"
    for document in (wrong_revision, wrong_state, wrong_skill):
        assert_rejected_without_mutation(current, document, "implement")


def test_primary_skill_and_interface_action_state_are_enforced() -> None:
    fixing = changes_required("fixing", attempts=1)
    wrong_fix_skill = patch("implement", fixing, "implementation_completed",
                            implementation_operations(2, HASH_B))
    assert_rejected_without_mutation(fixing, wrong_fix_skill, "implement")

    review_state = implemented()
    wrong_review_skill = patch("implement", review_state, "review_accepted",
                               implementation_operations(2, HASH_B))
    assert_rejected_without_mutation(review_state, wrong_review_skill, "implement")

    action_state = changes_required()
    skill_patch = patch("apply-scope-fix", action_state, "fixing", implementation_operations(
        2, HASH_B, "apply-scope-fix"))
    assert_rejected_without_mutation(action_state, skill_patch, "apply-scope-fix")


@pytest.mark.parametrize("factory", [changes_required, gate_failed])
def test_increment_fix_attempt_selects_destination_and_is_atomic(factory) -> None:
    current = factory(attempts=0)
    result = patch_runtime.apply_interface_action(current, "increment_fix_attempt")
    assert result["state"] == "fixing"
    assert result["execution"]["fix_cycle"]["attempt_count"] == 1
    assert current["execution"]["fix_cycle"]["attempt_count"] == 0

    current = factory(attempts=4)
    result = patch_runtime.apply_interface_action(current, "increment_fix_attempt")
    assert result["state"] == "blocked"
    assert result["execution"]["fix_cycle"]["attempt_count"] == 5
    assert result["blocking_issues"][0]["code"] == "FIX_ATTEMPT_LIMIT_REACHED"
    assert current["execution"]["fix_cycle"]["attempt_count"] == 4

    before = deepcopy(result)
    with pytest.raises(patch_runtime.ExecutionStatePatchError):
        patch_runtime.apply_interface_action(result, "increment_fix_attempt")
    assert result == before


def test_interface_action_callers_cannot_select_destination() -> None:
    with pytest.raises(TypeError):
        patch_runtime.apply_interface_action(changes_required(), "increment_fix_attempt", "fixing")


def _replace_value(document: dict, path: str, value) -> None:
    operation = next(item for item in document["patch"]["operations"] if item["path"] == path)
    operation["value"] = value


@pytest.mark.parametrize(("path", "value"), [
    ("/execution/context/artifact", None),
    ("/execution/context/repository_revision", None),
    ("/execution/context/design_lock_revision", None),
])
def test_context_ready_fixed_guard_rejects_incomplete_context(path, value) -> None:
    current = state()
    document = patch("inspect-execution-context", current, "execution_context_ready", [
        {"op": "replace", "path": "/execution/current_skill", "value": "inspect-execution-context"},
        {"op": "replace", "path": "/execution/context/artifact", "value": "context.yaml"},
        {"op": "replace", "path": "/execution/context/repository_revision", "value": REVISION},
        {"op": "replace", "path": "/execution/context/design_lock_revision", "value": 1},
    ])
    _replace_value(document, path, value)
    assert_rejected_without_mutation(current, document, "inspect-execution-context")


@pytest.mark.parametrize(("path", "value"), [
    ("/execution/implementation/artifact", None),
    ("/execution/implementation/revision", None),
    ("/execution/implementation/changed_files", []),
    ("/execution/implementation/snapshot_hash", None),
])
def test_implementation_completed_fixed_guard_rejects_incomplete_state(path, value) -> None:
    current = ready_for_implementation()
    document = patch("implement", current, "implementation_completed", implementation_operations())
    _replace_value(document, path, value)
    assert_rejected_without_mutation(current, document, "implement")


@pytest.mark.parametrize(("path", "value"), [
    ("/review/latest_artifact", None),
    ("/review/implementation_revision", 2),
    ("/review/reviewed_snapshot_hash", HASH_B),
])
def test_review_fixed_guards_reject_inconsistent_state(path, value) -> None:
    current = implemented()
    document = patch("review-implementation", current, "review_accepted", [
        {"op": "replace", "path": "/execution/current_skill", "value": "review-implementation"},
        {"op": "replace", "path": "/review/latest_result", "value": "accepted"},
        {"op": "replace", "path": "/review/latest_artifact", "value": "REVIEW.md"},
        {"op": "replace", "path": "/review/implementation_revision", "value": 1},
        {"op": "replace", "path": "/review/reviewed_snapshot_hash", "value": HASH_A},
    ])
    _replace_value(document, path, value)
    assert_rejected_without_mutation(current, document, "review-implementation")


def gate_document(current: dict, decision: str = "passed") -> dict:
    destination = "release_gate_passed" if decision == "passed" else "release_gate_failed"
    return patch("run-release-gate", current, destination, [
        {"op": "replace", "path": "/execution/current_skill", "value": "run-release-gate"},
        {"op": "replace", "path": "/release_gate/result", "value": decision},
        {"op": "replace", "path": "/release_gate/artifact", "value": "RELEASE_GATE.md"},
        {"op": "replace", "path": "/release_gate/implementation_revision", "value": 1},
        {"op": "replace", "path": "/release_gate/checked_snapshot_hash", "value": HASH_A},
        {"op": "replace", "path": "/release_gate/secret_scan",
         "value": "passed" if decision == "passed" else "failed"},
        {"op": "replace", "path": "/release_gate/privacy_scan", "value": "passed"},
        {"op": "replace", "path": "/release_gate/raw_source_scan", "value": "passed"},
    ])


@pytest.mark.parametrize(("decision", "path", "value"), [
    ("failed", "/release_gate/secret_scan", "passed"),
    ("passed", "/release_gate/privacy_scan", "failed"),
    ("passed", "/release_gate/implementation_revision", 2),
    ("passed", "/release_gate/checked_snapshot_hash", HASH_B),
])
def test_release_gate_fixed_guards_reject_inconsistent_state(decision, path, value) -> None:
    current = reviewed()
    document = gate_document(current, decision)
    _replace_value(document, path, value)
    assert_rejected_without_mutation(current, document, "run-release-gate")


def test_release_gate_failed_rejects_all_passed_even_with_blocking_issue() -> None:
    current = reviewed()
    document = gate_document(current, "failed")
    _replace_value(document, "/release_gate/secret_scan", "passed")
    document["patch"]["operations"].insert(
        -1, {"op": "add", "path": "/blocking_issues/-", "value": blocking_issue()}
    )
    assert_rejected_without_mutation(current, document, "run-release-gate")


def test_release_gate_failed_rejects_blocked_scan_and_accepts_failed_scan() -> None:
    current = reviewed()
    blocked = gate_document(current, "failed")
    _replace_value(blocked, "/release_gate/secret_scan", "blocked")
    assert_rejected_without_mutation(current, blocked, "run-release-gate")

    blocked_result = gate_document(current, "failed")
    _replace_value(blocked_result, "/release_gate/result", "blocked")
    _replace_value(blocked_result, "/release_gate/secret_scan", "blocked")
    _replace_value(blocked_result, "/state", "blocked")
    blocked_result["patch"]["requested_transition"]["to"] = "blocked"
    blocked_result["patch"]["postconditions"][0]["value"] = "blocked"
    blocked_result["patch"]["operations"].insert(
        -1, {"op": "add", "path": "/blocking_issues/-", "value": blocking_issue()}
    )
    result = apply(current, blocked_result, "run-release-gate")
    assert result["state"] == "blocked"
    assert result["release_gate"]["secret_scan"] == "blocked"

    failed = gate_document(current, "failed")
    result = apply(current, failed, "run-release-gate")
    assert result["state"] == "release_gate_failed"
    assert result["release_gate"]["secret_scan"] == "failed"


def test_empty_postcondition_and_fixed_guard_failure_are_atomic() -> None:
    current = ready_for_implementation()
    document = patch("implement", current, "implementation_completed", implementation_operations())
    document["patch"]["postconditions"] = []
    assert_rejected_without_mutation(current, document, "implement")

    document = patch("implement", current, "implementation_completed", implementation_operations())
    _replace_value(document, "/execution/implementation/artifact", None)
    assert document["patch"]["postconditions"][0]["value"] == "implementation_completed"
    assert_rejected_without_mutation(current, document, "implement")


def test_release_gate_passed_rejects_unresolved_blocking_issue() -> None:
    current = reviewed()
    current["blocking_issues"] = [blocking_issue()]
    assert_rejected_without_mutation(current, gate_document(current), "run-release-gate")


def handoff_document(current: dict) -> dict:
    return patch("create-repository-publish-handoff", current, "repository_publish_handoff_ready", [
        {"op": "replace", "path": "/execution/current_skill", "value":
         "create-repository-publish-handoff"},
        {"op": "replace", "path": "/repository_publish/handoff_reference", "value": "handoff.yaml"},
        {"op": "replace", "path": "/repository_publish/invocation_request_reference",
         "value": "invocation.yaml"},
        {"op": "replace", "path": "/repository_publish/repository_publish_run_id", "value": RUN_ID},
        {"op": "replace", "path": "/repository_publish/status", "value": "invocation_requested"},
    ])


@pytest.mark.parametrize("path", [
    "/repository_publish/handoff_reference",
    "/repository_publish/invocation_request_reference",
    "/repository_publish/repository_publish_run_id",
])
def test_handoff_ready_rejects_missing_reference(path) -> None:
    current = release_passed()
    document = handoff_document(current)
    _replace_value(document, path, None)
    assert_rejected_without_mutation(current, document, "create-repository-publish-handoff")


@pytest.mark.parametrize("field", [
    "handoff_reference", "invocation_request_reference", "repository_publish_run_id",
])
def test_development_completed_rejects_missing_handoff_reference(field) -> None:
    current = release_passed()
    ready = apply(current, handoff_document(current), "create-repository-publish-handoff")
    ready["repository_publish"][field] = None
    before = deepcopy(ready)
    with pytest.raises((patch_runtime.ExecutionStatePatchError, ValidationError)):
        patch_runtime.apply_interface_action(ready, "complete_execution")
    assert ready == before


def test_blocked_and_aborted_guards_require_explicit_reason() -> None:
    current = state()
    document = patch("inspect-execution-context", current, "blocked", [])
    assert_rejected_without_mutation(current, document, "inspect-execution-context")

    aborted = state("aborted")
    with pytest.raises(patch_runtime.ExecutionStatePatchError):
        patch_runtime._validate_entry_guard("aborted", aborted, "blocked", interface_owned=True)
    aborted["blocking_issues"] = [blocking_issue()]
    patch_runtime._validate_entry_guard("aborted", aborted, "blocked", interface_owned=True)


def test_workflow_runtime_references_and_primary_skills_are_synchronized() -> None:
    workflow = patch_runtime.load_contracts()[2]
    guards = {contract["entry_guard"] for contract in workflow["states"].values()}
    actions = {contract["interface_action"] for contract in workflow["states"].values()
               if "interface_action" in contract}
    assert guards == patch_runtime.ENTRY_GUARDS
    assert actions == patch_runtime.INTERFACE_ACTIONS
    action_types = yaml.safe_load((ROOT / ".codex/harness/development/shared/action-types.yaml").read_text())
    declared_actions = {item["id"] for item in action_types["interface_actions"]
                        if "execute" in item["scopes"]}
    assert actions <= declared_actions
    for contract in workflow["states"].values():
        skill = contract.get("primary_skill")
        if skill:
            assert (ROOT / ".codex/harness/development/skills/execute" / skill / "SKILL.md").is_file()

@pytest.mark.parametrize(("skill", "current_factory", "path", "value"), [
    ("inspect-execution-context", state, "/execution/context/unknown", "x"),
    ("review-implementation", implemented, "/execution/implementation/revision", 2),
    ("apply-scope-fix", lambda: implemented("fixing"), "/review/latest_result", "accepted"),
    ("run-release-gate", reviewed, "/execution/implementation/revision", 2),
    ("create-repository-publish-handoff", release_passed, "/repository_publish/commit_sha", "0" * 40),
])
def test_allowlist_and_unknown_paths_are_atomic(skill, current_factory, path, value) -> None:
    current = current_factory()
    destination = next(iter(patch_runtime.load_contracts()[2]["states"][current["state"]]["transitions"].values()))
    document = patch(skill, current, destination, [{"op": "add", "path": path, "value": value}])
    assert_rejected_without_mutation(current, document, skill)


def test_root_revision_invalid_transition_and_post_schema_violation_are_atomic() -> None:
    current = ready_for_implementation()
    base = patch("implement", current, "implementation_completed", implementation_operations())
    root = deepcopy(base); root["patch"]["operations"][0] = {"op": "replace", "path": "/", "value": {}}
    revision = deepcopy(base); revision["patch"]["operations"][0] = {"op": "replace", "path": "/revision", "value": 9}
    transition = deepcopy(base); transition["patch"]["requested_transition"]["to"] = "release_gate_passed"
    invalid_state = deepcopy(base)
    operation = next(item for item in invalid_state["patch"]["operations"] if item["path"] == "/execution/implementation/changed_files")
    operation["value"] = ["same.py", "same.py"]
    failed_postcondition = deepcopy(base)
    failed_postcondition["patch"]["postconditions"] = [
        {"type": "equals", "path": "/state", "value": "blocked"}
    ]
    wrong_target = deepcopy(base); wrong_target["patch"]["target"] = "plan-state"
    for document in (root, revision, transition, invalid_state, failed_postcondition, wrong_target):
        assert_rejected_without_mutation(current, document, "implement")
