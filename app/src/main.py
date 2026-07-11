from __future__ import annotations

import hashlib
import json
from difflib import SequenceMatcher
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
REPO_ROOT = ROOT.parent
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "templates"
THEMES_DIR = TEMPLATE_DIR / "themes"
GENERATED_DIR = ROOT / "generated"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
RELEASES_DIR = GENERATED_DIR / "releases"
CODEX_DIR = REPO_ROOT / ".codex"
LOOP_SKILLS_RULES_DIR = CODEX_DIR / "loop-skills" / "rules"
SOURCE_SYNC_DIR = DATA_DIR / "source_sync"
EVENTS_DIR = DATA_DIR / "events"
GUARD_REVIEWS_DIR = ROOT / "reviews" / "guard"
SKILL_REVIEWS_DIR = ROOT / "reviews" / "skills"
SKILL_REVIEWS_APPLIED_DIR = ROOT / "reviews" / "skills_applied"
SKILL_REVIEWS_APPLIED_INDEX = SKILL_REVIEWS_APPLIED_DIR / "index.jsonl"

PHASE_KEYS = [
    "requirement",
    "basic_design",
    "detail_design",
    "implementation",
    "review",
    "test",
    "operation",
]

REDACTION_RULES = [
    ("SLACK_URL", re.compile(r"https?://[^\s]*slack(?:-redir)?\.com[^\s]*", flags=re.IGNORECASE), "[REDACTED_SLACK_URL]"),
    ("GITHUB_URL", re.compile(r"https?://(?:www\.)?github\.com[^\s]*", flags=re.IGNORECASE), "[REDACTED_GITHUB_URL]"),
    ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags=re.IGNORECASE), "[REDACTED_EMAIL]"),
    ("URL", re.compile(r"\bhttps?://[^\s]+", flags=re.IGNORECASE), "[REDACTED_URL]"),
    ("BEARER_TOKEN", re.compile(r"\bBearer\s+[A-Za-z0-9._\-+/=]+\b", flags=re.IGNORECASE), "[REDACTED_BEARER_TOKEN]"),
    ("BEARER_TOKEN", re.compile(r"\bBearer token\b", flags=re.IGNORECASE), "[REDACTED_BEARER_TOKEN]"),
    ("AWS_SECRET_ACCESS_KEY", re.compile(r"\bAWS_SECRET_ACCESS_KEY\s*=\s*[^\s]+", flags=re.IGNORECASE), "[REDACTED_AWS_SECRET_ACCESS_KEY]"),
    ("API_KEY_VALUE", re.compile(r"\bAPI_KEY\s*=\s*[^\s]+", flags=re.IGNORECASE), "[REDACTED_API_KEY_VALUE]"),
    ("API_KEY", re.compile(r"\b(?:API[-_ ]?Key|api[-_ ]?key)[ \t]*[:=]?[ \t]*[A-Za-z0-9._\-]{8,}\b"), "[REDACTED_API_KEY]"),
    ("API_KEY", re.compile(r"\bAPI Key\b", flags=re.IGNORECASE), "[REDACTED_API_KEY]"),
    ("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[REDACTED_IP_ADDRESS]"),
    ("IP_ADDRESS", re.compile(r"\bIP Address\b", flags=re.IGNORECASE), "[REDACTED_IP_ADDRESS]"),
    ("PHONE_NUMBER", re.compile(r"\b(?:0\d{1,4}-\d{1,4}-\d{4}|0\d{9,10})\b"), "[REDACTED_PHONE_NUMBER]"),
    ("ADDRESS", re.compile(r"(?m)^(?:〒\d{3}-\d{4}\s*)?(?:東京都|北海道|(?:京都|大阪)府|(?:青森|岩手|宮城|秋田|山形|福島|茨城|栃木|群馬|埼玉|千葉|神奈川|新潟|富山|石川|福井|山梨|長野|岐阜|静岡|愛知|三重|滋賀|兵庫|奈良|和歌山|鳥取|島根|岡山|広島|山口|徳島|香川|愛媛|高知|福岡|佐賀|長崎|熊本|大分|宮崎|鹿児島|沖縄)県)[^\n]*$"), "[REDACTED_ADDRESS]"),
    ("PERSON_NAME", re.compile(r"(?m)^(?!社員名$)(?!案件名$)[一-龠々]{2,4}(?:[ \u3000]+[一-龠々]{1,4}|[一-龠々]{2,4})$"), "[REDACTED_PERSON_NAME]"),
    ("PROJECT_NAME_VALUE", re.compile(r"(?m)(案件名\s*:\s*)([^\n]+)$"), r"\1[REDACTED_PROJECT_NAME_VALUE]"),
    ("TICKET_ID", re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b"), "[REDACTED_TICKET_ID]"),
    ("BRANCH_NAME", re.compile(r"(?m)^(?:feature|bugfix|hotfix|release|chore|fix|refactor|docs|test|ci|build|perf|feat)/[A-Za-z0-9._-]+$"), "[REDACTED_BRANCH_NAME]"),
    ("ENV_OR_DB_NAME", re.compile(r"(?mi)^(?=.*(?:prod|stg|stage|dev|qa|db))[a-z0-9]+(?:-[a-z0-9]+)+$"), "[REDACTED_ENV_OR_DB_NAME]"),
    ("ORG_NAME", re.compile(r"株式会社[^\s,，。]{0,20}"), "[REDACTED_ORG_NAME]"),
    ("SLACK_URL", re.compile(r"\bSlack URL\b", flags=re.IGNORECASE), "[REDACTED_SLACK_URL]"),
    ("GITHUB_URL", re.compile(r"\bGitHub URL\b", flags=re.IGNORECASE), "[REDACTED_GITHUB_URL]"),
    ("EMPLOYEE_NAME", re.compile(r"\b社員名\b"), "[REDACTED_EMPLOYEE_NAME]"),
    ("PROJECT_NAME", re.compile(r"\b案件名\b"), "[REDACTED_PROJECT_NAME]"),
]


def read_yaml(path: Path) -> Any:
    if not path.exists():
        raise typer.BadParameter(f"Missing required file: {path}")
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def redact_sensitive_text(message: str) -> tuple[str, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    redacted = message

    for category, pattern, replacement in REDACTION_RULES:
        def replace_match(match: re.Match[str]) -> str:
            if category == "PROJECT_NAME_VALUE" and match.lastindex:
                line_number = str(redacted[: match.start(match.lastindex)].count("\n") + 1)
                replacement_label = "[REDACTED_PROJECT_NAME_VALUE]"
            else:
                line_number = str(redacted[: match.start()].count("\n") + 1)
                replacement_label = replacement
            findings.append(
                {
                    "category": category,
                    "replacement": replacement_label,
                    "line": line_number,
                }
            )
            if category == "PROJECT_NAME_VALUE" and match.lastindex:
                return match.group(1) + "[REDACTED_PROJECT_NAME_VALUE]"
            return replacement

        redacted = pattern.sub(replace_match, redacted)

    return redacted, findings


def build_guard_report(
    *,
    timestamp: str,
    event_path: Path,
    findings: list[dict[str, str]],
    redacted_message: str,
) -> str:
    grouped: dict[str, int] = {}
    for finding in findings:
        grouped[finding["category"]] = grouped.get(finding["category"], 0) + 1

    summary_lines = [f"- {category}: {count}" for category, count in sorted(grouped.items())]
    detail_lines = [
        f"| {finding['category']} | {finding['replacement']} | line {finding['line']} |"
        for finding in findings
    ]

    return f"""## {timestamp} add-log redaction

### Event
- {display_path(event_path)}

### Findings
{chr(10).join(summary_lines) if summary_lines else "- 検出なし"}

### Details
| Category | Replacement | Line |
| --- | --- | --- |
{chr(10).join(detail_lines) if detail_lines else "| none | none | - |"}

### Stored Message
```text
{redacted_message}
```
"""


def append_guard_report(report: str, report_date: str) -> Path:
    GUARD_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = GUARD_REVIEWS_DIR / f"{report_date}.md"
    if report_path.exists():
        content = report_path.read_text(encoding="utf-8").rstrip() + "\n\n" + report.rstrip() + "\n"
    else:
        content = "# Guard Review\n\n" + report.rstrip() + "\n"
    report_path.write_text(content, encoding="utf-8")
    return report_path


def read_yaml_files(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.yaml")):
        value = read_yaml(path)
        if isinstance(value, dict):
            try:
                value["_source"] = str(path.relative_to(ROOT))
            except ValueError:
                value["_source"] = str(path)
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


def read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_text_sources(directory: Path) -> list[dict[str, str]]:
    if not directory.exists():
        return []

    items: list[dict[str, str]] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt", ".yaml", ".yml"}:
            continue
        items.append(
            {
                "path": str(path.relative_to(ROOT)),
                "content": path.read_text(encoding="utf-8"),
            }
        )
    return items


def read_source_sync_inputs() -> list[dict[str, str]]:
    items = read_text_sources(SOURCE_SYNC_DIR)
    if items:
        return items

    fallback_paths = [
        REPO_ROOT / ".codex" / "steering_sheets" / "review_notes.md",
        REPO_ROOT / ".codex" / "steering_sheets" / "career_profile.md",
        REPO_ROOT / ".codex" / "steering_sheets" / "work_history.md",
        REPO_ROOT / ".codex" / "steering_sheets" / "resume_policy.md",
    ]
    fallback_items: list[dict[str, str]] = []
    for path in fallback_paths:
        if path.exists():
            fallback_items.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "content": path.read_text(encoding="utf-8"),
                }
            )
    return fallback_items


def read_loop_skill_rules() -> dict[str, Any]:
    rules: dict[str, Any] = {"global": {}, "agents": {}}
    if not LOOP_SKILLS_RULES_DIR.exists():
        return rules

    for path in sorted(LOOP_SKILLS_RULES_DIR.iterdir()):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            value = read_yaml(path)
        else:
            value = {"raw": path.read_text(encoding="utf-8")}
        if isinstance(value, dict):
            if "global" in value and isinstance(value["global"], dict):
                rules["global"].update(value["global"])
            if "agents" in value and isinstance(value["agents"], dict):
                rules["agents"].update(value["agents"])
            if "agent" in value and isinstance(value["agent"], str):
                rules["agents"][value["agent"]] = {k: v for k, v in value.items() if k != "agent"}
    return rules


def resume_project_titles(markdown: str) -> list[str]:
    titles = re.findall(r"^### (.+)$", markdown, flags=re.MULTILINE)
    return titles


def changelog_entry_titles(text: str) -> list[str]:
    return re.findall(r"^## \[(?:[^\]]+)\] - (\d{4}-\d{2}-\d{2})", text, flags=re.MULTILINE)


def summarize_sources(
    events: list[dict[str, Any]],
    source_sync_items: list[dict[str, str]],
    resume_markdown: str,
    changelog_text: str,
) -> dict[str, Any]:
    return {
        "events_count": len(events),
        "source_sync_count": len(source_sync_items),
        "latest_resume_projects": resume_project_titles(resume_markdown)[:3],
        "resume_mentions": {
            "AI": "AI活用経験" in resume_markdown,
            "changelog": "CHANGELOG" in changelog_text or "# Changelog" in changelog_text,
        },
        "changelog_dates": changelog_entry_titles(changelog_text)[:3],
    }


def build_skill_issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def collect_skill_review_issues(
    agent: str,
    skill_text: str,
    rule: dict[str, Any],
    source_summary: dict[str, Any],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    required_terms = rule.get("required_terms", [])
    for term in required_terms:
        if term and term not in skill_text:
            issues.append(build_skill_issue(f"required_term:{term}", str(term)))

    if agent == "source_sync":
        if "data/events/" not in skill_text:
            issues.append(build_skill_issue("missing_events_input", "data/events/ を読む前提が明示されていない"))
        if "data/source_sync/" not in skill_text:
            issues.append(build_skill_issue("missing_source_sync_input", "data/source_sync/ を読む前提が明示されていない"))
        if "generated/resume.md" not in skill_text:
            issues.append(
                build_skill_issue("missing_generated_resume", "generated/resume.md を同期判断の基準に含めていない")
            )
        if "CHANGELOG.md" not in skill_text:
            issues.append(build_skill_issue("missing_changelog", "CHANGELOG.md を差分判断の入力に含めていない"))
    elif agent == "evidence_guard":
        if "generated/resume.md" not in skill_text:
            issues.append(
                build_skill_issue(
                    "missing_generated_resume",
                    "生成済み resume を最終出力の監査対象として明示していない",
                )
            )
        if "CHANGELOG.md" not in skill_text:
            issues.append(build_skill_issue("missing_changelog", "CHANGELOG を変更履歴の証跡として読む前提が弱い"))
    elif agent == "career_architect":
        if "generated/resume.md" not in skill_text:
            issues.append(
                build_skill_issue(
                    "missing_generated_resume",
                    "生成済み resume を構成設計の入力として明示していない",
                )
            )
        if "CHANGELOG.md" not in skill_text:
            issues.append(build_skill_issue("missing_changelog", "CHANGELOG を最新の構成判断材料として扱っていない"))
    elif agent == "skill_mapper":
        if "generated/resume.md" not in skill_text:
            issues.append(
                build_skill_issue(
                    "missing_generated_resume",
                    "生成済み resume から現在のスキル見せ方を確認する前提がない",
                )
            )
        if "CHANGELOG.md" not in skill_text:
            issues.append(
                build_skill_issue("missing_changelog", "CHANGELOG から直近のスキル更新を拾う前提がない")
            )
    elif agent == "application_tailor":
        if "generated/resume.md" not in skill_text:
            issues.append(
                build_skill_issue("missing_generated_resume", "応募先調整の基準として最新 resume を読む前提がない")
            )
        if "CHANGELOG.md" not in skill_text:
            issues.append(build_skill_issue("missing_changelog", "CHANGELOG を提出前の補助情報として読む前提が弱い"))
    elif agent == "export_reviewer":
        if "generated/resume.md" not in skill_text:
            issues.append(
                build_skill_issue("missing_generated_resume", "生成済み resume の最終確認が明記されていない")
            )
        if "CHANGELOG.md" not in skill_text:
            issues.append(build_skill_issue("missing_changelog", "CHANGELOG に残す変更履歴との整合確認が弱い"))

    latest_projects = source_summary.get("latest_resume_projects", [])
    if latest_projects and agent in {"career_architect", "skill_mapper", "application_tailor"}:
        issues.append(
            build_skill_issue(
                "missing_latest_resume_baseline",
                f"最新 resume の先頭案件 {latest_projects[0]} を前提にした判断基準が明示されていない",
            )
        )

    if source_summary.get("events_count", 0) == 0 and agent in {"source_sync", "evidence_guard"}:
        issues.append(build_skill_issue("missing_events_fallback", "events が空のときの扱いが明示されていない"))

    if source_summary.get("source_sync_count", 0) == 0 and agent == "source_sync":
        issues.append(
            build_skill_issue(
                "missing_source_sync_fallback",
                "data/source_sync/ が空の場合のフォールバック方針が明示されていない",
            )
        )

    return issues


def skill_review_issue_lines(agent: str, skill_text: str, rule: dict[str, Any], source_summary: dict[str, Any]) -> list[str]:
    return [issue["message"] for issue in collect_skill_review_issues(agent, skill_text, rule, source_summary)]


def patch_lines_for_issue(agent: str, issue: dict[str, str], source_summary: dict[str, Any]) -> list[str]:
    code = issue["code"]
    latest_projects = source_summary.get("latest_resume_projects", [])
    latest_project = latest_projects[0] if latest_projects else "最新 resume の先頭案件"

    if code.startswith("required_term:"):
        return [issue["message"]]

    if code == "missing_generated_resume":
        if agent == "career_architect":
            return ["`generated/resume.md` を構成設計の入力に追加する"]
        if agent == "skill_mapper":
            return ["`generated/resume.md` から現在のスキル表示を確認する"]
        if agent == "application_tailor":
            return ["`generated/resume.md` を出発点にした応募先別メモを追加する"]
        if agent == "source_sync":
            return ["`generated/resume.md` を同期確認の基準に追加する"]
        if agent == "evidence_guard":
            return ["`generated/resume.md` を最終出力の根拠照合に追加する"]
        if agent == "export_reviewer":
            return ["`generated/resume.md` を最終確認対象に追加する"]

    if code == "missing_changelog":
        if agent == "career_architect":
            return ["`CHANGELOG.md` を優先度判断の参照先に追加する"]
        if agent == "skill_mapper":
            return ["`CHANGELOG.md` から直近の改善テーマを拾う"]
        if agent == "application_tailor":
            return ["`CHANGELOG.md` を使って直近の変更点と差別化ポイントを確認する"]
        if agent == "source_sync":
            return ["`CHANGELOG.md` を差分判断の入力に追加する"]
        if agent == "evidence_guard":
            return ["`CHANGELOG.md` を変更履歴の証跡として照合する"]
        if agent == "export_reviewer":
            return ["`CHANGELOG.md` と生成物の整合を最終確認する"]

    if code == "missing_latest_resume_baseline":
        if agent == "career_architect":
            return [
                f"{latest_project} を構成判断の基準として扱う",
                "直近案件で再現可能な強みを優先する",
                "古い案件との差別化ルールを追加する",
            ]
        if agent == "skill_mapper":
            return [
                f"{latest_project} で使っている技術を主軸スキルとして優先する",
                "主軸、実務、周辺、確認待ち、非掲載候補の区分を明記する",
            ]
        if agent == "application_tailor":
            return [
                f"{latest_project} を応募先向けの強調軸の起点にする",
                "強調、削る候補、言い換え、確認待ちを分けて出力する",
            ]

    if code == "missing_events_input":
        return ["`data/events/` を一次入力として扱う"]
    if code == "missing_source_sync_input":
        return ["`data/source_sync/` を一次入力として扱う"]
    if code == "missing_events_fallback":
        return ["events が空でもループを止めないフォールバック方針を明記する"]
    if code == "missing_source_sync_fallback":
        return ["data/source_sync/ が空の場合のフォールバック方針を明記する"]

    return [issue["message"]]


def dedupe_preserving_order(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        normalized = re.sub(r"\s+", " ", line.strip())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(line.strip())
    return result


def build_skill_review(
    agent: str,
    skill_text: str,
    rule: dict[str, Any],
    source_summary: dict[str, Any],
    review_date: date,
) -> str:
    issue_items = collect_skill_review_issues(agent, skill_text, rule, source_summary)
    issues = [issue["message"] for issue in issue_items]
    suggested_skill = rule.get("suggested_skill", [])
    reasons = list(rule.get("reasons", []))
    patch_lines = dedupe_preserving_order(
        [line for issue in issue_items for line in patch_lines_for_issue(agent, issue, source_summary)]
    )

    if not issues:
        issues = ["現行ルールと入力ソースの組み合わせに対し、追加の明示がない"]
    if not patch_lines:
        patch_lines = list(rule.get("patch", []))

    reason_lines = [
        f"- 参照ソース: events={source_summary['events_count']}件, source_sync={source_summary['source_sync_count']}件",
    ]
    if source_summary.get("latest_resume_projects"):
        reason_lines.append(f"- generated/resume.md の先頭案件: {source_summary['latest_resume_projects'][0]}")
    if source_summary.get("changelog_dates"):
        reason_lines.append(f"- CHANGELOG.md の最新記録日: {source_summary['changelog_dates'][0]}")
    for reason in reasons:
        reason_lines.append(f"- {reason}")

    patch_block = "\n".join(
        [
            f"## {review_date.strftime('%Y-%m-%d')} Added",
            "",
            *patch_lines,
        ]
    ).rstrip()

    target = f".codex/agents/{agent}/SKILLS.md"
    observed_lines = "\n".join(f"- {issue}" for issue in issues)
    suggested_lines = "\n".join(f"- {item}" for item in suggested_skill) if suggested_skill else "- 追加提案なし"
    reason_text = "\n".join(reason_lines)

    return f"""# Skill Improvement Proposal: {agent}

## Target
{target}

## Observed Issues
{observed_lines}

## Suggested Skill
{suggested_lines}

## Reason
{reason_text}

## Patch Proposal
```md
{patch_block}
```
"""


def list_skill_review_paths() -> list[Path]:
    if not SKILL_REVIEWS_DIR.exists():
        return []
    applied_records = read_applied_skill_reviews()
    paths = sorted(path for path in SKILL_REVIEWS_DIR.rglob("*.md") if path.is_file())
    return [path for path in paths if not proposal_file_is_applied(path, applied_records)]


def resolve_input_path(path_text: str) -> Path:
    candidate = Path(path_text).expanduser()
    possible_paths = [candidate]
    if not candidate.is_absolute():
        possible_paths.extend(
            [
                ROOT / candidate,
                REPO_ROOT / candidate,
            ]
        )
    for path in possible_paths:
        if path.exists():
            return path.resolve()
    raise typer.BadParameter(f"Missing file: {path_text}")


def extract_target_from_proposal(proposal_text: str) -> str:
    match = re.search(r"^## Target\s*\n(.+)$", proposal_text, flags=re.MULTILINE)
    if not match:
        raise typer.BadParameter("Proposal is missing Target section.")
    return match.group(1).strip()


def extract_agent_from_target(target_text: str) -> str:
    match = re.search(r"\.codex/agents/([^/]+)/SKILLS\.md$", target_text)
    if not match:
        raise typer.BadParameter(f"Unsupported Target: {target_text}")
    return match.group(1)


def extract_patch_block(proposal_text: str) -> str:
    match = re.search(r"^## Patch Proposal\s*\n```md\s*\n(.*?)\n```", proposal_text, flags=re.MULTILINE | re.DOTALL)
    if not match:
        raise typer.BadParameter("Proposal is missing Patch Proposal code block.")
    return match.group(1).strip("\n")


def normalize_patch_block(patch_block: str) -> str:
    normalized_lines: list[str] = []
    for raw_line in patch_block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^##\s+\d{4}-\d{2}-\d{2}\s+Added$", line):
            continue
        normalized_lines.append(re.sub(r"\s+", " ", line.replace("`", "")).strip())
    return "\n".join(normalized_lines)


def normalize_summary_lines(patch_block: str) -> str:
    lines = [line for line in normalize_patch_block(patch_block).splitlines() if line]
    if not lines:
        return "Patch Proposal を反映"
    return " / ".join(lines[:3])


def normalize_review_summary(summary: str) -> str:
    return re.sub(r"\s+", " ", summary.replace("`", "").strip())


def build_patch_hash(patch_block: str) -> str:
    normalized_patch = normalize_patch_block(patch_block)
    return hashlib.sha256(normalized_patch.encode("utf-8")).hexdigest()


def summary_similarity(left: str, right: str) -> float:
    left_normalized = normalize_review_summary(left)
    right_normalized = normalize_review_summary(right)
    if not left_normalized or not right_normalized:
        return 0.0
    if left_normalized == right_normalized:
        return 1.0
    return SequenceMatcher(None, left_normalized, right_normalized).ratio()


def read_applied_skill_reviews() -> list[dict[str, str]]:
    if not SKILL_REVIEWS_APPLIED_INDEX.exists():
        return []
    return [enrich_applied_skill_review_record(record) for record in read_raw_applied_skill_reviews()]


def read_raw_applied_skill_reviews() -> list[dict[str, str]]:
    if not SKILL_REVIEWS_APPLIED_INDEX.exists():
        return []
    records: list[dict[str, str]] = []
    for line in SKILL_REVIEWS_APPLIED_INDEX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append({k: str(v) for k, v in value.items()})
    return records


def append_applied_skill_review_record(record: dict[str, str]) -> None:
    SKILL_REVIEWS_APPLIED_INDEX.parent.mkdir(parents=True, exist_ok=True)
    with SKILL_REVIEWS_APPLIED_INDEX.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        file.write("\n")


def resolve_existing_path(path_text: str) -> Path | None:
    candidate = Path(path_text).expanduser()
    possible_paths = [candidate]
    if not candidate.is_absolute():
        possible_paths.extend(
            [
                ROOT / candidate,
                REPO_ROOT / candidate,
                SKILL_REVIEWS_APPLIED_DIR / date.today().strftime("%Y-%m-%d") / candidate.name,
                SKILL_REVIEWS_APPLIED_DIR / candidate.name,
            ]
        )
    for path in possible_paths:
        if path.exists():
            return path.resolve()
    return None


def infer_applied_copy_path(record: dict[str, str]) -> Path | None:
    source_proposal = record.get("source_proposal", "")
    if source_proposal:
        source_name = Path(source_proposal).name
        applied_at = record.get("applied_at", "")
        if applied_at:
            candidate = SKILL_REVIEWS_APPLIED_DIR / applied_at / source_name
            if candidate.exists():
                return candidate.resolve()
        for candidate in sorted(SKILL_REVIEWS_APPLIED_DIR.rglob(source_name)):
            if candidate.is_file():
                return candidate.resolve()
    return None


def enrich_applied_skill_review_record(record: dict[str, str]) -> dict[str, str]:
    enriched = dict(record)
    source_path: Path | None = None

    source_proposal = record.get("source_proposal", "")
    if source_proposal:
        source_path = resolve_existing_path(source_proposal)
    if source_path is None:
        source_path = infer_applied_copy_path(record)

    if source_path is not None:
        proposal_text = source_path.read_text(encoding="utf-8")
        enriched.setdefault("source_proposal", display_path(source_path))
        enriched.setdefault("source_hash", hashlib.sha256(proposal_text.encode("utf-8")).hexdigest())
        try:
            patch_block = extract_patch_block(proposal_text)
        except typer.BadParameter:
            patch_block = ""
        if patch_block:
            enriched.setdefault("patch_hash", build_patch_hash(patch_block))
            summary = normalize_summary_lines(patch_block)
            enriched.setdefault("patch_summary", summary)
            enriched.setdefault("normalized_summary", normalize_review_summary(summary))

    return enriched


def is_applied_skill_review(
    *,
    agent: str,
    source_hash: str,
    source_proposal: str,
    patch_hash: str,
    normalized_summary: str,
    applied_records: list[dict[str, str]],
) -> bool:
    for record in applied_records:
        if record.get("agent") != agent:
            continue
        if source_hash and record.get("source_hash") == source_hash:
            return True
        if source_proposal and record.get("source_proposal") == source_proposal:
            return True
        if record.get("patch_hash") == patch_hash:
            return True
        record_summary = normalize_review_summary(
            record.get("normalized_summary") or record.get("patch_summary") or record.get("summary", "")
        )
        if record_summary and summary_similarity(normalized_summary, record_summary) >= 0.9:
            return True
    return False


def collect_skill_review_proposals(review_date: date | None = None) -> tuple[list[Path], int]:
    review_date = review_date or date.today()
    rules = read_loop_skill_rules()
    events = read_yaml_files(EVENTS_DIR)
    source_sync_items = read_source_sync_inputs()
    resume_markdown = read_optional_text(GENERATED_DIR / "resume.md")
    changelog_text = read_optional_text(CHANGELOG_PATH)
    source_summary = summarize_sources(events, source_sync_items, resume_markdown, changelog_text)
    applied_records = read_applied_skill_reviews()

    SKILL_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    output_dir = SKILL_REVIEWS_DIR / review_date.strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_paths: list[Path] = []
    skipped_count = 0
    for agent_dir in sorted((CODEX_DIR / "agents").iterdir()):
        if not agent_dir.is_dir():
            continue
        skill_path = agent_dir / "SKILLS.md"
        if not skill_path.exists():
            continue
        agent = agent_dir.name
        skill_text = skill_path.read_text(encoding="utf-8")
        agent_rule = rules.get("agents", {}).get(agent, {})
        proposal = build_skill_review(
            agent=agent,
            skill_text=skill_text,
            rule=agent_rule,
            source_summary=source_summary,
            review_date=review_date,
        )
        proposal_hash = hashlib.sha256(proposal.encode("utf-8")).hexdigest()
        proposal_key = display_path((output_dir / f"{agent}.md").resolve())
        patch_block = extract_patch_block(proposal)
        patch_summary = normalize_summary_lines(patch_block)
        normalized_summary = normalize_review_summary(patch_summary)
        patch_hash = build_patch_hash(patch_block)

        if is_applied_skill_review(
            agent=agent,
            source_hash=proposal_hash,
            source_proposal=proposal_key,
            patch_hash=patch_hash,
            normalized_summary=normalized_summary,
            applied_records=applied_records,
        ):
            skipped_count += 1
            continue

        output_path = output_dir / f"{agent}.md"
        output_path.write_text(proposal, encoding="utf-8")
        generated_paths.append(output_path)

    return generated_paths, skipped_count


def write_skill_reviews(review_date: date | None = None) -> list[Path]:
    generated_paths, _ = collect_skill_review_proposals(review_date=review_date)
    return generated_paths


def proposal_file_is_applied(proposal_path: Path, applied_records: list[dict[str, str]]) -> bool:
    proposal_text = proposal_path.read_text(encoding="utf-8")
    try:
        target_text = extract_target_from_proposal(proposal_text)
        agent = extract_agent_from_target(target_text)
        patch_block = extract_patch_block(proposal_text)
    except typer.BadParameter:
        return False
    patch_hash = build_patch_hash(patch_block)
    patch_summary = normalize_summary_lines(patch_block)
    normalized_summary = normalize_review_summary(patch_summary)
    proposal_hash = hashlib.sha256(proposal_text.encode("utf-8")).hexdigest()
    proposal_key = display_path(proposal_path.resolve())

    for record in applied_records:
        if record.get("source_proposal") == proposal_key or record.get("source_hash") == proposal_hash:
            return True

    return is_applied_skill_review(
        agent=agent,
        source_hash=proposal_hash,
        source_proposal=proposal_key,
        patch_hash=patch_hash,
        normalized_summary=normalized_summary,
        applied_records=applied_records,
    )


def build_skill_review_changelog_entry(
    agent: str,
    proposal_path: Path,
    target_path: Path,
    summary: str,
) -> str:
    applied_date = date.today().strftime("%Y-%m-%d")
    return f"""## {applied_date} skill review applied: {agent}

### Source proposal
- {display_path(proposal_path)}

### Target
- {display_path(target_path)}

### Summary
- {summary}
"""


def apply_skill_review_file(proposal_path: Path) -> dict[str, str]:
    proposal_path = proposal_path.resolve()
    proposal_text = proposal_path.read_text(encoding="utf-8")
    target_text = extract_target_from_proposal(proposal_text)
    agent = extract_agent_from_target(target_text)
    patch_block = extract_patch_block(proposal_text)
    summary = normalize_summary_lines(patch_block)
    normalized_summary = normalize_review_summary(summary)
    patch_hash = build_patch_hash(patch_block)
    proposal_hash = hashlib.sha256(proposal_text.encode("utf-8")).hexdigest()
    source_key = display_path(proposal_path)
    target_path = resolve_input_path(target_text)
    target_text_current = target_path.read_text(encoding="utf-8")

    applied_records = read_applied_skill_reviews()
    is_already_applied = any(
        record.get("source_proposal") == source_key
        or record.get("source_hash") == proposal_hash
        or record.get("target") == display_path(target_path) and record.get("agent") == agent
        for record in applied_records
    ) or f"skill-review-source: {source_key}" in target_text_current

    if is_already_applied:
        return {
            "status": "already applied",
            "agent": agent,
            "proposal": source_key,
            "target": display_path(target_path),
        }

    target_lines = target_text_current.rstrip()
    appended_parts = [
        f"<!-- skill-review-source: {source_key} -->",
        patch_block,
    ]
    if target_lines:
        appended_block = target_lines + "\n\n" + "\n\n".join(appended_parts).rstrip() + "\n"
    else:
        appended_block = "\n\n".join(appended_parts).rstrip() + "\n"
    target_path.write_text(appended_block, encoding="utf-8")

    applied_dir = SKILL_REVIEWS_APPLIED_DIR / date.today().strftime("%Y-%m-%d")
    applied_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(proposal_path, applied_dir / proposal_path.name)

    changelog_entry = build_skill_review_changelog_entry(
        agent=agent,
        proposal_path=proposal_path,
        target_path=target_path,
        summary=summary,
    )
    append_changelog(changelog_entry)

    append_applied_skill_review_record(
        {
            "agent": agent,
            "applied_at": date.today().strftime("%Y-%m-%d"),
            "normalized_summary": normalized_summary,
            "patch_hash": patch_hash,
            "patch_summary": summary,
            "summary": summary,
            "source_hash": proposal_hash,
            "source_proposal": source_key,
            "target": display_path(target_path),
        }
    )

    return {
        "status": "applied",
        "agent": agent,
        "proposal": source_key,
        "target": display_path(target_path),
        "applied_copy": display_path(applied_dir / proposal_path.name),
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
    today = datetime.now().strftime("%Y-%m-%d")
    path = events_dir / f"{timestamp}.yaml"
    redacted_message, findings = redact_sensitive_text(message or "手動ログ")
    payload = {
        "date": today,
        "type": "manual_log",
        "message": redacted_message,
    }
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(payload, file, allow_unicode=True, sort_keys=False)
    if findings:
        report_path = append_guard_report(
            build_guard_report(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                event_path=path,
                findings=findings,
                redacted_message=redacted_message,
            ),
            report_date=today,
        )
        typer.echo(f"Guard report: {report_path.relative_to(ROOT)}")
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


@app.command("loop-skills")
def loop_skills() -> None:
    """Generate skill improvement proposals under reviews/skills/YYYY-MM-DD/."""
    review_paths, skipped_count = collect_skill_review_proposals()
    if not review_paths:
        typer.echo("No skill review proposals were generated.")
        typer.echo(f"Skipped {skipped_count} applied proposals")
        return
    typer.echo(f"Generated {len(review_paths)} skill review proposals")
    typer.echo(f"Skipped {skipped_count} applied proposals")
    for path in review_paths:
        typer.echo(f"- {path.relative_to(ROOT)}")


@app.command("backfill-skill-review-index")
def backfill_skill_review_index() -> None:
    """Backfill applied skill review records with proposal-derived metadata."""
    records = read_raw_applied_skill_reviews()
    if not records:
        typer.echo("No applied skill review records found.")
        return

    enriched_records = [enrich_applied_skill_review_record(record) for record in records]
    SKILL_REVIEWS_APPLIED_INDEX.parent.mkdir(parents=True, exist_ok=True)
    with SKILL_REVIEWS_APPLIED_INDEX.open("w", encoding="utf-8") as file:
        for record in enriched_records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            file.write("\n")

    updated_count = sum(
        1
        for before, after in zip(records, enriched_records, strict=False)
        if before.get("patch_hash") != after.get("patch_hash")
        or before.get("normalized_summary") != after.get("normalized_summary")
        or before.get("source_hash") != after.get("source_hash")
    )
    typer.echo(f"Backfilled {updated_count} applied skill review records")


@app.command("list-skill-reviews")
def list_skill_reviews() -> None:
    """List generated skill review proposals."""
    review_paths = list_skill_review_paths()
    if not review_paths:
        typer.echo("No skill review proposals found.")
        return
    for path in review_paths:
        typer.echo(display_path(path))


@app.command("apply-skill-review")
def apply_skill_review(
    file: str = typer.Option(..., "--file", "-f", help="Skill review proposal file to apply."),
) -> None:
    """Apply one approved skill review proposal to a target SKILLS.md."""
    result = apply_skill_review_file(resolve_input_path(file))
    if result["status"] == "already applied":
        typer.echo(f"already applied: {result['proposal']}")
        return

    typer.echo(f"Applied skill review: {result['proposal']}")
    typer.echo(f"- target: {result['target']}")
    typer.echo(f"- copy: {result['applied_copy']}")


if __name__ == "__main__":
    app()
