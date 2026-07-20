from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


identity = load_module("artifact_identity", ROOT / "shared/artifact_identity.py")
source_binding = load_module("source_binding", ROOT / "shared/source_binding.py")
revision = load_module("artifact_revision", ROOT / "shared/artifact_revision.py")
policy = load_module("artifact_path_policy", ROOT / "shared/artifact_path_policy.py")
HASH_A = "a" * 64

EXPECTED_PATHS = {
    "adr": ".codex/harness/development/artifacts/decisions/adr-0007/r0004.md",
    "decision_record": ".codex/harness/development/artifacts/decisions/decision-main/records/record-r0004.json",
    "plan": ".codex/harness/development/artifacts/plans/main-plan/r0004.md",
    "plan_review": ".codex/harness/development/artifacts/plan-reviews/main-plan/plan-r0004/review-r0002.md",
    "design_review": ".codex/harness/development/artifacts/design-reviews/main-plan/plan-r0004/review-r0002.md",
    "guardrail_validation": ".codex/harness/development/artifacts/guardrail-validations/main-plan/plan-r0004/validation-r0002.json",
    "design_lock": ".codex/harness/development/artifacts/design-locks/main-plan/plan-r0004/lock-r0001.md",
    "readiness_evidence": ".codex/harness/development/artifacts/readiness/main-plan/plan-r0004/readiness-r0002.json",
    "implementation_review": ".codex/harness/development/artifacts/implementation-reviews/implementation-main/implementation-r0012/review-r0003.md",
    "release_gate": ".codex/harness/development/artifacts/release-gates/implementation-main/implementation-r0012/gate-r0003.md",
    "fix_request": ".codex/harness/development/artifacts/fix-requests/implementation-main/implementation-r0012/request-r0003.json",
    "repository_publish_handoff": ".codex/harness/development/artifacts/repository-publish-handoffs/implementation-main/implementation-r0012/handoff-r0003.json",
    "authorization_grant": ".codex/harness/development/artifacts/authorizations/main-plan/plan-r0004/grant-r0001.json",
    "authorization_continuation": ".codex/harness/development/artifacts/authorizations/main-plan/plan-r0004/continuation-r0001.json",
    "authorization_revocation": ".codex/harness/development/artifacts/authorizations/main-plan/plan-r0004/revocation-r0001.json",
}


def subject_binding_factory(variant="none", subject_revision=None):
    if variant == "none": return {"binding_type": "none"}
    if variant == "decision":
        return {"binding_type": "decision", "subject_decision_id": "decision-main", "subject_revision": subject_revision or 4, "subject_content_hash": HASH_A}
    if variant == "plan":
        return {"binding_type": "plan", "subject_plan_id": "main-plan", "subject_revision": subject_revision or 4, "subject_content_hash": HASH_A}
    return {"binding_type": "implementation", "subject_implementation_id": "implementation-main", "subject_revision": subject_revision or 12, "repository_snapshot_hash": HASH_A}


def artifact_identity_factory(artifact_type="plan"):
    logical_ids = {"adr": "adr-0007"}
    revisions = {"plan_review": 2, "design_review": 2, "guardrail_validation": 2, "readiness_evidence": 2,
                 "implementation_review": 3, "release_gate": 3, "fix_request": 3, "repository_publish_handoff": 3,
                 "design_lock": 1, "authorization_grant": 1, "authorization_continuation": 1, "authorization_revocation": 1}
    subject_series = {"decision_record": "decision-main", "plan_review": "main-plan-r0004", "design_review": "main-plan-r0004",
                      "guardrail_validation": "main-plan-r0004", "design_lock": "main-plan-r0004", "readiness_evidence": "main-plan-r0004",
                      "implementation_review": "implementation-main-r0012", "release_gate": "implementation-main-r0012",
                      "fix_request": "implementation-main-r0012", "repository_publish_handoff": "implementation-main-r0012",
                      "authorization_grant": "main-plan-r0004", "authorization_continuation": "main-plan-r0004", "authorization_revocation": "main-plan-r0004"}
    return {"artifact_type": artifact_type, "logical_artifact_id": logical_ids.get(artifact_type, subject_series.get(artifact_type, "main-plan")),
            "artifact_revision": revisions.get(artifact_type, 4)}


def path_derivation_request_factory(artifact_type="plan"):
    identity = artifact_identity_factory(artifact_type)
    variants = {"adr": "none", "plan": "none", "decision_record": "decision",
                "plan_review": "plan", "design_review": "plan", "guardrail_validation": "plan", "design_lock": "plan", "readiness_evidence": "plan",
                "implementation_review": "implementation", "release_gate": "implementation", "fix_request": "implementation", "repository_publish_handoff": "implementation",
                "authorization_grant": "plan", "authorization_continuation": "plan", "authorization_revocation": "plan"}
    return {"path_policy_version": "path-policy-v1", **identity, "subject_binding": subject_binding_factory(variants[artifact_type])}


def path_policy_registry_factory():
    return deepcopy(yaml.safe_load((ROOT / "shared/artifact-canonicality-registry.yaml").read_text()))


def path_derivation_result_factory(artifact_type="plan"):
    return dict(policy.derive_artifact_path(path_derivation_request_factory(artifact_type)).path_derivation)


def claimed_path_factory(artifact_type="plan"):
    return EXPECTED_PATHS[artifact_type]


class PathMatrixTests(unittest.TestCase):
    def test_all_fifteen_registered_paths_match_independent_literals(self):
        self.assertEqual(set(EXPECTED_PATHS), set(path_policy_registry_factory()["artifact_types"]))
        generated = {}
        for artifact_type, expected in EXPECTED_PATHS.items():
            result = policy.derive_artifact_path(path_derivation_request_factory(artifact_type))
            self.assertEqual(result.status, "valid", artifact_type)
            self.assertEqual(result.path_derivation["repository_path"], expected)
            generated[artifact_type] = expected
        self.assertEqual(len(set(generated.values())), 15)

    def test_revision_padding_and_determinism(self):
        request = path_derivation_request_factory("plan"); request["artifact_revision"] = 1
        first = policy.derive_artifact_path(request); second = policy.derive_artifact_path(request)
        self.assertEqual(first, second); self.assertTrue(first.path_derivation["repository_path"].endswith("/r0001.md"))
        request["artifact_revision"] = 10000
        self.assertTrue(policy.derive_artifact_path(request).path_derivation["repository_path"].endswith("/r10000.md"))

    def test_all_types_remain_unique_across_multiple_identity_sets(self):
        for case_name, identifier, subject_revision, artifact_revision in (
            ("minimal", "a", 1, 1),
            ("hyphenated", "a-a", 9999, 9999),
            ("prefix-sensitive", "sample-a", 10000, 10000),
        ):
            paths = set()
            for artifact_type in EXPECTED_PATHS:
                with self.subTest(case=case_name, artifact_type=artifact_type, identifier=identifier):
                    request = path_derivation_request_factory(artifact_type)
                    request["artifact_revision"] = artifact_revision
                    binding = request["subject_binding"]
                    if binding["binding_type"] == "none":
                        request["logical_artifact_id"] = identifier
                    else:
                        subject_key = {
                            "decision": "subject_decision_id", "plan": "subject_plan_id",
                            "implementation": "subject_implementation_id",
                        }[binding["binding_type"]]
                        binding[subject_key] = identifier
                        binding["subject_revision"] = subject_revision
                        request["logical_artifact_id"] = identifier if binding["binding_type"] == "decision" else identity.build_revision_scoped_logical_id(identifier, subject_revision)
                    result = policy.derive_artifact_path(request)
                    self.assertEqual(result.status, "valid")
                    self.assertNotIn(result.path_derivation["repository_path"], paths)
                    paths.add(result.path_derivation["repository_path"])
            self.assertEqual(len(paths), 15)


class CallerAndIdentityTests(unittest.TestCase):
    def test_caller_path_extension_and_segment_fields_are_impossible(self):
        for field in ("target_path", "repository_path", "absolute_path", "extension", "filename", "directory", "revision_path_segment"):
            request = path_derivation_request_factory(); request[field] = "x"
            self.assertEqual(policy.derive_artifact_path(request).status, "invalid")

    def test_unknown_type_and_version_are_rejected(self):
        request = path_derivation_request_factory(); request["artifact_type"] = "other"
        self.assertEqual(policy.derive_artifact_path(request).reason_code, "path_policy_artifact_type_unregistered")
        request = path_derivation_request_factory(); request["path_policy_version"] = "path-policy-v2"
        self.assertNotEqual(policy.derive_artifact_path(request).status, "valid")

    def test_invalid_logical_and_subject_ids(self):
        bad = ("../plan", "main/plan", "main\\plan", "Main-Plan", "main_plan", "main plan", "main.", "-main", "main-", "プラン", "ｍａｉｎ", "main%2fplan", "con", "nul")
        for value in bad:
            request = path_derivation_request_factory(); request["logical_artifact_id"] = value
            self.assertNotEqual(policy.derive_artifact_path(request).status, "valid", value)
            request = path_derivation_request_factory("plan_review"); request["subject_binding"]["subject_plan_id"] = value
            self.assertNotEqual(policy.derive_artifact_path(request).status, "valid", value)

    def test_revision_types_zero_and_limit(self):
        for value in (0, -1, True, 1.5, "1", revision.MAX_REVISION + 1, "r0004"):
            request = path_derivation_request_factory(); request["artifact_revision"] = value
            self.assertNotEqual(policy.derive_artifact_path(request).status, "valid")


class SubjectBindingTests(unittest.TestCase):
    def test_missing_wrong_and_incomplete_subjects_are_rejected(self):
        request = path_derivation_request_factory("plan_review"); request["subject_binding"] = {"binding_type": "none"}
        self.assertEqual(policy.derive_artifact_path(request).reason_code, "path_policy_subject_binding_variant_mismatch")
        request = path_derivation_request_factory("plan_review"); request["subject_binding"] = subject_binding_factory("implementation")
        self.assertEqual(policy.derive_artifact_path(request).reason_code, "path_policy_subject_binding_variant_mismatch")
        request = path_derivation_request_factory("implementation_review"); del request["subject_binding"]["subject_revision"]
        self.assertEqual(policy.derive_artifact_path(request).status, "invalid")
        request = path_derivation_request_factory("decision_record"); del request["subject_binding"]["subject_decision_id"]
        self.assertEqual(policy.derive_artifact_path(request).status, "invalid")
        request = path_derivation_request_factory("adr"); request["subject_binding"] = subject_binding_factory("plan")
        self.assertEqual(policy.derive_artifact_path(request).reason_code, "path_policy_subject_binding_variant_mismatch")

    def test_artifact_and_subject_revisions_are_not_swapped(self):
        request = path_derivation_request_factory("plan_review")
        result = policy.derive_artifact_path(request)
        self.assertIn("plan-r0004/review-r0002.md", result.path_derivation["repository_path"])

    def test_subject_scoped_logical_series_is_deterministic(self):
        request = path_derivation_request_factory("plan_review")
        request["logical_artifact_id"] = "parallel-series"
        self.assertEqual(policy.derive_artifact_path(request).reason_code, "path_policy_logical_series_identity_mismatch")

    def test_all_logical_series_variants_are_explicit_records(self):
        cases = {
            "plan": {"identity_type": "logical_id", "logical_artifact_id": "main-plan"},
            "decision_record": {"identity_type": "subject_id", "subject_type": "decision", "subject_id": "decision-main"},
            "plan_review": {"identity_type": "subject_id_revision", "subject_type": "plan", "subject_id": "main-plan", "subject_revision": 4},
            "implementation_review": {"identity_type": "subject_id_revision", "subject_type": "implementation", "subject_id": "implementation-main", "subject_revision": 12},
            "authorization_grant": {"identity_type": "subject_id_revision", "subject_type": "plan", "subject_id": "main-plan", "subject_revision": 4},
        }
        for artifact_type, expected in cases.items():
            with self.subTest(artifact_type=artifact_type):
                result = policy.derive_artifact_path(path_derivation_request_factory(artifact_type))
                self.assertEqual(result.status, "valid")
                self.assertEqual(result.path_derivation["logical_series"], expected)

    def test_subject_revision_defines_distinct_path_and_revision_series(self):
        revision_four = path_derivation_request_factory("plan_review")
        revision_five = deepcopy(revision_four)
        revision_five["subject_binding"]["subject_revision"] = 5
        revision_five["logical_artifact_id"] = "main-plan-r0005"
        first = policy.derive_artifact_path(revision_four)
        second = policy.derive_artifact_path(revision_five)
        self.assertEqual((first.status, second.status), ("valid", "valid"))
        self.assertNotEqual(first.path_derivation["logical_series"], second.path_derivation["logical_series"])
        self.assertNotEqual(first.path_derivation["repository_path"], second.path_derivation["repository_path"])
        # Revision allocation uses artifact_type + this logical_artifact_id, so the
        # two Path series cannot collapse into one allocator series.
        self.assertNotEqual(revision_four["logical_artifact_id"], revision_five["logical_artifact_id"])
        self.assertEqual(
            policy.validate_derived_artifact_path(revision_five, first.path_derivation["repository_path"]).reason_code,
            "path_policy_claimed_path_mismatch",
        )


class ContainmentAndRederivationTests(unittest.TestCase):
    def test_claimed_path_rejects_absolute_backslash_traversal_empty_fixed_and_outside(self):
        request = path_derivation_request_factory()
        bad_paths = ("/tmp/x", ".codex\\harness\\x", ".codex/harness/development/artifacts/../x", ".codex//harness/development/artifacts/x", "PLAN.md", "other/x")
        for claimed in bad_paths:
            self.assertNotEqual(policy.validate_derived_artifact_path(request, claimed).status, "valid", claimed)

    def test_identity_revision_subject_extension_mismatches_are_rejected(self):
        request = path_derivation_request_factory("plan")
        for claimed in (EXPECTED_PATHS["design_lock"], EXPECTED_PATHS["plan"].replace("r0004", "r0005"), EXPECTED_PATHS["plan"].replace(".md", ".json")):
            self.assertEqual(policy.validate_derived_artifact_path(request, claimed).reason_code, "path_policy_claimed_path_mismatch")
        request = path_derivation_request_factory("plan_review")
        self.assertEqual(policy.validate_derived_artifact_path(request, EXPECTED_PATHS["plan_review"].replace("plan-r0004", "plan-r0003")).reason_code, "path_policy_claimed_path_mismatch")

    def test_exact_derived_path_is_valid(self):
        for artifact_type in EXPECTED_PATHS:
            self.assertEqual(policy.validate_derived_artifact_path(path_derivation_request_factory(artifact_type), claimed_path_factory(artifact_type)).status, "valid")

    def test_raw_containment_and_artifact_root_fixed_path_cases_are_distinct(self):
        request = path_derivation_request_factory()
        cases = {
            ".codex/harness/development/artifacts//plans/x/r0001.md": "path_policy_empty_segment_forbidden",
            ".codex/harness/development/artifacts/plans/x/r0001.md/": "path_policy_empty_segment_forbidden",
            "./.codex/harness/development/artifacts/plans/x/r0001.md": "path_policy_traversal_forbidden",
            ".codex/harness/development/artifacts/PLAN.md": "path_policy_fixed_path_forbidden",
        }
        for claimed, reason in cases.items():
            with self.subTest(claimed=claimed, reason=reason):
                self.assertEqual(policy.validate_derived_artifact_path(request, claimed).reason_code, reason)


class RegistrySemanticTests(unittest.TestCase):
    def test_canonical_registry_is_valid_and_closed(self):
        self.assertIsNone(policy.validate_path_policy_registry(path_policy_registry_factory()))
        forbidden = {"repository_publish_result", "repository_publish_result_reference", "generic_review", "misc", "other", "temp"}
        self.assertTrue(forbidden.isdisjoint(path_policy_registry_factory()["artifact_types"]))

    def test_duplicate_unknown_token_root_status_and_format_are_rejected(self):
        mutations = []
        duplicate = path_policy_registry_factory(); duplicate["artifact_types"]["design_review"]["path_policy"]["path_pattern"] = duplicate["artifact_types"]["plan_review"]["path_policy"]["path_pattern"]; mutations.append((duplicate, "path_policy_pattern_collision"))
        token = path_policy_registry_factory(); token["artifact_types"]["plan"]["path_policy"]["path_pattern"] = "plans/{status}/{artifact_revision}.md"; mutations.append((token, "path_policy_pattern_invalid"))
        root = path_policy_registry_factory(); root["path_policy"]["artifact_root"] = "outside"; mutations.append((root, "path_policy_pattern_invalid"))
        fmt = path_policy_registry_factory(); fmt["artifact_types"]["plan"]["path_policy"]["extension"] = ".json"; mutations.append((fmt, "path_policy_format_mismatch"))
        for registry, reason in mutations: self.assertEqual(policy.validate_path_policy_registry(registry), reason)

    def test_token_occurrence_and_closed_pattern_language_are_enforced(self):
        patterns = (
            "plans/{logical_id}/{logical_id}/{artifact_revision}.md",
            "plans/{logical_id}/{artifact_revision}/{artifact_revision}.md",
            "plans/{artifact_revision}.md",
            "plans/{logical_id}/{subject_plan_id}/{artifact_revision}.md",
            "plans/{logical_id.__class__}/{artifact_revision}.md",
            "plans/{logical_id!r}/{artifact_revision}.md",
            "plans/{logical_id}/{artifact_revision:04d}.md",
            "plans/{logical_id[0]}/{artifact_revision}.md",
            "plans/{}/{artifact_revision}.md",
            "plans/{{logical_id}}/{artifact_revision}.md",
            "plans/{logical_id/{artifact_revision}.md",
        )
        for pattern in patterns:
            with self.subTest(pattern=pattern):
                registry = path_policy_registry_factory()
                registry["artifact_types"]["plan"]["path_policy"]["path_pattern"] = pattern
                self.assertIsNotNone(policy.validate_path_policy_registry(registry))

    def test_partial_token_literal_patterns_are_not_in_the_closed_family(self):
        for pattern in ("x/{logical_id}-a/{artifact_revision}.md", "x/a-{logical_id}/{artifact_revision}.md"):
            with self.subTest(pattern=pattern):
                registry = path_policy_registry_factory()
                registry["artifact_types"]["plan"]["path_policy"]["path_pattern"] = pattern
                self.assertEqual(policy.validate_path_policy_registry(registry), "path_policy_pattern_invalid")

    def test_encoded_separator_variants_are_individually_rejected(self):
        for value in ("main%2fplan", "main%2Fplan", "main%5cplan", "main%5Cplan", "main%252fplan"):
            with self.subTest(value=value):
                request = path_derivation_request_factory()
                request["logical_artifact_id"] = value
                result = policy.derive_artifact_path(request)
                self.assertEqual((result.status, result.reason_code), ("invalid", "path_derivation_request_invalid"))


class RecordIntegrityTests(unittest.TestCase):
    def test_valid_record_revalidates(self):
        self.assertEqual(policy.validate_path_derivation_record(path_derivation_result_factory()).status, "valid")

    def test_path_version_extension_and_hash_tampering_are_rejected(self):
        for field, value in (("repository_path", EXPECTED_PATHS["design_lock"]), ("path_policy_version", "path-policy-v2"), ("extension", ".json"), ("derivation_record_hash", "b" * 64)):
            record = path_derivation_result_factory(); record[field] = value
            if field != "derivation_record_hash": record["derivation_record_hash"] = policy.derivation_record_hash(record)
            self.assertNotEqual(policy.validate_path_derivation_record(record).status, "valid")

    def test_every_identity_bearing_field_is_protected(self):
        mutations = {
            "artifact_type": "adr",
            "logical_artifact_id": "other-plan",
            "logical_series": {"identity_type": "logical_id", "logical_artifact_id": "other-plan"},
            "artifact_revision": 5,
            "subject_binding": {"binding_type": "plan", "subject_plan_id": "main-plan", "subject_revision": 4, "subject_content_hash": HASH_A},
            "payload_format": "json",
            "extension": ".json",
            "repository_path": EXPECTED_PATHS["design_lock"],
            "path_policy_version": "path-policy-v2",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                record = path_derivation_result_factory()
                record[field] = value
                record["derivation_record_hash"] = policy.derivation_record_hash(record)
                self.assertNotEqual(policy.validate_path_derivation_record(record).status, "valid")
        record = path_derivation_result_factory()
        record["derivation_record_hash"] = "b" * 64
        self.assertEqual(policy.validate_path_derivation_record(record).status, "invalid")

    def test_subject_series_identity_tampering_is_rejected(self):
        for field, value in (("identity_type", "subject_id"), ("subject_id", "other-plan"), ("subject_revision", 5)):
            with self.subTest(field=field):
                record = path_derivation_result_factory("plan_review")
                record["logical_series"][field] = value
                record["derivation_record_hash"] = policy.derivation_record_hash(record)
                self.assertNotEqual(policy.validate_path_derivation_record(record).status, "valid")


if __name__ == "__main__": unittest.main()
