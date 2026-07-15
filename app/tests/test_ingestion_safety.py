from dataclasses import asdict
import ast
from io import BytesIO
from pathlib import Path
import traceback
from urllib.error import HTTPError, URLError

import pytest
from typer.testing import CliRunner

import ingestion_safety
import main


RULE_PATH = Path(__file__).resolve().parents[2] / ".codex" / "source-intelligence" / "rules" / "real_data_ingestion_safety.yaml"
runner = CliRunner()


def inspect(value: object, **kwargs: object) -> ingestion_safety.SafetyGateResult:
    return ingestion_safety.inspect_before_persistence(value, rule_path=RULE_PATH, **kwargs)


def test_safe_input_passes_unchanged_without_raw_audit_content() -> None:
    source = "Implemented deterministic normalization and added focused tests."
    result = inspect(source)
    assert result.outcome == "pass"
    assert result.sanitized_content is not None
    assert result.sanitized_content.unwrap() == source
    assert result.findings == ()
    assert asdict(result.audit_report)["raw_value_included"] is False


def test_supported_categories_are_sanitized_deterministically_and_idempotently() -> None:
    source = (
        "Contact test.user@example.invalid or +1 202 555 0199 from 192.0.2.44. "
        "See https://service.internal/item?token_ref=safe and /home/test_only_user/work/note.md."
    )
    first = inspect(source)
    second = inspect(source)
    assert first.outcome == "pass_with_sanitization"
    assert first.sanitized_content is not None and second.sanitized_content is not None
    first_text = first.sanitized_content.unwrap()
    assert first_text == second.sanitized_content.unwrap()
    assert "test.user" not in first_text
    assert "192.0.2.44" not in first_text
    assert "/home/test_only_user" not in first_text
    assert "[REDACTED_EMAIL]" in first_text
    assert "[REDACTED_PHONE]" in first_text
    assert "[REDACTED_IP_ADDRESS]" in first_text
    assert "[REDACTED_PRIVATE_URL]" in first_text
    assert "[REDACTED_LOCAL_PATH]" in first_text
    rerun = inspect(first_text)
    assert rerun.sanitized_content is not None
    assert rerun.sanitized_content.unwrap() == first_text


@pytest.mark.parametrize("source", [
    "Authorization: Bearer TEST_ONLY_VALUE_123456789",
    "api_key=TEST_ONLY_VALUE_123456789",
    "UNKNOWN_HIGH_RISK_TEST_ONLY",
])
def test_high_risk_input_is_blocked_without_value_in_findings_or_exception(source: str) -> None:
    result = inspect(source)
    assert result.outcome == "blocked"
    assert result.sanitized_content is None
    assert source not in repr(result.findings)
    with pytest.raises(ingestion_safety.IngestionSafetyBlockedError) as error:
        ingestion_safety.require_persistable(result)
    assert source not in str(error.value)


def test_raw_persistence_request_and_rule_or_detector_failure_fail_closed(tmp_path: Path) -> None:
    assert inspect("safe", persistence_intent="raw").outcome == "blocked"
    with pytest.raises(ingestion_safety.IngestionSafetyError, match="rules"):
        ingestion_safety.inspect_before_persistence("safe", rule_path=tmp_path / "missing.yaml")

    def broken_detector(*args: object) -> object:
        raise RuntimeError("TEST_ONLY_SECRET_MUST_NOT_ESCAPE")

    with pytest.raises(ingestion_safety.IngestionSafetyError) as error:
        inspect("TEST_ONLY_SECRET_MUST_NOT_ESCAPE", detector=broken_detector)
    assert "TEST_ONLY_SECRET_MUST_NOT_ESCAPE" not in str(error.value)


def test_blocked_source_creates_no_file_and_preserves_existing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_sync = tmp_path / "source_sync"
    target = source_sync / "2026-07-15.md"
    source_sync.mkdir()
    target.write_text("existing\n", encoding="utf-8")
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync)
    raw = main.RawSource(
        id="safe-id", source_type="file", origin="safe-note.md", title="safe-note",
        content="password=TEST_ONLY_VALUE_123456789", captured_at="2026-07-15", metadata={},
    )
    with pytest.raises(ingestion_safety.IngestionSafetyBlockedError):
        main.normalize_raw_sources([raw], action_label="test")
    assert target.read_text(encoding="utf-8") == "existing\n"
    assert list(source_sync.iterdir()) == [target]


def test_sanitized_source_only_crosses_atomic_persistence_boundary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_sync = tmp_path / "source_sync"
    monkeypatch.setattr(main, "SOURCE_SYNC_DIR", source_sync)
    raw_value = "test.user@example.invalid"
    raw = main.RawSource(
        id="safe-id", source_type="file", origin="safe-note.md", title="safe-note",
        content=f"Implemented tests and contacted {raw_value}.", captured_at="2026-07-15", metadata={},
    )
    paths = main.normalize_raw_sources([raw], action_label="test")
    persisted = paths[0].read_text(encoding="utf-8")
    assert raw_value not in persisted
    assert "[REDACTED_EMAIL]" not in persisted  # placeholder is not promoted as fact/evidence
    assert not list(source_sync.glob("*.tmp"))


def test_safe_cli_never_prints_raw_or_sanitized_content(tmp_path: Path) -> None:
    raw_value = "cli.user@example.invalid"
    fixture = tmp_path / "sanitized-fixture.md"
    fixture.write_text(f"Implemented focused tests. Contact: {raw_value}\n", encoding="utf-8")
    result = runner.invoke(main.app, ["inspect-ingestion-safety", "--input", str(fixture)])
    assert result.exit_code == 0
    assert "outcome: pass_with_sanitization" in result.stdout
    assert "raw_values_logged: false" in result.stdout
    assert raw_value not in result.stdout
    assert "Implemented focused tests" not in result.stdout


def test_atomic_write_failure_leaves_existing_file_and_no_partial(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "safe-output.md"
    target.write_text("existing\n", encoding="utf-8")

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("synthetic write failure")

    monkeypatch.setattr(ingestion_safety.os, "replace", fail_replace)
    with pytest.raises(ingestion_safety.IngestionSafetyError, match="Atomic persistence failed"):
        ingestion_safety.persist_text_safely(target, "sanitized replacement\n", rule_path=RULE_PATH)
    assert target.read_text(encoding="utf-8") == "existing\n"
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("source", [
    "Bearer TEST_ONLY_CREDENTIAL_123456789",
    "Authorization: Basic TEST_ONLY_CREDENTIAL_123456789",
    "password: TEST_ONLY_CREDENTIAL_123456789",
    "client_secret=TEST_ONLY_CREDENTIAL_123456789",
    "xoxb-TEST-ONLY-CREDENTIAL-123456789",
])
def test_credential_matrix_is_always_blocked(source: str) -> None:
    result = inspect(source)
    assert result.outcome == "blocked"
    assert result.sanitized_content is None
    assert result.audit_report.blocked_categories == ["credential"]


def test_plain_text_credential_cannot_cross_public_writer(tmp_path: Path) -> None:
    target = tmp_path / "output.md"
    with pytest.raises(ingestion_safety.IngestionSafetyBlockedError):
        ingestion_safety.persist_text_safely(
            target, "Bearer TEST_ONLY_CREDENTIAL_123456789", rule_path=RULE_PATH,
        )
    assert not target.exists()


def test_safety_result_and_wrappers_cannot_be_forged() -> None:
    audit = ingestion_safety.SafetyAuditReport("gate", "rules", {}, [], [])
    with pytest.raises(TypeError, match="only be created"):
        ingestion_safety.SanitizedContent("raw")
    with pytest.raises(TypeError, match="only be created"):
        ingestion_safety.PersistableText("raw")
    with pytest.raises(TypeError, match="only be created"):
        ingestion_safety.SafetyGateResult("pass", None, (), audit)


def test_mutated_or_token_forged_wrapper_is_rechecked_by_public_writer(tmp_path: Path) -> None:
    marker = "Bearer TEST_ONLY_MUTATED_CREDENTIAL_123456789"
    mutated = ingestion_safety.inspect_text_for_persistence("safe", rule_path=RULE_PATH)
    mutated._value = marker
    with pytest.raises(ingestion_safety.IngestionSafetyBlockedError):
        ingestion_safety.persist_text_safely(tmp_path / "mutated.txt", mutated, rule_path=RULE_PATH)

    forged = ingestion_safety.PersistableText(marker, ingestion_safety._CONSTRUCTION_TOKEN)
    with pytest.raises(ingestion_safety.IngestionSafetyBlockedError):
        ingestion_safety.persist_text_safely(tmp_path / "forged.txt", forged, rule_path=RULE_PATH)

    assert not list(tmp_path.iterdir())


def test_detector_and_recheck_exception_tracebacks_do_not_include_cause_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    marker = "TEST_ONLY_EXCEPTION_SECRET_123"

    def broken_detector(*args: object) -> object:
        raise RuntimeError(marker)

    with pytest.raises(ingestion_safety.IngestionSafetyError) as detector_error:
        inspect("safe", detector=broken_detector)
    assert marker not in "".join(traceback.format_exception(detector_error.value))
    assert detector_error.value.__cause__ is None
    assert detector_error.value.__context__ is None

    original_walk = ingestion_safety._walk

    def trigger_recheck(value: object, path: str, rules: object) -> object:
        monkeypatch.setattr(ingestion_safety, "_walk", lambda *args: (_ for _ in ()).throw(RuntimeError(marker)))
        return value, [], False

    try:
        with pytest.raises(ingestion_safety.IngestionSafetyError) as recheck_error:
            inspect("safe", detector=trigger_recheck)
        assert marker not in "".join(traceback.format_exception(recheck_error.value))
        assert recheck_error.value.__cause__ is None
        assert recheck_error.value.__context__ is None
    finally:
        monkeypatch.setattr(ingestion_safety, "_walk", original_walk)


def test_rule_contract_drift_and_unsupported_findings_fail_closed(tmp_path: Path) -> None:
    document = ingestion_safety.load_safety_contract(RULE_PATH)
    document["protected_categories"].pop("credential")
    invalid_rules = tmp_path / "invalid-rules.yaml"
    invalid_rules.write_text(ingestion_safety.yaml.safe_dump(document), encoding="utf-8")
    with pytest.raises(ingestion_safety.IngestionSafetyError, match="category contract"):
        ingestion_safety.inspect_before_persistence("safe", rule_path=invalid_rules)

    def unsupported(value: object, path: str, rules: object) -> object:
        return value, [ingestion_safety.SafetyFinding("unsupported", "sanitize", path, "test", "high")], False

    with pytest.raises(ingestion_safety.IngestionSafetyError, match="unsupported"):
        inspect("safe", detector=unsupported)


def test_private_atomic_writer_is_only_called_by_public_safety_boundary() -> None:
    module_path = Path(ingestion_safety.__file__)
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    callers: list[str] = []

    class CallVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.function_stack: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name) and node.func.id == "_atomic_write_verified_text":
                callers.append(self.function_stack[-1] if self.function_stack else "<module>")
            self.generic_visit(node)

    CallVisitor().visit(tree)
    assert callers == ["persist_text_safely"]
    assert "_atomic_write_verified_text" not in Path(main.__file__).read_text(encoding="utf-8")


@pytest.mark.parametrize("adapter", ["slack_url", "slack_http", "graph_url", "graph_http"])
def test_adapter_transport_errors_discard_raw_exception_context(monkeypatch: pytest.MonkeyPatch, adapter: str) -> None:
    marker = "TEST_ONLY_ADAPTER_EXCEPTION_SECRET_123456789"

    if adapter.endswith("http"):
        code = 429 if adapter.startswith("slack") else 401

        def fail_request(*args: object, **kwargs: object) -> object:
            raise HTTPError("https://example.invalid", code, marker, {}, BytesIO(marker.encode()))
    else:
        def fail_request(*args: object, **kwargs: object) -> object:
            raise URLError(marker)

    monkeypatch.setattr(main, "urlopen", fail_request)
    caller = main.call_slack_api if adapter.startswith("slack") else main.call_graph_api
    arguments = ("conversations.history", {}) if adapter.startswith("slack") else ("/v1.0/test", {})

    with pytest.raises(main.SourceAdapterError) as error:
        caller(*arguments, token="TEST_ONLY_TOKEN")

    assert marker not in str(error.value)
    assert marker not in "".join(traceback.format_exception(error.value))
    assert error.value.__cause__ is None
    assert error.value.__context__ is None


def test_private_intranet_url_is_sanitized() -> None:
    result = inspect("See https://intranet.example.invalid/repository")
    assert result.outcome == "pass_with_sanitization"
    assert result.sanitized_content is not None
    assert result.sanitized_content.unwrap() == "See [REDACTED_PRIVATE_URL]"


def test_private_url_without_safe_target_leaves_no_reference_or_source_id() -> None:
    raw = main.RawSource(
        id="https://internal.example.invalid/private/source/123",
        source_type="slack",
        origin="slack",
        title="Synthetic source",
        content="Implemented deterministic safety tests for the ingestion boundary.",
        captured_at="2026-07-15T00:00:00+00:00",
        metadata={"source_reference": "https://internal.example.invalid/private/repository"},
    )

    event = main.build_canonical_event_from_raw_source(raw)
    serialized = main.format_canonical_event(event)

    assert event["source_id"] is None
    assert all(item["kind"] != "source_reference" for item in event["evidence"])
    assert "internal.example.invalid" not in serialized
    assert "[REDACTED_PRIVATE_URL]" not in serialized
    assert "\n  source_id:" not in serialized
    assert "source_id:present" not in serialized
    assert event["_safety_gate_result"].audit_report.finding_counts["private_url"] == 2


def test_existing_safe_local_source_reference_is_preserved(tmp_path: Path) -> None:
    source = tmp_path / "TEST_ONLY_SAFE_SOURCE.md"
    source.write_text("Synthetic source", encoding="utf-8")
    raw = main.RawSource(
        id="TEST_ONLY_SAFE_SOURCE_ID",
        source_type="file",
        origin=str(source),
        title=source.name,
        content="Implemented deterministic safety tests for the ingestion boundary.",
        captured_at="2026-07-15T00:00:00+00:00",
        metadata={"path": str(source)},
    )

    event = main.build_canonical_event_from_raw_source(raw)

    assert event["source_id"] == "TEST_ONLY_SAFE_SOURCE_ID"
    assert {"kind": "source_reference", "detail": source.name} in event["evidence"]


def test_all_source_inspection_cli_output_omits_raw_metadata_marker(tmp_path: Path) -> None:
    marker = "TEST_ONLY_PRIVATE_CLIENT_ALPHA"
    fixture = tmp_path / f"{marker}.md"
    fixture.write_text("Implemented focused tests.", encoding="utf-8")
    result = runner.invoke(main.app, ["inspect-daily-report", "--file", str(fixture)])
    assert result.exit_code == 0
    assert marker not in result.stdout
    assert marker not in (result.stderr or "")
    assert "source_index: 1" in result.stdout


def test_source_adapter_failure_cli_uses_safe_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    marker = "TEST_ONLY_PRIVATE_OWNER/TEST_ONLY_PRIVATE_REPO"

    class FailingGitHubAdapter:
        name = "github"

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def discover(self) -> list[main.RawSource]:
            raise main.SourceAccessError("GitHub repository is not accessible: " + marker)

    monkeypatch.setattr(main, "GitHubSourceAdapter", FailingGitHubAdapter)
    result = runner.invoke(main.app, ["inspect-github-source", "--repo", marker])
    assert result.exit_code == 1
    assert "error_code: adapter_access_failed" in result.stderr
    assert "adapter: github" in result.stderr
    assert marker not in result.stdout
    assert marker not in result.stderr
