"""Shared Development Artifact identity validation and construction rules."""
from __future__ import annotations

import re
from typing import Any


MAX_REVISION = 999_999_999
LOGICAL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$", re.ASCII)
RESERVED_NAMES = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def is_valid_logical_id(value: Any) -> bool:
    return (
        isinstance(value, str)
        and LOGICAL_ID_RE.fullmatch(value) is not None
        and not value.endswith("-")
        and value.casefold() not in RESERVED_NAMES
    )


def format_revision_token(revision: Any) -> str:
    if not isinstance(revision, int) or isinstance(revision, bool) or not 1 <= revision <= MAX_REVISION:
        raise ValueError("artifact_identity_revision_invalid")
    return f"r{revision:04d}"


def build_revision_scoped_logical_id(subject_id: str, subject_revision: int) -> str:
    if not is_valid_logical_id(subject_id):
        raise ValueError("artifact_identity_subject_id_invalid")
    value = f"{subject_id}-{format_revision_token(subject_revision)}"
    if not is_valid_logical_id(value):
        raise ValueError("artifact_identity_logical_id_invalid")
    return value


def validate_revision_scoped_logical_id(
    logical_artifact_id: str, subject_id: str, subject_revision: int,
) -> bool:
    try:
        expected = build_revision_scoped_logical_id(subject_id, subject_revision)
    except ValueError:
        return False
    return logical_artifact_id == expected
