from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = ROOT / ".codex/tools/repository_snapshot/build_snapshot.py"
SPEC = importlib.util.spec_from_file_location("repository_snapshot", TOOL_PATH)
assert SPEC and SPEC.loader
snapshot_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot_tool)


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, stdout=subprocess.PIPE)


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "snapshot@example.invalid")
    git(root, "config", "user.name", "Snapshot Test")
    (root / "tracked.txt").write_bytes(b"initial\n")
    git(root, "add", "--", "tracked.txt")
    git(root, "commit", "-m", "initial")
    git(root, "switch", "-c", "feature/snapshot")
    return root


def snap(root: Path, *includes: str):
    return snapshot_tool.build_snapshot(root, includes)["snapshot"]


def test_same_content_and_manifest_order_produce_same_hash(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "a.txt").write_bytes(b"a")
    (root / "b.txt").write_bytes(b"b")
    first = snap(root, "a.txt", "b.txt")
    second = snap(root, "b.txt", "a.txt")
    assert first["hash"] == second["hash"]
    manifest = first["manifest"]
    reversed_manifest = {**manifest, "files": list(reversed(manifest["files"]))}
    reversed_manifest["files"] = sorted(reversed_manifest["files"], key=lambda item: (item["path"], item["old_path"] or ""))
    assert snapshot_tool.canonical_manifest_bytes(manifest) == snapshot_tool.canonical_manifest_bytes(reversed_manifest)


def test_one_byte_change_changes_hash(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "tracked.txt").write_bytes(b"change-a")
    before = snap(root, "tracked.txt")["hash"]
    (root / "tracked.txt").write_bytes(b"change-b")
    assert snap(root, "tracked.txt")["hash"] != before


def test_add_delete_rename_and_untracked_are_manifest_changes(tmp_path: Path) -> None:
    root = repository(tmp_path)
    baseline = snap(root, "tracked.txt")["hash"]
    (root / "added.bin").write_bytes(b"\x00\xff\x10")
    added = snap(root, "tracked.txt", "added.bin")
    assert added["hash"] != baseline
    assert added["manifest"]["files"][0]["status"] == "untracked"
    (root / "tracked.txt").unlink()
    deleted = snap(root, "tracked.txt", "added.bin")
    deleted_entry = next(item for item in deleted["manifest"]["files"] if item["path"] == "tracked.txt")
    assert deleted_entry["status"] == "deleted"
    assert deleted_entry["mode"] is None and deleted_entry["content_sha256"] is None
    git(root, "restore", "tracked.txt")
    git(root, "mv", "tracked.txt", "renamed.txt")
    renamed = snap(root, "tracked.txt", "renamed.txt", "added.bin")
    rename_entry = next(item for item in renamed["manifest"]["files"] if item["path"] == "renamed.txt")
    assert rename_entry["status"] == "renamed" and rename_entry["old_path"] == "tracked.txt"
    assert renamed["hash"] != added["hash"]


def test_mode_change_and_binary_content_change_hash(tmp_path: Path) -> None:
    root = repository(tmp_path)
    path = root / "tracked.txt"
    path.write_bytes(b"\x00\x01\xff")
    content_hash = snap(root, "tracked.txt")["hash"]
    path.chmod(path.stat().st_mode | 0o100)
    mode_snapshot = snap(root, "tracked.txt")
    assert mode_snapshot["hash"] != content_hash
    assert mode_snapshot["manifest"]["files"][0]["mode"] == "100755"


def test_scope_external_change_is_unexpected_and_gate_change_is_detected(tmp_path: Path) -> None:
    root = repository(tmp_path)
    (root / "tracked.txt").write_bytes(b"gate")
    gate_hash = snap(root, "tracked.txt")["hash"]
    (root / "outside.txt").write_bytes(b"outside")
    current = snap(root, "tracked.txt")
    assert current["unexpected_files"] == ["outside.txt"]
    handoff = _handoff_for_snapshot(gate_hash)
    with pytest.raises(snapshot_tool.SnapshotError, match="scope-external"):
        snapshot_tool.validate_publish_snapshot(handoff, {"snapshot": current})
    (root / "outside.txt").unlink()
    (root / "tracked.txt").write_bytes(b"after-gate")
    changed = snap(root, "tracked.txt")
    with pytest.raises(snapshot_tool.SnapshotError, match="changed after Release Gate"):
        snapshot_tool.validate_publish_snapshot(handoff, {"snapshot": changed})


def _handoff_for_snapshot(snapshot_hash: str):
    run_id = snapshot_tool.repository_publish_run_id("owner/repo", "main", "feature/snapshot", snapshot_hash, 1)
    return {
        "handoff_revision": 1, "repository_publish_run_id": run_id,
        "release_gate": {"reviewed_diff_hash": snapshot_hash, "checked_diff_hash": snapshot_hash},
        "repository": {"id": "owner/repo", "base_branch": "main", "working_branch": "feature/snapshot"},
        "publish_scope": {"included_paths": ["tracked.txt"], "expected_changed_files": ["tracked.txt"]},
        "blocking_issues": [],
        "next_action": {"handoff_reference": "handoff.yaml", "repository_publish_run_id": run_id},
    }


def test_run_id_is_deterministic_and_input_sensitive() -> None:
    digest = "a" * 64
    first = snapshot_tool.repository_publish_run_id("owner/repo", "main", "feature/x", digest, 1)
    assert first == snapshot_tool.repository_publish_run_id("owner/repo", "main", "feature/x", digest, 1)
    assert first != snapshot_tool.repository_publish_run_id("owner/repo", "main", "feature/x", digest, 2)
    assert first.startswith("rpr-") and len(first) == 68
