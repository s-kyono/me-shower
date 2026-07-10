from pathlib import Path
from datetime import date
import json

import main
from main import load_resume_data, render_markdown


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
    assert "confidence: high" in content
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


def test_resume_agent_hook_is_design_only() -> None:
    context = main.run_resume_agent_hook("generate-md")

    assert context["trigger"] == "generate-md"
    assert context["status"] == "design_only"
    assert context["contract"]["normalizer_scope"] == "raw source -> canonical event / evidence"
    assert "generate-md" in context["contract"]["activation_points"]
    assert "issue" in context["contract"]["activation_points"]


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
