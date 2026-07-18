#!/usr/bin/env python3
"""Build deterministic repository publish snapshots and run identifiers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
from typing import Any, Iterable

SCHEMA_VERSION = "1.0"
DEFAULT_EXCLUDED_PREFIXES = (
    ".git", ".codex/runtime", ".codex/tmp",
    ".codex/harness/development/artifacts",
)


class SnapshotError(RuntimeError):
    pass


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise SnapshotError(f"git command failed: git {' '.join(args)}")
    return result.stdout


def _posix_path(raw: bytes) -> str:
    value = raw.decode("utf-8", "surrogateescape")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value in {"", "."}:
        raise SnapshotError("git returned an unsafe repository path")
    return path.as_posix()


def _matches(path: str, scopes: Iterable[str]) -> bool:
    for raw_scope in scopes:
        scope = PurePosixPath(raw_scope).as_posix().rstrip("/")
        if scope and (path == scope or path.startswith(f"{scope}/")):
            return True
    return False


def _working_mode(path: Path) -> str | None:
    if not path.exists() and not path.is_symlink():
        return None
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        return "120000"
    if stat.S_ISREG(mode):
        return "100755" if mode & stat.S_IXUSR else "100644"
    if stat.S_ISDIR(mode) and (path / ".git").exists():
        return "160000"
    raise SnapshotError("unsupported working tree file type")


def _content_hash(root: Path, relative_path: str, mode: str | None) -> str | None:
    path = root / relative_path
    if mode is None or (not path.exists() and not path.is_symlink()):
        return None
    if mode == "120000":
        payload = os.readlink(path).encode("utf-8", "surrogateescape")
    elif mode == "160000":
        payload = _git(path, "rev-parse", "HEAD").strip()
    else:
        payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest()


def _status_name(xy: str, head_mode: str | None, work_mode: str | None) -> str:
    if "A" in xy:
        return "added"
    if "D" in xy:
        return "deleted"
    if "R" in xy or "C" in xy:
        return "renamed"
    if "T" in xy or (head_mode and work_mode and head_mode != work_mode):
        return "mode_changed"
    return "modified"


def collect_changed_entries(repository_root: Path) -> list[dict[str, Any]]:
    records = _git(repository_root, "status", "--porcelain=v2", "-z", "--untracked-files=all").split(b"\0")
    entries: list[dict[str, Any]] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        kind = record[:1]
        if kind == b"u":
            raise SnapshotError("unmerged path detected")
        if kind == b"?":
            path = _posix_path(record[2:])
            mode = _working_mode(repository_root / path)
            entries.append({"path": path, "status": "untracked", "old_path": None, "mode": mode,
                            "content_sha256": _content_hash(repository_root, path, mode)})
            continue
        if kind == b"1":
            fields = record.split(b" ", 8)
            if len(fields) != 9:
                raise SnapshotError("invalid ordinary porcelain record")
            _, xy_raw, _, head_mode_raw, _, work_mode_raw, _, _, path_raw = fields
            xy, path, head_mode = xy_raw.decode(), _posix_path(path_raw), head_mode_raw.decode()
            mode = None if "D" in xy else (work_mode_raw.decode() if work_mode_raw != b"000000" else _working_mode(repository_root / path))
            entries.append({"path": path, "status": _status_name(xy, head_mode, mode), "old_path": None,
                            "mode": mode, "content_sha256": _content_hash(repository_root, path, mode)})
            continue
        if kind == b"2":
            fields = record.split(b" ", 9)
            if len(fields) != 10 or index >= len(records):
                raise SnapshotError("invalid rename porcelain record")
            _, _, _, _, _, work_mode_raw, _, _, _, path_raw = fields
            path, old_path = _posix_path(path_raw), _posix_path(records[index])
            index += 1
            mode = work_mode_raw.decode() if work_mode_raw != b"000000" else _working_mode(repository_root / path)
            entries.append({"path": path, "status": "renamed", "old_path": old_path, "mode": mode,
                            "content_sha256": _content_hash(repository_root, path, mode)})
            continue
        if kind != b"!":
            raise SnapshotError("unsupported porcelain record")
    return sorted(entries, key=lambda item: (item["path"], item["old_path"] or ""))


def canonical_manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def build_snapshot(repository_root: Path, included_paths: Iterable[str], excluded_paths: Iterable[str] = ()) -> dict[str, Any]:
    root = repository_root.resolve()
    if not (root / ".git").exists():
        raise SnapshotError("repository root must contain .git")
    includes = tuple(included_paths)
    if not includes:
        raise SnapshotError("at least one included path is required")
    excludes = tuple(DEFAULT_EXCLUDED_PREFIXES) + tuple(excluded_paths)
    included: list[dict[str, Any]] = []
    excluded: list[str] = []
    unexpected: list[str] = []
    for entry in collect_changed_entries(root):
        paths = [entry["path"]] + ([entry["old_path"]] if entry["old_path"] else [])
        if any(_matches(path, excludes) for path in paths):
            excluded.append(entry["path"])
        elif any(_matches(path, includes) for path in paths):
            included.append(entry)
        else:
            unexpected.append(entry["path"])
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "repository_root": ".",
        "base_revision": _git(root, "rev-parse", "HEAD").decode().strip(),
        "working_branch": _git(root, "branch", "--show-current").decode().strip(),
        "files": sorted(included, key=lambda item: (item["path"], item["old_path"] or "")),
    }
    return {"snapshot": {"manifest": manifest,
                         "hash": hashlib.sha256(canonical_manifest_bytes(manifest)).hexdigest(),
                         "included_files": [entry["path"] for entry in manifest["files"]],
                         "excluded_files": sorted(excluded), "unexpected_files": sorted(unexpected)}}


def repository_publish_run_id(repository_id: str, base_branch: str, working_branch: str,
                              checked_diff_hash: str, handoff_revision: int) -> str:
    payload = {"repository": repository_id, "base_branch": base_branch, "working_branch": working_branch,
               "checked_diff_hash": checked_diff_hash, "handoff_revision": handoff_revision}
    return "rpr-" + hashlib.sha256(canonical_manifest_bytes(payload)).hexdigest()


def validate_handoff_cross_fields(handoff: dict[str, Any]) -> None:
    gate, repository, scope, next_action = (handoff["release_gate"], handoff["repository"],
                                            handoff["publish_scope"], handoff["next_action"])
    if gate["reviewed_diff_hash"] != gate["checked_diff_hash"]:
        raise SnapshotError("reviewed and checked diff hashes differ")
    if repository["base_branch"] == repository["working_branch"]:
        raise SnapshotError("base and working branches must differ")
    if handoff["blocking_issues"]:
        raise SnapshotError("unresolved blocking issue")
    if not scope["included_paths"] or not scope["expected_changed_files"]:
        raise SnapshotError("publish scope must not be empty")
    expected = repository_publish_run_id(repository["id"], repository["base_branch"], repository["working_branch"],
                                         gate["checked_diff_hash"], handoff["handoff_revision"])
    if handoff["repository_publish_run_id"] != expected or next_action["repository_publish_run_id"] != expected:
        raise SnapshotError("repository publish run ID mismatch")
    if not next_action["handoff_reference"]:
        raise SnapshotError("handoff reference is empty")


def validate_publish_snapshot(handoff: dict[str, Any], snapshot: dict[str, Any]) -> None:
    """Fail closed when the current repository no longer matches the Gate."""
    validate_handoff_cross_fields(handoff)
    current = snapshot["snapshot"]
    if current["unexpected_files"]:
        raise SnapshotError("scope-external changes detected")
    if current["hash"] != handoff["release_gate"]["checked_diff_hash"]:
        raise SnapshotError("repository changed after Release Gate")
    if sorted(current["included_files"]) != sorted(handoff["publish_scope"]["expected_changed_files"]):
        raise SnapshotError("current changed files do not match publish scope")


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--repository-root", type=Path, required=True)
    build.add_argument("--include", action="append", required=True)
    build.add_argument("--exclude", action="append", default=[])
    build.add_argument("--output", type=Path)
    run_id = commands.add_parser("run-id")
    for name in ("repository-id", "base-branch", "working-branch", "checked-diff-hash"):
        run_id.add_argument(f"--{name}", required=True)
    run_id.add_argument("--handoff-revision", type=int, required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        result = build_snapshot(args.repository_root, args.include, args.exclude)
        if args.output:
            args.output.write_text(json.dumps(result["snapshot"]["manifest"], sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result["snapshot"]["manifest_path"] = str(args.output)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    else:
        print(repository_publish_run_id(args.repository_id, args.base_branch, args.working_branch,
                                        args.checked_diff_hash, args.handoff_revision))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_main())
    except SnapshotError as error:
        print(f"blocked: {error}", file=sys.stderr)
        raise SystemExit(2)
