from __future__ import annotations

from contextlib import ExitStack
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
scan_adapter = load_module(
    "development_security_scan_trusted_adapter",
    ROOT / "shared/development_security_scan_trusted_adapter.py",
)
write = load_module("artifact_write_request", ROOT / "shared/artifact_write_request.py")


PAYLOAD = b"---\ntitle: Safe plan\n---\n"
PAYLOAD_HASH = hashlib.sha256(PAYLOAD).hexdigest()
SAFE_HASH = "a" * 64
GENERATOR = {"source_id": "assemble-plan", "source_version": "1.0"}
SCANNER = {"scanner_id": "development-security-scanner", "scanner_version": "1.0"}
CHECKS = ("exact_payload", "global_hard_block", "raw_content", "type_policy")


class TestSourceAuthority(source.SourceBindingAuthority):
    def __init__(self, binding): self.binding = deepcopy(binding)
    def supports_binding_type(self, binding_type): return binding_type == "generated_only"
    def resolve_source_binding(self, generator_identity, generator_execution_id):
        return deepcopy(self.binding)
    def resolve_generation_execution_evidence(self, generator_identity, generator_execution_id):
        return source.GenerationExecutionEvidence(
            deepcopy(GENERATOR), "execution-1", "1.0", "generation-input-v1",
            "development-artifact-generation-input", (SAFE_HASH,),
        )


class TestScanAuthority(scan.SecurityScanAuthority):
    def __init__(self, evidence): self.evidence = deepcopy(evidence)
    def resolve_scan_evidence(self, scan_evidence_id): return deepcopy(self.evidence)
    def resolve_test_scan_proof(self, scan_evidence_id):
        evidence = self.evidence
        return scan.TestSecurityScanProof(
            evidence["scanner_id"], evidence["scanner_version"],
            evidence["security_policy_version"], evidence["artifact_type_policy_version"],
            evidence["payload_hash"], evidence["scan_evidence_id"], evidence["evidence_hash"],
            evidence["scan_started_at"], evidence["scan_completed_at"], "test-adapter",
        )


def thaw(value):
    if hasattr(value, "items"):
        return {key: thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [thaw(child) for child in value]
    return value


def candidate():
    binding = source.build_generated_only_binding(GENERATOR, "execution-1", (SAFE_HASH,))
    return {
        "candidate_schema_version": "1.0", "candidate_id": "candidate-1",
        "artifact_type": "plan", "logical_artifact_id": "main-plan",
        "candidate_revision": 1, "artifact_lifecycle_status": "candidate",
        "payload_hash": PAYLOAD_HASH, "payload_format": "markdown",
        "subject_binding": {"binding_type": "none"}, "generated_by": deepcopy(GENERATOR),
        "source_binding": binding,
    }


def evidence(item=None, status="pass"):
    item = item or candidate()
    reasons = () if status == "pass" else ({
        "review_required": "contextual_finding", "blocked": "credential_pattern_detected",
        "unknown": "scanner_unavailable",
    }[status],)
    locations = {"state": "none"}
    review = {"state": "not_required"}
    if status == "review_required":
        locations = {"state": "present", "locations": [
            {"location_type": "section_id", "section_id": "summary"},
        ]}
        review = {
            "state": "human_review_required",
            "allowed_action_types": [
                "candidate_revision_required", "false_positive_confirmed", "policy_decision_required",
            ],
            "reason_codes": ["contextual_finding"],
        }
    result = scan.SecurityScanResult(
        status, tuple({"check_id": check, "completion_status": "unknown" if status == "unknown" else "completed"} for check in CHECKS),
        reasons, locations, review, "2026-07-20T01:00:00Z", "2026-07-20T01:00:01Z",
    )
    built = scan.build_scan_evidence_for_test(
        item, PAYLOAD, "scan-evidence-1", SCANNER, "development-security-v1",
        "artifact-security-v1", result, TestSourceAuthority(item["source_binding"]),
    )
    assert built.scan_evidence is not None
    return built.scan_evidence


def build_test(expected=None, item=None, scan_evidence=None):
    item = item or candidate(); scan_evidence = scan_evidence or evidence(item)
    return write.build_write_request_for_test(
        candidate=item, exact_payload_bytes=PAYLOAD,
        expected_latest=expected or {"state": "absent"},
        request_id="write-request-1", idempotency_key="write-operation-1",
        scan_evidence=scan_evidence,
        source_authority=TestSourceAuthority(item["source_binding"]),
        scan_authority=TestScanAuthority(scan_evidence),
    )


def production_context(item, scan_evidence):
    stack = ExitStack()
    current_source_adapter = sys.modules["source_binding_trusted_adapter"]
    current_scan_adapter = sys.modules["development_security_scan_trusted_adapter"]
    stack.enter_context(
        current_source_adapter._production_source_provenance_composition_fixture_for_test(
            item["source_binding"], (SAFE_HASH,),
        )
    )
    stack.enter_context(current_scan_adapter._production_scanner_composition_fixture_for_test(scan_evidence))
    return stack


class WriteRequestSchemaTests(unittest.TestCase):
    def test_exact_thirteen_fields_and_prohibited_fields(self):
        result = build_test(); self.assertEqual(result.status, "valid")
        request = thaw(result.write_request)
        self.assertEqual(set(request), {
            "request_schema_version", "request_id", "idempotency_key", "request_fingerprint",
            "artifact_type", "logical_artifact_id", "payload", "payload_format", "payload_hash",
            "subject_binding", "expected_latest", "source_binding",
            "development_security_scan_binding",
        })
        for field in ("artifact_revision", "target_path", "repository_path", "artifact_reference", "raw_payload"):
            with self.subTest(field=field):
                changed = deepcopy(request); changed[field] = 1
                self.assertEqual(write.validate_write_request_structure(changed).status, "invalid")
        for field in tuple(request):
            with self.subTest(missing=field):
                changed = deepcopy(request); del changed[field]
                self.assertEqual(write.validate_write_request_structure(changed).status, "invalid")

    def test_payload_is_lossless_and_hash_bound(self):
        request = thaw(build_test().write_request)
        self.assertEqual(write.decode_payload(request["payload"]), PAYLOAD)
        changed = deepcopy(request); changed["payload"]["data"] = write.encode_payload(PAYLOAD + b"\n")["data"]
        self.assertEqual(write.validate_write_request_structure(changed).reason_code, "write_request_payload_hash_mismatch")
        changed = deepcopy(request); changed["payload_hash"] = hashlib.sha256(PAYLOAD + b"\n").hexdigest()
        changed["request_fingerprint"] = write.request_fingerprint(changed)
        self.assertEqual(write.validate_write_request_structure(changed).reason_code, "write_request_payload_hash_mismatch")
        changed = deepcopy(request); changed["payload_format"] = "yaml"
        changed["request_fingerprint"] = write.request_fingerprint(changed)
        self.assertNotEqual(write.validate_write_request_structure(changed).status, "valid")

    def test_subject_binding_and_logical_identity_are_registry_bound(self):
        request = thaw(build_test().write_request)
        changed = deepcopy(request)
        changed["subject_binding"] = {
            "binding_type": "bound", "subject_type": "plan", "subject_id": "main-plan",
            "subject_revision": 1, "subject_hash": SAFE_HASH,
        }
        changed["request_fingerprint"] = write.request_fingerprint(changed)
        self.assertEqual(write.validate_write_request_structure(changed).reason_code, "write_request_subject_binding_mismatch")
        changed = deepcopy(request); changed["logical_artifact_id"] = "Bad"
        changed["request_fingerprint"] = write.request_fingerprint(changed)
        self.assertNotEqual(write.validate_write_request_structure(changed).status, "valid")

    def test_expected_latest_variants_are_closed(self):
        self.assertEqual(build_test({"state": "absent"}).status, "valid")
        self.assertEqual(build_test({"state": "present", "artifact_revision": 4, "content_hash": SAFE_HASH}).status, "valid")
        request = thaw(build_test().write_request)
        for value in (
            {"state": "unknown"}, {"state": "absent", "artifact_revision": 1},
            {"state": "present", "artifact_revision": 1},
            {"state": "present", "content_hash": SAFE_HASH},
            {"state": "present", "artifact_revision": True, "content_hash": SAFE_HASH},
        ):
            with self.subTest(value=value):
                changed = deepcopy(request); changed["expected_latest"] = value
                changed["request_fingerprint"] = write.request_fingerprint(changed)
                self.assertEqual(write.validate_write_request_structure(changed).status, "invalid")


class WriteRequestAuthorityTests(unittest.TestCase):
    def test_test_entrypoint_builds_only_test_validated_snapshot(self):
        result = build_test()
        self.assertEqual((result.status, result.authority_kind), ("valid", "test"))
        item = candidate(); scan_evidence = evidence(item)
        production = write.validate_write_request_authority_production(
            result.write_request, candidate=item, exact_payload_bytes=PAYLOAD,
            scan_evidence=scan_evidence,
        )
        self.assertNotEqual(production.status, "valid")
        with self.assertRaises(TypeError):
            write.build_write_request_production(
                candidate=item, exact_payload_bytes=PAYLOAD, expected_latest={"state": "absent"},
                request_id="write-request-1", idempotency_key="write-operation-1",
                scan_evidence=scan_evidence, authority=TestScanAuthority(scan_evidence),
            )

    def test_production_entrypoint_uses_installed_authorities(self):
        item = candidate(); scan_evidence = evidence(item)
        without = write.build_write_request_production(
            candidate=item, exact_payload_bytes=PAYLOAD, expected_latest={"state": "absent"},
            request_id="write-request-1", idempotency_key="write-operation-1",
            scan_evidence=scan_evidence,
        )
        self.assertNotEqual(without.status, "valid")
        with production_context(item, scan_evidence):
            result = write.build_write_request_production(
                candidate=item, exact_payload_bytes=PAYLOAD, expected_latest={"state": "absent"},
                request_id="write-request-1", idempotency_key="write-operation-1",
                scan_evidence=scan_evidence,
            )
            validated = write.validate_write_request_authority_production(
                result.write_request, candidate=item, exact_payload_bytes=PAYLOAD,
                scan_evidence=scan_evidence,
            )
        self.assertEqual((result.status, result.authority_kind), ("valid", "production"))
        self.assertEqual((validated.status, validated.authority_kind), ("valid", "production"))

    def test_candidate_and_source_binding_mismatches_fail_closed(self):
        request = thaw(build_test().write_request); item = candidate(); scan_evidence = evidence(item)
        for field, value in (
            ("artifact_type", "adr"), ("logical_artifact_id", "other-plan"),
            ("payload_hash", "b" * 64), ("payload_format", "yaml"),
            ("subject_binding", {"binding_type": "bound", "subject_type": "plan", "subject_id": "main-plan", "subject_revision": 1, "subject_hash": SAFE_HASH}),
        ):
            with self.subTest(field=field):
                changed = deepcopy(request); changed[field] = value
                changed["request_fingerprint"] = write.request_fingerprint(changed)
                with production_context(item, scan_evidence):
                    actual = write.validate_write_request_authority_production(
                        changed, candidate=item, exact_payload_bytes=PAYLOAD,
                        scan_evidence=scan_evidence,
                    )
                self.assertNotEqual(actual.status, "valid")
        changed = deepcopy(item); changed["source_binding"]["source_binding_hash"] = "b" * 64
        with production_context(item, scan_evidence):
            result = write.validate_write_request_authority_production(
                request, candidate=changed, exact_payload_bytes=PAYLOAD, scan_evidence=scan_evidence,
            )
        self.assertNotEqual(result.status, "valid")
        invalid = deepcopy(item); del invalid["candidate_schema_version"]
        with production_context(item, scan_evidence):
            result = write.validate_write_request_authority_production(
                request, candidate=invalid, exact_payload_bytes=PAYLOAD, scan_evidence=scan_evidence,
            )
        self.assertEqual(result.reason_code, "write_request_candidate_invalid")

    def test_security_binding_requires_exact_production_evidence(self):
        item = candidate(); scan_evidence = evidence(item)
        with production_context(item, scan_evidence):
            result = write.build_write_request_production(
                candidate=item, exact_payload_bytes=PAYLOAD, expected_latest={"state": "absent"},
                request_id="write-request-1", idempotency_key="write-operation-1",
                scan_evidence=scan_evidence,
            )
        request = thaw(result.write_request)
        for field, value in (
            ("scan_evidence_hash", "b" * 64), ("scanned_payload_hash", "b" * 64),
            ("security_policy_version", "other-policy"),
        ):
            with self.subTest(field=field):
                changed = deepcopy(request)
                changed["development_security_scan_binding"][field] = value
                changed["request_fingerprint"] = write.request_fingerprint(changed)
                structural = write.validate_write_request_structure(changed)
                if field == "scanned_payload_hash":
                    self.assertNotEqual(structural.status, "valid")
                else:
                    self.assertEqual(structural.status, "valid")
        caller = deepcopy(request)
        with production_context(item, scan_evidence):
            self.assertEqual(
                write.validate_write_request_authority_production(
                    caller, candidate=item, exact_payload_bytes=PAYLOAD, scan_evidence=scan_evidence,
                ).status,
                "valid",
            )
        caller["development_security_scan_binding"]["scan_evidence_hash"] = "b" * 64
        caller["request_fingerprint"] = write.request_fingerprint(caller)
        with production_context(item, scan_evidence):
            self.assertNotEqual(
                write.validate_write_request_authority_production(
                    caller, candidate=item, exact_payload_bytes=PAYLOAD, scan_evidence=scan_evidence,
                ).status,
                "valid",
            )

    def test_non_pass_and_human_decision_never_build(self):
        for status in ("review_required", "blocked", "unknown"):
            with self.subTest(status=status):
                item = candidate(); scan_evidence = evidence(item, status)
                result = write.build_write_request_for_test(
                    candidate=item, exact_payload_bytes=PAYLOAD, expected_latest={"state": "absent"},
                    request_id="write-request-1", idempotency_key="write-operation-1",
                    scan_evidence=scan_evidence,
                    source_authority=TestSourceAuthority(item["source_binding"]),
                    scan_authority=TestScanAuthority(scan_evidence),
                )
                self.assertNotEqual(result.status, "valid")
        request = thaw(build_test().write_request)
        request["development_security_scan_binding"].update({
            "scan_status": "review_required", "final_security_decision": "human_false_positive_confirmed",
            "human_review_binding": {"state": "required", "human_action_id": "action-1", "human_action_record_hash": SAFE_HASH},
        })
        request["request_fingerprint"] = write.request_fingerprint(request)
        self.assertEqual(write.validate_write_request_structure(request).reason_code, "write_request_final_decision_not_allowed")


class WriteRequestIdentityTests(unittest.TestCase):
    def test_fingerprint_is_stable_and_identifiers_are_not_meaning(self):
        first = thaw(build_test().write_request)
        second = deepcopy(first); second["request_id"] = "write-request-2"; second["idempotency_key"] = "write-operation-2"
        self.assertEqual(write.request_fingerprint(first), write.request_fingerprint(second))
        second["expected_latest"] = {"state": "present", "artifact_revision": 1, "content_hash": SAFE_HASH}
        self.assertNotEqual(write.request_fingerprint(first), write.request_fingerprint(second))

    def test_immutable_snapshot_resists_post_build_mutation(self):
        item = candidate(); scan_evidence = evidence(item); expected = {"state": "absent"}
        result = write.build_write_request_for_test(
            candidate=item, exact_payload_bytes=PAYLOAD, expected_latest=expected,
            request_id="write-request-1", idempotency_key="write-operation-1",
            scan_evidence=scan_evidence, source_authority=TestSourceAuthority(item["source_binding"]),
            scan_authority=TestScanAuthority(scan_evidence),
        )
        original = result.write_request["request_fingerprint"]
        item["source_binding"]["source_binding_hash"] = "b" * 64
        item["subject_binding"]["binding_type"] = "changed"
        expected["state"] = "present"
        scan_evidence["payload_hash"] = "c" * 64
        self.assertEqual(result.write_request["request_fingerprint"], original)
        self.assertEqual(dict(result.write_request["expected_latest"]), {"state": "absent"})
        with self.assertRaises(TypeError): result.write_request["artifact_type"] = "adr"
        with self.assertRaises(TypeError): result.write_request["source_binding"]["source_binding_hash"] = "d" * 64

    def test_local_idempotency_and_complete_record_conflicts(self):
        request = thaw(build_test().write_request); index = write.WriteRequestLocalIndex()
        self.assertEqual(index.record(request), "write_request_recorded")
        self.assertEqual(index.record(deepcopy(request)), "write_request_idempotent")
        for field, value in (
            ("expected_latest", {"state": "present", "artifact_revision": 1, "content_hash": SAFE_HASH}),
            ("payload", write.encode_payload(PAYLOAD + b"\n")),
        ):
            with self.subTest(field=field):
                changed = deepcopy(request); changed[field] = value
                if field == "payload":
                    changed["payload_hash"] = hashlib.sha256(PAYLOAD + b"\n").hexdigest()
                    changed["development_security_scan_binding"]["scanned_payload_hash"] = changed["payload_hash"]
                changed["request_fingerprint"] = write.request_fingerprint(changed)
                self.assertEqual(index.record(changed), "write_request_identity_conflict")


if __name__ == "__main__":
    unittest.main()
