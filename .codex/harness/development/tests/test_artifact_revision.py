from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

import yaml
from jsonschema import ValidationError, validators
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


identity = load_module("artifact_identity", ROOT / "shared/artifact_identity.py")
revision = load_module("artifact_revision", ROOT / "shared/artifact_revision.py")
adapter = load_module("artifact_revision_trusted_adapter", ROOT / "shared/artifact_revision_trusted_adapter.py")

HASH_A, HASH_B, HASH_C, HASH_D = (character * 64 for character in "abcd")
NOW = "2026-07-20T10:00:00Z"
ALLOCATOR = {"source_id": "persistence-orchestrator", "source_version": "1.0"}


def candidate_factory(artifact_type="plan", logical_id=None, candidate_revision=3):
    subject_type = "implementation" if artifact_type in {"implementation_review", "release_gate", "fix_request"} else "plan"
    subject_id = "implementation-main" if subject_type == "implementation" else "main-plan"
    subject_revision = 2 if subject_type == "implementation" else 4
    subject_hash = HASH_C if subject_type == "implementation" else HASH_A
    if logical_id is None:
        logical_id = subject_id if artifact_type in {"decision_record"} else (
            identity.build_revision_scoped_logical_id(subject_id, subject_revision) if artifact_type not in {"plan", "adr"} else "main-plan"
        )
    return {
        "candidate_schema_version": "1.0", "candidate_id": f"{artifact_type}-candidate-1",
        "artifact_type": artifact_type, "logical_artifact_id": logical_id,
        "candidate_revision": candidate_revision, "artifact_lifecycle_status": "candidate",
        "payload_hash": HASH_B, "payload_format": "markdown",
        "subject_binding": {"binding_type": "bound", "subject_type": subject_type, "subject_id": subject_id, "subject_revision": subject_revision, "subject_hash": subject_hash},
        "generated_by": {"source_id": "assemble-plan", "source_version": "1.0"},
    }


def revision_binding_factory(artifact_type="plan"):
    values = {
        "plan": {"binding_type": "plan", "accepted_decision_set_hash": HASH_A},
        "design_lock": {"binding_type": "plan_subject", "subject_plan_logical_artifact_id": "main-plan", "subject_revision": 4, "subject_content_hash": HASH_A, "accepted_decision_set_hash": HASH_C},
        "implementation_review": {"binding_type": "implementation_subject", "subject_implementation_logical_artifact_id": "implementation-main", "implementation_revision": 2, "repository_snapshot_hash": HASH_C},
        "adr": {"binding_type": "decision", "decision_revision": 2, "decision_content_hash": HASH_C},
        "authorization_grant": {"binding_type": "authorization", "authorization_revision": 2, "authorized_plan_revision": 4, "authorized_plan_content_hash": HASH_A, "accepted_decision_set_hash": HASH_C},
    }
    return deepcopy(values[artifact_type])


def expected_latest_factory(state="absent", artifact_revision=4, content_hash=HASH_A):
    return {"state": "absent"} if state == "absent" else {"state": "present", "artifact_revision": artifact_revision, "content_hash": content_hash}


def allocation_request_factory(candidate=None, expected_latest=None, requested_by=None, allocation_id="allocation-1", binding=None):
    candidate = candidate or candidate_factory()
    request = {
        "allocation_schema_version": "1.0", "allocation_record_id": allocation_id,
        "requested_by": deepcopy(requested_by or ALLOCATOR), "artifact_type": candidate["artifact_type"],
        "logical_artifact_id": candidate["logical_artifact_id"], "candidate_id": candidate["candidate_id"],
        "candidate_revision": candidate["candidate_revision"], "candidate_payload_hash": candidate["payload_hash"],
        "candidate_identity_hash": revision.candidate_identity_hash(candidate),
        "expected_latest": deepcopy(expected_latest or expected_latest_factory()),
        "revision_binding": deepcopy(binding or revision_binding_factory(candidate["artifact_type"])),
        "allocation_request_fingerprint": "0" * 64,
    }
    request["allocation_request_fingerprint"] = revision.allocation_request_fingerprint(request)
    return request


def allocation_record_factory(candidate=None, request=None, allocated_revision=1):
    candidate = candidate or candidate_factory()
    request = request or allocation_request_factory(candidate)
    record = {
        "allocation_schema_version": "1.0", "allocation_record_id": request["allocation_record_id"],
        "artifact_type": request["artifact_type"], "logical_artifact_id": request["logical_artifact_id"],
        "allocated_artifact_revision": allocated_revision, "expected_latest": deepcopy(request["expected_latest"]),
        "observed_latest": deepcopy(request["expected_latest"]), "candidate_id": candidate["candidate_id"],
        "candidate_revision": candidate["candidate_revision"], "candidate_payload_hash": candidate["payload_hash"],
        "candidate_identity_hash": revision.candidate_identity_hash(candidate), "revision_binding": deepcopy(request["revision_binding"]),
        "allocation_request_fingerprint": request["allocation_request_fingerprint"], "allocation_status": "allocated",
        "allocated_by": deepcopy(request["requested_by"]), "allocated_at": NOW, "allocation_record_hash": "0" * 64,
    }
    record["allocation_record_hash"] = revision.allocation_record_hash(record)
    return record


def revision_evidence_factory(candidate=None, record=None, content_hash=HASH_A):
    candidate = candidate or candidate_factory()
    record = record or allocation_record_factory(candidate)
    evidence = {
        "artifact_type": record["artifact_type"], "logical_artifact_id": record["logical_artifact_id"],
        "artifact_revision": record["allocated_artifact_revision"], "candidate_id": candidate["candidate_id"],
        "candidate_revision": candidate["candidate_revision"], "candidate_payload_hash": candidate["payload_hash"],
        "candidate_identity_hash": revision.candidate_identity_hash(candidate), "content_hash": content_hash,
        "allocation_record_id": record["allocation_record_id"], "allocation_record_hash": record["allocation_record_hash"],
        "revision_evidence_hash": "0" * 64,
    }
    evidence["revision_evidence_hash"] = revision.revision_evidence_hash(evidence)
    return evidence


def trusted_revision_store_factory(*, artifact_type="plan", logical_id="main-plan", state="absent", latest_revision=None,
                                   latest_hash=None, reserved=None, revision_index=None, allocation_index=None,
                                   allocator_identity=None):
    return adapter.VerifiedRevisionStoreSnapshot(
        artifact_type, logical_id, state, latest_revision, latest_hash, frozenset(reserved or set()),
        deepcopy(revision_index or {}), deepcopy(allocation_index or {}), deepcopy(allocator_identity or ALLOCATOR), NOW,
    )


def production_adapter_fixture(**store_overrides):
    return adapter.ProductionArtifactRevisionResolver(trusted_revision_store_factory(**store_overrides))


class ForgedResolver(revision.TrustedArtifactRevisionResolver):
    def resolve_revision_context(self, *args):
        return self.context if hasattr(self, "context") else {}


def allocate(candidate=None, request=None, resolver=None):
    candidate = candidate or candidate_factory()
    request = request or allocation_request_factory(candidate)
    if resolver is None:
        resolver = production_adapter_fixture(artifact_type=candidate["artifact_type"], logical_id=candidate["logical_artifact_id"])
    return revision.allocate_artifact_revision(candidate, request, resolver)


def present_fixture(candidate=None, request=None, revision_number=4, content_hash=HASH_A, reserved=None):
    candidate = candidate or candidate_factory()
    prior_request = allocation_request_factory(candidate, allocation_id="prior-allocation")
    prior_record = allocation_record_factory(candidate, prior_request, revision_number)
    evidence = revision_evidence_factory(candidate, prior_record, content_hash)
    return production_adapter_fixture(
        artifact_type=candidate["artifact_type"], logical_id=candidate["logical_artifact_id"], state="present",
        latest_revision=revision_number, latest_hash=content_hash, reserved=reserved,
        revision_index={revision_number: evidence}, allocation_index={prior_record["allocation_record_id"]: prior_record},
    )


class RevisionDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        domain = yaml.safe_load((ROOT / "schemas/revision-domains.schema.yaml").read_text())
        value = yaml.safe_load((ROOT / "schemas/revision-domain-value.schema.yaml").read_text())
        resources = Registry().with_resources([(domain["$id"], Resource.from_contents(domain)), (value["$id"], Resource.from_contents(value))])
        cls.validator = validators.validator_for(value)(value, registry=resources)

    def invalid(self, value):
        with self.assertRaises(ValidationError): self.validator.validate(value)

    def test_domains_and_policy_limits(self):
        for field in ("artifact_revision", "candidate_revision", "subject_revision", "state_revision", "decision_revision", "authorization_revision"):
            self.validator.validate({"revision_domain": field, field: 1})
            for bad in (0, -1, True, 1.5, "1", revision.MAX_REVISION + 1): self.invalid({"revision_domain": field, field: bad})

    def test_generic_and_cross_domain_fields_are_rejected(self):
        self.invalid({"revision": 4})
        self.invalid({"revision_domain": "subject_revision", "artifact_revision": 4})


class ResolverProvenanceTests(unittest.TestCase):
    def test_base_resolver_has_no_mint_helper(self):
        self.assertFalse(hasattr(revision.TrustedArtifactRevisionResolver, "_mint_context"))

    def test_raw_mapping_forged_resolver_and_exception_fail_closed(self):
        for resolver in ({}, ForgedResolver()):
            self.assertEqual(allocate(resolver=resolver).reason_code, "revision_context_provenance_invalid")
        class Raising(ForgedResolver):
            def resolve_revision_context(self, *args): raise RuntimeError("unavailable")
        self.assertEqual(allocate(resolver=Raising()).reason_code, "revision_context_provenance_invalid")

    def test_production_adapter_succeeds(self):
        self.assertEqual(allocate().status, "allocated")


class BindingAndIdentityTests(unittest.TestCase):
    def test_complete_binding_variants_allocate(self):
        for artifact_type in ("plan", "design_lock", "implementation_review", "adr", "authorization_grant"):
            candidate = candidate_factory(artifact_type)
            request = allocation_request_factory(candidate)
            self.assertEqual(allocate(candidate, request).status, "allocated")

    def test_missing_binding_fields_and_wrong_variant_are_rejected(self):
        cases = (("plan", "accepted_decision_set_hash"), ("design_lock", "subject_revision"),
                 ("design_lock", "subject_content_hash"), ("implementation_review", "repository_snapshot_hash"),
                 ("adr", "decision_revision"), ("authorization_grant", "authorization_revision"))
        for artifact_type, field in cases:
            candidate = candidate_factory(artifact_type)
            request = allocation_request_factory(candidate)
            del request["revision_binding"][field]
            request["allocation_request_fingerprint"] = revision.allocation_request_fingerprint(request)
            self.assertEqual(allocate(candidate, request).reason_code, "revision_binding_required")
        request = allocation_request_factory(); request["revision_binding"]["binding_type"] = "decision"
        request["allocation_request_fingerprint"] = revision.allocation_request_fingerprint(request)
        self.assertEqual(allocate(request=request).reason_code, "revision_binding_variant_mismatch")

    def test_subject_binding_must_match_candidate(self):
        for artifact_type, field in (("design_lock", "subject_revision"), ("implementation_review", "implementation_revision")):
            candidate = candidate_factory(artifact_type)
            request = allocation_request_factory(candidate)
            request["revision_binding"][field] += 1
            request["allocation_request_fingerprint"] = revision.allocation_request_fingerprint(request)
            self.assertEqual(allocate(candidate, request).reason_code, "revision_binding_invalid")

    def test_subject_revision_series_cannot_reuse_an_unscoped_logical_id(self):
        candidate = candidate_factory("design_lock")
        candidate["logical_artifact_id"] = "main-plan"
        request = allocation_request_factory(candidate)
        self.assertEqual(allocate(candidate, request).reason_code, "revision_series_identity_mismatch")

        candidate = candidate_factory("design_lock")
        candidate["logical_artifact_id"] = "main-plan-r0005"
        request = allocation_request_factory(candidate)
        self.assertEqual(allocate(candidate, request).reason_code, "revision_series_identity_mismatch")

    def test_allocator_three_way_identity_and_version(self):
        malicious = {"source_id": "malicious-skill", "source_version": "1.0"}
        request = allocation_request_factory(requested_by=malicious)
        self.assertEqual(allocate(request=request, resolver=production_adapter_fixture(allocator_identity=malicious)).reason_code, "revision_allocator_registry_mismatch")
        request = allocation_request_factory(requested_by={"source_id": "persistence-orchestrator", "source_version": "2.0"})
        self.assertEqual(allocate(request=request).reason_code, "revision_allocator_registry_mismatch")


class ContextConsistencyTests(unittest.TestCase):
    def test_absent_requires_all_indexes_empty(self):
        for kwargs in ({"reserved": {1}}, {"revision_index": {1: {}}}, {"allocation_index": {"x": {}}}):
            self.assertNotEqual(allocate(resolver=production_adapter_fixture(**kwargs)).status, "allocated")

    def test_latest_index_and_content_must_match(self):
        resolver = present_fixture(revision_number=4)
        snapshot = resolver._ProductionArtifactRevisionResolver__snapshot
        self.assertEqual(allocate(request=allocation_request_factory(expected_latest=expected_latest_factory("present")), resolver=resolver).status, "allocated")
        bad = trusted_revision_store_factory(state="present", latest_revision=3, latest_hash=HASH_A,
            revision_index=snapshot.existing_revision_index, allocation_index=snapshot.existing_allocation_records)
        self.assertEqual(allocate(resolver=adapter.ProductionArtifactRevisionResolver(bad)).reason_code, "revision_index_latest_mismatch")
        bad = trusted_revision_store_factory(state="present", latest_revision=4, latest_hash=HASH_C,
            revision_index=snapshot.existing_revision_index, allocation_index=snapshot.existing_allocation_records)
        self.assertEqual(allocate(resolver=adapter.ProductionArtifactRevisionResolver(bad)).reason_code, "revision_index_content_hash_mismatch")

    def test_persisted_reserved_overlap_and_dangling_allocation_are_rejected(self):
        resolver = present_fixture(revision_number=4)
        snapshot = resolver._ProductionArtifactRevisionResolver__snapshot
        overlap = adapter.ProductionArtifactRevisionResolver(trusted_revision_store_factory(state="present", latest_revision=4, latest_hash=HASH_A,
            reserved={4}, revision_index=snapshot.existing_revision_index, allocation_index=snapshot.existing_allocation_records))
        self.assertEqual(allocate(resolver=overlap).reason_code, "revision_reservation_conflict")
        dangling = allocation_record_factory(allocated_revision=7)
        bad_index = dict(snapshot.existing_allocation_records); bad_index[dangling["allocation_record_id"]] = dangling
        bad = production_adapter_fixture(state="present", latest_revision=4, latest_hash=HASH_A,
            revision_index=snapshot.existing_revision_index, allocation_index=bad_index)
        self.assertEqual(allocate(resolver=bad).reason_code, "revision_context_inconsistent")

    def test_consistent_gap_allocates_after_reservation(self):
        request = allocation_request_factory(expected_latest=expected_latest_factory("present"))
        self.assertEqual(allocate(request=request, resolver=present_fixture(revision_number=4, reserved={5, 7})).allocation_record["allocated_artifact_revision"], 8)


class EvidenceIntegrityTests(unittest.TestCase):
    def test_evidence_tampering_series_revision_allocation_and_nonhex_are_rejected(self):
        resolver = present_fixture(); snapshot = resolver._ProductionArtifactRevisionResolver__snapshot
        base = dict(snapshot.existing_revision_index[4])
        mutations = (("artifact_type", "adr"), ("logical_artifact_id", "other"), ("artifact_revision", 3),
                     ("allocation_record_hash", HASH_C), ("revision_evidence_hash", HASH_C), ("content_hash", "z" * 64))
        for field, value in mutations:
            evidence = dict(base); evidence[field] = value
            if field != "revision_evidence_hash": evidence["revision_evidence_hash"] = revision.revision_evidence_hash(evidence)
            bad = production_adapter_fixture(state="present", latest_revision=4, latest_hash=evidence.get("content_hash"),
                revision_index={4: evidence}, allocation_index=snapshot.existing_allocation_records)
            self.assertNotEqual(allocate(resolver=bad).status, "allocated")


class FingerprintAndAllocationTests(unittest.TestCase):
    def test_supplied_fingerprint_mismatch(self):
        request = allocation_request_factory(); request["allocation_request_fingerprint"] = HASH_C
        self.assertEqual(allocate(request=request).reason_code, "allocation_request_fingerprint_mismatch")

    def test_same_id_same_fingerprint_is_idempotent(self):
        candidate = candidate_factory(); request = allocation_request_factory(candidate, expected_latest_factory("present", 1, HASH_A))
        record = allocation_record_factory(candidate, request, 2); evidence = revision_evidence_factory(candidate, record)
        resolver = production_adapter_fixture(state="present", latest_revision=2, latest_hash=HASH_A,
            revision_index={2: evidence}, allocation_index={record["allocation_record_id"]: record})
        first = allocate(candidate, request, resolver); second = allocate(candidate, request, resolver)
        self.assertEqual(first, second); self.assertEqual(first.status, "idempotent_allocation")

    def test_same_id_changed_meaning_is_blocked(self):
        candidate = candidate_factory(); original = allocation_request_factory(candidate, expected_latest_factory("present", 1, HASH_A))
        record = allocation_record_factory(candidate, original, 2); evidence = revision_evidence_factory(candidate, record)
        resolver = production_adapter_fixture(state="present", latest_revision=2, latest_hash=HASH_A,
            revision_index={2: evidence}, allocation_index={record["allocation_record_id"]: record})
        for mutate in ("expected", "candidate", "allocator", "binding"):
            changed = deepcopy(original)
            if mutate == "expected": changed["expected_latest"] = expected_latest_factory("present", 1, HASH_C)
            elif mutate == "candidate": changed["candidate_identity_hash"] = HASH_C
            elif mutate == "allocator": changed["requested_by"] = {"source_id": "artifact-writer", "source_version": "1.0"}
            else: changed["revision_binding"]["accepted_decision_set_hash"] = HASH_D
            changed["allocation_request_fingerprint"] = revision.allocation_request_fingerprint(changed)
            self.assertNotEqual(allocate(candidate, changed, resolver).status, "idempotent_allocation")

    def test_limit_and_candidate_final_revision(self):
        request = allocation_request_factory(expected_latest=expected_latest_factory("present", revision.MAX_REVISION, HASH_A))
        self.assertEqual(allocate(request=request, resolver=present_fixture(revision_number=revision.MAX_REVISION)).reason_code, "revision_policy_limit_exceeded")
        for field in ("revision", "artifact_revision", "new_artifact_revision", "target_artifact_revision", "revision_path_segment", "content_hash"):
            candidate = candidate_factory(); candidate[field] = 1 if field != "content_hash" else HASH_A
            self.assertEqual(allocate(candidate=candidate).reason_code, "candidate_artifact_revision_forbidden")

    def test_candidate_revision_is_not_artifact_revision_and_no_path(self):
        record = allocate().allocation_record
        self.assertEqual((record["candidate_revision"], record["allocated_artifact_revision"]), (3, 1))
        for field in ("path", "repository_path", "revision_path_segment", "content_hash"): self.assertNotIn(field, record)


if __name__ == "__main__": unittest.main()
