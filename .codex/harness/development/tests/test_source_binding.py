from __future__ import annotations

from copy import deepcopy
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


identity = load_module("artifact_identity", ROOT / "shared/artifact_identity.py")
binding = load_module("source_binding", ROOT / "shared/source_binding.py")
adapter = load_module("source_binding_trusted_adapter", ROOT / "shared/source_binding_trusted_adapter.py")
revision = load_module("artifact_revision", ROOT / "shared/artifact_revision.py")

HASH_A, HASH_B, HASH_C = (character * 64 for character in "abc")
GENERATOR = {"source_id": "assemble-plan", "source_version": "1.0"}


class TestSourceBindingAuthority(binding.SourceBindingAuthority):
    """Test-only authority; it never creates a production resolver or attestation."""

    def __init__(self):
        self.index = binding.SourceBindingExecutionIndex()
        self.evidence = {}

    def register(self, record, safe_hashes=(HASH_A,)):
        outcome = self.index.record(record)
        if outcome == "source_binding_execution_conflict":
            raise ValueError("source_binding_execution_conflict")
        if record["binding_type"] == "generated_only":
            key = (
                record["generator_identity"]["source_id"],
                record["generator_identity"]["source_version"],
                record["generator_execution_id"],
            )
            self.evidence[key] = binding.GenerationExecutionEvidence(
                deepcopy(record["generator_identity"]), record["generator_execution_id"],
                "1.0", "generation-input-v1", "development-artifact-generation-input",
                tuple(safe_hashes),
            )

    def resolve_source_binding(self, generator_identity, generator_execution_id):
        return self.index.resolve(generator_identity, generator_execution_id)

    def supports_binding_type(self, binding_type):
        return binding_type in {"generated_only", "artifact_references", "repository_snapshot"}

    def resolve_generation_execution_evidence(self, generator_identity, generator_execution_id):
        key = (generator_identity["source_id"], generator_identity["source_version"], generator_execution_id)
        return self.evidence.get(key)


def generated(execution_id="execution-1", hashes=(HASH_A,)):
    return binding.build_generated_only_binding(GENERATOR, execution_id, hashes)


def logical_series(subject_revision=4):
    return {
        "identity_type": "subject_id_revision", "subject_type": "plan",
        "subject_id": "main-plan", "subject_revision": subject_revision,
    }


def reference(subject_revision=4, artifact_revision=2, content_hash=HASH_A):
    return {
        "artifact_type": "plan_review",
        "logical_artifact_id": identity.build_revision_scoped_logical_id("main-plan", subject_revision),
        "logical_series": logical_series(subject_revision),
        "artifact_revision": artifact_revision, "content_hash": content_hash,
    }


def artifact_binding(references):
    result = binding.build_artifact_references_binding(GENERATOR, "execution-refs", references)
    assert result.source_binding is not None
    return result.source_binding


def snapshot(repository_id="repository-1", snapshot_hash=HASH_B):
    return binding.build_repository_snapshot_binding(
        GENERATOR, "execution-snapshot",
        {"provider": "github", "repository_id": repository_id}, snapshot_hash,
    )


def candidate(record=None, generator=GENERATOR):
    return {
        "candidate_schema_version": "1.0", "candidate_id": "candidate-1",
        "artifact_type": "plan", "logical_artifact_id": "main-plan",
        "candidate_revision": 1, "artifact_lifecycle_status": "candidate",
        "payload_hash": HASH_C, "payload_format": "markdown",
        "subject_binding": {"binding_type": "none"},
        "generated_by": deepcopy(generator), "source_binding": deepcopy(record or generated()),
    }


class StructuralContractTests(unittest.TestCase):
    def test_generated_fingerprint_is_versioned_deterministic_and_domain_separated(self):
        first = generated()
        self.assertEqual(first, generated())
        self.assertEqual(first["generation_input_fingerprint_schema_version"], "1.0")
        self.assertEqual(first["generation_input_policy_version"], "generation-input-v1")
        self.assertEqual(first["generation_input_domain"], "development-artifact-generation-input")
        self.assertNotEqual(first["generation_input_fingerprint"], generated(hashes=(HASH_B,))["generation_input_fingerprint"])
        for field, value in (
            ("generation_input_policy_version", "other-policy"),
            ("generation_input_domain", "other-domain"),
        ):
            changed = deepcopy(first); changed[field] = value
            changed["source_binding_hash"] = binding.source_binding_hash(changed)
            self.assertEqual(binding.validate_source_binding_structure(changed).status, "invalid")

    def test_reference_order_is_canonical_and_series_is_complete(self):
        refs = [reference(5), reference(4)]
        first = artifact_binding(refs)
        second = artifact_binding(reversed(refs))
        self.assertEqual(first, second)
        self.assertNotEqual(first["source_references"][0]["logical_series"], first["source_references"][1]["logical_series"])
        changed = deepcopy(first); changed["source_references"][0]["logical_series"]["subject_revision"] = 9
        changed["source_reference_set_hash"] = binding.source_reference_set_hash(changed["source_references"])
        changed["source_binding_hash"] = binding.source_binding_hash(changed)
        self.assertEqual(binding.validate_source_binding_structure(changed).reason_code, "source_binding_logical_series_mismatch")

    def test_duplicate_and_content_conflict_use_identity_without_content_hash(self):
        duplicate = binding.build_artifact_references_binding(GENERATOR, "execution-refs", [reference(), reference()])
        self.assertEqual(duplicate.reason_code, "source_binding_reference_duplicate")
        conflict = binding.build_artifact_references_binding(
            GENERATOR, "execution-refs", [reference(content_hash=HASH_A), reference(content_hash=HASH_B)],
        )
        self.assertEqual(conflict.reason_code, "source_binding_artifact_reference_conflict")

    def test_repository_identity_kind_and_policy_are_integrity_protected(self):
        first, second = snapshot("repository-1"), snapshot("repository-2")
        self.assertNotEqual(first["source_binding_hash"], second["source_binding_hash"])
        for field in ("repository_identity", "snapshot_kind", "snapshot_policy_version"):
            changed = deepcopy(first); del changed[field]
            self.assertEqual(binding.validate_source_binding_structure(changed).status, "invalid")
        changed = deepcopy(first); changed["branch"] = "main"
        self.assertEqual(binding.validate_source_binding_structure(changed).reason_code, "source_binding_forbidden_field")

    def test_closed_variants_hashes_and_forbidden_content(self):
        records = (generated(), artifact_binding([reference()]), snapshot())
        for original in records:
            changed = deepcopy(original); changed["source_binding_hash"] = HASH_C
            self.assertEqual(binding.validate_source_binding_structure(changed).reason_code, "source_binding_integrity_invalid")
        changed = deepcopy(generated()); changed["repository_snapshot_hash"] = HASH_B
        self.assertEqual(binding.validate_source_binding_structure(changed).status, "invalid")
        for field in ("raw_source_content", "raw_tool_output", "prompt", "content", "secret", "credential", "absolute_path"):
            changed = deepcopy(generated()); changed[field] = "synthetic"
            self.assertEqual(binding.validate_source_binding_structure(changed).reason_code, "source_binding_forbidden_field")
        changed = deepcopy(artifact_binding([reference()]))
        changed["source_reference_set_hash"] = HASH_C
        self.assertEqual(
            binding.validate_source_binding_structure(changed).reason_code,
            "source_binding_reference_set_integrity_invalid",
        )


class AuthorityContractTests(unittest.TestCase):
    def test_registered_execution_validates_and_retry_is_idempotent(self):
        record = generated(); authority = TestSourceBindingAuthority()
        authority.register(record); authority.register(record)
        self.assertEqual(binding.validate_source_binding_authority(record, authority).status, "valid")

    def test_test_authority_validates_reference_and_snapshot_without_production_mint(self):
        authority = TestSourceBindingAuthority()
        for record in (artifact_binding([reference()]), snapshot()):
            authority.register(record)
            self.assertEqual(binding.validate_source_binding_authority(record, authority).status, "valid")
        self.assertEqual(
            binding.validate_source_binding_authority(
                artifact_binding([reference()]), adapter.PRODUCTION_SOURCE_PROVENANCE_AUTHORITY,
            ).reason_code,
            "source_binding_artifact_reference_unverified",
        )

    def test_caller_authored_binding_and_raw_or_arbitrary_authority_are_rejected(self):
        record = generated()
        self.assertEqual(binding.validate_source_binding_authority(record, {}).reason_code, "source_binding_authority_required")
        class Arbitrary:
            def resolve_source_binding(self, *args): return record
        self.assertEqual(binding.validate_source_binding_authority(record, Arbitrary()).reason_code, "source_binding_authority_required")
        self.assertEqual(
            binding.validate_source_binding_authority(record, adapter.PRODUCTION_SOURCE_PROVENANCE_AUTHORITY).reason_code,
            "source_binding_authority_invalid",
        )

    def test_production_entry_does_not_accept_generic_or_test_authority(self):
        record = generated()
        class Evil(binding.SourceBindingAuthority):
            def supports_binding_type(self, binding_type): return True
            def resolve_source_binding(self, *args): return record
            def resolve_generation_execution_evidence(self, *args):
                return binding.GenerationExecutionEvidence(
                    GENERATOR, "execution-1", "1.0", "generation-input-v1",
                    "development-artifact-generation-input", (HASH_A,),
                )
        self.assertEqual(
            binding.validate_candidate_source_binding_production(candidate(record)).reason_code,
            "source_binding_production_authority_required",
        )
        with self.assertRaises(TypeError):
            binding.validate_candidate_source_binding_production(candidate(record), Evil())

    def test_same_hash_with_different_body_is_execution_conflict(self):
        record = generated(); index = binding.SourceBindingExecutionIndex()
        self.assertEqual(index.record(record), "source_binding_execution_recorded")
        changed = deepcopy(record)
        changed["generation_input_fingerprint"] = HASH_B
        self.assertEqual(index.record(changed), "source_binding_execution_conflict")

    def test_production_resolver_has_no_store_injection(self):
        with self.assertRaises(TypeError):
            adapter.ProductionSourceProvenanceResolver(object())
        self.assertIsNone(adapter.PRODUCTION_SOURCE_PROVENANCE_AUTHORITY.resolve_source_binding(GENERATOR, "execution-1"))

    def test_execution_rebinding_conflicts_for_every_variant(self):
        pairs = (
            (generated(), generated(hashes=(HASH_B,))),
            (artifact_binding([reference()]), artifact_binding([reference(5)])),
            (snapshot(), snapshot(snapshot_hash=HASH_C)),
        )
        for first, changed in pairs:
            authority = TestSourceBindingAuthority(); authority.register(first)
            with self.assertRaisesRegex(ValueError, "source_binding_execution_conflict"):
                authority.register(changed)

    def test_candidate_requires_matching_authoritative_binding(self):
        record = generated(); authority = TestSourceBindingAuthority(); authority.register(record)
        self.assertEqual(binding.validate_candidate_source_binding_with_authority(candidate(record), authority).status, "valid")
        forged = generated(hashes=(HASH_B,))
        self.assertEqual(binding.validate_candidate_source_binding_with_authority(candidate(forged), authority).reason_code, "source_binding_fingerprint_mismatch")
        mismatch = candidate(record, {"source_id": "other", "source_version": "1.0"})
        self.assertEqual(binding.validate_candidate_source_binding_with_authority(mismatch, authority).reason_code, "source_binding_generator_identity_mismatch")

    def test_candidate_identity_hash_covers_complete_binding(self):
        original = candidate(generated())
        changed = candidate(generated(hashes=(HASH_B,)))
        self.assertNotEqual(revision.candidate_identity_hash(original), revision.candidate_identity_hash(changed))

    def test_fingerprint_is_recomputed_from_trusted_safe_input_evidence(self):
        record = generated(hashes=(HASH_A, HASH_B))
        authority = TestSourceBindingAuthority(); authority.register(record, safe_hashes=(HASH_B, HASH_A))
        self.assertEqual(binding.validate_source_binding_authority(record, authority).status, "valid")

        mismatch = TestSourceBindingAuthority(); mismatch.register(record, safe_hashes=(HASH_C,))
        self.assertEqual(
            binding.validate_source_binding_authority(record, mismatch).reason_code,
            "source_binding_fingerprint_mismatch",
        )

        key = (GENERATOR["source_id"], GENERATOR["source_version"], "execution-1")
        authority.evidence[key] = binding.GenerationExecutionEvidence(
            GENERATOR, "execution-1", "1.0", "other-policy",
            "development-artifact-generation-input", (HASH_A, HASH_B),
        )
        self.assertEqual(
            binding.validate_source_binding_authority(record, authority).reason_code,
            "source_binding_fingerprint_policy_mismatch",
        )


if __name__ == "__main__":
    unittest.main()
