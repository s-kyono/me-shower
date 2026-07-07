from pathlib import Path

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
