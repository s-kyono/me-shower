"""Minimal atomic run claim used to prevent duplicate Repository Publish runs."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

RUN_ID = re.compile(r"^rpr-[0-9a-f]{64}$")


def claim_run(registry_root: Path, run_id: str) -> tuple[bool, dict[str, Any]]:
    if not RUN_ID.fullmatch(run_id):
        raise ValueError("invalid repository publish run ID")
    run_dir = registry_root / run_id
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        result_path = run_dir / "result.json"
        if result_path.exists():
            return False, json.loads(result_path.read_text(encoding="utf-8"))
        return False, {"repository_publish_run_id": run_id, "status": "running"}
    claim = {"repository_publish_run_id": run_id, "status": "running"}
    (run_dir / "claim.json").write_text(
        json.dumps(claim, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    return True, claim


def record_result(registry_root: Path, run_id: str, result: dict[str, Any]) -> None:
    if not RUN_ID.fullmatch(run_id) or result.get("repository_publish_run_id") != run_id:
        raise ValueError("run result identity mismatch")
    run_dir = registry_root / run_id
    if not run_dir.is_dir():
        raise ValueError("run must be claimed before recording a result")
    temporary = run_dir / "result.json.tmp"
    temporary.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(run_dir / "result.json")
