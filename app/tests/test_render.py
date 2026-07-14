from pathlib import Path
from datetime import date
import json

import main
from main import load_resume_data, render_markdown
import pytest
from typer.testing import CliRunner


runner = CliRunner()


def configure_review_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path, Path]:
    repo_root = tmp_path / "repo"
    app_root = repo_root / "app"
    source_sync_dir = app_root / "data" / "source_sync"
    decision_dir = app_root / "data" / "review_decisions"
    write_source_sync_fixture(source_sync_dir)
    monkeypatch.setattr(main, "REPO_ROOT", repo_root)
    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    return repo_root, source_sync_dir, decision_dir


def review_decision(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "source_sync_file": "app/data/source_sync/2026-07-10.md",
        "source_id": "daily_report:2026-07-10.md",
        "event_index": 1,
        "event_date": "2026-07-10",
        "status": "approved",
        "reviewer_id": "self",
        "reviewed_at": "2026-07-12T10:00:00+09:00",
        "reason": "Evidence is traceable and the meaning is acceptable.",
        "evidence_refs": ["daily_report:2026-07-10.md"],
    }
    values.update(overrides)
    return main.create_review_decision(**values)  # type: ignore[arg-type]


def test_review_decision_approved_appends_with_unique_ids(tmp_path: Path) -> None:
    first = review_decision()
    second = review_decision(status="needs_more_evidence", evidence_refs=[])
    assert first["decision_id"] != second["decision_id"]

    path = main.append_review_decision(first, decision_log_dir=tmp_path)
    main.append_review_decision(second, decision_log_dir=tmp_path)

    assert path.name == "2026-07-12.jsonl"
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


@pytest.mark.parametrize("status", ["rejected", "deferred", "needs_more_evidence"])
def test_review_decision_requires_reason_for_every_non_approved_status(status: str) -> None:
    with pytest.raises(ValueError, match="reason"):
        review_decision(status=status, reason="", evidence_refs=[])


def test_review_decision_approved_requires_evidence_and_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="evidence_ref"):
        review_decision(evidence_refs=[])
    with pytest.raises(ValueError, match="status must be one of"):
        review_decision(status="ready_for_review")
    with pytest.raises(ValueError, match="normalized repository-relative path"):
        review_decision(source_sync_file="/Users/example/app/data/source_sync/2026-07-10.md")


@pytest.mark.parametrize("field,value", [
    ("reason", "API_KEY=super-secret-value"),
    ("notes", "See https://private.example.invalid/item"),
])
def test_review_decision_rejects_unsafe_free_text(field: str, value: str) -> None:
    with pytest.raises(ValueError, match="must not contain"):
        review_decision(**{field: value})


@pytest.mark.parametrize("unsafe_ref", [
    "/Users/alice/private/client-project.txt",
    "/home/alice/private/client-project.txt",
    "file:///Users/alice/private/client-project.txt",
    r"C:\Users\alice\private\client-project.txt",
    "~/private/client-project.txt",
    "../private/client-project.txt",
    "https://private.example.invalid/review",
    "contact@example.com",
    "API_KEY=super-secret-value",
    "TOKEN=secret-value",
    "SECRET=client-password",
])
def test_review_decision_rejects_unsafe_evidence_ref_without_appending(
    tmp_path: Path, unsafe_ref: str,
) -> None:
    with pytest.raises(ValueError, match="unsafe evidence or source reference"):
        record = review_decision(evidence_refs=[unsafe_ref])
        main.append_review_decision(record, decision_log_dir=tmp_path)

    assert not list(tmp_path.glob("*.jsonl"))


def test_append_review_decision_rejects_unsafe_evidence_ref_without_appending(tmp_path: Path) -> None:
    record = review_decision()
    record["evidence_refs"] = ["/Users/alice/private/client-project.txt"]

    with pytest.raises(ValueError, match="unsafe evidence or source reference"):
        main.append_review_decision(record, decision_log_dir=tmp_path)

    assert not list(tmp_path.glob("*.jsonl"))


def test_review_decision_cli_rejects_unsafe_evidence_ref_without_appending(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _, source_sync_dir, decision_dir = configure_review_workspace(monkeypatch, tmp_path)

    result = runner.invoke(main.app, [
        "add-review-decision", "--decision-log-dir", str(decision_dir),
        "--source-sync-file", str(source_sync_dir / "2026-07-10.md"),
        "--event-index", "1", "--reviewer-id", "self", "--status", "approved",
        "--reason", "Supported.", "--evidence-ref=/Users/alice/private/client-project.txt",
    ])

    assert result.exit_code != 0
    assert not list(decision_dir.glob("*.jsonl"))


def test_review_decision_preserves_safe_evidence_refs(tmp_path: Path) -> None:
    safe_refs = [
        "github:s-kyono/me-shower#3",
        "daily_report:2026-07-10.md",
        "source_sync:2026-07-10.md#event-1",
        "review_queue:2026-07-10#event-1",
    ]
    record = review_decision(evidence_refs=safe_refs)

    path = main.append_review_decision(record, decision_log_dir=tmp_path)

    assert json.loads(path.read_text(encoding="utf-8"))["evidence_refs"] == safe_refs


def test_review_decision_cli_inspects_status_source_id_and_limit_without_mutating_inputs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _, source_sync_dir, decision_dir = configure_review_workspace(monkeypatch, tmp_path)
    source_sync = source_sync_dir / "2026-07-10.md"
    review_queue = tmp_path / "review_queue.jsonl"
    review_queue.write_text("queue\n", encoding="utf-8")
    before = (source_sync.read_bytes(), review_queue.read_bytes())
    common = ["--decision-log-dir", str(decision_dir), "--source-sync-file", str(source_sync),
              "--event-index", "1", "--reviewer-id", "self"]
    approved = runner.invoke(main.app, ["add-review-decision", *common,
        "--status", "approved", "--reason", "Supported.", "--evidence-ref", "file:one"])
    rejected = runner.invoke(main.app, ["add-review-decision", *common,
        "--status", "rejected", "--reason", "Out of scope."])
    assert approved.exit_code == rejected.exit_code == 0

    result = runner.invoke(main.app, ["inspect-review-decisions", "--decision-log-dir", str(decision_dir),
        "--status", "approved", "--source-id", "daily_report:2026-07-10.md", "--limit", "1"])
    assert result.exit_code == 0
    assert "items: 1" in result.stdout
    assert "daily_report:2026-07-10.md" in result.stdout
    assert before == (source_sync.read_bytes(), review_queue.read_bytes())

    stored = main.read_review_decisions(decision_dir)
    assert stored[0]["canonical_event_ref"]["source_id"] == "daily_report:2026-07-10.md"
    assert stored[0]["canonical_event_ref"]["event_date"] == "2026-07-10"
    assert stored[0]["canonical_event_ref"]["source_sync_file"] == "app/data/source_sync/2026-07-10.md"


@pytest.mark.parametrize(
    "source_file,event_index,extra_args,error_text",
    [
        ("missing.md", 1, [], "Missing file"),
        ("2026-07-10.md", 99, [], "event_index 99 does not exist"),
        ("2026-07-10.md", 1, ["--source-id", "daily_report:wrong.md"], "source_id does not match"),
        ("2026-07-10.md", 1, ["--event-date", "2026-07-11"], "event_date does not match"),
    ],
)
def test_review_decision_cli_rejects_invalid_canonical_event_without_writing_jsonl(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source_file: str, event_index: int,
    extra_args: list[str], error_text: str,
) -> None:
    _, source_sync_dir, decision_dir = configure_review_workspace(monkeypatch, tmp_path)
    source_path = source_sync_dir / source_file
    original = {path.name: path.read_bytes() for path in source_sync_dir.glob("*.md")}

    result = runner.invoke(main.app, [
        "add-review-decision", "--decision-log-dir", str(decision_dir),
        "--source-sync-file", str(source_path), "--event-index", str(event_index),
        "--status", "needs_more_evidence", "--reviewer-id", "self",
        "--reason", "Need stronger Evidence.", *extra_args,
    ])

    assert result.exit_code != 0
    assert error_text in result.output
    assert not decision_dir.exists() or not list(decision_dir.glob("*.jsonl"))
    assert original == {path.name: path.read_bytes() for path in source_sync_dir.glob("*.md")}


def test_review_decision_cli_rejects_blocked_approval_but_allows_non_approved_statuses(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _, source_sync_dir, decision_dir = configure_review_workspace(monkeypatch, tmp_path)
    source_path = source_sync_dir / "2026-07-10.md"
    source_path.write_text(
        source_path.read_text(encoding="utf-8").replace(
            "GraphQL Resolver分離を実施", "contact@example.com の情報を確認"
        ),
        encoding="utf-8",
    )
    common = [
        "--decision-log-dir", str(decision_dir), "--source-sync-file", str(source_path),
        "--event-index", "1", "--reviewer-id", "self",
    ]

    approved = runner.invoke(main.app, [
        "add-review-decision", *common, "--status", "approved", "--reason", "Supported.",
        "--evidence-ref", "daily_report:2026-07-10.md",
    ])

    assert approved.exit_code != 0
    assert "blocked_by_policy Canonical Events cannot be approved" in approved.output
    assert not decision_dir.exists() or not list(decision_dir.glob("*.jsonl"))

    for status in ["rejected", "deferred", "needs_more_evidence"]:
        result = runner.invoke(main.app, [
            "add-review-decision", *common, "--status", status, "--reason", "Policy review required.",
        ])
        assert result.exit_code == 0, result.output

    assert {record["status"] for record in main.read_review_decisions(decision_dir)} == {
        "rejected", "deferred", "needs_more_evidence",
    }


def test_review_decision_cli_normalizes_absolute_and_relative_source_sync_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    repo_root, source_sync_dir, decision_dir = configure_review_workspace(monkeypatch, tmp_path)
    source_path = source_sync_dir / "2026-07-10.md"
    relative_path = source_path.relative_to(repo_root).as_posix()
    common = ["--decision-log-dir", str(decision_dir), "--event-index", "1", "--reviewer-id", "self"]

    for status, path_text in [("rejected", str(source_path)), ("deferred", relative_path)]:
        result = runner.invoke(main.app, [
            "add-review-decision", *common, "--source-sync-file", path_text,
            "--status", status, "--reason", "Not promoted.",
        ])
        assert result.exit_code == 0, result.output

    stored_paths = {
        record["canonical_event_ref"]["source_sync_file"]
        for record in main.read_review_decisions(decision_dir)
    }
    assert stored_paths == {"app/data/source_sync/2026-07-10.md"}
    assert str(tmp_path) not in json.dumps(main.read_review_decisions(decision_dir))


def test_review_decision_cli_rejects_source_sync_path_escape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    repo_root, source_sync_dir, decision_dir = configure_review_workspace(monkeypatch, tmp_path)
    outside = repo_root / "outside.md"
    outside.write_text((source_sync_dir / "2026-07-10.md").read_text(encoding="utf-8"), encoding="utf-8")
    symlink = source_sync_dir / "outside-link.md"
    symlink.symlink_to(outside)
    paths = [
        str(outside),
        "app/data/source_sync/../../../outside.md",
        str(symlink),
    ]

    for path_text in paths:
        result = runner.invoke(main.app, [
            "add-review-decision", "--decision-log-dir", str(decision_dir),
            "--source-sync-file", path_text, "--event-index", "1", "--status", "rejected",
            "--reviewer-id", "self", "--reason", "Outside source_sync.",
        ])
        assert result.exit_code != 0
        assert "source_sync_file must be under" in result.output

    assert not decision_dir.exists() or not list(decision_dir.glob("*.jsonl"))


def build_command_runner(fixtures: dict[tuple[str, ...], main.CommandResult]):
    def runner(command: list[str]) -> main.CommandResult:
        key = tuple(command)
        if key not in fixtures:
            raise AssertionError(f"Unexpected command: {command}")
        return fixtures[key]

    return runner


def build_slack_api_caller(fixtures: dict[tuple[str, tuple[tuple[str, object], ...]], dict[str, object]]):
    def caller(method: str, params: dict[str, object]) -> dict[str, object]:
        normalized = tuple(sorted((key, value) for key, value in params.items() if value is not None))
        key = (method, normalized)
        if key not in fixtures:
            raise AssertionError(f"Unexpected Slack API call: {method} {params}")
        return fixtures[key]

    return caller


def build_graph_api_caller(fixtures: dict[tuple[str, tuple[tuple[str, object], ...]], dict[str, object]]):
    def caller(path: str, params: dict[str, object]) -> dict[str, object]:
        normalized = tuple(sorted((key, value) for key, value in params.items() if value is not None))
        key = (path, normalized)
        if key not in fixtures:
            raise AssertionError(f"Unexpected Microsoft Graph API call: {path} {params}")
        return fixtures[key]

    return caller


def write_source_sync_fixture(source_sync_dir: Path) -> None:
    source_sync_dir.mkdir(parents=True, exist_ok=True)
    (source_sync_dir / "2026-07-10.md").write_text(
        "\n".join(
            [
                "# Canonical Events",
                "",
                "date: 2026-07-10",
                "",
                "## Event 1",
                "",
                "- schema: canonical_event_v0_3",
                "- date: 2026-07-10",
                "  source_id: daily_report:2026-07-10.md",
                "  source_type: daily_report",
                "  category: implementation",
                "  summary: GraphQL Resolver分離を実施",
                "  actions:",
                "  - GraphQL Resolver分離を実施",
                "  decisions:",
                "  - none",
                "  improvements:",
                "  - Resolver責務を整理",
                "  tags:",
                "  - GraphQL",
                "  - Resolver",
                "  tools:",
                "  - none",
                "  noise_removed:",
                "  - low_signal",
                "  confidence: medium",
                "  confidence_reasons:",
                "  - source_type:daily_report",
                "  - actions:1",
                "  evidence:",
                "  - kind: source_reference",
                "    detail: daily_report:2026-07-10.md",
                "",
                "## Event 2",
                "",
                "- schema: canonical_event_v0_3",
                "- date: 2026-07-10",
                "  source_type: github",
                "  category: review",
                "  summary: PRレビューで設計指摘を受領",
                "  actions:",
                "  - PRレビューで設計指摘を受領",
                "  decisions:",
                "  - リファクタ方針を決定",
                "  improvements:",
                "  - none",
                "  tags:",
                "  - PR",
                "  tools:",
                "  - gh",
                "  noise_removed:",
                "  - none",
                "  confidence: high",
                "  confidence_reasons:",
                "  - source_type:github",
                "  - actions:1",
                "  evidence:",
                "  - kind: source_reference",
                "    detail: github:s-kyono/me-shower#3",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (source_sync_dir / "2026-07-11.md").write_text(
        "\n".join(
            [
                "# Canonical Events", "", "date: 2026-07-11", "", "## Event 1", "",
                "- schema: canonical_event_v0_3", "- date: 2026-07-11",
                "  source_id: slack:C0123456789:1781736600.000100", "  source_type: slack",
                "  category: implementation", "  summary: Slack Connector関連の実装・調査を実施",
                "  actions:", "  - Slack Connector関連の実装・調査を実施", "  decisions:", "  - none",
                "  improvements:", "  - none", "  tags:", "  - Slack", "  - Connector", "  tools:",
                "  - none", "  noise_removed:", "  - none", "  confidence: low",
                "  confidence_reasons:", "  - source_type:slack", "  - actions:1", "  evidence:",
                "  - kind: source_reference", "    detail: slack:C0123456789", "",
            ]
        ),
        encoding="utf-8",
    )


def test_review_queue_builds_from_source_sync_with_stable_ids_and_readiness(tmp_path: Path) -> None:
    source_sync_dir = tmp_path / "source_sync"
    write_source_sync_fixture(source_sync_dir)

    first = main.read_review_queue_items(source_sync_dir)
    second = main.read_review_queue_items(source_sync_dir)

    assert [item.queue_id for item in first] == [item.queue_id for item in second]
    assert len(first) == 3
    assert {item.readiness["status"] for item in first} <= main.REVIEW_READINESS_STATUSES
    assert not ({item.readiness["status"] for item in first} & main.FORBIDDEN_REVIEW_QUEUE_STATUSES)
    assert any(item.readiness["status"] == "ready_for_review" for item in first)
    low_item = next(item for item in first if item.confidence["level"] == "low")
    assert low_item.readiness["status"] != "ready_for_review"


def test_review_queue_requires_evidence_and_blocks_sensitive_content(tmp_path: Path) -> None:
    source_sync_dir = tmp_path / "source_sync"
    write_source_sync_fixture(source_sync_dir)
    path = source_sync_dir / "2026-07-10.md"
    content = path.read_text(encoding="utf-8")
    content = content.replace("detail: daily_report:2026-07-10.md", "detail: none", 1)
    content = content.replace("PRレビューで設計指摘を受領", "contact@example.com の情報を確認")
    path.write_text(content, encoding="utf-8")

    items = main.read_review_queue_items(source_sync_dir)
    missing = next(item for item in items if item.canonical_event_ref["event_index"] == 1 and item.canonical_event_ref["source_sync_file"] == "2026-07-10.md")
    sensitive = next(item for item in items if item.canonical_event_ref["event_index"] == 2 and item.canonical_event_ref["source_sync_file"] == "2026-07-10.md")

    assert missing.readiness["status"] == "needs_evidence_before_review"
    assert sensitive.readiness["status"] == "blocked_by_policy"


@pytest.mark.parametrize(
    "sensitive_text",
    [
        "contact@example.com の情報を確認",
        "See https://private.example.invalid/review for details",
        "API_KEY=super-secret-value を確認",
    ],
)
def test_blocked_review_queue_outputs_only_safe_metadata(tmp_path: Path, sensitive_text: str) -> None:
    source_sync_dir = tmp_path / "source_sync"
    write_source_sync_fixture(source_sync_dir)
    path = source_sync_dir / "2026-07-10.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("PRレビューで設計指摘を受領", sensitive_text),
        encoding="utf-8",
    )
    output = tmp_path / "generated" / "review_queue.md"
    jsonl_output = tmp_path / "generated" / "review_queue.jsonl"

    main.build_review_queue(
        source_sync_dir=source_sync_dir, output_path=output, jsonl_output_path=jsonl_output,
    )
    inspected = runner.invoke(main.app, [
        "inspect-review-queue", "--source-sync-dir", str(source_sync_dir),
        "--readiness", "blocked_by_policy",
    ])

    markdown = output.read_text(encoding="utf-8")
    records = [json.loads(line) for line in jsonl_output.read_text(encoding="utf-8").splitlines()]
    blocked = next(
        record for record in records
        if record["canonical_event_ref"]["source_sync_file"] == "2026-07-10.md"
        and record["canonical_event_ref"]["event_index"] == 2
    )
    assert sensitive_text not in markdown
    assert sensitive_text not in json.dumps(records, ensure_ascii=False)
    assert inspected.exit_code == 0, inspected.output
    assert sensitive_text not in inspected.output
    assert "blocking_reasons: confidential_or_raw_sensitive_content_risk" in inspected.output
    assert blocked["readiness"]["status"] == "blocked_by_policy"
    assert blocked["readiness"]["blocking_reasons"] == ["confidential_or_raw_sensitive_content_risk"]
    assert blocked["canonical_event_ref"]["event_index"] == 2
    assert blocked["evidence"]["source_reference"] == "github:s-kyono/me-shower#3"
    assert not ({"summary", "actions", "decisions", "improvements", "tags", "tools"} & blocked.keys())
    normal = next(
        record for record in records
        if record["canonical_event_ref"]["source_sync_file"] == "2026-07-10.md"
        and record["canonical_event_ref"]["event_index"] == 1
    )
    assert normal["summary"] == "GraphQL Resolver分離を実施"
    assert "GraphQL Resolver分離を実施" in markdown


@pytest.mark.parametrize("evidence_kind", ["source_reference", "file_reference"])
@pytest.mark.parametrize("unsafe_ref", [
    "/Users/alice/private/client-project.txt",
    "/home/alice/private/client-project.txt",
    "file:///Users/alice/private/client-project.txt",
    r"C:\Users\alice\private\client-project.txt",
    "~/private/client-project.txt",
    "../private/client-project.txt",
    "https://private.example.invalid/review",
    "contact@example.com",
    "API_KEY=super-secret-value",
    "TOKEN=secret-value",
    "SECRET=client-password",
])
def test_blocked_review_queue_omits_unsafe_evidence_references_from_all_outputs(
    tmp_path: Path, unsafe_ref: str, evidence_kind: str,
) -> None:
    source_sync_dir = tmp_path / "source_sync"
    write_source_sync_fixture(source_sync_dir)
    path = source_sync_dir / "2026-07-10.md"
    content = path.read_text(encoding="utf-8")
    content = content.replace("PRレビューで設計指摘を受領", "contact@example.com の情報を確認")
    content = content.replace(
        "kind: source_reference\n    detail: github:s-kyono/me-shower#3",
        f"kind: {evidence_kind}\n    detail: {unsafe_ref}",
    )
    path.write_text(content, encoding="utf-8")
    output = tmp_path / "generated" / "review_queue.md"
    jsonl_output = tmp_path / "generated" / "review_queue.jsonl"

    main.build_review_queue(
        source_sync_dir=source_sync_dir, output_path=output, jsonl_output_path=jsonl_output,
    )
    inspected = runner.invoke(main.app, [
        "inspect-review-queue", "--source-sync-dir", str(source_sync_dir),
        "--readiness", "blocked_by_policy",
    ])
    combined_output = output.read_text(encoding="utf-8") + jsonl_output.read_text(encoding="utf-8") + inspected.output

    assert inspected.exit_code == 0, inspected.output
    assert unsafe_ref not in combined_output


def test_blocked_review_queue_preserves_safe_evidence_reference(tmp_path: Path) -> None:
    source_sync_dir = tmp_path / "source_sync"
    write_source_sync_fixture(source_sync_dir)
    path = source_sync_dir / "2026-07-10.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "PRレビューで設計指摘を受領", "contact@example.com の情報を確認",
        ),
        encoding="utf-8",
    )

    blocked = next(
        item for item in main.read_review_queue_items(source_sync_dir)
        if item.readiness["status"] == "blocked_by_policy"
    )

    assert blocked.evidence["source_reference"] == "github:s-kyono/me-shower#3"


def test_build_review_queue_writes_safe_markdown_and_jsonl_without_mutating_source_sync(tmp_path: Path) -> None:
    source_sync_dir = tmp_path / "source_sync"
    write_source_sync_fixture(source_sync_dir)
    path = source_sync_dir / "2026-07-10.md"
    content = path.read_text(encoding="utf-8").replace(
        "  - kind: source_reference\n    detail: daily_report:2026-07-10.md",
        "  - kind: redacted_excerpt\n    detail: raw source secret phrase\n"
        "  - kind: source_reference\n    detail: daily_report:2026-07-10.md",
        1,
    )
    path.write_text(content + "\n", encoding="utf-8")
    original = {item.name: item.read_bytes() for item in source_sync_dir.glob("*.md")}
    output = tmp_path / "generated" / "review_queue.md"
    jsonl_output = tmp_path / "generated" / "review_queue.jsonl"

    markdown_path, jsonl_path, count = main.build_review_queue(
        source_sync_dir=source_sync_dir, output_path=output, jsonl_output_path=jsonl_output
    )

    assert count == 3
    assert markdown_path.exists() and jsonl_path == jsonl_output and jsonl_output.exists()
    generated = markdown_path.read_text(encoding="utf-8") + jsonl_output.read_text(encoding="utf-8")
    assert "Canonical Events" not in generated
    assert "raw source secret phrase" not in generated
    assert original == {item.name: item.read_bytes() for item in source_sync_dir.glob("*.md")}


def test_review_queue_cli_filters_by_readiness_source_type_and_limit(tmp_path: Path) -> None:
    source_sync_dir = tmp_path / "source_sync"
    write_source_sync_fixture(source_sync_dir)

    result = runner.invoke(main.app, [
        "inspect-review-queue", "--source-sync-dir", str(source_sync_dir),
        "--readiness", "ready_for_review", "--source-type", "github", "--limit", "1",
    ])

    assert result.exit_code == 0, result.output
    assert "items: 1" in result.output
    assert "[ready_for_review]" in result.output


def test_review_queue_cli_build_supports_date_filter(tmp_path: Path) -> None:
    source_sync_dir = tmp_path / "source_sync"
    write_source_sync_fixture(source_sync_dir)
    output = tmp_path / "generated" / "review_queue.md"
    jsonl = tmp_path / "generated" / "review_queue.jsonl"

    result = runner.invoke(main.app, [
        "build-review-queue", "--source-sync-dir", str(source_sync_dir), "--output", str(output),
        "--jsonl-output", str(jsonl), "--from", "2026-07-11", "--to", "2026-07-11",
    ])

    assert result.exit_code == 0, result.output
    assert "items: 1" in result.output
    assert output.exists() and jsonl.exists()


def test_load_resume_data_has_projects() -> None:
    data = load_resume_data()

    assert data["profile"]["title"] == "職務経歴書"
    assert len(data["projects"]) >= 1


def test_render_markdown_contains_required_sections() -> None:
    markdown = render_markdown()

    assert "# 職務経歴書" in markdown
    assert "## 職務要約" in markdown
    assert "## 技術スタック" in markdown
    assert "## AI活用経験" in markdown
    assert "## プロジェクト経歴" in markdown
    assert '<table class="phase-table">' in markdown
    assert "バージョン" in markdown


def test_generate_markdown_file_writes_output(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main, "GENERATED_DIR", tmp_path / "generated")

    output_path = main.generate_markdown_file()

    assert output_path.exists()
    assert "# 職務経歴書" in output_path.read_text(encoding="utf-8")


def test_source_rule_loaders_read_split_rule_files() -> None:
    categories = main.load_category_rules()
    technologies = main.load_technology_rules()
    ai_tools = main.load_ai_tool_rules()
    noise = main.load_noise_rules()
    confidence = main.load_confidence_rules()
    evidence = main.load_evidence_rules()
    sensitive_labels = main.load_sensitive_label_rules()

    assert "categories" in categories
    assert "category_keywords" in categories
    assert "tag_keywords" in technologies
    assert "tool_keywords" in ai_tools
    assert "noise_keywords" in noise
    assert "thresholds" in confidence
    assert "source_type_weights" in confidence
    assert confidence["levels"]["high"]["min_score"] == 80
    assert evidence["schema"] == "canonical_event_v0_3"
    assert "labels" in sensitive_labels


def test_generate_pdf_file_writes_output(monkeypatch, tmp_path: Path) -> None:
    generated_dir = tmp_path / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = generated_dir / "resume.md"
    markdown_path.write_text("# sample\n", encoding="utf-8")

    def fake_markdown_to_pdf(markdown_path_arg: Path, output_path_arg: Path, theme: str = "forest") -> None:
        assert markdown_path_arg == markdown_path
        assert theme == "forest"
        output_path_arg.write_bytes(b"%PDF-1.7\n% test\n")

    monkeypatch.setattr(main, "GENERATED_DIR", generated_dir)
    monkeypatch.setattr(main, "markdown_to_pdf", fake_markdown_to_pdf)

    output_path = main.generate_pdf_file(theme="forest")

    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF-1.7")


def test_issue_creates_release_and_changelog(monkeypatch, tmp_path: Path) -> None:
    generated_dir = tmp_path / "generated"
    changelog_path = tmp_path / "CHANGELOG.md"

    monkeypatch.setattr(main, "GENERATED_DIR", generated_dir)
    monkeypatch.setattr(main, "RELEASES_DIR", generated_dir / "releases")
    monkeypatch.setattr(main, "CHANGELOG_PATH", changelog_path)

    def fake_generate_pdf_file(theme: str = "forest") -> Path:
        generated_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = generated_dir / "職務経歴書.pdf"
        pdf_path.write_bytes(b"%PDF-1.7\n% test\n")
        return pdf_path

    monkeypatch.setattr(main, "generate_pdf_file", fake_generate_pdf_file)

    release_dir = main.issue_resume(title="pytest発行", note="テスト発行")
    changelog = changelog_path.read_text(encoding="utf-8")

    assert (release_dir / "resume.md").exists()
    assert (release_dir / "職務経歴書.pdf").exists()
    assert "pytest発行" in changelog
    assert "### フィードバックエージェント結果" in changelog
    assert "全体として、提出可能な職務経歴書として最低限の構成は揃っている" in changelog


def test_forest_theme_exists() -> None:
    assert main.resolve_theme_css("forest").name == "forest.css"


def test_redact_sensitive_text_masks_guard_targets() -> None:
    message = "\n".join(
        [
            "株式会社〇〇",
            "https://example.com",
            "syogo@example.com",
            "https://workspace.slack.com/archives/C123",
            "https://github.com/example/repo",
            "Bearer token",
            "API Key",
            "192.168.0.1",
            "社員名",
            "案件名",
        ]
    )

    redacted, findings = main.redact_sensitive_text(message)

    assert "株式会社〇〇" not in redacted
    assert "https://example.com" not in redacted
    assert "syogo@example.com" not in redacted
    assert "192.168.0.1" not in redacted
    assert "[REDACTED_ORG_NAME]" in redacted
    assert "[REDACTED_URL]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_SLACK_URL]" in redacted
    assert "[REDACTED_GITHUB_URL]" in redacted
    assert "[REDACTED_BEARER_TOKEN]" in redacted
    assert "[REDACTED_API_KEY]" in redacted
    assert "[REDACTED_IP_ADDRESS]" in redacted
    assert "[REDACTED_EMPLOYEE_NAME]" in redacted
    assert "[REDACTED_PROJECT_NAME]" in redacted
    assert len(findings) == 10


def test_redact_sensitive_text_masks_realistic_sensitive_inputs() -> None:
    message = "\n".join(
        [
            "株式会社サンプル",
            "山田太郎",
            "tanaka@example.co.jp",
            "090-1234-5678",
            "03-1234-5678",
            "東京都渋谷区恵比寿1-1-1",
            "https://github.com/example/private-repo",
            "https://company.slack.com/archives/C123/p456",
            "Bearer abcdefghijklmnopqrstuvwxyz123456",
            "API_KEY=sk_test_1234567890abcdef",
            "AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxx",
            "192.168.10.20",
            "案件名: 次世代決済基盤",
            "PROJECT-1234",
            "feature/secret-branch",
            "prod-db-main",
        ]
    )

    redacted, findings = main.redact_sensitive_text(message)
    categories = {finding["category"] for finding in findings}

    for raw in [
        "山田太郎",
        "090-1234-5678",
        "03-1234-5678",
        "東京都渋谷区恵比寿1-1-1",
        "API_KEY=sk_test_1234567890abcdef",
        "AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxx",
        "次世代決済基盤",
        "PROJECT-1234",
        "feature/secret-branch",
        "prod-db-main",
    ]:
        assert raw not in redacted

    for marker in [
        "[REDACTED_PERSON_NAME]",
        "[REDACTED_PHONE_NUMBER]",
        "[REDACTED_ADDRESS]",
        "[REDACTED_API_KEY_VALUE]",
        "[REDACTED_AWS_SECRET_ACCESS_KEY]",
        "[REDACTED_PROJECT_NAME_VALUE]",
        "[REDACTED_TICKET_ID]",
        "[REDACTED_BRANCH_NAME]",
        "[REDACTED_ENV_OR_DB_NAME]",
    ]:
        assert marker in redacted

    assert {
        "PHONE_NUMBER",
        "ADDRESS",
        "PERSON_NAME",
        "API_KEY_VALUE",
        "AWS_SECRET_ACCESS_KEY",
        "TICKET_ID",
        "BRANCH_NAME",
        "ENV_OR_DB_NAME",
        "PROJECT_NAME_VALUE",
    }.issubset(categories)


def test_add_log_redacts_before_saving_and_writes_guard_report(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    events_dir = data_dir / "events"
    reviews_dir = app_root / "reviews" / "guard"

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "EVENTS_DIR", events_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    main.add_log(
        message="\n".join(
            [
                "株式会社〇〇",
                "https://example.com",
                "syogo@example.com",
                "Slack URL",
                "GitHub URL",
                "Bearer token",
                "API Key",
                "IP Address",
                "社員名",
                "案件名",
            ]
        )
    )

    event_files = sorted(events_dir.glob("*.yaml"))
    assert len(event_files) == 1
    event_text = event_files[0].read_text(encoding="utf-8")
    assert "株式会社〇〇" not in event_text
    assert "syogo@example.com" not in event_text
    assert "https://example.com" not in event_text
    assert "[REDACTED_ORG_NAME]" in event_text
    assert "[REDACTED_EMAIL]" in event_text
    assert "[REDACTED_URL]" in event_text

    report_files = sorted(reviews_dir.glob("*.md"))
    assert len(report_files) == 1
    report_text = report_files[0].read_text(encoding="utf-8")
    assert "株式会社〇〇" not in report_text
    assert "syogo@example.com" not in report_text
    assert "https://example.com" not in report_text
    assert "REDACTED_ORG_NAME" in report_text
    assert "REDACTED_EMAIL" in report_text
    assert "Stored Message" in report_text


def test_add_log_redacts_realistic_sensitive_inputs_before_saving(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    events_dir = data_dir / "events"
    reviews_dir = app_root / "reviews" / "guard"

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "EVENTS_DIR", events_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    message = "\n".join(
        [
            "株式会社サンプル",
            "山田太郎",
            "tanaka@example.co.jp",
            "090-1234-5678",
            "東京都渋谷区恵比寿1-1-1",
            "https://github.com/example/private-repo",
            "https://company.slack.com/archives/C123/p456",
            "Bearer abcdefghijklmnopqrstuvwxyz123456",
            "API_KEY=sk_test_1234567890abcdef",
            "AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxx",
            "192.168.10.20",
            "案件名: 次世代決済基盤",
            "PROJECT-1234",
            "feature/secret-branch",
            "prod-db-main",
        ]
    )

    main.add_log(message=message)

    event_text = next(events_dir.glob("*.yaml")).read_text(encoding="utf-8")
    report_text = next(reviews_dir.glob("*.md")).read_text(encoding="utf-8")

    for raw in [
        "山田太郎",
        "090-1234-5678",
        "東京都渋谷区恵比寿1-1-1",
        "API_KEY=sk_test_1234567890abcdef",
        "AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxx",
        "次世代決済基盤",
        "PROJECT-1234",
        "feature/secret-branch",
        "prod-db-main",
    ]:
        assert raw not in event_text
        assert raw not in report_text

    assert "[REDACTED_PERSON_NAME]" in event_text
    assert "[REDACTED_PHONE_NUMBER]" in event_text
    assert "[REDACTED_ADDRESS]" in event_text
    assert "[REDACTED_API_KEY_VALUE]" in event_text
    assert "[REDACTED_AWS_SECRET_ACCESS_KEY]" in event_text
    assert "[REDACTED_PROJECT_NAME_VALUE]" in event_text
    assert "[REDACTED_TICKET_ID]" in event_text
    assert "[REDACTED_BRANCH_NAME]" in event_text
    assert "[REDACTED_ENV_OR_DB_NAME]" in event_text


def test_normalize_source_extracts_canonical_event_and_removes_noise(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    raw_file = data_dir / "raw_sources" / "2026-07-09_sample.txt"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_text(
        "\n".join(
            [
                "眠いしコーヒー飲んだ",
                "GraphQL Resolver の N+1 を見直して Cursor と Claude で修正方針を整理",
                "PR レビューで設計の指摘を反映してリファクタ方針を決定",
                "株式会社サンプル 090-1234-5678 https://github.com/example/private-repo",
                "昼飯の話だけした",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    output_path = main.normalize_source_file(raw_file)
    content = output_path.read_text(encoding="utf-8")
    report_text = next(reviews_dir.glob("*.md")).read_text(encoding="utf-8")

    assert output_path.name == "2026-07-09.md"
    assert "schema: canonical_event_v0_3" in content
    assert "actions:" in content
    assert "tags:" in content
    assert "tools:" in content
    assert "evidence:" in content
    assert "GraphQL" in content
    assert "Resolver" in content
    assert "Cursor" in content
    assert "Claude" in content
    assert "レビュー" in content
    assert "眠い" not in content
    assert "コーヒー" not in content
    assert "昼飯" not in content
    assert "株式会社サンプル" not in content
    assert "090-1234-5678" not in content
    assert "https://github.com/example/private-repo" not in content
    assert "noise_removed:" in content
    assert "fatigue" in content
    assert "drink" in content
    assert "meal" in content
    assert "confidence: medium" in content
    assert "confidence_reasons:" in content
    assert "[REDACTED_ORG_NAME]" not in content
    assert "[REDACTED_PHONE_NUMBER]" not in content
    assert "[REDACTED_GITHUB_URL]" not in content
    assert "source_reference" in content
    assert "2026-07-09_sample.txt" in content
    assert "[REDACTED_ORG_NAME]" in report_text
    assert "[REDACTED_PHONE_NUMBER]" in report_text
    assert "[REDACTED_GITHUB_URL]" in report_text


def test_normalize_sources_processes_multiple_files(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    raw_dir = data_dir / "raw_sources"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "2026-07-08_daily.txt").write_text(
        "GraphQL の schema 修正と Resolver 実装を進めた",
        encoding="utf-8",
    )
    (raw_dir / "2026-07-09_slack.txt").write_text(
        "Claude でレビュー観点を整理して PR レビューを実施",
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    output_paths = main.normalize_all_sources()

    assert len(output_paths) == 2
    assert source_sync_dir.joinpath("2026-07-08.md").exists()
    assert source_sync_dir.joinpath("2026-07-09.md").exists()
    assert "GraphQL" in source_sync_dir.joinpath("2026-07-08.md").read_text(encoding="utf-8")
    assert "Claude" in source_sync_dir.joinpath("2026-07-09.md").read_text(encoding="utf-8")


def test_file_source_adapter_discovers_raw_sources(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "app" / "data"
    raw_dir = data_dir / "raw_sources"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sample = raw_dir / "2026-07-09_sample.txt"
    sample.write_text("GraphQL Resolver を見直した", encoding="utf-8")

    monkeypatch.setattr(main, "DATA_DIR", data_dir)

    adapter = main.FileSourceAdapter(raw_dir)
    sources = adapter.discover()

    assert len(sources) == 1
    source = sources[0]
    assert source.source_type == "file"
    assert source.origin == str(sample.resolve())
    assert source.content == "GraphQL Resolver を見直した"
    assert source.title == "2026-07-09_sample.txt"
    assert source.id == "2026-07-09_sample.txt"


def test_file_source_adapter_fetches_source_by_id(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "app" / "data"
    raw_dir = data_dir / "raw_sources"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sample = raw_dir / "2026-07-09_sample.txt"
    sample.write_text("PR レビューを実施", encoding="utf-8")

    monkeypatch.setattr(main, "DATA_DIR", data_dir)

    adapter = main.FileSourceAdapter(raw_dir)
    source = adapter.fetch("2026-07-09_sample.txt")

    assert source.content == "PR レビューを実施"
    with pytest.raises(main.SourceNotFoundError):
        adapter.fetch("missing.txt")


def test_daily_report_source_adapter_discovers_reports(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "app" / "data"
    reports_dir = data_dir / "daily_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    sample = reports_dir / "2026-07-11.md"
    sample.write_text("GraphQL Resolver を分離した", encoding="utf-8")
    nested = reports_dir / "notes" / "20260710-worklog.txt"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("Slack Connector を追加した", encoding="utf-8")

    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)

    adapter = main.DailyReportSourceAdapter(reports_dir)
    sources = adapter.discover()

    assert len(sources) == 2
    assert all(source.source_type == "daily_report" for source in sources)
    assert all(source.metadata["kind"] in {"freestyle_report", "worklog"} for source in sources)
    assert sources[0].id == "daily_report:2026-07-11.md"
    assert sources[0].content == "GraphQL Resolver を分離した"
    assert sources[0].metadata["relative_path"] == "2026-07-11.md"
    assert sources[0].metadata["format"] == "markdown"
    assert sources[1].id == "daily_report:notes/20260710-worklog.txt"
    assert sources[1].metadata["format"] == "text"


def test_daily_report_source_adapter_fetches_source_by_id(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "app" / "data"
    reports_dir = data_dir / "daily_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    sample = reports_dir / "2026-07-11.md"
    sample.write_text("PR レビューを実施", encoding="utf-8")

    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)

    adapter = main.DailyReportSourceAdapter(reports_dir)
    source = adapter.fetch("daily_report:2026-07-11.md")

    assert source.content == "PR レビューを実施"
    with pytest.raises(main.SourceNotFoundError):
        adapter.fetch("daily_report:missing.md")


def test_daily_report_detects_date_from_filename() -> None:
    assert main.detect_daily_report_date(
        Path("2026-07-11.md"),
        "",
        "",
        {},
    ) == "2026-07-11"
    assert main.detect_daily_report_date(
        Path("20260711-worklog.txt"),
        "",
        "",
        {},
    ) == "2026-07-11"
    assert main.detect_daily_report_date(
        Path("2026_07_11_note.md"),
        "",
        "",
        {},
    ) == "2026-07-11"


def test_daily_report_detects_date_from_frontmatter() -> None:
    assert main.detect_daily_report_date(
        Path("free-note.md"),
        "---\ndate: 2026-07-11\n---\nbody",
        "body",
        {"date": "2026-07-11"},
    ) == "2026-07-11"


def test_daily_report_single_file_and_bulk_import_use_same_source_id(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "app" / "data"
    reports_dir = data_dir / "daily_reports"
    report = reports_dir / "notes" / "20260710-worklog.txt"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("Slack Connector を追加した", encoding="utf-8")

    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)

    single_source = main.inspect_daily_report_file(report)
    bulk_source = main.DailyReportSourceAdapter(reports_dir).discover()[0]

    assert single_source.id == "daily_report:notes/20260710-worklog.txt"
    assert bulk_source.id == "daily_report:notes/20260710-worklog.txt"
    assert single_source.id == bulk_source.id


def test_daily_report_file_outside_default_dir_uses_parent_as_root(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "app" / "data"
    reports_dir = data_dir / "daily_reports"
    external_dir = tmp_path / "external"
    report = external_dir / "external-note.md"
    external_dir.mkdir(parents=True, exist_ok=True)
    report.write_text("GraphQL Resolver を分離した", encoding="utf-8")

    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)

    source = main.inspect_daily_report_file(report)

    assert source.id == "daily_report:external-note.md"


def test_source_adapter_registry_lists_file_adapter(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "app" / "data"
    raw_dir = data_dir / "raw_sources"
    reports_dir = data_dir / "daily_reports"
    raw_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "sample.txt").write_text("sample", encoding="utf-8")
    (reports_dir / "2026-07-11.md").write_text("sample", encoding="utf-8")

    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)

    registry = main.build_source_adapter_registry()

    assert "file" in registry.list()
    assert "daily_report" in registry.list()
    assert "github" in registry.list()
    assert "slack" in registry.list()
    assert "teams" in registry.list()
    result = runner.invoke(main.app, ["list-source-adapters"])
    assert result.exit_code == 0
    assert result.stdout.strip().splitlines() == ["daily_report", "file", "github", "slack", "teams"]


def test_inspect_source_adapter_lists_discovered_sources(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "app" / "data"
    raw_dir = data_dir / "raw_sources"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sample = raw_dir / "2026-07-09_sample.txt"
    sample.write_text("Resolver 分離を実施", encoding="utf-8")

    monkeypatch.setattr(main, "DATA_DIR", data_dir)

    result = runner.invoke(main.app, ["inspect-source-adapter", "--adapter", "file"])

    assert result.exit_code == 0
    assert "adapter: file" in result.stdout
    assert "discovered_sources: 1" in result.stdout
    assert "id: 2026-07-09_sample.txt" in result.stdout
    assert f"origin: {sample.resolve()}" in result.stdout
    assert "title: 2026-07-09_sample.txt" in result.stdout


def test_inspect_daily_report_cli(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    reports_dir = data_dir / "daily_reports"
    sample = reports_dir / "2026-07-11.md"
    reports_dir.mkdir(parents=True, exist_ok=True)
    sample.write_text("# 2026-07-11\n\nGraphQL Resolver を分離した", encoding="utf-8")

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)

    result = runner.invoke(main.app, ["inspect-daily-report", "--file", str(sample)])

    assert result.exit_code == 0
    assert "adapter: daily_report" in result.stdout
    assert "id: daily_report:2026-07-11.md" in result.stdout
    assert "title: Daily Report 2026-07-11" in result.stdout
    assert "detected_date: 2026-07-11" in result.stdout
    assert "GraphQL Resolver" not in result.stdout


def test_inspect_daily_reports_cli(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    reports_dir = data_dir / "daily_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "2026-07-11.md").write_text("GraphQL Resolver を分離した", encoding="utf-8")
    (reports_dir / "free-note.txt").write_text("Slack Connector を追加した", encoding="utf-8")

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)

    result = runner.invoke(main.app, ["inspect-daily-reports", "--dir", str(reports_dir), "--limit", "20"])

    assert result.exit_code == 0
    assert "adapter: daily_report" in result.stdout
    assert "discovered_sources: 2" in result.stdout
    assert "daily_report:2026-07-11.md" in result.stdout
    assert "GraphQL Resolver" not in result.stdout


def test_normalize_sources_still_works_with_file_adapter(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    raw_dir = data_dir / "raw_sources"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "2026-07-09_daily.txt").write_text(
        "\n".join(
            [
                "今日は眠い",
                "GraphQL Resolver の分離を実施",
                "Claude でレビュー観点を整理",
                "昼飯ラーメン",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    output_paths = main.normalize_all_sources()

    assert len(output_paths) == 1
    output_path = output_paths[0]
    assert output_path == source_sync_dir / "2026-07-09.md"
    content = output_path.read_text(encoding="utf-8")
    assert "GraphQL Resolver分離を実施" in content
    assert "noise_removed:" in content
    assert "fatigue" in content
    assert "meal" in content
    assert "low_signal" in content


def test_normalize_source_filters_low_signal_noisy_input(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    raw_file = data_dir / "raw_sources" / "noisy_sample.txt"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_text(
        "\n".join(
            [
                "今日は眠い",
                "コーヒー飲んだ",
                "レビュー受けた",
                "GraphQLやった",
                "Cursor便利",
                "Resolver分離した",
                "雨だった",
                "Claudeに聞いた",
                "疲れた",
                "PRで設計指摘もらった",
                "リファクタ方針を決めた",
                "昼飯ラーメン",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    output_path = main.normalize_source_file(raw_file)
    content = output_path.read_text(encoding="utf-8")

    assert "レビュー対応を実施" in content
    assert "GraphQL関連の実装・調査を実施" in content
    assert "Resolver分離を実施" in content
    assert "PRレビューで設計指摘を受領" in content
    assert "リファクタ方針を決定" in content
    assert "Cursor便利" not in content
    assert "Claudeに聞いた" not in content
    assert "今日は眠い" not in content
    assert "コーヒー" not in content
    assert "雨だった" not in content
    assert "疲れた" not in content
    assert "昼飯" not in content
    assert "fatigue" in content
    assert "drink" in content
    assert "weather" in content
    assert "meal" in content
    assert "low_signal" in content


def test_github_source_adapter_discovers_pull_requests() -> None:
    fixtures = {
        (
            "gh",
            "pr",
            "list",
            "--repo",
            "s-kyono/me-shower",
            "--state",
            "all",
            "--limit",
            "20",
            "--json",
            "number,title,body,state,author,createdAt,updatedAt,url,labels",
        ): main.CommandResult(
            stdout=json.dumps(
                [
                    {
                        "number": 3,
                        "title": "Add source normalizer and split source intelligence rules",
                        "body": "GraphQL Resolver を分離し、正規化ルールを整理した",
                        "state": "OPEN",
                        "author": {"login": "s-kyono"},
                        "createdAt": "2026-07-10T08:00:00Z",
                        "updatedAt": "2026-07-11T09:30:00Z",
                        "url": "https://github.com/s-kyono/me-shower/pull/3",
                        "labels": [{"name": "source-intelligence"}, {"name": "normalizer"}],
                    }
                ]
            ),
            stderr="",
            returncode=0,
        )
    }

    adapter = main.GitHubSourceAdapter(
        repo="s-kyono/me-shower",
        command_runner=build_command_runner(fixtures),
    )
    sources = adapter.discover()

    assert len(sources) == 1
    source = sources[0]
    assert source.source_type == "github"
    assert source.metadata["kind"] == "pull_request"
    assert source.id == "github:s-kyono/me-shower:pr:3"
    assert source.origin == "github:s-kyono/me-shower#3"
    assert "PR #3 Add source normalizer and split source intelligence rules" in source.content
    assert "GraphQL Resolver を分離し、正規化ルールを整理した" in source.content


def test_github_source_adapter_fetches_source_by_id() -> None:
    fixtures = {
        (
            "gh",
            "pr",
            "view",
            "3",
            "--repo",
            "s-kyono/me-shower",
            "--json",
            "number,title,body,state,author,createdAt,updatedAt,url,labels,files",
        ): main.CommandResult(
            stdout=json.dumps(
                {
                    "number": 3,
                    "title": "Add source normalizer and split source intelligence rules",
                    "body": "Resolver 分離とルール整理を実施",
                    "state": "MERGED",
                    "author": {"login": "s-kyono"},
                    "createdAt": "2026-07-10T08:00:00Z",
                    "updatedAt": "2026-07-11T09:30:00Z",
                    "url": "https://github.com/s-kyono/me-shower/pull/3",
                    "labels": [{"name": "source-intelligence"}],
                    "files": [
                        {"path": "app/src/main.py", "additions": 120, "deletions": 12},
                        {"path": "app/tests/test_render.py", "additions": 40, "deletions": 0},
                    ],
                }
            ),
            stderr="",
            returncode=0,
        ),
        (
            "gh",
            "pr",
            "view",
            "999",
            "--repo",
            "s-kyono/me-shower",
            "--json",
            "number,title,body,state,author,createdAt,updatedAt,url,labels,files",
        ): main.CommandResult(
            stdout="",
            stderr="pull request not found",
            returncode=1,
        ),
    }

    adapter = main.GitHubSourceAdapter(
        repo="s-kyono/me-shower",
        command_runner=build_command_runner(fixtures),
    )
    source = adapter.fetch("github:s-kyono/me-shower:pr:3")

    assert source.metadata["number"] == 3
    assert source.metadata["changed_files"] == [
        "app/src/main.py (+120 -12)",
        "app/tests/test_render.py (+40 -0)",
    ]
    with pytest.raises(main.SourceNotFoundError):
        adapter.fetch("github:s-kyono/me-shower:pr:999")


def test_slack_source_adapter_discovers_messages(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-secret")
    fixtures = {
        (
            "conversations.history",
            (("channel", "C0123456789"), ("inclusive", True), ("limit", 20)),
        ): {
            "ok": True,
            "messages": [
                {
                    "ts": "1781736600.000100",
                    "text": "SLACK_SENTINEL GraphQL Resolver を分離した",
                    "user": "U12345678",
                    "thread_ts": "1781736600.000100",
                }
            ],
        },
        (
            "chat.getPermalink",
            (("channel", "C0123456789"), ("message_ts", "1781736600.000100")),
        ): {
            "ok": True,
            "permalink": "https://example.slack.com/archives/C0123456789/p1781736600000100",
        },
    }

    adapter = main.SlackSourceAdapter(
        channel="C0123456789",
        api_caller=build_slack_api_caller(fixtures),
    )
    sources = adapter.discover()

    assert len(sources) == 1
    source = sources[0]
    assert source.source_type == "slack"
    assert source.metadata["kind"] == "message"
    assert source.id == "slack:C0123456789:1781736600.000100"
    assert source.origin == "slack:C0123456789:1781736600.000100"
    assert "SLACK_SENTINEL GraphQL Resolver を分離した" in source.content
    assert source.metadata["permalink"] == "https://example.slack.com/archives/C0123456789/p1781736600000100"


def test_slack_source_adapter_fetches_source_by_id(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-secret")
    fixtures = {
        (
            "conversations.history",
            (("channel", "C0123456789"), ("inclusive", True), ("limit", 20)),
        ): {
            "ok": True,
            "messages": [
                {
                    "ts": "1781736600.000100",
                    "text": "GraphQL Resolver を分離した",
                    "user": "U12345678",
                }
            ],
        },
        (
            "chat.getPermalink",
            (("channel", "C0123456789"), ("message_ts", "1781736600.000100")),
        ): {
            "ok": True,
            "permalink": "https://example.slack.com/archives/C0123456789/p1781736600000100",
        },
    }

    adapter = main.SlackSourceAdapter(
        channel="C0123456789",
        api_caller=build_slack_api_caller(fixtures),
    )
    source = adapter.fetch("slack:C0123456789:1781736600.000100")

    assert source.metadata["ts"] == "1781736600.000100"
    with pytest.raises(main.SourceNotFoundError):
        adapter.fetch("slack:C0123456789:missing")


def test_teams_html_body_to_text() -> None:
    body = "<div>GraphQL Resolver を分離しました <at id=\"0\">山田太郎</at> &amp; schema を更新</div>"

    text = main.teams_html_body_to_text(body)

    assert text == "GraphQL Resolver を分離しました 山田太郎 & schema を更新"


def test_teams_source_adapter_discovers_messages(monkeypatch) -> None:
    monkeypatch.setenv("MS_GRAPH_TOKEN", "eyJ.fake.token")
    fixtures = {
        (
            "/v1.0/teams/team-123/channels/channel-456/messages",
            (("$top", 20),),
        ): {
            "value": [
                {
                    "id": "1700000000001",
                    "createdDateTime": "2026-07-11T01:30:00Z",
                    "lastModifiedDateTime": "2026-07-11T01:45:00Z",
                    "subject": "",
                    "summary": "",
                    "importance": "normal",
                    "messageType": "message",
                    "replyToId": None,
                    "webUrl": "https://teams.microsoft.com/l/message/abc",
                    "body": {
                        "contentType": "html",
                        "content": "<div>GraphQL Resolver を分離しました <at id=\"0\">山田太郎</at> &amp; schema を更新</div>",
                    },
                    "from": {
                        "user": {
                            "id": "user-123",
                            "displayName": "山田太郎",
                        }
                    },
                }
            ]
        }
    }

    adapter = main.TeamsSourceAdapter(
        team_id="team-123",
        channel_id="channel-456",
        api_caller=build_graph_api_caller(fixtures),
    )
    sources = adapter.discover()

    assert len(sources) == 1
    source = sources[0]
    assert source.source_type == "teams"
    assert source.metadata["kind"] == "channel_message"
    assert source.id == "teams:team-123:channel-456:1700000000001"
    assert source.origin == "teams:team-123:channel-456:1700000000001"
    assert "GraphQL Resolver を分離しました 山田太郎 & schema を更新" in source.content
    assert "<at id=" not in source.content


def test_teams_source_adapter_fetches_source_by_id(monkeypatch) -> None:
    monkeypatch.setenv("MS_GRAPH_TOKEN", "eyJ.fake.token")
    fixtures = {
        (
            "/v1.0/teams/team-123/channels/channel-456/messages",
            (("$top", 20),),
        ): {
            "value": [
                {
                    "id": "1700000000001",
                    "createdDateTime": "2026-07-11T01:30:00Z",
                    "lastModifiedDateTime": "2026-07-11T01:45:00Z",
                    "importance": "normal",
                    "messageType": "message",
                    "body": {
                        "contentType": "html",
                        "content": "<div>GraphQL Resolver を分離しました</div>",
                    },
                    "from": {"user": {"id": "user-123", "displayName": "山田太郎"}},
                }
            ]
        }
    }

    adapter = main.TeamsSourceAdapter(
        team_id="team-123",
        channel_id="channel-456",
        api_caller=build_graph_api_caller(fixtures),
    )
    source = adapter.fetch("teams:team-123:channel-456:1700000000001")

    assert source.metadata["message_id"] == "1700000000001"
    with pytest.raises(main.SourceNotFoundError):
        adapter.fetch("teams:team-123:channel-456:missing")


def test_github_connector_does_not_persist_raw_content(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"

    fixtures = {
        (
            "gh",
            "pr",
            "list",
            "--repo",
            "s-kyono/me-shower",
            "--state",
            "all",
            "--limit",
            "10",
            "--json",
            "number,title,body,state,author,createdAt,updatedAt,url,labels",
        ): main.CommandResult(
            stdout=json.dumps(
                [
                    {
                        "number": 3,
                        "title": "Add source normalizer and split source intelligence rules",
                        "body": "INTERNAL_RAW_BODY_SHOULD_NOT_BE_PERSISTED GraphQL Resolver 分離を実施",
                        "state": "OPEN",
                        "author": {"login": "s-kyono"},
                        "createdAt": "2026-07-10T08:00:00Z",
                        "updatedAt": "2026-07-11T09:30:00Z",
                        "url": "https://github.com/s-kyono/me-shower/pull/3",
                        "labels": [{"name": "source-intelligence"}],
                    }
                ]
            ),
            stderr="",
            returncode=0,
        )
    }

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    output_paths = main.normalize_github_sources(
        repo="s-kyono/me-shower",
        limit=10,
        command_runner=build_command_runner(fixtures),
    )

    assert len(output_paths) == 1
    content = output_paths[0].read_text(encoding="utf-8")
    assert "GraphQL Resolver分離を実施" in content
    assert "INTERNAL_RAW_BODY_SHOULD_NOT_BE_PERSISTED" not in content


def test_github_connector_handles_gh_failure() -> None:
    fixtures = {
        (
            "gh",
            "pr",
            "list",
            "--repo",
            "s-kyono/me-shower",
            "--state",
            "all",
            "--limit",
            "20",
            "--json",
            "number,title,body,state,author,createdAt,updatedAt,url,labels",
        ): main.CommandResult(
            stdout="",
            stderr="authentication failed GH_TOKEN=super-secret github_pat_deadbeef",
            returncode=1,
        )
    }

    adapter = main.GitHubSourceAdapter(
        repo="s-kyono/me-shower",
        command_runner=build_command_runner(fixtures),
    )

    with pytest.raises(main.SourceAccessError) as exc_info:
        adapter.discover()

    message = str(exc_info.value)
    assert "super-secret" not in message
    assert "github_pat_deadbeef" not in message
    assert "GitHub CLI is not authenticated" in message


def test_slack_connector_does_not_persist_raw_message(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-secret")
    fixtures = {
        (
            "conversations.history",
            (("channel", "C0123456789"), ("inclusive", True), ("limit", 10)),
        ): {
            "ok": True,
            "messages": [
                {
                    "ts": "1781736600.000100",
                    "text": "SLACK_RAW_MESSAGE_SENTINEL GraphQL Resolver を分離した",
                    "user": "U12345678",
                }
            ],
        },
        (
            "chat.getPermalink",
            (("channel", "C0123456789"), ("message_ts", "1781736600.000100")),
        ): {"ok": False, "error": "message_not_found"},
    }

    output_paths = main.normalize_slack_sources(
        channel="C0123456789",
        limit=10,
        api_caller=build_slack_api_caller(fixtures),
    )

    assert len(output_paths) == 1
    content = output_paths[0].read_text(encoding="utf-8")
    assert "GraphQL Resolver分離を実施" in content
    assert "SLACK_RAW_MESSAGE_SENTINEL" not in content


def test_slack_connector_does_not_overwrite_existing_source_sync(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    source_sync_dir.mkdir(parents=True, exist_ok=True)
    existing = source_sync_dir / "2026-06-18.md"
    existing.write_text(
        "\n".join(
            [
                "# Canonical Events",
                "",
                "date: 2026-06-18",
                "",
                "## Event 1",
                "- schema: canonical_event_v0_3",
                "- date: 2026-06-18",
                "  source_id: file:daily:1",
                "  source_type: file",
                "  category: implementation",
                "  summary: 既存 file event",
                "  actions:",
                "  - 既存 file event",
                "  decisions:",
                "  - none",
                "  improvements:",
                "  - none",
                "  tags:",
                "  - none",
                "  tools:",
                "  - none",
                "  noise_removed:",
                "  - none",
                "  confidence: medium",
                "  evidence:",
                "  - kind: source_reference",
                "    detail: sample.txt",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-secret")
    fixtures = {
        (
            "conversations.history",
            (("channel", "C0123456789"), ("inclusive", True), ("limit", 10)),
        ): {
            "ok": True,
            "messages": [
                {
                    "ts": "1781736600.000100",
                    "text": "GraphQL Resolver を分離した",
                    "user": "U12345678",
                    "thread_ts": "1781736600.000100",
                }
            ],
        },
        (
            "chat.getPermalink",
            (("channel", "C0123456789"), ("message_ts", "1781736600.000100")),
        ): {"ok": False, "error": "message_not_found"},
    }

    output_paths = main.normalize_slack_sources(
        channel="C0123456789",
        limit=10,
        api_caller=build_slack_api_caller(fixtures),
    )

    assert len(output_paths) == 1
    content = output_paths[0].read_text(encoding="utf-8")
    assert "既存 file event" in content
    assert "slack:C0123456789:1781736600.000100" in content
    assert content.count("## Event 1") == 1
    assert content.count("## Event 2") == 1
    assert "## Event 1\n\n## Event" not in content


def test_slack_connector_does_not_duplicate_same_message(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-secret")
    fixtures = {
        (
            "conversations.history",
            (("channel", "C0123456789"), ("inclusive", True), ("limit", 10)),
        ): {
            "ok": True,
            "messages": [
                {
                    "ts": "1781736600.000100",
                    "text": "GraphQL Resolver を分離した",
                    "user": "U12345678",
                }
            ],
        },
        (
            "chat.getPermalink",
            (("channel", "C0123456789"), ("message_ts", "1781736600.000100")),
        ): {"ok": False, "error": "message_not_found"},
    }

    caller = build_slack_api_caller(fixtures)
    main.normalize_slack_sources(channel="C0123456789", limit=10, api_caller=caller)
    output_paths = main.normalize_slack_sources(channel="C0123456789", limit=10, api_caller=caller)

    assert len(output_paths) == 1
    content = output_paths[0].read_text(encoding="utf-8")
    assert content.count("source_id: slack:C0123456789:1781736600.000100") == 1
    assert content.count("## Event 1") == 1
    assert "## Event 2" not in content


def test_source_sync_merge_does_not_duplicate_event_headings(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    source_sync_dir.mkdir(parents=True, exist_ok=True)
    (source_sync_dir / "2026-06-18.md").write_text(
        "\n".join(
            [
                "# Canonical Events",
                "",
                "date: 2026-06-18",
                "",
                "## Event 1",
                "",
                "- schema: canonical_event_v0_3",
                "- date: 2026-06-18",
                "  source_id: file:daily:1",
                "  source_type: file",
                "  category: implementation",
                "  summary: 既存 file event",
                "  actions:",
                "  - 既存 file event",
                "  decisions:",
                "  - none",
                "  improvements:",
                "  - none",
                "  tags:",
                "  - none",
                "  tools:",
                "  - none",
                "  noise_removed:",
                "  - none",
                "  confidence: medium",
                "  evidence:",
                "  - kind: source_reference",
                "    detail: sample.txt",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-secret")
    fixtures = {
        (
            "conversations.history",
            (("channel", "C0123456789"), ("inclusive", True), ("limit", 10)),
        ): {
            "ok": True,
            "messages": [
                {
                    "ts": "1781736600.000100",
                    "text": "GraphQL Resolver を分離した",
                    "user": "U12345678",
                }
            ],
        },
        (
            "chat.getPermalink",
            (("channel", "C0123456789"), ("message_ts", "1781736600.000100")),
        ): {"ok": False, "error": "message_not_found"},
    }

    output_paths = main.normalize_slack_sources(
        channel="C0123456789",
        limit=10,
        api_caller=build_slack_api_caller(fixtures),
    )

    content = output_paths[0].read_text(encoding="utf-8")
    assert content.count("## Event 1") == 1
    assert content.count("## Event 2") == 1
    assert "## Event 1\n\n## Event" not in content


def test_source_sync_merge_preserves_existing_event_without_source_id(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    source_sync_dir.mkdir(parents=True, exist_ok=True)
    (source_sync_dir / "2026-06-18.md").write_text(
        "\n".join(
            [
                "# Canonical Events",
                "",
                "date: 2026-06-18",
                "",
                "## Event 1",
                "",
                "- schema: canonical_event_v0_3",
                "- date: 2026-06-18",
                "  source_type: file",
                "  category: implementation",
                "  summary: source_id なし既存 event",
                "  actions:",
                "  - source_id なし既存 event",
                "  decisions:",
                "  - none",
                "  improvements:",
                "  - none",
                "  tags:",
                "  - none",
                "  tools:",
                "  - none",
                "  noise_removed:",
                "  - none",
                "  confidence: medium",
                "  evidence:",
                "  - kind: source_reference",
                "    detail: legacy.txt",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-secret")
    fixtures = {
        (
            "conversations.history",
            (("channel", "C0123456789"), ("inclusive", True), ("limit", 10)),
        ): {
            "ok": True,
            "messages": [
                {
                    "ts": "1781736600.000100",
                    "text": "GraphQL Resolver を分離した",
                    "user": "U12345678",
                }
            ],
        },
        (
            "chat.getPermalink",
            (("channel", "C0123456789"), ("message_ts", "1781736600.000100")),
        ): {"ok": False, "error": "message_not_found"},
    }

    output_paths = main.normalize_slack_sources(
        channel="C0123456789",
        limit=10,
        api_caller=build_slack_api_caller(fixtures),
    )

    content = output_paths[0].read_text(encoding="utf-8")
    assert "source_id なし既存 event" in content
    assert "source_id: slack:C0123456789:1781736600.000100" in content
    assert content.count("## Event 1") == 1
    assert content.count("## Event 2") == 1


def test_source_sync_merge_does_not_duplicate_same_source_id(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-secret")
    fixtures = {
        (
            "conversations.history",
            (("channel", "C0123456789"), ("inclusive", True), ("limit", 10)),
        ): {
            "ok": True,
            "messages": [
                {
                    "ts": "1781736600.000100",
                    "text": "GraphQL Resolver を分離した",
                    "user": "U12345678",
                }
            ],
        },
        (
            "chat.getPermalink",
            (("channel", "C0123456789"), ("message_ts", "1781736600.000100")),
        ): {"ok": False, "error": "message_not_found"},
    }

    caller = build_slack_api_caller(fixtures)
    main.normalize_slack_sources(channel="C0123456789", limit=10, api_caller=caller)
    output_paths = main.normalize_slack_sources(channel="C0123456789", limit=10, api_caller=caller)

    content = output_paths[0].read_text(encoding="utf-8")
    assert content.count("source_id: slack:C0123456789:1781736600.000100") == 1
    assert content.count("## Event 1") == 1
    assert "## Event 2" not in content


def test_slack_connector_handles_api_failure(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-super-secret")
    fixtures = {
        (
            "conversations.history",
            (("channel", "C0123456789"), ("inclusive", True), ("limit", 20)),
        ): {
            "ok": False,
            "error": "invalid_auth xoxb-super-secret",
        }
    }
    adapter = main.SlackSourceAdapter(
        channel="C0123456789",
        api_caller=build_slack_api_caller(fixtures),
    )

    with pytest.raises(main.SourceAccessError) as exc_info:
        adapter.discover()

    message = str(exc_info.value)
    assert "xoxb-super-secret" not in message
    assert "Slack API access denied" in message


def test_teams_connector_does_not_persist_raw_message(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)
    monkeypatch.setenv("MS_GRAPH_TOKEN", "eyJ.fake.token")
    fixtures = {
        (
            "/v1.0/teams/team-123/channels/channel-456/messages",
            (("$top", 10),),
        ): {
            "value": [
                {
                    "id": "1700000000001",
                    "createdDateTime": "2026-07-11T01:30:00Z",
                    "lastModifiedDateTime": "2026-07-11T01:45:00Z",
                    "importance": "normal",
                    "messageType": "message",
                    "body": {
                        "contentType": "html",
                        "content": "<div>TEAMS_RAW_HTML_SENTINEL GraphQL Resolver を分離した</div>",
                    },
                    "from": {"user": {"id": "user-123", "displayName": "山田太郎"}},
                }
            ]
        }
    }

    output_paths = main.normalize_teams_sources(
        team_id="team-123",
        channel_id="channel-456",
        limit=10,
        api_caller=build_graph_api_caller(fixtures),
    )

    content = output_paths[0].read_text(encoding="utf-8")
    assert "GraphQL Resolver分離を実施" in content
    assert "TEAMS_RAW_HTML_SENTINEL" not in content
    assert "<div>" not in content


def test_teams_connector_does_not_overwrite_existing_source_sync(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    source_sync_dir.mkdir(parents=True, exist_ok=True)
    (source_sync_dir / "2026-07-11.md").write_text(
        "\n".join(
            [
                "# Canonical Events",
                "",
                "date: 2026-07-11",
                "",
                "## Event 1",
                "",
                "- schema: canonical_event_v0_3",
                "- date: 2026-07-11",
                "  source_id: file:daily:1",
                "  source_type: file",
                "  category: implementation",
                "  summary: 既存 file event",
                "  actions:",
                "  - 既存 file event",
                "  decisions:",
                "  - none",
                "  improvements:",
                "  - none",
                "  tags:",
                "  - none",
                "  tools:",
                "  - none",
                "  noise_removed:",
                "  - none",
                "  confidence: medium",
                "  evidence:",
                "  - kind: source_reference",
                "    detail: sample.txt",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)
    monkeypatch.setenv("MS_GRAPH_TOKEN", "eyJ.fake.token")
    fixtures = {
        (
            "/v1.0/teams/team-123/channels/channel-456/messages",
            (("$top", 10),),
        ): {
            "value": [
                {
                    "id": "1700000000001",
                    "createdDateTime": "2026-07-11T01:30:00Z",
                    "lastModifiedDateTime": "2026-07-11T01:45:00Z",
                    "importance": "normal",
                    "messageType": "message",
                    "body": {"contentType": "html", "content": "<div>GraphQL Resolver を分離した</div>"},
                    "from": {"user": {"id": "user-123", "displayName": "山田太郎"}},
                }
            ]
        }
    }

    output_paths = main.normalize_teams_sources(
        team_id="team-123",
        channel_id="channel-456",
        limit=10,
        api_caller=build_graph_api_caller(fixtures),
    )

    content = output_paths[0].read_text(encoding="utf-8")
    assert "既存 file event" in content
    assert "teams:team-123:channel-456:1700000000001" in content
    assert content.count("## Event 1") == 1
    assert content.count("## Event 2") == 1
    assert "## Event 1\n\n## Event" not in content


def test_teams_connector_does_not_duplicate_same_message(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)
    monkeypatch.setenv("MS_GRAPH_TOKEN", "eyJ.fake.token")
    fixtures = {
        (
            "/v1.0/teams/team-123/channels/channel-456/messages",
            (("$top", 10),),
        ): {
            "value": [
                {
                    "id": "1700000000001",
                    "createdDateTime": "2026-07-11T01:30:00Z",
                    "lastModifiedDateTime": "2026-07-11T01:45:00Z",
                    "importance": "normal",
                    "messageType": "message",
                    "body": {"contentType": "html", "content": "<div>GraphQL Resolver を分離した</div>"},
                    "from": {"user": {"id": "user-123", "displayName": "山田太郎"}},
                }
            ]
        }
    }

    caller = build_graph_api_caller(fixtures)
    main.normalize_teams_sources(team_id="team-123", channel_id="channel-456", limit=10, api_caller=caller)
    output_paths = main.normalize_teams_sources(team_id="team-123", channel_id="channel-456", limit=10, api_caller=caller)

    content = output_paths[0].read_text(encoding="utf-8")
    assert content.count("source_id: teams:team-123:channel-456:1700000000001") == 1
    assert content.count("## Event 1") == 1
    assert "## Event 2" not in content


def test_daily_report_import_does_not_persist_raw_text(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    reports_dir = data_dir / "daily_reports"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    report = reports_dir / "2026-07-11.md"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# 2026-07-11",
                "",
                "今日は眠い",
                "DAILY_SENTINEL GraphQL Resolver を分離した",
                "Slack Connector を追加した",
                "PRで設計指摘を受けた",
                "昼はラーメン",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    output_path = main.normalize_daily_report_file(report)
    content = output_path.read_text(encoding="utf-8")

    assert "DAILY_SENTINEL" not in content
    assert "GraphQL Resolver分離を実施" in content
    assert "Slack Connector関連の実装・調査を実施" in content
    assert "PRレビューで設計指摘を受領" in content
    assert "今日は眠い" not in content
    assert "ラーメン" not in content


def test_daily_report_import_does_not_overwrite_existing_source_sync(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    reports_dir = data_dir / "daily_reports"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    reports_dir.mkdir(parents=True, exist_ok=True)
    source_sync_dir.mkdir(parents=True, exist_ok=True)
    report = reports_dir / "2026-07-11.md"
    report.write_text("GraphQL Resolver を分離した", encoding="utf-8")
    (source_sync_dir / "2026-07-11.md").write_text(
        "\n".join(
            [
                "# Canonical Events",
                "",
                "date: 2026-07-11",
                "",
                "## Event 1",
                "",
                "- schema: canonical_event_v0_3",
                "- date: 2026-07-11",
                "  source_id: github:repo:pr:1",
                "  source_type: github",
                "  category: implementation",
                "  summary: 既存 GitHub event",
                "  actions:",
                "  - 既存 GitHub event",
                "  decisions:",
                "  - none",
                "  improvements:",
                "  - none",
                "  tags:",
                "  - none",
                "  tools:",
                "  - none",
                "  noise_removed:",
                "  - none",
                "  confidence: medium",
                "  evidence:",
                "  - kind: source_reference",
                "    detail: pr.txt",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    output_path = main.normalize_daily_report_file(report)
    content = output_path.read_text(encoding="utf-8")

    assert "既存 GitHub event" in content
    assert "source_id: daily_report:2026-07-11.md" in content
    assert content.count("## Event 1") == 1
    assert content.count("## Event 2") == 1
    assert "## Event 1\n\n## Event" not in content


def test_daily_report_import_does_not_duplicate_same_report(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    reports_dir = data_dir / "daily_reports"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report = reports_dir / "2026-07-11.md"
    report.write_text("GraphQL Resolver を分離した", encoding="utf-8")

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    main.normalize_daily_report_file(report)
    output_path = main.normalize_daily_report_file(report)
    content = output_path.read_text(encoding="utf-8")

    assert content.count("source_id: daily_report:2026-07-11.md") == 1
    assert content.count("## Event 1") == 1
    assert "## Event 2" not in content


def test_daily_report_single_then_bulk_import_does_not_duplicate(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    reports_dir = data_dir / "daily_reports"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    report = reports_dir / "notes" / "20260710-worklog.txt"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("Slack Connector を追加した", encoding="utf-8")

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    main.normalize_daily_report_file(report)
    output_path = main.normalize_daily_reports_dir(reports_dir, limit=20)[0]
    content = output_path.read_text(encoding="utf-8")

    assert content.count("source_id: daily_report:notes/20260710-worklog.txt") == 1
    assert content.count("## Event 1") == 1
    assert "## Event 2" not in content


def test_daily_report_free_style_noise_filtering(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    reports_dir = data_dir / "daily_reports"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    report = reports_dir / "2026-07-11.txt"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "今日は眠い",
                "コーヒー飲んだ",
                "GraphQL Resolver を分離した",
                "Slack Connector を追加した",
                "昼はラーメン",
                "PRで設計指摘を受けた",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    output_path = main.normalize_daily_report_file(report)
    content = output_path.read_text(encoding="utf-8")

    assert "GraphQL Resolver分離を実施" in content
    assert "Slack Connector関連の実装・調査を実施" in content
    assert "PRレビューで設計指摘を受領" in content
    assert "今日は眠い" not in content
    assert "コーヒー" not in content
    assert "ラーメン" not in content


def test_source_confidence_high_for_structured_github_event() -> None:
    raw_source = main.RawSource(
        id="github:s-kyono/me-shower:pr:3",
        source_type="github",
        origin="github:s-kyono/me-shower#3",
        title="PR #3 Add source confidence",
        content="\n".join(
            [
                "PR #3 Add source confidence",
                "Repository: s-kyono/me-shower",
                "State: merged",
                "Labels: source-intelligence, confidence",
                "Changed Files:",
                "- app/src/main.py (+120 -12)",
                "Body:",
                "GraphQL Resolver を分離し、PRレビューで設計指摘を反映して方針を決定した",
            ]
        ),
        captured_at="2026-07-11T09:30:00+09:00",
        metadata={
            "repo": "s-kyono/me-shower",
            "kind": "pull_request",
            "number": 3,
            "state": "merged",
            "created_at": "2026-07-10T08:00:00Z",
            "updated_at": "2026-07-11T09:30:00Z",
            "labels": ["source-intelligence", "confidence"],
            "changed_files": ["app/src/main.py (+120 -12)"],
            "source_reference": "github:s-kyono/me-shower#3",
        },
    )

    event = main.build_canonical_event_from_raw_source(raw_source)

    assert event["confidence"] == "high"
    assert "source_type:github" in event["confidence_reasons"]
    assert any(reason.startswith("actions:") for reason in event["confidence_reasons"])


def test_source_confidence_medium_for_daily_report_with_clear_actions_and_noise() -> None:
    raw_source = main.RawSource(
        id="daily_report:2026-07-11.md",
        source_type="daily_report",
        origin="daily_report:app/data/daily_reports/2026-07-11.md",
        title="Daily Report 2026-07-11",
        content="\n".join(
            [
                "今日は眠い",
                "コーヒー飲んだ",
                "GraphQL Resolver を分離した",
                "Slack Connector を追加した",
                "昼はラーメン",
            ]
        ),
        captured_at="2026-07-11",
        metadata={
            "kind": "freestyle_report",
            "path": "/tmp/2026-07-11.md",
            "relative_path": "2026-07-11.md",
            "detected_date": "2026-07-11",
            "source_reference": "daily_report:app/data/daily_reports/2026-07-11.md",
            "format": "markdown",
        },
    )

    event = main.build_canonical_event_from_raw_source(raw_source)

    assert event["confidence"] == "medium"
    assert "source_type:daily_report" in event["confidence_reasons"]
    assert any(reason.startswith("noise_removed:") for reason in event["confidence_reasons"])


def test_source_confidence_low_for_low_signal_report() -> None:
    raw_source = main.RawSource(
        id="daily_report:low-signal.txt",
        source_type="daily_report",
        origin="daily_report:app/data/daily_reports/low-signal.txt",
        title="Daily Report 2026-07-11",
        content="\n".join(
            [
                "今日は眠い",
                "コーヒー飲んだ",
                "昼はラーメン",
            ]
        ),
        captured_at="2026-07-11",
        metadata={
            "kind": "freestyle_report",
            "path": "/tmp/low-signal.txt",
            "relative_path": "low-signal.txt",
            "detected_date": "2026-07-11",
            "source_reference": "daily_report:app/data/daily_reports/low-signal.txt",
            "format": "text",
        },
    )

    event = main.build_canonical_event_from_raw_source(raw_source)

    assert event["confidence"] == "low"
    assert "actions:0" in event["confidence_reasons"]


def test_source_confidence_penalizes_unknown_source_type() -> None:
    raw_source = main.RawSource(
        id="unknown:1",
        source_type="unknown",
        origin="unknown:1",
        title="Unknown source",
        content="GraphQL Resolver を分離した",
        captured_at="2026-07-11",
        metadata={"path": "/tmp/unknown.txt"},
    )

    confidence = main.calculate_source_confidence(
        raw_source=raw_source,
        source_type="unknown",
        actions=["GraphQL Resolver分離を実施"],
        decisions=[],
        improvements=[],
        tags=["GraphQL", "Resolver"],
        tools=[],
        noise_removed=[],
        evidence_basis="GraphQL Resolver分離を実施",
        guard_findings=[],
    )

    assert confidence.level == "low"
    assert "penalty:unknown_source_type" in confidence.reasons


def test_source_confidence_reasons_do_not_include_raw_text() -> None:
    raw_source = main.RawSource(
        id="daily_report:2026-07-11.md",
        source_type="daily_report",
        origin="daily_report:app/data/daily_reports/2026-07-11.md",
        title="Daily Report 2026-07-11",
        content="CONFIDENCE_SENTINEL GraphQL Resolver を分離した",
        captured_at="2026-07-11",
        metadata={
            "kind": "freestyle_report",
            "path": "/tmp/2026-07-11.md",
            "relative_path": "2026-07-11.md",
            "detected_date": "2026-07-11",
            "source_reference": "daily_report:app/data/daily_reports/2026-07-11.md",
            "format": "markdown",
        },
    )

    event = main.build_canonical_event_from_raw_source(raw_source)

    assert "CONFIDENCE_SENTINEL" not in "\n".join(event["confidence_reasons"])


def test_source_confidence_loaded_from_rules() -> None:
    rules = main.load_confidence_rules()

    assert rules["source_type_weights"]["github"] == 15
    assert rules["levels"]["medium"]["min_score"] == 45


def test_existing_canonical_event_output_still_contains_confidence(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    reviews_dir = app_root / "reviews" / "guard"
    raw_file = data_dir / "raw_sources" / "2026-07-11_sample.txt"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_text("GraphQL Resolver を分離した", encoding="utf-8")

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    output_path = main.normalize_source_file(raw_file)
    content = output_path.read_text(encoding="utf-8")

    assert "confidence:" in content
    assert "confidence_reasons:" in content


def test_teams_connector_handles_api_failure(monkeypatch) -> None:
    monkeypatch.setenv("MS_GRAPH_TOKEN", "eyJ.super.secret.token")
    fixtures = {
        (
            "/v1.0/teams/team-123/channels/channel-456/messages",
            (("$top", 20),),
        ): {
            "error": {
                "code": "InvalidAuthenticationToken",
                "message": "token eyJ.super.secret.token is invalid",
            }
        }
    }
    adapter = main.TeamsSourceAdapter(
        team_id="team-123",
        channel_id="channel-456",
        api_caller=build_graph_api_caller(fixtures),
    )

    with pytest.raises(main.SourceAccessError) as exc_info:
        adapter.discover()

    message = str(exc_info.value)
    assert "eyJ.super.secret.token" not in message
    assert "invalid or expired" in message


def test_existing_cli_still_works(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    raw_dir = data_dir / "raw_sources"
    reports_dir = data_dir / "daily_reports"
    source_sync_dir = data_dir / "source_sync"
    generated_dir = app_root / "generated"
    reviews_dir = app_root / "reviews" / "guard"
    raw_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "2026-07-09_daily.txt").write_text("GraphQL Resolver の分離を実施", encoding="utf-8")
    write_source_sync_fixture(source_sync_dir)

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "DATA_DIR", data_dir)
    monkeypatch.setattr(main, "DAILY_REPORTS_DIR", reports_dir)
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync_dir)
    monkeypatch.setattr(main, "GENERATED_DIR", generated_dir)
    monkeypatch.setattr(main, "SOURCE_TIMELINE_PATH", generated_dir / "source_timeline.md")
    monkeypatch.setattr(main, "SOURCE_TIMELINE_JSONL_PATH", generated_dir / "source_timeline.jsonl")
    monkeypatch.setattr(main, "GUARD_REVIEWS_DIR", reviews_dir)

    list_result = runner.invoke(main.app, ["list-source-adapters"])
    inspect_result = runner.invoke(main.app, ["inspect-source-adapter", "--adapter", "file"])
    normalize_result = runner.invoke(main.app, ["normalize-sources"])
    timeline_build_result = runner.invoke(
        main.app,
        [
            "build-source-timeline",
            "--source-sync-dir",
            str(source_sync_dir),
            "--output",
            str(generated_dir / "source_timeline.md"),
            "--jsonl-output",
            str(generated_dir / "source_timeline.jsonl"),
        ],
    )
    timeline_inspect_result = runner.invoke(
        main.app,
        [
            "inspect-source-timeline",
            "--source-sync-dir",
            str(source_sync_dir),
            "--limit",
            "20",
        ],
    )

    assert list_result.exit_code == 0
    assert "daily_report" in list_result.stdout
    assert "file" in list_result.stdout
    assert "github" in list_result.stdout
    assert "slack" in list_result.stdout
    assert "teams" in list_result.stdout
    assert inspect_result.exit_code == 0
    assert "adapter: file" in inspect_result.stdout
    assert normalize_result.exit_code == 0
    assert timeline_build_result.exit_code == 0
    assert timeline_inspect_result.exit_code == 0
    assert source_sync_dir.joinpath("2026-07-09.md").exists()
    assert generated_dir.joinpath("source_timeline.md").exists()
    assert "Source Timeline" in timeline_inspect_result.stdout


def test_resume_agent_hook_is_design_only() -> None:
    context = main.run_resume_agent_hook("generate-md")

    assert context["trigger"] == "generate-md"
    assert context["status"] == "design_only"
    assert context["contract"]["normalizer_scope"] == "raw source -> canonical event / evidence"
    assert "generate-md" in context["contract"]["activation_points"]
    assert "issue" in context["contract"]["activation_points"]


def test_parse_source_sync_file_extracts_timeline_items(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    source_sync_dir = app_root / "data" / "source_sync"
    write_source_sync_fixture(source_sync_dir)
    monkeypatch.setattr(main, "ROOT", app_root)

    items = main.parse_source_sync_file(source_sync_dir / "2026-07-10.md")

    assert len(items) == 2
    assert items[0].date == "2026-07-10"
    assert items[0].source_id == "daily_report:2026-07-10.md"
    assert items[0].source_type == "daily_report"
    assert items[0].summary == "GraphQL Resolver分離を実施"
    assert items[0].confidence == "medium"
    assert items[1].source_id.startswith("unknown:2026-07-10:2")


def test_build_source_timeline_outputs_markdown(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    raw_dir = data_dir / "raw_sources"
    generated_dir = app_root / "generated"
    write_source_sync_fixture(source_sync_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "sentinel.txt").write_text("RAW_SOURCE_SENTINEL", encoding="utf-8")
    monkeypatch.setattr(main, "ROOT", app_root)

    output_path, _, item_count = main.build_source_timeline(
        source_sync_dir=source_sync_dir,
        output_path=generated_dir / "source_timeline.md",
        jsonl_output_path=None,
    )

    content = output_path.read_text(encoding="utf-8")
    assert item_count == 3
    assert "# Source Timeline" in content
    assert "GraphQL Resolver分離を実施" in content
    assert "daily_report:2026-07-10.md" in content
    assert "### medium · daily_report · implementation" in content
    assert "RAW_SOURCE_SENTINEL" not in content


def test_build_source_timeline_outputs_jsonl(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    source_sync_dir = app_root / "data" / "source_sync"
    generated_dir = app_root / "generated"
    write_source_sync_fixture(source_sync_dir)
    monkeypatch.setattr(main, "ROOT", app_root)

    _, jsonl_path, _ = main.build_source_timeline(
        source_sync_dir=source_sync_dir,
        output_path=generated_dir / "source_timeline.md",
        jsonl_output_path=generated_dir / "source_timeline.jsonl",
    )

    assert jsonl_path is not None
    lines = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 3
    assert all("date" in line for line in lines)
    assert all("source_id" in line for line in lines)
    assert all("confidence" in line for line in lines)


def test_inspect_source_timeline_filters_by_date_range(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    source_sync_dir = app_root / "data" / "source_sync"
    write_source_sync_fixture(source_sync_dir)
    monkeypatch.setattr(main, "ROOT", app_root)

    result = runner.invoke(
        main.app,
        [
            "inspect-source-timeline",
            "--source-sync-dir",
            str(source_sync_dir),
            "--from",
            "2026-07-10",
            "--to",
            "2026-07-10",
            "--limit",
            "20",
        ],
    )

    assert result.exit_code == 0
    assert "2026-07-10" in result.stdout
    assert "2026-07-11" not in result.stdout


def test_inspect_source_timeline_filters_by_source_type(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    source_sync_dir = app_root / "data" / "source_sync"
    write_source_sync_fixture(source_sync_dir)
    monkeypatch.setattr(main, "ROOT", app_root)

    result = runner.invoke(
        main.app,
        [
            "inspect-source-timeline",
            "--source-sync-dir",
            str(source_sync_dir),
            "--source-type",
            "daily_report",
            "--limit",
            "20",
        ],
    )

    assert result.exit_code == 0
    assert "daily_report" in result.stdout
    assert "slack implementation" not in result.stdout
    assert "github review" not in result.stdout


def test_inspect_source_timeline_filters_by_min_confidence(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    source_sync_dir = app_root / "data" / "source_sync"
    write_source_sync_fixture(source_sync_dir)
    monkeypatch.setattr(main, "ROOT", app_root)

    result = runner.invoke(
        main.app,
        [
            "inspect-source-timeline",
            "--source-sync-dir",
            str(source_sync_dir),
            "--min-confidence",
            "medium",
            "--limit",
            "20",
        ],
    )

    assert result.exit_code == 0
    assert "[high]" in result.stdout
    assert "[medium]" in result.stdout
    assert "[low]" not in result.stdout


def test_source_timeline_does_not_read_raw_sources(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    data_dir = app_root / "data"
    source_sync_dir = data_dir / "source_sync"
    raw_dir = data_dir / "raw_sources"
    generated_dir = app_root / "generated"
    write_source_sync_fixture(source_sync_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "sentinel.txt").write_text("RAW_SOURCE_SENTINEL", encoding="utf-8")
    monkeypatch.setattr(main, "ROOT", app_root)

    output_path, _, _ = main.build_source_timeline(
        source_sync_dir=source_sync_dir,
        output_path=generated_dir / "source_timeline.md",
        jsonl_output_path=None,
    )

    assert "RAW_SOURCE_SENTINEL" not in output_path.read_text(encoding="utf-8")


def test_source_timeline_does_not_modify_source_sync(monkeypatch, tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    source_sync_dir = app_root / "data" / "source_sync"
    generated_dir = app_root / "generated"
    write_source_sync_fixture(source_sync_dir)
    before = {path.name: path.read_text(encoding="utf-8") for path in source_sync_dir.glob("*.md")}
    monkeypatch.setattr(main, "ROOT", app_root)

    main.build_source_timeline(
        source_sync_dir=source_sync_dir,
        output_path=generated_dir / "source_timeline.md",
        jsonl_output_path=generated_dir / "source_timeline.jsonl",
    )

    after = {path.name: path.read_text(encoding="utf-8") for path in source_sync_dir.glob("*.md")}
    assert after == before


def test_loop_skills_writes_review_files(monkeypatch, tmp_path: Path) -> None:
    review_root = tmp_path / "reviews" / "skills"
    monkeypatch.setattr(main, "SKILL_REVIEWS_DIR", review_root)

    output_paths = main.write_skill_reviews(review_date=date(2026, 7, 9))

    assert len(output_paths) == 6
    target = review_root / "2026-07-09" / "career_architect.md"
    assert target.exists()
    proposal = target.read_text(encoding="utf-8")
    assert "# Skill Improvement Proposal: career_architect" in proposal
    assert "generated/resume.md" in proposal
    assert "CHANGELOG.md" in proposal


def test_list_skill_reviews_lists_generated_files(monkeypatch, tmp_path: Path, capsys) -> None:
    review_root = tmp_path / "reviews" / "skills"
    review_date = review_root / "2026-07-09"
    review_date.mkdir(parents=True, exist_ok=True)
    (review_date / "source_sync.md").write_text(
        """# Skill Improvement Proposal: source_sync

## Target
.codex/agents/source_sync/SKILLS.md

## Observed Issues
- sample issue

## Suggested Skill
- sample skill

## Reason
- sample reason

## Patch Proposal
```md
## 2026-07-09 Added

data/events/ を読む
```
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "SKILL_REVIEWS_DIR", review_root)

    main.list_skill_reviews()
    captured = capsys.readouterr().out

    assert "reviews/skills/2026-07-09/source_sync.md" in captured


def test_apply_skill_review_updates_target_once(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    app_root = repo_root / "app"
    codex_dir = repo_root / ".codex"
    proposal_dir = app_root / "reviews" / "skills" / "2026-07-09"
    applied_dir = app_root / "reviews" / "skills_applied"
    target_path = codex_dir / "agents" / "career_architect" / "SKILLS.md"
    changelog_path = app_root / "CHANGELOG.md"
    proposal_path = proposal_dir / "career_architect.md"

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("# career_architect サブエージェント\n", encoding="utf-8")
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text(
        """# Skill Improvement Proposal: career_architect

## Target
.codex/agents/career_architect/SKILLS.md

## Observed Issues
- sample issue

## Suggested Skill
- sample skill

## Reason
- sample reason

## Patch Proposal
```md
## 2026-07-09 Added

`generated/resume.md` を構成設計の入力に追加する
`CHANGELOG.md` を優先度判断の参照先に追加する
詳細、要点、統合、削る候補の分類を案件ごとに必須化する
```
""",
        encoding="utf-8",
    )
    changelog_path.write_text("# CHANGELOG\n\n", encoding="utf-8")

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "REPO_ROOT", repo_root)
    monkeypatch.setattr(main, "CODEX_DIR", codex_dir)
    monkeypatch.setattr(main, "CHANGELOG_PATH", changelog_path)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_DIR", applied_dir)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_INDEX", applied_dir / "index.jsonl")

    result = main.apply_skill_review_file(proposal_path)

    assert result["status"] == "applied"
    assert target_path.read_text(encoding="utf-8").count("generated/resume.md") == 1
    assert "skill-review-source: reviews/skills/2026-07-09/career_architect.md" in target_path.read_text(encoding="utf-8")
    assert "skill review applied: career_architect" in changelog_path.read_text(encoding="utf-8")
    assert (applied_dir / "2026-07-09" / "career_architect.md").exists()
    assert applied_dir.joinpath("index.jsonl").exists()

    second = main.apply_skill_review_file(proposal_path)
    assert second["status"] == "already applied"
    assert target_path.read_text(encoding="utf-8").count("skill-review-source: reviews/skills/2026-07-09/career_architect.md") == 1


def test_loop_skills_skips_applied_proposal_by_patch_hash(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    app_root = repo_root / "app"
    codex_dir = repo_root / ".codex"
    review_root = app_root / "reviews" / "skills"
    applied_dir = app_root / "reviews" / "skills_applied"
    agents_dir = codex_dir / "agents"
    target_date = date(2026, 7, 9)

    for agent in ["career_architect", "skill_mapper"]:
        agent_dir = agents_dir / agent
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "SKILLS.md").write_text("# sample\n", encoding="utf-8")

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "REPO_ROOT", repo_root)
    monkeypatch.setattr(main, "CODEX_DIR", codex_dir)
    monkeypatch.setattr(main, "GENERATED_DIR", app_root / "generated")
    monkeypatch.setattr(main, "CHANGELOG_PATH", app_root / "CHANGELOG.md")
    monkeypatch.setattr(main, "LOOP_SKILLS_RULES_DIR", repo_root / ".codex" / "loop-skills" / "rules")
    monkeypatch.setattr(main, "SKILL_REVIEWS_DIR", review_root)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_DIR", applied_dir)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_INDEX", applied_dir / "index.jsonl")

    proposal = main.build_skill_review(
        agent="career_architect",
        skill_text="# sample\n",
        rule={},
        source_summary={"events_count": 0, "source_sync_count": 0, "latest_resume_projects": [], "resume_mentions": {}, "changelog_dates": []},
        review_date=target_date,
    )
    patch_block = main.extract_patch_block(proposal)
    patch_hash = main.build_patch_hash(patch_block)
    summary = main.normalize_summary_lines(patch_block)
    applied_dir.mkdir(parents=True, exist_ok=True)
    (applied_dir / "index.jsonl").write_text(
        json.dumps(
            {
                "agent": "career_architect",
                "patch_hash": patch_hash,
                "patch_summary": summary,
                "normalized_summary": main.normalize_review_summary(summary),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    output_paths, skipped_count = main.collect_skill_review_proposals(review_date=target_date)

    assert skipped_count == 1
    assert review_root.joinpath("2026-07-09", "career_architect.md").exists() is False
    assert review_root.joinpath("2026-07-09", "skill_mapper.md").exists()
    assert len(output_paths) == 1


def test_loop_skills_skips_applied_proposal_with_legacy_index_source_proposal(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    app_root = repo_root / "app"
    codex_dir = repo_root / ".codex"
    review_root = app_root / "reviews" / "skills"
    applied_dir = app_root / "reviews" / "skills_applied"
    agents_dir = codex_dir / "agents"
    target_date = date(2026, 7, 9)

    agent_dir = agents_dir / "career_architect"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "SKILLS.md").write_text("# sample\n", encoding="utf-8")

    proposal_dir = review_root / "2026-07-09"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_text = main.build_skill_review(
        agent="career_architect",
        skill_text="# sample\n",
        rule={},
        source_summary={"events_count": 0, "source_sync_count": 0, "latest_resume_projects": [], "resume_mentions": {}, "changelog_dates": []},
        review_date=target_date,
    )
    (proposal_dir / "career_architect.md").write_text(proposal_text, encoding="utf-8")

    applied_dir.mkdir(parents=True, exist_ok=True)
    (applied_dir / "index.jsonl").write_text(
        json.dumps(
            {
                "agent": "career_architect",
                "applied_at": "2026-07-09",
                "source_proposal": "reviews/skills/2026-07-09/career_architect.md",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "REPO_ROOT", repo_root)
    monkeypatch.setattr(main, "CODEX_DIR", codex_dir)
    monkeypatch.setattr(main, "GENERATED_DIR", app_root / "generated")
    monkeypatch.setattr(main, "CHANGELOG_PATH", app_root / "CHANGELOG.md")
    monkeypatch.setattr(main, "LOOP_SKILLS_RULES_DIR", repo_root / ".codex" / "loop-skills" / "rules")
    monkeypatch.setattr(main, "SKILL_REVIEWS_DIR", review_root)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_DIR", applied_dir)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_INDEX", applied_dir / "index.jsonl")

    output_paths, skipped_count = main.collect_skill_review_proposals(review_date=target_date)

    assert skipped_count == 1
    assert output_paths == []
    assert review_root.joinpath("2026-07-09", "career_architect.md").exists()


def test_loop_skills_skips_applied_proposal_with_legacy_applied_copy(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    app_root = repo_root / "app"
    codex_dir = repo_root / ".codex"
    review_root = app_root / "reviews" / "skills"
    applied_dir = app_root / "reviews" / "skills_applied"
    agents_dir = codex_dir / "agents"
    target_date = date(2026, 7, 9)

    agent_dir = agents_dir / "career_architect"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "SKILLS.md").write_text("# sample\n", encoding="utf-8")

    proposal_text = main.build_skill_review(
        agent="career_architect",
        skill_text="# sample\n",
        rule={},
        source_summary={"events_count": 0, "source_sync_count": 0, "latest_resume_projects": [], "resume_mentions": {}, "changelog_dates": []},
        review_date=target_date,
    )
    applied_copy_dir = applied_dir / "2026-07-09"
    applied_copy_dir.mkdir(parents=True, exist_ok=True)
    (applied_copy_dir / "career_architect.md").write_text(proposal_text, encoding="utf-8")
    (applied_dir / "index.jsonl").write_text(
        json.dumps(
            {
                "agent": "career_architect",
                "applied_at": "2026-07-09",
                "source_proposal": "reviews/skills/2026-07-09/career_architect.md",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "REPO_ROOT", repo_root)
    monkeypatch.setattr(main, "CODEX_DIR", codex_dir)
    monkeypatch.setattr(main, "GENERATED_DIR", app_root / "generated")
    monkeypatch.setattr(main, "CHANGELOG_PATH", app_root / "CHANGELOG.md")
    monkeypatch.setattr(main, "LOOP_SKILLS_RULES_DIR", repo_root / ".codex" / "loop-skills" / "rules")
    monkeypatch.setattr(main, "SKILL_REVIEWS_DIR", review_root)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_DIR", applied_dir)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_INDEX", applied_dir / "index.jsonl")

    output_paths, skipped_count = main.collect_skill_review_proposals(review_date=target_date)

    assert skipped_count == 1
    assert output_paths == []
    assert review_root.joinpath("2026-07-09", "career_architect.md").exists() is False


def test_loop_skills_skips_applied_proposal_by_similar_summary(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    app_root = repo_root / "app"
    codex_dir = repo_root / ".codex"
    review_root = app_root / "reviews" / "skills"
    applied_dir = app_root / "reviews" / "skills_applied"
    agents_dir = codex_dir / "agents"
    target_date = date(2026, 7, 9)

    agent_dir = agents_dir / "career_architect"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "SKILLS.md").write_text("# sample\n", encoding="utf-8")

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "REPO_ROOT", repo_root)
    monkeypatch.setattr(main, "CODEX_DIR", codex_dir)
    monkeypatch.setattr(main, "GENERATED_DIR", app_root / "generated")
    monkeypatch.setattr(main, "CHANGELOG_PATH", app_root / "CHANGELOG.md")
    monkeypatch.setattr(main, "LOOP_SKILLS_RULES_DIR", repo_root / ".codex" / "loop-skills" / "rules")
    monkeypatch.setattr(main, "SKILL_REVIEWS_DIR", review_root)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_DIR", applied_dir)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_INDEX", applied_dir / "index.jsonl")

    applied_dir.mkdir(parents=True, exist_ok=True)
    proposal = main.build_skill_review(
        agent="career_architect",
        skill_text="# sample\n",
        rule={},
        source_summary={"events_count": 0, "source_sync_count": 0, "latest_resume_projects": [], "resume_mentions": {}, "changelog_dates": []},
        review_date=target_date,
    )
    patch_block = main.extract_patch_block(proposal)
    summary = main.normalize_summary_lines(patch_block)
    similar_summary = summary.replace("CHANGELOG.md", "CHANGELOG.md ").replace(" / ", "  /  ")
    (applied_dir / "index.jsonl").write_text(
        json.dumps(
            {
                "agent": "career_architect",
                "patch_hash": "different",
                "normalized_summary": main.normalize_review_summary(similar_summary),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    output_paths, skipped_count = main.collect_skill_review_proposals(review_date=target_date)

    assert skipped_count == 1
    assert output_paths == []
    assert review_root.joinpath("2026-07-09", "career_architect.md").exists() is False


def test_build_skill_review_updates_patch_to_remaining_issues() -> None:
    source_summary = {
        "events_count": 0,
        "source_sync_count": 4,
        "latest_resume_projects": ["貿易書類デジタル化パッケージエンハンス開発"],
        "resume_mentions": {},
        "changelog_dates": [],
    }

    day1 = main.build_skill_review(
        agent="career_architect",
        skill_text="# sample\n",
        rule={},
        source_summary=source_summary,
        review_date=date(2026, 7, 9),
    )
    day2 = main.build_skill_review(
        agent="career_architect",
        skill_text="""
`generated/resume.md` を構成設計の入力に追加する
`CHANGELOG.md` を優先度判断の参照先に追加する
""",
        rule={},
        source_summary=source_summary,
        review_date=date(2026, 7, 9),
    )

    assert "生成済み resume を構成設計の入力として明示していない" in day1
    assert "CHANGELOG を最新の構成判断材料として扱っていない" in day1
    assert "最新 resume の先頭案件 貿易書類デジタル化パッケージエンハンス開発 を前提にした判断基準が明示されていない" in day2
    assert "貿易書類デジタル化パッケージエンハンス開発 を構成判断の基準として扱う" in day2
    assert "直近案件で再現可能な強みを優先する" in day2
    assert "古い案件との差別化ルールを追加する" in day2
    assert "`generated/resume.md` を構成設計の入力に追加する" not in day2
    assert "`CHANGELOG.md` を優先度判断の参照先に追加する" not in day2


def test_backfill_skill_review_index_updates_legacy_records(monkeypatch, tmp_path: Path, capsys) -> None:
    repo_root = tmp_path / "repo"
    app_root = repo_root / "app"
    applied_dir = app_root / "reviews" / "skills_applied"
    review_dir = app_root / "reviews" / "skills" / "2026-07-09"
    proposal_text = """# Skill Improvement Proposal: career_architect

## Target
.codex/agents/career_architect/SKILLS.md

## Observed Issues
- sample issue

## Suggested Skill
- sample skill

## Reason
- sample reason

## Patch Proposal
```md
## 2026-07-09 Added

最新 resume の先頭案件を構成判断の基準として扱う
```
"""

    review_dir.mkdir(parents=True, exist_ok=True)
    (review_dir / "career_architect.md").write_text(proposal_text, encoding="utf-8")
    applied_dir.mkdir(parents=True, exist_ok=True)
    (applied_dir / "index.jsonl").write_text(
        json.dumps(
            {
                "agent": "career_architect",
                "applied_at": "2026-07-09",
                "source_proposal": "reviews/skills/2026-07-09/career_architect.md",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "REPO_ROOT", repo_root)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_DIR", applied_dir)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_INDEX", applied_dir / "index.jsonl")

    main.backfill_skill_review_index()
    captured = capsys.readouterr().out
    records = main.read_applied_skill_reviews()

    assert "Backfilled 1 applied skill review records" in captured
    assert records[0]["patch_hash"]
    assert records[0]["normalized_summary"]


def test_day2_career_architect_proposal_is_not_regenerated_after_apply(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    app_root = repo_root / "app"
    codex_dir = repo_root / ".codex"
    review_root = app_root / "reviews" / "skills"
    applied_dir = app_root / "reviews" / "skills_applied"
    target_date = date(2026, 7, 9)

    target_path = codex_dir / "agents" / "career_architect" / "SKILLS.md"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("# career_architect サブエージェント\n", encoding="utf-8")

    proposal_dir = review_root / "2026-07-09"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposal_path = proposal_dir / "career_architect.md"
    proposal_path.write_text(
        main.build_skill_review(
            agent="career_architect",
            skill_text="# career_architect サブエージェント\n",
            rule={},
            source_summary={
                "events_count": 0,
                "source_sync_count": 4,
                "latest_resume_projects": ["貿易書類デジタル化パッケージエンハンス開発"],
                "resume_mentions": {},
                "changelog_dates": [],
            },
            review_date=target_date,
        ),
        encoding="utf-8",
    )

    changelog_path = app_root / "CHANGELOG.md"
    changelog_path.write_text("# CHANGELOG\n\n", encoding="utf-8")

    monkeypatch.setattr(main, "ROOT", app_root)
    monkeypatch.setattr(main, "REPO_ROOT", repo_root)
    monkeypatch.setattr(main, "CODEX_DIR", codex_dir)
    monkeypatch.setattr(main, "CHANGELOG_PATH", changelog_path)
    monkeypatch.setattr(main, "SKILL_REVIEWS_DIR", review_root)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_DIR", applied_dir)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_INDEX", applied_dir / "index.jsonl")

    apply_result = main.apply_skill_review_file(proposal_path)
    output_paths, skipped_count = main.collect_skill_review_proposals(review_date=target_date)

    assert apply_result["status"] == "applied"
    assert skipped_count == 1
    assert output_paths == []


def test_list_skill_reviews_excludes_applied_proposals(monkeypatch, tmp_path: Path, capsys) -> None:
    review_root = tmp_path / "reviews" / "skills"
    applied_dir = tmp_path / "reviews" / "skills_applied"
    review_date = review_root / "2026-07-09"
    review_date.mkdir(parents=True, exist_ok=True)
    proposal_path = review_date / "career_architect.md"
    proposal_text = """# Skill Improvement Proposal: career_architect

## Target
.codex/agents/career_architect/SKILLS.md

## Observed Issues
- sample issue

## Suggested Skill
- sample skill

## Reason
- sample reason

## Patch Proposal
```md
## 2026-07-09 Added

`generated/resume.md` を構成設計の入力に追加する
`CHANGELOG.md` を優先度判断の参照先に追加する
```
"""
    proposal_path.write_text(proposal_text, encoding="utf-8")

    patch_block = main.extract_patch_block(proposal_text)
    patch_summary = main.normalize_summary_lines(patch_block)
    patch_hash = main.build_patch_hash(patch_block)
    applied_dir.mkdir(parents=True, exist_ok=True)
    (applied_dir / "index.jsonl").write_text(
        json.dumps(
            {
                "agent": "career_architect",
                "patch_hash": patch_hash,
                "normalized_summary": main.normalize_review_summary(patch_summary),
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "SKILL_REVIEWS_DIR", review_root)
    monkeypatch.setattr(main, "SKILL_REVIEWS_APPLIED_INDEX", applied_dir / "index.jsonl")

    main.list_skill_reviews()
    captured = capsys.readouterr().out

    assert "No skill review proposals found." in captured
