from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("artifact_identity", ROOT / "shared/artifact_identity.py")
identity = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["artifact_identity"] = identity
SPEC.loader.exec_module(identity)


class RevisionScopedLogicalIdentityTests(unittest.TestCase):
    def test_builds_the_closed_revision_scoped_form(self):
        cases = (
            ("main-plan", 1, "main-plan-r0001"),
            ("main-plan", 4, "main-plan-r0004"),
            ("implementation-main", 12, "implementation-main-r0012"),
            ("main-plan", 10000, "main-plan-r10000"),
        )
        for subject_id, revision, expected in cases:
            with self.subTest(subject_id=subject_id, revision=revision):
                self.assertEqual(identity.build_revision_scoped_logical_id(subject_id, revision), expected)

    def test_validates_against_the_same_canonical_builder(self):
        self.assertTrue(identity.validate_revision_scoped_logical_id("main-plan-r0004", "main-plan", 4))
        for logical_id in ("main-plan-r0005", "main-plan-r4", "main-plan-r0000"):
            with self.subTest(logical_id=logical_id):
                self.assertFalse(identity.validate_revision_scoped_logical_id(logical_id, "main-plan", 4))

    def test_rejects_invalid_subjects_and_revision_domains(self):
        cases = (("../plan", 4), ("con", 4), ("main-plan", True), ("main-plan", 0),
                 ("main-plan", identity.MAX_REVISION + 1))
        for subject_id, revision in cases:
            with self.subTest(subject_id=subject_id, revision=revision):
                with self.assertRaises(ValueError):
                    identity.build_revision_scoped_logical_id(subject_id, revision)
                self.assertFalse(identity.validate_revision_scoped_logical_id("main-plan-r0004", subject_id, revision))


if __name__ == "__main__":
    unittest.main()
