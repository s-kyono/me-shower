from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / ".codex/agents/repository-publish/shared/run_registry.py"
SPEC = importlib.util.spec_from_file_location("repository_publish_run_registry", PATH)
assert SPEC and SPEC.loader
registry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry)


def test_running_and_completed_run_are_not_claimed_twice(tmp_path: Path) -> None:
    run_id = "rpr-" + "a" * 64
    claimed, first = registry.claim_run(tmp_path, run_id)
    assert claimed and first["status"] == "running"
    claimed, existing = registry.claim_run(tmp_path, run_id)
    assert not claimed and existing["status"] == "running"
    registry.record_result(tmp_path, run_id, {"repository_publish_run_id": run_id, "status": "completed"})
    claimed, existing = registry.claim_run(tmp_path, run_id)
    assert not claimed and existing["status"] == "completed"
