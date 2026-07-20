from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

import yaml
from jsonschema import validators


DEVELOPMENT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = DEVELOPMENT_ROOT / "shared/canonicality_authority.py"
SPEC = importlib.util.spec_from_file_location("canonicality_authority", MODULE_PATH)
canonicality = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = canonicality
SPEC.loader.exec_module(canonicality)


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
MATERIAL_HASH = "d" * 64
SNAPSHOT_HASH = "e" * 64
NOW = "2026-07-20T00:00:00Z"


TYPE_CASES = {
    "plan": {
        "generator": "assemble-plan",
        "lifecycle": "candidate",
        "decision": "accepted",
        "authority_type": "human_action",
        "source": "human-action-boundary",
        "action": "submit_plan",
        "subject_type": "plan",
    },
    "adr": {
        "generator": "build-adr-candidates",
        "lifecycle": "proposed",
        "decision": "accepted",
        "authority_type": "human_action",
        "source": "human-action-boundary",
        "action": "submit_decision",
        "subject_type": "decision",
    },
    "design_lock": {
        "generator": "lock-design",
        "lifecycle": "candidate",
        "decision": "locked",
        "authority_type": "human_action",
        "source": "human-action-boundary",
        "action": "submit_design",
        "subject_type": "plan",
    },
    "implementation_review": {
        "generator": "review-implementation",
        "lifecycle": "candidate",
        "decision": "accepted",
        "authority_type": "source_agent_decision",
        "source": "review-implementation",
        "action": "implementation_review_decision",
        "subject_type": "implementation",
    },
    "release_gate": {
        "generator": "run-release-gate",
        "lifecycle": "candidate",
        "decision": "passed",
        "authority_type": "workflow_guard",
        "source": "run-release-gate",
        "action": "release_gate_decision",
        "subject_type": "implementation",
    },
}


def subject(subject_type: str = "plan", *, revision: int = 4, digest: str = HASH_A):
    return {
        "binding_type": "bound",
        "subject_type": subject_type,
        "subject_id": "main-subject",
        "subject_revision": revision,
        "subject_hash": digest,
    }


def candidate_for(artifact_type: str = "plan"):
    case = TYPE_CASES[artifact_type]
    return {
        "candidate_schema_version": "1.0",
        "candidate_id": f"{artifact_type.replace('_', '-')}-candidate-1",
        "artifact_type": artifact_type,
        "logical_artifact_id": f"{artifact_type.replace('_', '-')}-main",
        "artifact_lifecycle_status": case["lifecycle"],
        "payload_hash": HASH_B,
        "subject_binding": subject(case["subject_type"]),
        "generated_by": {"source_id": case["generator"], "source_version": "1.0"},
    }


def authority_for(candidate, *, decision=None):
    case = TYPE_CASES[candidate["artifact_type"]]
    authority_type = case["authority_type"]
    record = {
        "authority_schema_version": "1.0",
        "authority_record_id": f"authority-{candidate['candidate_id']}",
        "authority_type": authority_type,
        "authority_source": {"source_id": case["source"], "source_version": "1.0"},
        "actor_identity": (
            {"actor_id": "human-1", "identity_provider": "trusted-ui", "verified": True}
            if authority_type == "human_action"
            else None
        ),
        "action_type": case["action"],
        "artifact_type": candidate["artifact_type"],
        "logical_artifact_id": candidate["logical_artifact_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_payload_hash": candidate["payload_hash"],
        "subject_binding": deepcopy(candidate["subject_binding"]),
        "canonical_decision": decision or case["decision"],
        "checked_snapshot_hash": None if authority_type == "human_action" else SNAPSHOT_HASH,
        "material_context_hash": MATERIAL_HASH,
        "status": "effective",
        "decided_at": NOW,
        "authority_record_hash": "0" * 64,
    }
    record["authority_record_hash"] = canonicality.canonical_record_hash(
        record, "authority_record_hash"
    )
    return record


def decision_for(candidate, authority, *, decision=None, record_id=None):
    record = {
        "decision_schema_version": "1.0",
        "decision_record_id": record_id or f"decision-{candidate['candidate_id']}",
        "artifact_type": candidate["artifact_type"],
        "logical_artifact_id": candidate["logical_artifact_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_payload_hash": candidate["payload_hash"],
        "subject_binding": deepcopy(candidate["subject_binding"]),
        "canonical_decision": decision or authority["canonical_decision"],
        "authority_type": authority["authority_type"],
        "authority_reference": {
            "authority_record_id": authority["authority_record_id"],
            "authority_record_hash": authority["authority_record_hash"],
        },
        "decided_at": NOW,
        "decision_record_hash": "0" * 64,
    }
    record["decision_record_hash"] = canonicality.canonical_record_hash(
        record, "decision_record_hash"
    )
    return record


def context_for(candidate, authority):
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_payload_hash": candidate["payload_hash"],
        "subject_binding": deepcopy(candidate["subject_binding"]),
        "material_context_hash": MATERIAL_HASH,
        "checked_snapshot_hash": authority["checked_snapshot_hash"],
        "verified_authority_record_hash": authority["authority_record_hash"],
        "verified_authority_source": deepcopy(authority["authority_source"]),
        "verified_actor_identity": deepcopy(authority["actor_identity"]),
        "effective_authority_record_ids": [authority["authority_record_id"]],
        "revoked_authority_record_ids": [],
    }


def validate(artifact_type="plan"):
    candidate = candidate_for(artifact_type)
    authority = authority_for(candidate)
    decision = decision_for(candidate, authority)
    context = context_for(candidate, authority)
    result = canonicality.validate_canonicality_authority(
        candidate, decision, authority, context
    )
    return result, candidate, authority, decision, context


def rehash_authority(authority):
    authority["authority_record_hash"] = canonicality.canonical_record_hash(
        authority, "authority_record_hash"
    )


def rehash_decision(decision, authority=None):
    if authority is not None:
        decision["authority_reference"] = {
            "authority_record_id": authority["authority_record_id"],
            "authority_record_hash": authority["authority_record_hash"],
        }
    decision["decision_record_hash"] = canonicality.canonical_record_hash(
        decision, "decision_record_hash"
    )


class RegistryAndCandidateTests(unittest.TestCase):
    def test_registry_is_closed_and_valid(self):
        registry, _ = canonicality.load_canonicality_contracts()
        self.assertEqual(
            set(registry["artifact_types"]),
            {
                "adr", "decision_record", "plan", "plan_review", "design_review",
                "guardrail_validation", "design_lock", "readiness_evidence",
                "implementation_review", "release_gate", "fix_request",
                "repository_publish_handoff", "authorization_grant",
                "authorization_continuation", "authorization_revocation",
            },
        )

    def test_candidate_generation_without_decision_is_valid(self):
        for artifact_type in TYPE_CASES:
            with self.subTest(artifact_type=artifact_type):
                self.assertEqual(
                    canonicality.validate_candidate(candidate_for(artifact_type)).status, "valid"
                )

    def test_adr_draft_and_proposed_are_lifecycle_only(self):
        for lifecycle in ("draft", "proposed"):
            candidate = candidate_for("adr")
            candidate["artifact_lifecycle_status"] = lifecycle
            self.assertEqual(canonicality.validate_candidate(candidate).status, "valid")

    def test_candidate_direct_canonical_fields_are_rejected(self):
        for field, value in (
            ("status", "accepted"),
            ("canonical_decision", "accepted"),
            ("canonicality_authority", "review-implementation"),
            ("artifact_written", True),
        ):
            with self.subTest(field=field):
                candidate = candidate_for("plan")
                candidate[field] = value
                result = canonicality.validate_candidate(candidate)
                self.assertEqual(result.status, "invalid")
                self.assertEqual(result.reason_code, "candidate_canonical_field_forbidden")

    def test_candidate_generator_cannot_impersonate_another_source(self):
        candidate = candidate_for("plan")
        candidate["generated_by"] = {"source_id": "artifact-writer", "source_version": "1.0"}
        result = canonicality.validate_candidate(candidate)
        self.assertEqual((result.status, result.reason_code),
                         ("blocked", "candidate_generator_not_allowed"))

    def test_not_applicable_type_rejects_canonical_decision(self):
        candidate = candidate_for("plan")
        candidate["artifact_type"] = "plan_review"
        candidate["logical_artifact_id"] = "plan-review-main"
        candidate["candidate_id"] = "plan-review-candidate-1"
        candidate["generated_by"] = {"source_id": "review-plan", "source_version": "1.0"}
        authority = authority_for(candidate_for("plan"))
        decision = decision_for(candidate_for("plan"), authority)
        context = context_for(candidate, authority)
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "canonicality_not_applicable")

    def test_candidate_templates_do_not_offer_canonical_decisions(self):
        plan = (DEVELOPMENT_ROOT / "templates/PLAN.md").read_text(encoding="utf-8")
        adr = (DEVELOPMENT_ROOT / "templates/ADR.md").read_text(encoding="utf-8")
        lock = (DEVELOPMENT_ROOT / "templates/DESIGN_LOCK.md").read_text(encoding="utf-8")
        self.assertNotIn("| accepted", plan.splitlines()[3])
        self.assertNotIn("| accepted", adr.splitlines()[3])
        self.assertNotIn("| locked", lock.splitlines()[3])

    def test_adr_schema_lifecycle_excludes_human_decisions(self):
        schema = yaml.safe_load(
            (DEVELOPMENT_ROOT / "schemas/adr.schema.yaml").read_text(encoding="utf-8")
        )
        values = schema["properties"]["artifact_lifecycle_status"]["enum"]
        self.assertEqual(values, ["draft", "proposed", "superseded"])

    def test_changed_artifact_schemas_are_valid_json_schemas(self):
        for name in ("adr.schema.yaml", "design-lock.schema.yaml"):
            with self.subTest(schema=name):
                schema = yaml.safe_load(
                    (DEVELOPMENT_ROOT / "schemas" / name).read_text(encoding="utf-8")
                )
                validators.validator_for(schema).check_schema(schema)


class HumanAuthorityTests(unittest.TestCase):
    def test_valid_plan_and_design_lock_human_actions(self):
        for artifact_type, expected in (("plan", "accepted"), ("design_lock", "locked")):
            with self.subTest(artifact_type=artifact_type):
                result, *_ = validate(artifact_type)
                self.assertEqual(result.status, "valid")
                self.assertEqual(result.canonical_decision, expected)

    def test_valid_adr_decision_record(self):
        for decision_value in ("accepted", "rejected", "deferred"):
            candidate = candidate_for("adr")
            authority = authority_for(candidate, decision=decision_value)
            decision = decision_for(candidate, authority, decision=decision_value)
            result = canonicality.validate_canonicality_authority(
                candidate, decision, authority, context_for(candidate, authority)
            )
            self.assertEqual(result.status, "valid")

    def test_missing_human_action_record_is_rejected(self):
        candidate = candidate_for("plan")
        result = canonicality.validate_canonicality_authority(candidate, {}, {}, {})
        self.assertEqual(result.status, "invalid")

    def test_stale_submit_actions_are_rejected(self):
        for artifact_type in ("plan", "design_lock"):
            with self.subTest(artifact_type=artifact_type):
                _, candidate, authority, decision, context = validate(artifact_type)
                context["effective_authority_record_ids"] = []
                result = canonicality.validate_canonicality_authority(
                    candidate, decision, authority, context
                )
                self.assertEqual((result.status, result.reason_code),
                                 ("blocked", "authority_stale"))

    def test_different_plan_revision_is_rejected(self):
        _, candidate, authority, decision, context = validate("plan")
        authority["subject_binding"]["subject_revision"] += 1
        rehash_authority(authority)
        rehash_decision(decision, authority)
        context["verified_authority_record_hash"] = authority["authority_record_hash"]
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "authority_subject_binding_mismatch")

    def test_candidate_change_invalidates_old_action(self):
        _, candidate, authority, decision, context = validate("plan")
        candidate["payload_hash"] = HASH_C
        context["candidate_payload_hash"] = HASH_C
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "decision_candidate_hash_mismatch")

    def test_current_subject_mismatch_is_rejected(self):
        _, candidate, authority, decision, context = validate("plan")
        context["subject_binding"] = subject("plan", revision=5, digest=HASH_C)
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "current_subject_binding_mismatch")

    def test_revoked_and_materially_stale_actions_are_rejected(self):
        _, candidate, authority, decision, context = validate("plan")
        context["revoked_authority_record_ids"] = [authority["authority_record_id"]]
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "authority_revoked")
        context["revoked_authority_record_ids"] = []
        context["material_context_hash"] = HASH_C
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "authority_material_context_stale")

    def test_actor_name_string_is_not_a_human_identity(self):
        _, candidate, authority, decision, context = validate("plan")
        authority["actor_identity"] = "Alice"
        rehash_authority(authority)
        rehash_decision(decision, authority)
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.status, "invalid")

    def test_self_asserted_human_identity_is_rejected(self):
        _, candidate, authority, decision, context = validate("plan")
        authority["actor_identity"]["actor_id"] = "impostor"
        rehash_authority(authority)
        rehash_decision(decision, authority)
        context["verified_authority_record_hash"] = authority["authority_record_hash"]
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "human_actor_identity_mismatch")


class AgentAndGuardAuthorityTests(unittest.TestCase):
    def test_registered_review_source_is_valid(self):
        result, *_ = validate("implementation_review")
        self.assertEqual((result.status, result.canonical_decision), ("valid", "accepted"))

    def test_agent_and_guard_decision_vocabularies_are_closed_and_usable(self):
        for artifact_type, decisions in (
            ("implementation_review", ("accepted", "changes_required", "blocked")),
            ("release_gate", ("passed", "failed", "blocked")),
        ):
            for decision_value in decisions:
                with self.subTest(artifact_type=artifact_type, decision=decision_value):
                    candidate = candidate_for(artifact_type)
                    authority = authority_for(candidate, decision=decision_value)
                    decision = decision_for(candidate, authority, decision=decision_value)
                    result = canonicality.validate_canonicality_authority(
                        candidate, decision, authority, context_for(candidate, authority)
                    )
                    self.assertEqual(result.status, "valid")

    def test_unregistered_review_source_is_rejected(self):
        _, candidate, authority, decision, context = validate("implementation_review")
        authority["authority_source"] = {"source_id": "unknown-reviewer", "source_version": "1.0"}
        rehash_authority(authority)
        rehash_decision(decision, authority)
        context["verified_authority_record_hash"] = authority["authority_record_hash"]
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "authority_source_not_allowed")

    def test_registered_source_cannot_be_self_asserted(self):
        _, candidate, authority, decision, context = validate("implementation_review")
        context["verified_authority_source"] = {
            "source_id": "run-release-gate",
            "source_version": "1.0",
        }
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "authority_source_identity_mismatch")

    def test_review_for_different_snapshot_is_rejected(self):
        _, candidate, authority, decision, context = validate("implementation_review")
        context["checked_snapshot_hash"] = HASH_C
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "authority_snapshot_mismatch")

    def test_valid_release_gate_guard_is_valid(self):
        result, *_ = validate("release_gate")
        self.assertEqual((result.status, result.canonical_decision), ("valid", "passed"))

    def test_release_gate_body_status_without_guard_is_rejected(self):
        candidate = candidate_for("release_gate")
        candidate["status"] = "passed"
        result = canonicality.validate_candidate(candidate)
        self.assertEqual(result.reason_code, "candidate_canonical_field_forbidden")

    def test_stale_release_gate_guard_is_rejected(self):
        _, candidate, authority, decision, context = validate("release_gate")
        context["effective_authority_record_ids"] = []
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "authority_stale")

    def test_writer_cannot_be_canonicality_authority(self):
        _, candidate, authority, decision, context = validate("implementation_review")
        authority["authority_source"] = {"source_id": "artifact-writer", "source_version": "1.0"}
        rehash_authority(authority)
        rehash_decision(decision, authority)
        context["verified_authority_record_hash"] = authority["authority_record_hash"]
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "authority_source_not_allowed")


class IntegrityAndIdempotencyTests(unittest.TestCase):
    def test_same_candidate_and_authority_are_idempotent(self):
        _, candidate, authority, decision, context = validate("plan")
        first = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        second = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context,
            existing_decision_records={decision["decision_record_id"]: decision["decision_record_hash"]},
        )
        self.assertEqual(first, second)

    def test_same_decision_id_with_different_content_is_rejected(self):
        _, candidate, authority, decision, context = validate("plan")
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context,
            existing_decision_records={decision["decision_record_id"]: HASH_C},
        )
        self.assertEqual(result.reason_code, "decision_record_id_conflict")

    def test_authority_integrity_mismatch_is_invalid(self):
        _, candidate, authority, decision, context = validate("plan")
        authority["candidate_payload_hash"] = HASH_C
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "authority_record_integrity_invalid")

    def test_untrusted_authority_record_content_is_rejected(self):
        _, candidate, authority, decision, context = validate("plan")
        context["verified_authority_record_hash"] = HASH_C
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "authority_record_not_trusted")

    def test_decision_integrity_mismatch_is_invalid(self):
        _, candidate, authority, decision, context = validate("plan")
        decision["canonical_decision"] = "rejected"
        result = canonicality.validate_canonicality_authority(
            candidate, decision, authority, context
        )
        self.assertEqual(result.reason_code, "decision_record_integrity_invalid")

    def test_validator_does_not_mutate_candidate(self):
        _, candidate, authority, decision, context = validate("plan")
        original = deepcopy(candidate)
        canonicality.validate_canonicality_authority(candidate, decision, authority, context)
        self.assertEqual(candidate, original)
        self.assertNotIn("canonical_decision", candidate)


if __name__ == "__main__":
    unittest.main()
