from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load_module("artifact_identity", ROOT / "shared/artifact_identity.py")
source = load_module("source_binding", ROOT / "shared/source_binding.py")
source_adapter = load_module("source_binding_trusted_adapter", ROOT / "shared/source_binding_trusted_adapter.py")
load_module("canonicality_authority", ROOT / "shared/canonicality_authority.py")
scan = load_module("development_security_scan", ROOT / "shared/development_security_scan.py")
adapter = load_module(
    "development_security_scan_trusted_adapter",
    ROOT / "shared/development_security_scan_trusted_adapter.py",
)


PAYLOAD = b"---\ntitle: Safe plan\n---\n"
PAYLOAD_HASH = hashlib.sha256(PAYLOAD).hexdigest()
SAFE_HASH = "a" * 64
GENERATOR = {"source_id": "assemble-plan", "source_version": "1.0"}
SCANNER = {"scanner_id": "development-security-scanner", "scanner_version": "1.0"}
CHECKS = ("exact_payload", "global_hard_block", "raw_content", "type_policy")


class TestSourceAuthority(source.SourceBindingAuthority):
    def __init__(self, binding):
        self.binding = deepcopy(binding)

    def supports_binding_type(self, binding_type):
        return binding_type == "generated_only"

    def resolve_source_binding(self, generator_identity, generator_execution_id):
        return deepcopy(self.binding)

    def resolve_generation_execution_evidence(self, generator_identity, generator_execution_id):
        return source.GenerationExecutionEvidence(
            deepcopy(GENERATOR), "execution-1", "1.0", "generation-input-v1",
            "development-artifact-generation-input", (SAFE_HASH,),
        )


class TestScanAuthority(scan.SecurityScanAuthority):
    def __init__(self):
        self.records = {}

    def register(self, evidence):
        previous = self.records.get(evidence["scan_evidence_id"])
        if previous is not None and previous != evidence:
            return "security_scan_execution_conflict"
        self.records[evidence["scan_evidence_id"]] = deepcopy(evidence)
        return "security_scan_execution_idempotent" if previous is not None else "security_scan_execution_recorded"

    def resolve_scan_evidence(self, scan_evidence_id):
        value = self.records.get(scan_evidence_id)
        return deepcopy(value) if value is not None else None

    def resolve_test_scan_proof(self, scan_evidence_id):
        evidence = self.records.get(scan_evidence_id)
        if evidence is None:
            return None
        return scan.TestSecurityScanProof(
            evidence["scanner_id"], evidence["scanner_version"], evidence["security_policy_version"],
            evidence["artifact_type_policy_version"], evidence["payload_hash"],
            evidence["scan_evidence_id"], evidence["evidence_hash"],
            evidence["scan_started_at"], evidence["scan_completed_at"], "test-scan-adapter",
        )


class DeterministicTestScanner:
    """Test-only Scanner; it has no production authority capability."""

    def __init__(self, status):
        self.status = status

    def scan(self, candidate_identity, exact_payload_bytes):
        complete = "unknown" if self.status == "unknown" else "completed"
        reasons = {
            "pass": (), "review_required": ("contextual_finding",),
            "blocked": ("credential_pattern_detected",),
            "unknown": ("scanner_unavailable",),
        }[self.status]
        locations = (
            {"state": "present", "locations": [{"location_type": "section_id", "section_id": "summary"}]}
            if self.status == "review_required" else {"state": "none"}
        )
        review = (
            {"state": "human_review_required", "allowed_action_types": [
                "policy_decision_required", "false_positive_confirmed", "candidate_revision_required",
            ], "reason_codes": ["contextual_finding"]}
            if self.status == "review_required" else {"state": "not_required"}
        )
        return scan.SecurityScanResult(
            self.status, tuple(
                {"check_id": check, "completion_status": complete} for check in reversed(CHECKS)
            ), tuple(reversed(reasons)), locations, review,
            "2026-07-20T01:00:00Z", "2026-07-20T01:00:01Z",
        )


def source_binding():
    return source.build_generated_only_binding(GENERATOR, "execution-1", (SAFE_HASH,))


def candidate():
    binding = source_binding()
    return {
        "candidate_schema_version": "1.0", "candidate_id": "candidate-1",
        "artifact_type": "plan", "logical_artifact_id": "main-plan",
        "candidate_revision": 1, "artifact_lifecycle_status": "candidate",
        "payload_hash": PAYLOAD_HASH, "payload_format": "markdown",
        "subject_binding": {"binding_type": "none"}, "generated_by": deepcopy(GENERATOR),
        "source_binding": binding,
    }


def build(status="pass", evidence_id="scan-evidence-1"):
    item = candidate()
    built = scan.build_scan_evidence_for_test(
        item, PAYLOAD, evidence_id, SCANNER, "development-security-v1",
        "artifact-security-v1", DeterministicTestScanner(status).scan(item, PAYLOAD),
        TestSourceAuthority(item["source_binding"]),
    )
    assert built.scan_evidence is not None
    return item, built.scan_evidence


def validate(evidence, item=None, authority=None):
    item = item or candidate()
    authority = authority or TestScanAuthority()
    authority.register(evidence)
    return scan.validate_scan_evidence_with_authority_for_test(evidence, item, authority)


def production_source_fixture(item):
    # unittest discovery reloads shared modules in other test files before execution.
    # Resolve the composition module at call time so the production validator and
    # fixture always operate on the same installed authority singleton.
    current_adapter = sys.modules["source_binding_trusted_adapter"]
    return current_adapter._production_source_provenance_composition_fixture_for_test(
        item["source_binding"], (SAFE_HASH,),
    )


class SchemaAndStructureTests(unittest.TestCase):
    def test_policy_and_all_four_statuses_are_closed_and_valid(self):
        for status in ("pass", "review_required", "blocked", "unknown"):
            with self.subTest(status=status):
                _, evidence = build(status)
                self.assertEqual(scan.validate_scan_evidence_structure(evidence).status, "valid")

    def test_exact_evidence_field_set_rejects_missing_and_extra_fields(self):
        _, evidence = build()
        for field in ("scanner_id", "scan_status", "payload_hash", "source_binding"):
            with self.subTest(missing=field):
                changed = deepcopy(evidence); del changed[field]
                self.assertEqual(scan.validate_scan_evidence_structure(changed).reason_code, "security_scan_schema_invalid")
        for field in ("candidate_identity_hash", "artifact_revision", "development_security_scan_binding", "details", "raw_secret"):
            with self.subTest(extra=field):
                changed = deepcopy(evidence); changed[field] = SAFE_HASH
                self.assertEqual(scan.validate_scan_evidence_structure(changed).reason_code, "security_scan_schema_invalid")

    def test_unknown_status_and_unknown_reason_are_rejected(self):
        _, evidence = build()
        changed = deepcopy(evidence); changed["scan_status"] = "warning"
        changed["evidence_hash"] = scan.evidence_hash(changed)
        self.assertEqual(scan.validate_scan_evidence_structure(changed).reason_code, "security_scan_schema_invalid")
        _, blocked = build("blocked")
        blocked["reason_codes"] = ["free-form-finding"]
        blocked["evidence_hash"] = scan.evidence_hash(blocked)
        self.assertEqual(scan.validate_scan_evidence_structure(blocked).reason_code, "security_scan_findings_invalid")

    def test_blocked_requires_a_closed_hard_block_reason(self):
        _, evidence = build("blocked")
        evidence["reason_codes"] = []
        evidence["evidence_hash"] = scan.evidence_hash(evidence)
        self.assertEqual(scan.validate_scan_evidence_structure(evidence).reason_code, "security_scan_status_invalid")

    def test_malformed_scanner_result_fails_closed(self):
        item = candidate()
        malformed = scan.SecurityScanResult(
            "pass", ({"completion_status": "completed"},), (), {"state": "none"},
            {"state": "not_required"}, "2026-07-20T01:00:00Z", "2026-07-20T01:00:01Z",
        )
        result = scan.build_scan_evidence_for_test(
            item, PAYLOAD, "scan-evidence-1", SCANNER, "development-security-v1",
            "artifact-security-v1", malformed, TestSourceAuthority(item["source_binding"]),
        )
        self.assertEqual(result.reason_code, "security_scan_result_invalid")

    def test_status_combinations_are_rejected(self):
        for status in ("review_required", "blocked", "unknown"):
            with self.subTest(status=status):
                _, evidence = build(status)
                binding = {
                    "scan_evidence_id": evidence["scan_evidence_id"], "scan_evidence_hash": evidence["evidence_hash"],
                    "scanned_payload_hash": evidence["payload_hash"], "security_policy_version": evidence["security_policy_version"],
                    "artifact_type_policy_version": evidence["artifact_type_policy_version"], "scan_status": status,
                    "final_security_decision": "automatic_pass", "human_review_binding": {"state": "not_required"},
                }
                self.assertEqual(scan.validate_development_security_scan_binding(binding), "security_scan_binding_invalid")

    def test_canonical_findings_and_locations_make_hash_deterministic(self):
        item = candidate()
        result = DeterministicTestScanner("review_required").scan(item, PAYLOAD)
        first = scan.build_scan_evidence_for_test(
            item, PAYLOAD, "scan-evidence-1", SCANNER, "development-security-v1",
            "artifact-security-v1", result, TestSourceAuthority(item["source_binding"]),
        ).scan_evidence
        changed_result = scan.SecurityScanResult(
            result.scan_status, tuple(reversed(result.completed_checks)), tuple(reversed(result.reason_codes)),
            result.safe_locations, result.review_requirement, result.scan_started_at, result.scan_completed_at,
        )
        second = scan.build_scan_evidence_for_test(
            item, PAYLOAD, "scan-evidence-1", SCANNER, "development-security-v1",
            "artifact-security-v1", changed_result, TestSourceAuthority(item["source_binding"]),
        ).scan_evidence
        self.assertEqual(first, second)


class BindingAndAuthorityTests(unittest.TestCase):
    def test_candidate_five_fields_and_complete_source_binding_match(self):
        item, evidence = build(); authority = TestScanAuthority(); authority.register(evidence)
        self.assertEqual(scan.validate_scan_evidence_with_authority_for_test(evidence, item, authority).status, "valid")
        for field, reason, replacement in (
            ("artifact_type", "security_scan_artifact_type_mismatch", "adr"),
            ("logical_artifact_id", "security_scan_logical_artifact_id_mismatch", "other"),
            ("payload_hash", "security_scan_payload_hash_mismatch", "b" * 64),
            ("payload_format", "security_scan_payload_format_mismatch", "yaml"),
        ):
            with self.subTest(field=field):
                changed = deepcopy(item); changed[field] = replacement
                self.assertEqual(scan.validate_scan_evidence_with_authority_for_test(evidence, changed, authority).reason_code, reason)
        changed = deepcopy(item)
        changed["source_binding"]["generation_input_fingerprint"] = "b" * 64
        self.assertEqual(
            scan.validate_scan_evidence_with_authority_for_test(evidence, changed, authority).reason_code,
            "security_scan_source_binding_mismatch",
        )

    def test_evidence_tampering_is_rejected(self):
        _, evidence = build()
        for field, value in (
            ("scan_status", "blocked"), ("reason_codes", ["credential_pattern_detected"]),
            ("security_policy_version", "other-policy"), ("payload_hash", "b" * 64),
        ):
            with self.subTest(field=field):
                changed = deepcopy(evidence); changed[field] = value
                self.assertNotEqual(scan.validate_scan_evidence_structure(changed).status, "valid")
        changed = deepcopy(evidence); changed["source_binding"]["source_binding_hash"] = "b" * 64
        self.assertEqual(scan.validate_scan_evidence_structure(changed).reason_code, "security_scan_source_binding_mismatch")

    def test_generic_and_caller_authored_evidence_fail_production(self):
        item, evidence = build()
        class Evil(scan.SecurityScanAuthority):
            def resolve_scan_evidence(self, scan_evidence_id): return evidence
            def resolve_test_scan_proof(self, scan_evidence_id): return None
        with production_source_fixture(item):
            self.assertEqual(
                scan.validate_scan_evidence_production(evidence, item).reason_code,
                "security_scan_production_authority_required",
            )
        with self.assertRaises(TypeError):
            scan.validate_scan_evidence_production(evidence, item, Evil())
        self.assertFalse(hasattr(adapter, "ProductionSecurityScanExecutionAttestation"))

    def test_authority_exact_record_and_execution_conflict(self):
        item, evidence = build(); authority = TestScanAuthority()
        self.assertEqual(authority.register(evidence), "security_scan_execution_recorded")
        self.assertEqual(authority.register(evidence), "security_scan_execution_idempotent")
        changed = deepcopy(evidence); changed["scan_completed_at"] = "2026-07-20T01:00:02Z"
        changed["evidence_hash"] = scan.evidence_hash(changed)
        self.assertEqual(authority.register(changed), "security_scan_execution_conflict")
        self.assertEqual(scan.validate_scan_evidence_with_authority_for_test(changed, item, authority).reason_code, "security_scan_authority_invalid")

    def test_only_authority_validated_pass_evidence_derives_exact_binding(self):
        item, evidence = build(); authority = TestScanAuthority(); authority.register(evidence)
        structural = scan.validate_scan_evidence_structure(evidence)
        self.assertEqual(
            scan.derive_development_security_scan_binding(structural)[1],
            "security_scan_binding_derivation_not_allowed",
        )
        validated = scan.validate_scan_evidence_with_authority_for_test(evidence, item, authority)
        security_binding, reason = scan.derive_development_security_scan_binding(validated)
        self.assertEqual((security_binding, reason), (None, "security_scan_binding_derivation_not_allowed"))
        with production_source_fixture(item):
            with adapter._production_scanner_composition_fixture_for_test(evidence):
                security_binding, reason = scan.validate_and_derive_development_security_scan_binding_production(
                    item, PAYLOAD, evidence,
                )
        self.assertEqual(reason, "security_scan_binding_valid")
        self.assertEqual(set(security_binding), {
            "scan_evidence_id", "scan_evidence_hash", "scanned_payload_hash",
            "security_policy_version", "artifact_type_policy_version", "scan_status",
            "final_security_decision", "human_review_binding",
        })
        self.assertEqual(security_binding["final_security_decision"], "automatic_pass")
        changed = dict(security_binding); changed["scanner_id"] = "development-security-scanner"
        self.assertEqual(scan.validate_development_security_scan_binding(changed), "security_scan_binding_invalid")

    def test_non_pass_evidence_never_derives_automatic_pass(self):
        for status, reason in (
            ("review_required", "security_scan_review_required"),
            ("blocked", "security_scan_blocked"), ("unknown", "security_scan_unknown"),
        ):
            with self.subTest(status=status):
                item, evidence = build(status)
                with production_source_fixture(item):
                    with adapter._production_scanner_composition_fixture_for_test(evidence):
                        actual = scan.validate_and_derive_development_security_scan_binding_production(
                            item, PAYLOAD, evidence,
                        )
                self.assertEqual(actual, (None, reason))

    def test_validated_evidence_is_a_deep_immutable_snapshot(self):
        item, evidence = build(); authority = TestScanAuthority(); authority.register(evidence)
        validated = scan.validate_scan_evidence_with_authority_for_test(evidence, item, authority)
        original_payload_hash = validated.scan_evidence["payload_hash"]
        original_source_hash = validated.scan_evidence["source_binding"]["source_binding_hash"]
        evidence["payload_hash"] = "b" * 64
        evidence["source_binding"]["source_binding_hash"] = "c" * 64
        evidence["reason_codes"].append("scanner_unavailable")
        evidence["safe_locations"] = {"state": "present", "locations": []}
        self.assertEqual(validated.scan_evidence["payload_hash"], original_payload_hash)
        self.assertEqual(validated.scan_evidence["source_binding"]["source_binding_hash"], original_source_hash)
        self.assertEqual(validated.scan_evidence["reason_codes"], ())
        self.assertEqual(dict(validated.scan_evidence["safe_locations"]), {"state": "none"})
        with self.assertRaises(TypeError):
            validated.scan_evidence["payload_hash"] = "d" * 64

    def test_production_snapshot_is_stable_after_caller_mutation(self):
        item, evidence = build()
        with production_source_fixture(item):
            with adapter._production_scanner_composition_fixture_for_test(evidence):
                validated = scan.validate_scan_evidence_production(evidence, item)
                evidence["payload_hash"] = "b" * 64
                evidence["evidence_hash"] = "c" * 64
                security_binding, reason = scan._derive_binding_from_production_snapshot(validated)
        self.assertEqual(reason, "security_scan_binding_valid")
        self.assertEqual(security_binding["scanned_payload_hash"], PAYLOAD_HASH)
        self.assertNotEqual(security_binding["scan_evidence_hash"], "c" * 64)

    def test_wrong_or_empty_production_adapter_identity_is_rejected(self):
        item, evidence = build()
        for identity in ("test-scan-adapter", ""):
            with self.subTest(identity=identity):
                with production_source_fixture(item):
                    with adapter._production_scanner_composition_fixture_for_test(evidence, adapter_identity=identity):
                        result = scan.validate_scan_evidence_production(evidence, item)
                self.assertEqual(result.reason_code, "security_scan_production_authority_required")

    def test_production_attestation_has_no_public_constructor_and_rejects_fake_token(self):
        _, evidence = build()
        self.assertFalse(hasattr(adapter, "ProductionSecurityScanExecutionAttestation"))
        with self.assertRaises(TypeError):
            adapter._ProductionSecurityScanExecutionAttestation(
                token=object(), evidence=evidence,
                adapter_identity=adapter.PRODUCTION_SCANNER_ADAPTER_IDENTITY,
            )

    def test_registered_field_path_is_allowed_and_unknown_paths_fail_closed(self):
        item, evidence = build("review_required")
        evidence["safe_locations"] = {
            "state": "present", "locations": [
                {"location_type": "field_path", "field_path": ["payload", "decisions"]},
            ],
        }
        evidence["evidence_hash"] = scan.evidence_hash(evidence)
        self.assertEqual(scan.validate_scan_evidence_structure(evidence).status, "valid")
        for path in (
            ["payload", "some_unknown_field"], ["payload", "0"],
            ["/tmp", "secret"], ["payload", "*"],
        ):
            with self.subTest(path=path):
                changed = deepcopy(evidence)
                changed["safe_locations"]["locations"][0]["field_path"] = path
                changed["evidence_hash"] = scan.evidence_hash(changed)
                self.assertNotEqual(scan.validate_scan_evidence_structure(changed).status, "valid")
        changed = deepcopy(evidence); changed["artifact_type"] = "adr"
        changed["evidence_hash"] = scan.evidence_hash(changed)
        self.assertEqual(
            scan.validate_scan_evidence_structure(changed).reason_code,
            "security_scan_field_path_unregistered",
        )
        changed = deepcopy(evidence); changed["artifact_type"] = "unregistered"
        changed["evidence_hash"] = scan.evidence_hash(changed)
        self.assertEqual(
            scan.validate_scan_evidence_structure(changed).reason_code,
            "security_scan_policy_mismatch",
        )

    def test_exact_payload_bytes_are_hash_bound_without_normalization(self):
        item = candidate()
        result = DeterministicTestScanner("pass").scan(item, PAYLOAD)
        changed = scan.build_scan_evidence_for_test(
            item, PAYLOAD + b"\n", "scan-evidence-1", SCANNER, "development-security-v1",
            "artifact-security-v1", result, TestSourceAuthority(item["source_binding"]),
        )
        self.assertEqual(changed.reason_code, "security_scan_payload_hash_mismatch")


if __name__ == "__main__":
    unittest.main()
