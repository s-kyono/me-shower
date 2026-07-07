from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import re
import shutil
from typing import Any

import typer
import yaml
from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt


app = typer.Typer(help="Generate career resume Markdown and PDF outputs.")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "templates"
THEMES_DIR = TEMPLATE_DIR / "themes"
GENERATED_DIR = ROOT / "generated"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
RELEASES_DIR = GENERATED_DIR / "releases"

PHASE_KEYS = [
    "requirement",
    "basic_design",
    "detail_design",
    "implementation",
    "review",
    "test",
    "operation",
]


def read_yaml(path: Path) -> Any:
    if not path.exists():
        raise typer.BadParameter(f"Missing required file: {path}")
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def read_yaml_files(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.yaml")):
        value = read_yaml(path)
        if isinstance(value, dict):
            value["_source"] = str(path.relative_to(ROOT))
            items.append(value)
    return items


def select_enabled(values: Any) -> list[str]:
    if not values:
        return []
    if isinstance(values, list):
        result: list[str] = []
        for item in values:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict) and item.get("enabled", True):
                name = item.get("name")
                if name:
                    result.append(str(name))
        return result
    if isinstance(values, dict):
        return [str(key) for key, enabled in values.items() if enabled]
    return []


def normalize_project(project: dict[str, Any]) -> dict[str, Any]:
    technologies = project.setdefault("technologies", {})
    for key in ["languages", "frameworks", "db", "tools"]:
        technologies.setdefault(key, [])

    phases = project.setdefault("phases", {})
    for key in PHASE_KEYS:
        phases.setdefault(key, False)

    project.setdefault("responsibilities", [])
    project.setdefault("achievements", [])
    project.setdefault("ai_usage", [])
    project.setdefault("versions", [])
    project.setdefault("team_size", "")
    project.setdefault("role", "")
    project.setdefault("summary", "")
    project.setdefault("period", {"from": "", "to": ""})
    return project


def load_resume_data() -> dict[str, Any]:
    profile = read_yaml(DATA_DIR / "profile.yaml")
    projects = [normalize_project(project) for project in read_yaml_files(DATA_DIR / "projects")]
    skills = read_yaml_files(DATA_DIR / "skills")
    events = read_yaml_files(DATA_DIR / "events")

    projects.sort(key=lambda item: item.get("sort_order", 9999))

    return {
        "profile": profile,
        "projects": projects,
        "skills": skills,
        "events": events,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
    }


def render_markdown() -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["select_enabled"] = select_enabled
    template = env.get_template("resume.md.j2")
    return template.render(**load_resume_data())


def safe_path_part(value: str) -> str:
    sanitized = re.sub(r'[\\/:*?"<>|\s]+', "_", value.strip())
    sanitized = re.sub(r"_+", "_", sanitized).strip("._")
    return sanitized or "職務経歴書発行"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve_theme_css(theme: str) -> Path:
    theme_path = THEMES_DIR / f"{safe_path_part(theme)}.css"
    if not theme_path.exists():
        available = ", ".join(path.stem for path in sorted(THEMES_DIR.glob("*.css"))) or "none"
        typer.echo(f"Theme not found: {theme}. Available themes: {available}")
        raise typer.Exit(1)
    return theme_path


def markdown_to_pdf(markdown_path: Path, output_path: Path, theme: str = "forest") -> None:
    try:
        from weasyprint import CSS, HTML
    except OSError as exc:
        typer.echo(
            "WeasyPrint system libraries are missing. "
            "Install the required native dependencies such as glib, pango, "
            "harfbuzz, and fontconfig, then rerun generate-pdf."
        )
        typer.echo(str(exc))
        raise typer.Exit(1)

    css_path = TEMPLATE_DIR / "resume.css"
    theme_css_path = resolve_theme_css(theme)
    markdown = markdown_path.read_text(encoding="utf-8")
    md = MarkdownIt("commonmark", {"html": True}).enable("table")
    body = md.render(markdown)
    html = f"<!doctype html><html><head><meta charset=\"utf-8\"></head><body>{body}</body></html>"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=str(ROOT)).write_pdf(
        str(output_path),
        stylesheets=[CSS(filename=str(css_path)), CSS(filename=str(theme_css_path))],
    )


def generate_markdown_file() -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = GENERATED_DIR / "resume.md"
    output_path.write_text(render_markdown(), encoding="utf-8")
    return output_path


def generate_pdf_file(theme: str = "forest") -> Path:
    markdown_path = GENERATED_DIR / "resume.md"
    if not markdown_path.exists():
        typer.echo("generated/resume.md not found. Running generate-md first.")
        generate_markdown_file()

    output_path = GENERATED_DIR / "職務経歴書.pdf"
    markdown_to_pdf(markdown_path, output_path, theme=theme)
    return output_path


def review_resume(markdown: str, data: dict[str, Any]) -> list[str]:
    results: list[str] = []
    required_sections = [
        ("職務要約", "## 職務要約"),
        ("技術スタック", "## 技術スタック"),
        ("AI活用経験", "## AI活用経験"),
        ("プロジェクト経歴", "## プロジェクト経歴"),
    ]

    missing_sections = [label for label, marker in required_sections if marker not in markdown]
    if missing_sections:
        results.append(f"不足セクションがある: {', '.join(missing_sections)}")
    else:
        results.append("全体として、提出可能な職務経歴書として最低限の構成は揃っている")

    if "#### 担当業務" in markdown and "#### 成果・改善" in markdown:
        results.append("「担当業務」と「成果・改善」が分離されている点は良い")
    else:
        results.append("「担当業務」と「成果・改善」の分離を確認する")

    if '<table class="phase-table">' in markdown:
        results.append("担当工程が表形式で可視化されており、経験範囲が直感的に分かる")
    else:
        results.append("担当工程テーブルが見つからないため、経験範囲の可視化を確認する")

    projects = data["projects"]
    missing_achievements = [project.get("name", "unknown") for project in projects if not project.get("achievements")]
    if missing_achievements:
        results.append(f"成果・改善が未設定のプロジェクトがある: {', '.join(missing_achievements)}")
    else:
        results.append("今後は成果に数値・規模・影響範囲を追加すると説得力が上がる")

    if data["profile"].get("ai_usage"):
        results.append("AI活用経験は、単なる利用ツール一覧ではなく「どう開発プロセスを改善したか」まで書けると強い")
    else:
        results.append("AI活用経験が未設定のため、開発プロセス改善との関係を追記する")

    evidence_projects = [project for project in projects if project.get("evidence")]
    if evidence_projects:
        results.append("一部プロジェクトに evidence が設定されている")
    else:
        results.append("evidence が未設定のため、GitHub PR / Issue / commit との紐付けが今後の改善点")

    return results


def build_changelog_entry(
    title: str,
    note: str,
    release_dir: Path,
    review_results: list[str],
) -> str:
    release_date = date.today().strftime("%Y-%m-%d")
    pdf_path = release_dir / "職務経歴書.pdf"
    markdown_path = release_dir / "resume.md"
    return f"""## {release_date} {title}

### 発行物
- {display_path(pdf_path)}
- {display_path(markdown_path)}

### 発行理由
{note}

### 生成内容サマリー
- 職務要約
- 技術スタック
- AI活用経験
- プロジェクト経歴
- 担当工程チェック

### フィードバックエージェント結果
{chr(10).join(f"- {item}" for item in review_results)}

### 次回改善ポイント
- 各プロジェクトの成果に定量情報を追加する
- GitHub PR / Issue / commit を evidence として紐付ける
- AI活用経験をプロジェクト別に具体化する
- 職務要約を応募先ごとに最適化できるようにする
"""


def append_changelog(entry: str) -> None:
    if CHANGELOG_PATH.exists():
        current = CHANGELOG_PATH.read_text(encoding="utf-8")
        if current.startswith("# CHANGELOG"):
            content = current.rstrip() + "\n\n" + entry.rstrip() + "\n"
        else:
            content = "# CHANGELOG\n\n" + current.rstrip() + "\n\n" + entry.rstrip() + "\n"
    else:
        content = "# CHANGELOG\n\n" + entry.rstrip() + "\n"
    CHANGELOG_PATH.write_text(content, encoding="utf-8")


def issue_resume(title: str, note: str, theme: str = "forest") -> Path:
    markdown_path = generate_markdown_file()
    pdf_path = generate_pdf_file(theme=theme)

    base_name = f"{date.today().strftime('%Y-%m-%d')}_{safe_path_part(title)}"
    release_dir = RELEASES_DIR / base_name
    if release_dir.exists():
        release_dir = RELEASES_DIR / f"{base_name}_{datetime.now().strftime('%H%M%S')}"
    release_dir.mkdir(parents=True, exist_ok=False)

    release_markdown = release_dir / "resume.md"
    release_pdf = release_dir / "職務経歴書.pdf"
    shutil.copy2(markdown_path, release_markdown)
    shutil.copy2(pdf_path, release_pdf)

    data = load_resume_data()
    review_results = review_resume(markdown_path.read_text(encoding="utf-8"), data)
    append_changelog(build_changelog_entry(title, note, release_dir, review_results))
    return release_dir


@app.command("add-log")
def add_log(message: str = typer.Option("", "--message", "-m", help="Log message to append.")) -> None:
    """Append a simple event log entry."""
    events_dir = DATA_DIR / "events"
    events_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    path = events_dir / f"{timestamp}.yaml"
    payload = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "type": "manual_log",
        "message": message or "手動ログ",
    }
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(payload, file, allow_unicode=True, sort_keys=False)
    typer.echo(f"Added log: {path.relative_to(ROOT)}")


@app.command("analyze")
def analyze() -> None:
    """Print a compact data summary."""
    data = load_resume_data()
    profile = data["profile"]
    projects = data["projects"]
    skills = data["skills"]
    typer.echo(f"profile: {profile.get('name', 'unknown')}")
    typer.echo(f"projects: {len(projects)}")
    typer.echo(f"skill files: {len(skills)}")
    typer.echo(f"events: {len(data['events'])}")
    missing_phases = [project.get("name", "unknown") for project in projects if not project.get("phases")]
    if missing_phases:
        typer.echo("projects missing phases:")
        for name in missing_phases:
            typer.echo(f"- {name}")


@app.command("generate-md")
def generate_md() -> None:
    """Generate Markdown resume from YAML data and Jinja2 template."""
    output_path = generate_markdown_file()
    typer.echo(f"Generated Markdown: {output_path.relative_to(ROOT)}")


@app.command("generate-pdf")
def generate_pdf(theme: str = typer.Option("forest", "--theme", help="PDF theme name")) -> None:
    """Generate PDF resume from generated Markdown and CSS."""
    output_path = generate_pdf_file(theme=theme)
    typer.echo(f"Generated PDF: {output_path.relative_to(ROOT)}")


@app.command("issue")
def issue(
    title: str = typer.Option("職務経歴書発行", "--title", help="発行タイトル"),
    note: str = typer.Option("職務経歴書PDFを発行", "--note", help="発行理由やメモ"),
    theme: str = typer.Option("forest", "--theme", help="PDF theme name"),
) -> None:
    """Generate and archive an issued resume with CHANGELOG entry."""
    release_dir = issue_resume(title=title, note=note, theme=theme)
    typer.echo(f"Issued resume: {release_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    app()
