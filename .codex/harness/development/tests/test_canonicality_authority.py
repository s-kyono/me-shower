from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

import yaml
from jsonschema import validators


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "canonicality_authority", ROOT / "shared/canonicality_authority.py"
)
canonicality = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = canonicality
SPEC.loader.exec_module(canonicality)

HASH_A = "a" * 64
HASH_C = "c" * 64
MATERIAL_HASH = "d" * 64
SNAPSHOT_HASH = "e" * 64
NOW = "2026-07-20T00:00:00Z"
ACTOR = {"actor_id": "human-1", "identity_provider": "trusted-ui", "verified": True}

CASES = {
    "plan": ("assemble-plan", "candidate", "accepted", "human_action", "human-action-boundary", "submit_plan", "plan"),
    "adr": ("build-adr-candidates", "proposed", "accepted", "human_action", "human-action-boundary", "submit_decision", "decision"),
    "design_lock": ("lock-design", "candidate", "locked", "human_action", "human-action-boundary", "submit_design", "plan"),
    "implementation_review": ("review-implementation", "candidate", "accepted", "source_agent_decision", "review-implementation", "implementation_review_decision", "implementation"),
    "release_gate": ("run-release-gate", "candidate", "passed", "workflow_guard", "run-release-gate", "release_gate_decision", "implementation"),
}


def payload_for(artifact_type: str, metadata: str | None = None, body: str = "Candidate body.") -> bytes:
    lifecycle = CASES[artifact_type][1]
    front_matter = metadata or f"artifact_lifecycle_status: {lifecycle}"
    return f"---\n{front_matter}\n---\n\n{body}\n".encode()


def subject(subject_type: str = "plan", revision: int = 4, digest: str = HASH_A):
    return {
        "binding_type": "bound", "subject_type": subject_type,
        "subject_id": "main-subject", "subject_revision": revision,
        "subject_hash": digest,
    }


def candidate_factory(artifact_type: str = "plan", payload: bytes | None = None):
    generator, lifecycle, *_, subject_type = CASES[artifact_type]
    exact_payload = payload if payload is not None else payload_for(artifact_type)
    return {
        "candidate_schema_version": "1.0",
        "candidate_id": f"{artifact_type.replace('_', '-')}-candidate-1",
        "artifact_type": artifact_type,
        "logical_artifact_id": f"{artifact_type.replace('_', '-')}-main",
        "candidate_revision": 3,
        "artifact_lifecycle_status": lifecycle,
        "payload_hash": hashlib.sha256(exact_payload).hexdigest(),
        "payload_format": "markdown",
        "subject_binding": subject(subject_type),
        "generated_by": {"source_id": generator, "source_version": "1.0"},
    }


def authority_record_factory(candidate, decision_value: str | None = None):
    _, _, default_decision, authority_type, source_id, action, _ = CASES[candidate["artifact_type"]]
    record = {
        "authority_schema_version": "1.0",
        "authority_record_id": f"authority-{candidate['candidate_id']}",
        "authority_type": authority_type,
        "authority_source": {"source_id": source_id, "source_version": "1.0"},
        "actor_identity": deepcopy(ACTOR) if authority_type == "human_action" else None,
        "action_type": action,
        "artifact_type": candidate["artifact_type"],
        "logical_artifact_id": candidate["logical_artifact_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_payload_hash": candidate["payload_hash"],
        "subject_binding": deepcopy(candidate["subject_binding"]),
        "canonical_decision": decision_value or default_decision,
        "checked_snapshot_hash": None if authority_type == "human_action" else SNAPSHOT_HASH,
        "material_context_hash": MATERIAL_HASH,
        "status": "effective", "decided_at": NOW,
        "authority_record_hash": "0" * 64,
    }
    record["authority_record_hash"] = canonicality.canonical_record_hash(record, "authority_record_hash")
    return record


def decision_record_factory(candidate, authority, decision_value: str | None = None, record_id: str | None = None):
    record = {
        "decision_schema_version": "1.0",
        "decision_record_id": record_id or f"decision-{candidate['candidate_id']}",
        "decision_revision": 2,
        "artifact_type": candidate["artifact_type"],
        "logical_artifact_id": candidate["logical_artifact_id"],
        "candidate_id": candidate["candidate_id"],
        "candidate_payload_hash": candidate["payload_hash"],
        "subject_binding": deepcopy(candidate["subject_binding"]),
        "canonical_decision": decision_value or authority["canonical_decision"],
        "authority_type": authority["authority_type"],
        "authority_reference": {
            "authority_record_id": authority["authority_record_id"],
            "authority_record_hash": authority["authority_record_hash"],
        },
        "decided_at": NOW, "decision_record_hash": "0" * 64,
    }
    record["decision_record_hash"] = canonicality.canonical_record_hash(record, "decision_record_hash")
    return record


class FixtureResolver(canonicality.TrustedCanonicalityContextResolver):
    def __init__(self, candidate_context=None, canonical_context=None):
        self.candidate_context = candidate_context
        self.canonical_context = canonical_context

    def resolve_candidate(self, candidate_id):
        return self.candidate_context

    def resolve_canonicality(self, candidate_id, authority_record_id):
        return self.canonical_context


def trusted_context_factory(
    artifact_type: str, candidate, *, authority_hash: str,
    decision_index=None, authority_index=None, overrides=None,
):
    generator, _, _, authority_type, authority_source, _, _ = CASES[artifact_type]
    facts = {
        "candidate_id": candidate["candidate_id"],
        "candidate_payload_hash": candidate["payload_hash"],
        "trusted_candidate_generator": {"source_id": generator, "source_version": "1.0"},
        "subject_binding": deepcopy(candidate["subject_binding"]),
        "material_context_hash": MATERIAL_HASH,
        "checked_snapshot_hash": None if authority_type == "human_action" else SNAPSHOT_HASH,
        "verified_authority_record_hash": authority_hash,
        "verified_authority_source": {"source_id": authority_source, "source_version": "1.0"},
        "verified_actor_identity": deepcopy(ACTOR) if authority_type == "human_action" else None,
        "effective_authority_record_ids": frozenset({f"authority-{candidate['candidate_id']}"}),
        "revoked_authority_record_ids": frozenset(),
        "existing_decision_records": {} if decision_index is None else decision_index,
        "existing_authority_records": {} if authority_index is None else authority_index,
    }
    if overrides:
        facts.update(overrides)
    return FixtureResolver(
        candidate_context=FixtureResolver._mint_context(**facts),
        canonical_context=FixtureResolver._mint_context(**facts),
    )


def valid_case(artifact_type="plan", decision_value=None, payload=None):
    exact_payload = payload or payload_for(artifact_type)
    candidate = candidate_factory(artifact_type, exact_payload)
    authority = authority_record_factory(candidate, decision_value)
    decision = decision_record_factory(candidate, authority, decision_value)
    resolver = trusted_context_factory(
        artifact_type, candidate, authority_hash=authority["authority_record_hash"]
    )
    result = canonicality.validate_canonicality_authority(
        candidate, exact_payload, decision, authority, resolver
    )
    return result, exact_payload, candidate, authority, decision, resolver


class RegistrySubjectAndSchemaTests(unittest.TestCase):
    def test_registry_is_closed_and_subject_policy_is_consistent(self):
        registry, _ = canonicality.load_canonicality_contracts()
        self.assertEqual(len(registry["artifact_types"]), 15)
        for item in registry["artifact_types"].values():
            applicable = item["canonicality"]["authority_types"] != ["not_applicable"]
            self.assertEqual(item["subject_binding_policy"], "required" if applicable else "optional")

    def test_changed_schemas_are_valid(self):
        for name in (
            "canonicality-common.schema.yaml", "artifact-candidate.schema.yaml",
            "artifact-canonicality-registry.schema.yaml",
            "canonicality-authority-record.schema.yaml",
            "canonicality-decision-record.schema.yaml",
        ):
            schema = yaml.safe_load((ROOT / "schemas" / name).read_text())
            validators.validator_for(schema).check_schema(schema)

    def test_required_subject_none_is_rejected_for_canonical_types(self):
        for artifact_type in ("plan", "design_lock", "implementation_review", "release_gate"):
            with self.subTest(artifact_type=artifact_type):
                payload = payload_for(artifact_type)
                candidate = candidate_factory(artifact_type, payload)
                candidate["subject_binding"] = {"binding_type": "none"}
                authority = authority_record_factory(candidate)
                decision = decision_record_factory(candidate, authority)
                resolver = trusted_context_factory(
                    artifact_type, candidate,
                    authority_hash=authority["authority_record_hash"],
                    overrides={"subject_binding": {"binding_type": "none"}},
                )
                result = canonicality.validate_canonicality_authority(
                    candidate, payload, decision, authority, resolver
                )
                self.assertEqual(result.reason_code, "subject_binding_required")

    def test_subject_revision_and_hash_mismatch_are_rejected(self):
        for changed in (
            subject("plan", revision=5), subject("plan", revision=4, digest=HASH_C),
        ):
            result, payload, candidate, authority, decision, _ = valid_case("plan")
            resolver = trusted_context_factory(
                "plan", candidate, authority_hash=authority["authority_record_hash"],
                overrides={"subject_binding": changed},
            )
            result = canonicality.validate_canonicality_authority(
                candidate, payload, decision, authority, resolver
            )
            self.assertEqual(result.reason_code, "current_subject_binding_mismatch")


class PayloadValidationTests(unittest.TestCase):
    def assert_payload_blocked(self, artifact_type, metadata):
        payload = payload_for(artifact_type, metadata)
        candidate = candidate_factory(artifact_type, payload)
        authority = authority_record_factory(candidate)
        resolver = trusted_context_factory(
            artifact_type, candidate, authority_hash=authority["authority_record_hash"]
        )
        result = canonicality.validate_candidate(candidate, payload, resolver)
        self.assertEqual(result.reason_code, "candidate_payload_contains_canonical_field")

    def test_plan_canonical_front_matter_is_rejected(self):
        self.assert_payload_blocked("plan", "status: accepted")
        self.assert_payload_blocked("plan", "approval_status: accepted")

    def test_design_lock_canonical_metadata_is_rejected(self):
        self.assert_payload_blocked("design_lock", "locked: true")
        self.assert_payload_blocked("design_lock", "approval:\n  submitted: true")

    def test_adr_final_decisions_are_rejected(self):
        for value in ("accepted", "rejected", "deferred"):
            self.assert_payload_blocked("adr", f"status: {value}")

    def test_release_gate_body_status_is_not_authority(self):
        self.assert_payload_blocked("release_gate", "status: passed")

    def test_payload_hash_mismatch_and_missing_payload_are_rejected(self):
        result, payload, candidate, _, _, resolver = valid_case("plan")
        self.assertEqual(
            canonicality.validate_candidate(candidate, payload + b"changed", resolver).reason_code,
            "candidate_payload_hash_mismatch",
        )
        self.assertEqual(
            canonicality.validate_candidate(candidate, None, resolver).reason_code,
            "candidate_payload_required",
        )

    def test_normal_prose_may_contain_accepted(self):
        payload = payload_for("plan", body="The parser accepted this ordinary sentence.")
        candidate = candidate_factory("plan", payload)
        authority = authority_record_factory(candidate)
        resolver = trusted_context_factory("plan", candidate, authority_hash=authority["authority_record_hash"])
        self.assertEqual(canonicality.validate_candidate(candidate, payload, resolver).status, "valid")


class TrustedContextAndGeneratorTests(unittest.TestCase):
    def test_raw_mapping_is_not_a_trusted_context(self):
        payload = payload_for("plan")
        candidate = candidate_factory("plan", payload)
        result = canonicality.validate_candidate(candidate, payload, {})
        self.assertEqual(result.reason_code, "trusted_context_required")

    def test_resolver_returning_mapping_is_rejected(self):
        class ForgedResolver(FixtureResolver):
            def resolve_candidate(self, candidate_id):
                return {"trusted_candidate_generator": candidate_id}
        payload = payload_for("plan")
        candidate = candidate_factory("plan", payload)
        self.assertEqual(
            canonicality.validate_candidate(candidate, payload, ForgedResolver()).reason_code,
            "trusted_context_required",
        )

    def test_resolver_failure_is_fail_closed(self):
        class BrokenResolver(FixtureResolver):
            def resolve_candidate(self, candidate_id):
                raise RuntimeError("unavailable")
        payload = payload_for("plan")
        candidate = candidate_factory("plan", payload)
        self.assertEqual(
            canonicality.validate_candidate(candidate, payload, BrokenResolver()).reason_code,
            "trusted_context_required",
        )

    def test_missing_trusted_source_actor_and_subject_fail_closed(self):
        for override, reason in (
            ({"verified_authority_source": None}, "trusted_authority_source_missing"),
            ({"verified_actor_identity": None}, "trusted_actor_identity_missing"),
            ({"subject_binding": None}, "subject_binding_required"),
        ):
            _, payload, candidate, authority, decision, _ = valid_case("plan")
            resolver = trusted_context_factory(
                "plan", candidate, authority_hash=authority["authority_record_hash"],
                overrides=override,
            )
            result = canonicality.validate_canonicality_authority(
                candidate, payload, decision, authority, resolver
            )
            self.assertEqual(result.reason_code, reason)

    def test_generator_impersonation_and_missing_identity_are_rejected(self):
        for artifact_type, trusted, reason in (
            ("plan", {"source_id": "malicious-skill", "source_version": "1.0"}, "candidate_generator_identity_mismatch"),
            ("design_lock", None, "trusted_candidate_generator_missing"),
        ):
            _, payload, candidate, authority, _, _ = valid_case(artifact_type)
            resolver = trusted_context_factory(
                artifact_type, candidate, authority_hash=authority["authority_record_hash"],
                overrides={"trusted_candidate_generator": trusted},
            )
            result = canonicality.validate_candidate(candidate, payload, resolver)
            self.assertEqual(result.reason_code, reason)

    def test_matching_trusted_generator_is_valid(self):
        result, payload, candidate, _, _, resolver = valid_case("plan")
        self.assertEqual(canonicality.validate_candidate(candidate, payload, resolver).status, "valid")


class RecordUniquenessAndAuthorityTests(unittest.TestCase):
    def test_indexes_are_required(self):
        for override, reason in (
            ({"existing_decision_records": None}, "decision_record_index_required"),
            ({"existing_authority_records": None}, "authority_record_index_required"),
        ):
            _, payload, candidate, authority, decision, _ = valid_case("plan")
            resolver = trusted_context_factory(
                "plan", candidate, authority_hash=authority["authority_record_hash"],
                overrides=override,
            )
            result = canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver)
            self.assertEqual(result.reason_code, reason)

    def test_empty_indexes_allow_first_records(self):
        self.assertEqual(valid_case("plan")[0].status, "valid")

    def test_same_ids_and_hashes_are_idempotent(self):
        _, payload, candidate, authority, decision, _ = valid_case("plan")
        resolver = trusted_context_factory(
            "plan", candidate, authority_hash=authority["authority_record_hash"],
            decision_index={decision["decision_record_id"]: decision["decision_record_hash"]},
            authority_index={authority["authority_record_id"]: authority["authority_record_hash"]},
        )
        first = canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver)
        second = canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver)
        self.assertEqual(first, second)

    def test_decision_and_authority_id_conflicts_are_rejected(self):
        for indexes, reason in (
            ({"decision_index": {"decision-plan-candidate-1": HASH_C}}, "decision_record_id_conflict"),
            ({"authority_index": {"authority-plan-candidate-1": HASH_C}}, "authority_record_id_conflict"),
        ):
            _, payload, candidate, authority, decision, _ = valid_case("plan")
            resolver = trusted_context_factory(
                "plan", candidate, authority_hash=authority["authority_record_hash"], **indexes
            )
            result = canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver)
            self.assertEqual(result.reason_code, reason)

    def test_human_agent_guard_positive_paths(self):
        for artifact_type, decisions in (
            ("plan", ("accepted",)), ("design_lock", ("locked",)),
            ("adr", ("accepted", "rejected", "deferred")),
            ("implementation_review", ("accepted", "changes_required", "blocked")),
            ("release_gate", ("passed", "failed", "blocked")),
        ):
            for decision in decisions:
                with self.subTest(artifact_type=artifact_type, decision=decision):
                    self.assertEqual(valid_case(artifact_type, decision)[0].status, "valid")

    def test_stale_revoked_material_snapshot_writer_and_candidate_change(self):
        cases = (
            ("plan", {"effective_authority_record_ids": frozenset()}, "authority_stale"),
            ("plan", {"revoked_authority_record_ids": frozenset({"authority-plan-candidate-1"})}, "authority_revoked"),
            ("plan", {"material_context_hash": HASH_C}, "authority_material_context_stale"),
            ("release_gate", {"checked_snapshot_hash": HASH_C}, "authority_snapshot_mismatch"),
        )
        for artifact_type, override, reason in cases:
            _, payload, candidate, authority, decision, _ = valid_case(artifact_type)
            resolver = trusted_context_factory(artifact_type, candidate, authority_hash=authority["authority_record_hash"], overrides=override)
            self.assertEqual(
                canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver).reason_code,
                reason,
            )

        _, payload, candidate, authority, decision, _ = valid_case("implementation_review")
        authority["authority_source"] = {"source_id": "artifact-writer", "source_version": "1.0"}
        authority["authority_record_hash"] = canonicality.canonical_record_hash(authority, "authority_record_hash")
        decision["authority_reference"]["authority_record_hash"] = authority["authority_record_hash"]
        decision["decision_record_hash"] = canonicality.canonical_record_hash(decision, "decision_record_hash")
        resolver = trusted_context_factory("implementation_review", candidate, authority_hash=authority["authority_record_hash"])
        self.assertEqual(
            canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver).reason_code,
            "authority_source_not_allowed",
        )

        candidate["payload_hash"] = HASH_C
        self.assertEqual(
            canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver).reason_code,
            "candidate_payload_hash_mismatch",
        )

    def test_candidate_is_not_mutated(self):
        _, payload, candidate, authority, decision, resolver = valid_case("plan")
        original = deepcopy(candidate)
        canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver)
        self.assertEqual(candidate, original)
        self.assertNotIn("canonical_decision", candidate)


class SafetyRegressionTests(unittest.TestCase):
    def test_structured_yaml_payload_is_parsed(self):
        payload = b"status: accepted\n"
        candidate = candidate_factory("plan", payload)
        candidate["payload_format"] = "yaml"
        authority = authority_record_factory(candidate)
        resolver = trusted_context_factory("plan", candidate, authority_hash=authority["authority_record_hash"])
        self.assertEqual(
            canonicality.validate_candidate(candidate, payload, resolver).reason_code,
            "candidate_payload_contains_canonical_field",
        )

    def test_malformed_front_matter_is_invalid(self):
        payload = b"---\nstatus: accepted\n"
        candidate = candidate_factory("plan", payload)
        authority = authority_record_factory(candidate)
        resolver = trusted_context_factory("plan", candidate, authority_hash=authority["authority_record_hash"])
        self.assertEqual(
            canonicality.validate_candidate(candidate, payload, resolver).reason_code,
            "candidate_payload_invalid",
        )

    def test_direct_candidate_canonical_fields_remain_rejected(self):
        payload = payload_for("plan")
        for field, value in (("status", "accepted"), ("canonical_decision", "accepted"), ("artifact_written", True)):
            candidate = candidate_factory("plan", payload)
            candidate[field] = value
            authority = authority_record_factory(candidate)
            resolver = trusted_context_factory("plan", candidate, authority_hash=authority["authority_record_hash"])
            self.assertEqual(
                canonicality.validate_candidate(candidate, payload, resolver).reason_code,
                "candidate_canonical_field_forbidden",
            )

    def test_unregistered_candidate_generator_is_rejected(self):
        payload = payload_for("plan")
        candidate = candidate_factory("plan", payload)
        candidate["generated_by"] = {"source_id": "artifact-writer", "source_version": "1.0"}
        authority = authority_record_factory(candidate)
        resolver = trusted_context_factory(
            "plan", candidate, authority_hash=authority["authority_record_hash"],
            overrides={"trusted_candidate_generator": candidate["generated_by"]},
        )
        self.assertEqual(
            canonicality.validate_candidate(candidate, payload, resolver).reason_code,
            "candidate_generator_not_allowed",
        )

    def test_authority_source_identity_mismatch_is_rejected(self):
        _, payload, candidate, authority, decision, _ = valid_case("implementation_review")
        resolver = trusted_context_factory(
            "implementation_review", candidate, authority_hash=authority["authority_record_hash"],
            overrides={"verified_authority_source": {"source_id": "run-release-gate", "source_version": "1.0"}},
        )
        self.assertEqual(
            canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver).reason_code,
            "authority_source_identity_mismatch",
        )

    def test_human_actor_identity_mismatch_is_rejected(self):
        _, payload, candidate, authority, decision, _ = valid_case("plan")
        resolver = trusted_context_factory(
            "plan", candidate, authority_hash=authority["authority_record_hash"],
            overrides={"verified_actor_identity": {"actor_id": "other", "identity_provider": "trusted-ui", "verified": True}},
        )
        self.assertEqual(
            canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver).reason_code,
            "human_actor_identity_mismatch",
        )

    def test_authority_and_decision_integrity_are_checked(self):
        for target, reason in (("authority", "authority_record_integrity_invalid"), ("decision", "decision_record_integrity_invalid")):
            _, payload, candidate, authority, decision, resolver = valid_case("plan")
            if target == "authority":
                authority["canonical_decision"] = "rejected"
            else:
                decision["canonical_decision"] = "rejected"
            self.assertEqual(
                canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver).reason_code,
                reason,
            )

    def test_authority_reference_mismatch_is_rejected(self):
        _, payload, candidate, authority, decision, resolver = valid_case("plan")
        decision["authority_reference"]["authority_record_id"] = "authority-other"
        decision["decision_record_hash"] = canonicality.canonical_record_hash(decision, "decision_record_hash")
        self.assertEqual(
            canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver).reason_code,
            "authority_reference_mismatch",
        )

    def test_missing_human_action_record_is_invalid(self):
        payload = payload_for("plan")
        candidate = candidate_factory("plan", payload)
        self.assertEqual(
            canonicality.validate_canonicality_authority(candidate, payload, {}, {}, FixtureResolver()).status,
            "blocked",
        )

    def test_templates_do_not_expose_final_decision_fields(self):
        for name in ("PLAN.md", "ADR.md", "DESIGN_LOCK.md"):
            text = (ROOT / "templates" / name).read_text()
            front = text.split("---", 2)[1]
            self.assertNotIn("status:", front.replace("artifact_lifecycle_status:", ""))
            self.assertNotIn("approval_status", front)
            self.assertNotIn("submitted_by", front)

    def test_not_applicable_registry_type_has_no_authority_contract(self):
        registry, _ = canonicality.load_canonicality_contracts()
        contract = registry["artifact_types"]["plan_review"]["canonicality"]
        self.assertEqual(contract["authority_types"], ["not_applicable"])
        self.assertEqual(contract["contracts"], [])

    def test_decision_vocabularies_are_closed(self):
        result, payload, candidate, authority, decision, resolver = valid_case("plan")
        authority["canonical_decision"] = "locked"
        authority["authority_record_hash"] = canonicality.canonical_record_hash(authority, "authority_record_hash")
        decision = decision_record_factory(candidate, authority, "locked")
        resolver = trusted_context_factory("plan", candidate, authority_hash=authority["authority_record_hash"])
        self.assertEqual(
            canonicality.validate_canonicality_authority(candidate, payload, decision, authority, resolver).reason_code,
            "canonical_decision_not_allowed",
        )


if __name__ == "__main__":
    unittest.main()
