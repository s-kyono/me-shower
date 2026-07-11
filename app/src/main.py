from __future__ import annotations

import html
import hashlib
import json
import os
from dataclasses import dataclass
from difflib import SequenceMatcher
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import typer
import yaml
from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt


app = typer.Typer(help="Generate career resume Markdown and PDF outputs.")

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
DATA_DIR = ROOT / "data"
DAILY_REPORTS_DIR = DATA_DIR / "daily_reports"
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


@dataclass(frozen=True)
class RawSource:
    id: str
    source_type: str
    origin: str
    title: str
    content: str
    captured_at: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SourceConfidence:
    level: str
    score: int
    reasons: list[str]


class SourceAdapterError(Exception):
    pass


class SourceNotFoundError(SourceAdapterError):
    pass


class SourceAccessError(SourceAdapterError):
    pass


class SourceAdapter(Protocol):
    name: str

    def discover(self) -> list[RawSource]:
        ...

    def fetch(self, source_id: str) -> RawSource:
        ...


class FileSourceAdapter:
    name = "file"

    def __init__(self, raw_dir: Path) -> None:
        self.raw_dir = raw_dir

    def discover(self) -> list[RawSource]:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        return [self._build_raw_source(path) for path in sorted(self.raw_dir.glob("*.txt"))]

    def fetch(self, source_id: str) -> RawSource:
        for source in self.discover():
            if source.id == source_id:
                return source
        raise SourceNotFoundError(f"Unknown source id for adapter '{self.name}': {source_id}")

    def _build_raw_source(self, path: Path) -> RawSource:
        resolved = path.resolve()
        stat = resolved.stat()
        return RawSource(
            id=resolved.name,
            source_type="file",
            origin=str(resolved),
            title=resolved.name,
            content=resolved.read_text(encoding="utf-8"),
            captured_at=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            metadata={
                "path": str(resolved),
                "size_bytes": stat.st_size,
            },
        )


class DailyReportSourceAdapter:
    name = "daily_report"

    def __init__(self, reports_dir: Path, limit: int | None = None) -> None:
        self.reports_dir = reports_dir
        self.limit = limit

    def discover(self) -> list[RawSource]:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        paths = [
            path
            for path in sorted(self.reports_dir.rglob("*"))
            if path.is_file() and path.suffix.lower() in {".md", ".txt"}
        ]
        sources = [self._build_raw_source(path) for path in paths]
        sources.sort(key=lambda item: (item.metadata.get("detected_date", ""), item.id), reverse=True)
        if self.limit is not None:
            return sources[: self.limit]
        return sources

    def fetch(self, source_id: str) -> RawSource:
        for source in self.discover():
            if source.id == source_id:
                return source
        raise SourceNotFoundError(f"Unknown source id for adapter '{self.name}': {source_id}")

    def _build_raw_source(self, path: Path) -> RawSource:
        resolved = path.resolve()
        stat = resolved.stat()
        relative_path = self._relative_path(resolved)
        raw_text = resolved.read_text(encoding="utf-8", errors="replace")
        parsed = parse_optional_frontmatter(raw_text)
        content = parsed["content"]
        frontmatter = parsed["frontmatter"]
        detected_date = detect_daily_report_date(
            resolved,
            raw_text,
            content,
            frontmatter,
            fallback=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        )
        source_reference = f"daily_report:{display_path(resolved)}"
        title_suffix = detected_date or resolved.stem
        metadata: dict[str, Any] = {
            "kind": infer_daily_report_kind(resolved, frontmatter, content),
            "path": str(resolved),
            "relative_path": relative_path,
            "detected_date": detected_date,
            "source_reference": source_reference,
            "format": "markdown" if resolved.suffix.lower() == ".md" else "text",
        }
        if frontmatter:
            metadata["frontmatter"] = frontmatter
            tags = frontmatter.get("tags")
            if isinstance(tags, list):
                metadata["tags"] = [str(tag) for tag in tags]

        return RawSource(
            id=f"daily_report:{relative_path}",
            source_type="daily_report",
            origin=source_reference,
            title=f"Daily Report {title_suffix}",
            content=content,
            captured_at=detected_date or datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            metadata=metadata,
        )

    def _relative_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.reports_dir).as_posix()
        except ValueError:
            return path.name


@dataclass(frozen=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


CommandRunner = Callable[[list[str]], CommandResult]
SlackApiCaller = Callable[[str, dict[str, Any]], dict[str, Any]]
GraphApiCaller = Callable[[str, dict[str, Any]], dict[str, Any]]


def run_command(command: list[str]) -> CommandResult:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return CommandResult(
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )


class UnconfiguredSourceAdapter:
    def __init__(self, name: str, message: str) -> None:
        self.name = name
        self.message = message

    def discover(self) -> list[RawSource]:
        raise SourceAccessError(self.message)

    def fetch(self, source_id: str) -> RawSource:
        raise SourceAccessError(self.message)


class GitHubSourceAdapter:
    name = "github"

    def __init__(self, repo: str, limit: int = 20, command_runner: CommandRunner | None = None) -> None:
        self.repo = repo
        self.limit = limit
        self.command_runner = command_runner or run_command

    def discover(self) -> list[RawSource]:
        payload = self._run_gh(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                self.repo,
                "--state",
                "all",
                "--limit",
                str(self.limit),
                "--json",
                "number,title,body,state,author,createdAt,updatedAt,url,labels",
            ]
        )
        if not isinstance(payload, list):
            raise SourceAccessError("Failed to parse GitHub pull request list.")
        return [self._build_raw_source(pr) for pr in payload if isinstance(pr, dict)]

    def fetch(self, source_id: str) -> RawSource:
        pr_number = self._parse_source_id(source_id)
        payload = self._run_gh(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--repo",
                self.repo,
                "--json",
                "number,title,body,state,author,createdAt,updatedAt,url,labels,files",
            ],
            missing_error=SourceNotFoundError(f"Pull request not found: {source_id}"),
        )
        if not isinstance(payload, dict):
            raise SourceAccessError(f"Failed to parse GitHub pull request detail for {source_id}.")
        return self._build_raw_source(payload)

    def _run_gh(
        self,
        command: list[str],
        *,
        missing_error: SourceAdapterError | None = None,
    ) -> Any:
        try:
            result = self.command_runner(command)
        except FileNotFoundError as exc:
            raise SourceAccessError("GitHub CLI 'gh' is not installed or not available on PATH.") from exc

        if result.returncode != 0:
            stderr = sanitize_command_error(result.stderr)
            lowered = stderr.lower()
            if missing_error is not None and ("not found" in lowered or "could not resolve to a pull request" in lowered):
                raise missing_error
            if "not logged into any hosts" in lowered or "authentication failed" in lowered:
                raise SourceAccessError("GitHub CLI is not authenticated. Run 'gh auth login' and try again.")
            if "could not resolve to a repository" in lowered or "repository not found" in lowered:
                raise SourceAccessError(f"GitHub repository is not accessible: {self.repo}")
            if stderr:
                raise SourceAccessError(f"GitHub CLI command failed: {stderr}")
            raise SourceAccessError("GitHub CLI command failed.")

        try:
            return json.loads(result.stdout or "null")
        except json.JSONDecodeError as exc:
            raise SourceAccessError("Failed to parse JSON output from GitHub CLI.") from exc

    def _parse_source_id(self, source_id: str) -> int:
        prefix = f"github:{self.repo}:pr:"
        if not source_id.startswith(prefix):
            raise SourceNotFoundError(f"Unknown source id for adapter '{self.name}': {source_id}")
        number_text = source_id.removeprefix(prefix)
        if not number_text.isdigit():
            raise SourceNotFoundError(f"Unknown source id for adapter '{self.name}': {source_id}")
        return int(number_text)

    def _build_raw_source(self, payload: dict[str, Any]) -> RawSource:
        number = int(payload.get("number", 0))
        title = str(payload.get("title", "")).strip()
        body = str(payload.get("body") or "").strip()
        state = str(payload.get("state", "unknown")).lower()
        url = str(payload.get("url", "")).strip()
        created_at = str(payload.get("createdAt", "")).strip()
        updated_at = str(payload.get("updatedAt", "")).strip()
        author = self._extract_author(payload.get("author"))
        labels = self._extract_labels(payload.get("labels"))
        changed_files = self._extract_changed_files(payload.get("files"))
        pr_title = f"PR #{number} {title}".strip()

        metadata: dict[str, Any] = {
            "repo": self.repo,
            "kind": "pull_request",
            "number": number,
            "state": state,
            "url": url,
            "author": author,
            "created_at": created_at,
            "updated_at": updated_at,
            "labels": labels,
            "source_reference": f"github:{self.repo}#{number}",
        }
        if changed_files:
            metadata["changed_files"] = changed_files

        return RawSource(
            id=f"github:{self.repo}:pr:{number}",
            source_type="github",
            origin=f"github:{self.repo}#{number}",
            title=pr_title,
            content=self._build_content(
                title=pr_title,
                body=body,
                state=state,
                author=author,
                created_at=created_at,
                updated_at=updated_at,
                url=url,
                labels=labels,
                changed_files=changed_files,
            ),
            captured_at=updated_at or datetime.now().isoformat(timespec="seconds"),
            metadata=metadata,
        )

    def _build_content(
        self,
        *,
        title: str,
        body: str,
        state: str,
        author: str,
        created_at: str,
        updated_at: str,
        url: str,
        labels: list[str],
        changed_files: list[str],
    ) -> str:
        lines = [
            title,
            f"Repository: {self.repo}",
            f"State: {state}",
            f"Author: {author or 'unknown'}",
            f"Created At: {created_at or 'unknown'}",
            f"Updated At: {updated_at or 'unknown'}",
            f"Labels: {', '.join(labels) if labels else 'none'}",
            f"URL: {url or 'unknown'}",
            "Body:",
            body or "(empty)",
        ]
        if changed_files:
            lines.append("Changed Files:")
            lines.extend(f"- {item}" for item in changed_files)
        return "\n".join(lines)

    def _extract_author(self, author: Any) -> str:
        if isinstance(author, dict):
            login = author.get("login")
            if isinstance(login, str) and login.strip():
                return login.strip()
            name = author.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        if isinstance(author, str):
            return author.strip()
        return ""

    def _extract_labels(self, labels: Any) -> list[str]:
        if not isinstance(labels, list):
            return []
        result: list[str] = []
        for item in labels:
            if isinstance(item, dict):
                name = item.get("name")
                if isinstance(name, str) and name.strip():
                    result.append(name.strip())
            elif isinstance(item, str) and item.strip():
                result.append(item.strip())
        return result

    def _extract_changed_files(self, files: Any) -> list[str]:
        if not isinstance(files, list):
            return []
        result: list[str] = []
        for item in files:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path") or "").strip()
            if not path:
                continue
            additions = item.get("additions")
            deletions = item.get("deletions")
            if isinstance(additions, int) and isinstance(deletions, int):
                result.append(f"{path} (+{additions} -{deletions})")
            else:
                result.append(path)
        return result


def call_slack_api(method: str, params: dict[str, Any], *, token: str) -> dict[str, Any]:
    encoded = urlencode({key: value for key, value in params.items() if value is not None}).encode("utf-8")
    request = Request(
        url=f"https://slack.com/api/{method}",
        data=encoded,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(request) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        message = sanitize_slack_error_message(exc.read().decode("utf-8", errors="replace") or str(exc))
        if exc.code == 429:
            raise SourceAccessError("Slack API rate limit exceeded.") from exc
        raise SourceAccessError(f"Slack API request failed: {message or 'http error'}") from exc
    except URLError as exc:
        raise SourceAccessError(f"Slack API request failed: {sanitize_slack_error_message(str(exc.reason))}") from exc

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SourceAccessError("Failed to parse Slack API JSON response.") from exc
    if not isinstance(parsed, dict):
        raise SourceAccessError("Failed to parse Slack API response.")
    return parsed


def call_graph_api(path: str, params: dict[str, Any], *, token: str) -> dict[str, Any]:
    query = urlencode({key: value for key, value in params.items() if value is not None})
    url = f"https://graph.microsoft.com{path}"
    if query:
        url = f"{url}?{query}"
    request = Request(
        url=url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(request) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        message = sanitize_graph_error_message(exc.read().decode("utf-8", errors="replace") or str(exc))
        if exc.code == 401:
            raise SourceAccessError("Microsoft Graph token is invalid or expired.") from exc
        if exc.code == 403:
            raise SourceAccessError("Microsoft Graph access denied for the requested Teams channel.") from exc
        if exc.code == 404:
            raise SourceNotFoundError("Teams team, channel, or message was not found.") from exc
        if exc.code == 429:
            raise SourceAccessError("Microsoft Graph API rate limit exceeded.") from exc
        raise SourceAccessError(f"Microsoft Graph API request failed: {message or 'http error'}") from exc
    except URLError as exc:
        raise SourceAccessError(f"Microsoft Graph API request failed: {sanitize_graph_error_message(str(exc.reason))}") from exc

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SourceAccessError("Failed to parse Microsoft Graph API JSON response.") from exc
    if not isinstance(parsed, dict):
        raise SourceAccessError("Failed to parse Microsoft Graph API response.")
    return parsed


class SlackSourceAdapter:
    name = "slack"

    def __init__(
        self,
        channel: str,
        limit: int = 20,
        token_env: str = "SLACK_BOT_TOKEN",
        oldest: str | None = None,
        latest: str | None = None,
        api_caller: SlackApiCaller | None = None,
    ) -> None:
        self.channel = channel
        self.limit = limit
        self.token_env = token_env
        self.oldest = oldest
        self.latest = latest
        self._api_caller = api_caller

    def discover(self) -> list[RawSource]:
        messages = self._fetch_messages()
        return [self._build_raw_source(message) for message in messages]

    def fetch(self, source_id: str) -> RawSource:
        for source in self.discover():
            if source.id == source_id:
                return source
        raise SourceNotFoundError(f"Unknown source id for adapter '{self.name}': {source_id}")

    def _fetch_messages(self) -> list[dict[str, Any]]:
        payload = self._call_api(
            "conversations.history",
            {
                "channel": self.channel,
                "limit": self.limit,
                "oldest": self.oldest,
                "latest": self.latest,
                "inclusive": True,
            },
        )
        messages = payload.get("messages")
        if not isinstance(messages, list):
            raise SourceAccessError("Slack API did not return a valid message list.")
        return [item for item in messages if isinstance(item, dict) and str(item.get("ts") or "").strip()]

    def _call_api(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        token = self._resolve_token()
        caller = self._api_caller or (lambda api_method, api_params: call_slack_api(api_method, api_params, token=token))
        try:
            payload = caller(method, params)
        except SourceAdapterError:
            raise
        except Exception as exc:
            raise SourceAccessError(f"Slack API request failed: {sanitize_slack_error_message(str(exc))}") from exc
        if not isinstance(payload, dict):
            raise SourceAccessError("Failed to parse Slack API response.")
        if payload.get("ok") is False:
            raise self._build_api_error(payload)
        return payload

    def _resolve_token(self) -> str:
        token = os.getenv(self.token_env, "").strip()
        if not token:
            raise SourceAccessError(f"Slack token environment variable is not set: {self.token_env}")
        return token

    def _build_api_error(self, payload: dict[str, Any]) -> SourceAdapterError:
        error_code = str(payload.get("error") or "unknown_error").strip()
        normalized_error_code = error_code.split()[0] if error_code else "unknown_error"
        if normalized_error_code in {"channel_not_found", "message_not_found"}:
            return SourceNotFoundError(f"Slack resource not found: {normalized_error_code}")
        if normalized_error_code in {"not_in_channel", "missing_scope", "invalid_auth", "not_authed", "account_inactive"}:
            return SourceAccessError(f"Slack API access denied: {normalized_error_code}")
        if normalized_error_code == "ratelimited":
            return SourceAccessError("Slack API rate limit exceeded.")
        return SourceAccessError(f"Slack API request failed: {sanitize_slack_error_message(error_code)}")

    def _build_raw_source(self, payload: dict[str, Any]) -> RawSource:
        ts = str(payload.get("ts") or "").strip()
        thread_ts = str(payload.get("thread_ts") or "").strip()
        user = str(payload.get("user") or payload.get("bot_id") or "").strip()
        text = str(payload.get("text") or "").strip()
        subtype = str(payload.get("subtype") or "").strip()
        message_datetime = slack_ts_to_datetime(ts)
        permalink = self._get_permalink(ts)

        metadata: dict[str, Any] = {
            "channel": self.channel,
            "kind": "message",
            "ts": ts,
            "thread_ts": thread_ts,
            "user": user,
            "created_at": message_datetime.isoformat(timespec="seconds"),
        }
        if subtype:
            metadata["subtype"] = subtype
        if permalink:
            metadata["permalink"] = permalink

        return RawSource(
            id=f"slack:{self.channel}:{ts}",
            source_type="slack",
            origin=f"slack:{self.channel}:{ts}",
            title=f"Slack message {message_datetime.strftime('%Y-%m-%d %H:%M')}",
            content=self._build_content(
                text=text,
                channel=self.channel,
                ts=ts,
                thread_ts=thread_ts,
                user=user,
                created_at=message_datetime.isoformat(timespec="seconds"),
                subtype=subtype,
                permalink=permalink,
            ),
            captured_at=message_datetime.isoformat(timespec="seconds"),
            metadata=metadata,
        )

    def _get_permalink(self, message_ts: str) -> str:
        try:
            payload = self._call_api("chat.getPermalink", {"channel": self.channel, "message_ts": message_ts})
        except SourceAdapterError:
            return ""
        permalink = payload.get("permalink")
        if isinstance(permalink, str):
            return permalink.strip()
        return ""

    def _build_content(
        self,
        *,
        text: str,
        channel: str,
        ts: str,
        thread_ts: str,
        user: str,
        created_at: str,
        subtype: str,
        permalink: str,
    ) -> str:
        lines = [
            f"Slack Channel: {channel}",
            f"Message TS: {ts}",
            f"Thread TS: {thread_ts or 'none'}",
            f"User: {user or 'unknown'}",
            f"Created At: {created_at}",
            f"Subtype: {subtype or 'none'}",
        ]
        if permalink:
            lines.append(f"Permalink: {permalink}")
        lines.extend(["Text:", text or "(empty)"])
        return "\n".join(lines)


class TeamsSourceAdapter:
    name = "teams"

    def __init__(
        self,
        team_id: str,
        channel_id: str,
        limit: int = 20,
        token_env: str = "MS_GRAPH_TOKEN",
        oldest: datetime | None = None,
        latest: datetime | None = None,
        api_caller: GraphApiCaller | None = None,
    ) -> None:
        self.team_id = team_id
        self.channel_id = channel_id
        self.limit = limit
        self.token_env = token_env
        self.oldest = oldest
        self.latest = latest
        self._api_caller = api_caller

    def discover(self) -> list[RawSource]:
        messages = self._fetch_messages()
        return [self._build_raw_source(message) for message in messages]

    def fetch(self, source_id: str) -> RawSource:
        for source in self.discover():
            if source.id == source_id:
                return source
        raise SourceNotFoundError(f"Unknown source id for adapter '{self.name}': {source_id}")

    def _fetch_messages(self) -> list[dict[str, Any]]:
        payload = self._call_api(
            f"/v1.0/teams/{self.team_id}/channels/{self.channel_id}/messages",
            {"$top": min(self.limit, 50)},
        )
        messages = payload.get("value")
        if not isinstance(messages, list):
            raise SourceAccessError("Microsoft Graph API did not return a valid Teams message list.")
        filtered = [item for item in messages if isinstance(item, dict) and str(item.get("id") or "").strip()]
        return [item for item in filtered if self._is_within_range(str(item.get("createdDateTime") or "").strip())]

    def _call_api(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        token = self._resolve_token()
        caller = self._api_caller or (lambda api_path, api_params: call_graph_api(api_path, api_params, token=token))
        try:
            payload = caller(path, params)
        except SourceAdapterError:
            raise
        except Exception as exc:
            raise SourceAccessError(f"Microsoft Graph API request failed: {sanitize_graph_error_message(str(exc))}") from exc
        if not isinstance(payload, dict):
            raise SourceAccessError("Failed to parse Microsoft Graph API response.")
        if "error" in payload:
            raise self._build_api_error(payload)
        return payload

    def _resolve_token(self) -> str:
        token = os.getenv(self.token_env, "").strip()
        if not token:
            raise SourceAccessError(f"Microsoft Graph token environment variable is not set: {self.token_env}")
        return token

    def _build_api_error(self, payload: dict[str, Any]) -> SourceAdapterError:
        raw_error = payload.get("error")
        if isinstance(raw_error, dict):
            code = str(raw_error.get("code") or "unknown_error").strip()
            message = str(raw_error.get("message") or "").strip()
        else:
            code = str(raw_error or "unknown_error").strip()
            message = ""
        normalized = code.lower()
        full_message = sanitize_graph_error_message(f"{code} {message}".strip())
        if normalized in {"itemnotfound", "notfound", "erroritemnotfound"}:
            return SourceNotFoundError(f"Teams resource not found: {code}")
        if normalized in {"unauthenticated", "invalidauthenticationtoken", "accesstokenexpired"}:
            return SourceAccessError("Microsoft Graph token is invalid or expired.")
        if normalized in {"forbidden", "accessdenied", "authorization_requestdenied"}:
            return SourceAccessError("Microsoft Graph access denied for the requested Teams channel.")
        if normalized in {"toomanyrequests", "throttledrequest"}:
            return SourceAccessError("Microsoft Graph API rate limit exceeded.")
        return SourceAccessError(f"Microsoft Graph API request failed: {full_message or code}")

    def _is_within_range(self, created_at: str) -> bool:
        if not created_at:
            return True
        created = teams_datetime_to_datetime(created_at)
        if self.oldest is not None and created < self.oldest:
            return False
        if self.latest is not None and created > self.latest:
            return False
        return True

    def _build_raw_source(self, payload: dict[str, Any]) -> RawSource:
        message_id = str(payload.get("id") or "").strip()
        created_at = str(payload.get("createdDateTime") or "").strip()
        last_modified_at = str(payload.get("lastModifiedDateTime") or "").strip()
        subject = str(payload.get("subject") or "").strip()
        summary = str(payload.get("summary") or "").strip()
        importance = str(payload.get("importance") or "normal").strip() or "normal"
        message_type = str(payload.get("messageType") or "message").strip() or "message"
        reply_to_id = str(payload.get("replyToId") or "").strip()
        web_url = str(payload.get("webUrl") or "").strip()
        body = payload.get("body") if isinstance(payload.get("body"), dict) else {}
        body_content_type = str(body.get("contentType") or "text").strip() or "text"
        body_content = str(body.get("content") or "").strip()
        body_text = teams_html_body_to_text(body_content) if body_content_type.lower() == "html" else normalize_text_whitespace(html.unescape(body_content))
        from_user_id, from_user_display_name = self._extract_from_user(payload.get("from"))
        captured_at = created_at or datetime.now().astimezone().isoformat(timespec="seconds")
        created_datetime = teams_datetime_to_datetime(captured_at)

        metadata: dict[str, Any] = {
            "team_id": self.team_id,
            "channel_id": self.channel_id,
            "kind": "channel_message",
            "message_id": message_id,
            "reply_to_id": reply_to_id or None,
            "created_at": created_at,
            "last_modified_at": last_modified_at,
            "message_type": message_type,
            "importance": importance,
            "from_user_id": from_user_id,
            "from_user_display_name": from_user_display_name,
            "body_content_type": body_content_type,
        }
        if subject:
            metadata["subject"] = subject
        if summary:
            metadata["summary"] = summary
        if web_url:
            metadata["web_url"] = web_url

        return RawSource(
            id=f"teams:{self.team_id}:{self.channel_id}:{message_id}",
            source_type="teams",
            origin=f"teams:{self.team_id}:{self.channel_id}:{message_id}",
            title=f"Teams message {created_datetime.strftime('%Y-%m-%d %H:%M')}",
            content=self._build_content(
                message_id=message_id,
                created_at=created_at,
                last_modified_at=last_modified_at,
                subject=subject,
                summary=summary,
                importance=importance,
                message_type=message_type,
                reply_to_id=reply_to_id,
                web_url=web_url,
                from_user_id=from_user_id,
                from_user_display_name=from_user_display_name,
                body_content_type=body_content_type,
                body_text=body_text,
            ),
            captured_at=created_at or created_datetime.isoformat(timespec="seconds"),
            metadata=metadata,
        )

    def _extract_from_user(self, from_value: Any) -> tuple[str, str]:
        if not isinstance(from_value, dict):
            return "", ""
        user = from_value.get("user")
        if not isinstance(user, dict):
            return "", ""
        user_id = str(user.get("id") or "").strip()
        display_name = str(user.get("displayName") or "").strip()
        return user_id, display_name

    def _build_content(
        self,
        *,
        message_id: str,
        created_at: str,
        last_modified_at: str,
        subject: str,
        summary: str,
        importance: str,
        message_type: str,
        reply_to_id: str,
        web_url: str,
        from_user_id: str,
        from_user_display_name: str,
        body_content_type: str,
        body_text: str,
    ) -> str:
        lines = [
            f"Teams Team ID: {self.team_id}",
            f"Teams Channel ID: {self.channel_id}",
            f"Message ID: {message_id}",
            f"Created At: {created_at or 'unknown'}",
            f"Last Modified At: {last_modified_at or 'unknown'}",
            f"Subject: {subject or 'none'}",
            f"Summary: {summary or 'none'}",
            f"Importance: {importance or 'normal'}",
            f"Message Type: {message_type or 'message'}",
            f"Reply To ID: {reply_to_id or 'none'}",
            f"From User ID: {from_user_id or 'unknown'}",
            f"From User Display Name: {from_user_display_name or 'unknown'}",
            f"Body Content Type: {body_content_type or 'text'}",
        ]
        if web_url:
            lines.append(f"Web URL: {web_url}")
        lines.extend(["Text:", body_text or "(empty)"])
        return "\n".join(lines)


class SourceAdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, SourceAdapter] = {}

    def register(self, adapter: SourceAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> SourceAdapter:
        adapter = self._adapters.get(name)
        if adapter is None:
            raise typer.BadParameter(f"Unknown source adapter: {name}")
        return adapter

    def list(self) -> list[str]:
        return sorted(self._adapters)


def read_yaml(path: Path) -> Any:
    if not path.exists():
        raise typer.BadParameter(f"Missing required file: {path}")
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def parse_optional_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {"frontmatter": {}, "content": text}
    match = re.match(r"(?s)^---\n(.*?)\n---\n?", text)
    if not match:
        return {"frontmatter": {}, "content": text}
    raw_frontmatter = match.group(1)
    try:
        parsed = yaml.safe_load(raw_frontmatter) or {}
    except yaml.YAMLError:
        return {"frontmatter": {}, "content": text}
    if not isinstance(parsed, dict):
        return {"frontmatter": {}, "content": text}
    return {
        "frontmatter": parsed,
        "content": text[match.end() :].lstrip("\n"),
    }


def source_intelligence_rules_dir() -> Path:
    return REPO_ROOT / ".codex" / "source-intelligence" / "rules"


def rule_file_path(filename: str) -> Path:
    return source_intelligence_rules_dir() / filename


@lru_cache(maxsize=32)
def load_rule_document(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    value = read_yaml(path)
    if not isinstance(value, dict):
        raise typer.BadParameter(f"Invalid source intelligence rule: {path}")
    return value


def load_rule_file(filename: str) -> dict[str, Any]:
    return load_rule_document(str(rule_file_path(filename)))


def load_category_rules() -> dict[str, Any]:
    return load_rule_file("categories.yaml")


def load_noise_rules() -> dict[str, Any]:
    return load_rule_file("noise.yaml")


def load_ai_tool_rules() -> dict[str, Any]:
    return load_rule_file("ai_tools.yaml")


def load_technology_rules() -> dict[str, Any]:
    return load_rule_file("technologies.yaml")


def load_confidence_rules() -> dict[str, Any]:
    return load_rule_file("confidence.yaml")


def load_evidence_rules() -> dict[str, Any]:
    return load_rule_file("evidence.yaml")


def load_sensitive_label_rules() -> dict[str, Any]:
    return load_rule_file("sensitive_labels.yaml")


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


def sanitize_command_error(message: str) -> str:
    sanitized = re.sub(r"\b[A-Z][A-Z0-9_]*=[^\s]+", "[REDACTED_ENV]", message)
    sanitized = re.sub(r"\bgh[pousr]_[A-Za-z0-9_]+\b", "[REDACTED_GITHUB_TOKEN]", sanitized)
    sanitized = re.sub(r"\bgithub_pat_[A-Za-z0-9_]+\b", "[REDACTED_GITHUB_TOKEN]", sanitized)
    sanitized, _ = redact_sensitive_text(sanitized)
    return sanitized.strip()


def build_guard_report(
    *,
    timestamp: str,
    event_path: Path,
    findings: list[dict[str, str]],
    redacted_message: str,
    action_label: str = "add-log",
) -> str:
    grouped: dict[str, int] = {}
    for finding in findings:
        grouped[finding["category"]] = grouped.get(finding["category"], 0) + 1

    summary_lines = [f"- {category}: {count}" for category, count in sorted(grouped.items())]
    detail_lines = [
        f"| {finding['category']} | {finding['replacement']} | line {finding['line']} |"
        for finding in findings
    ]

    return f"""## {timestamp} {action_label} redaction

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


def maybe_write_guard_report(
    *,
    timestamp: str,
    report_date: str,
    event_path: Path,
    findings: list[dict[str, str]],
    redacted_message: str,
    action_label: str,
) -> Path | None:
    if not findings:
        return None
    return append_guard_report(
        build_guard_report(
            timestamp=timestamp,
            event_path=event_path,
            findings=findings,
            redacted_message=redacted_message,
            action_label=action_label,
        ),
        report_date=report_date,
    )


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
                "path": display_path(path),
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


def resolve_optional_input_path(path_text: str, *, root_candidates: list[Path] | None = None) -> Path:
    candidate = Path(path_text).expanduser()
    possible_paths = [candidate]
    if not candidate.is_absolute():
        possible_paths.extend(base / candidate for base in (root_candidates or [ROOT, REPO_ROOT]))
    for path in possible_paths:
        if path.exists():
            return path.resolve()
    return ((root_candidates or [ROOT])[0] / candidate).resolve()


def build_source_adapter_registry(github_repo: str | None = None) -> SourceAdapterRegistry:
    registry = SourceAdapterRegistry()
    registry.register(FileSourceAdapter(DATA_DIR / "raw_sources"))
    registry.register(DailyReportSourceAdapter(DAILY_REPORTS_DIR))
    registry.register(
        UnconfiguredSourceAdapter(
            "slack",
            "Slack adapter requires a channel and token env. Use inspect-slack-source or normalize-slack-source.",
        )
    )
    registry.register(
        UnconfiguredSourceAdapter(
            "teams",
            "Teams adapter requires a team id, channel id, and token env. Use inspect-teams-source or normalize-teams-source.",
        )
    )
    if github_repo:
        registry.register(GitHubSourceAdapter(repo=github_repo))
    else:
        registry.register(
            UnconfiguredSourceAdapter(
                "github",
                "GitHub adapter requires a repository. Use inspect-github-source or normalize-github-source with --repo.",
            )
        )
    return registry


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


def infer_review_date(path: Path, proposal_text: str = "") -> str:
    for candidate in [str(path), proposal_text]:
        match = re.search(r"(20\d{2}-\d{2}-\d{2})", candidate)
        if match:
            return match.group(1)
    return date.today().strftime("%Y-%m-%d")


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
    applied_date = infer_review_date(proposal_path, proposal_text)

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

    applied_dir = SKILL_REVIEWS_APPLIED_DIR / applied_date
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
            "applied_at": applied_date,
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


def build_resume_agent_hook_context(trigger: str) -> dict[str, Any]:
    return {
        "trigger": trigger,
        "status": "design_only",
        "reads": [
            display_path(SOURCE_SYNC_DIR),
            display_path(EVENTS_DIR),
            display_path(GENERATED_DIR / "resume.md"),
            display_path(CHANGELOG_PATH),
        ],
        "contract": {
            "normalizer_scope": "raw source -> canonical event / evidence",
            "resume_agent_scope": "canonical event から resume 向けの選別・要約・反映判断を行う",
            "activation_points": ["generate-md", "issue"],
        },
    }


def run_resume_agent_hook(trigger: str) -> dict[str, Any]:
    # Hook contract only. Resume-oriented filtering is intentionally not executed here yet.
    return build_resume_agent_hook_context(trigger)


def generate_markdown_file() -> Path:
    run_resume_agent_hook("generate-md")
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


def source_rule_list(name: str) -> list[str]:
    merged_rules = {}
    for loader in [load_category_rules, load_technology_rules, load_ai_tool_rules, load_confidence_rules, load_evidence_rules]:
        merged_rules.update(loader())
    value = merged_rules.get(name, [])
    return [str(item) for item in value] if isinstance(value, list) else []


def source_rule_map(name: str) -> dict[str, list[str]]:
    merged_rules = {}
    for loader in [load_category_rules, load_noise_rules, load_evidence_rules]:
        merged_rules.update(loader())
    value = merged_rules.get(name, {})
    if not isinstance(value, dict):
        return {}
    return {
        str(key): [str(item) for item in items]
        for key, items in value.items()
        if isinstance(items, list)
    }


def detect_source_type(path: Path, text: str) -> str:
    lowered = f"{path.name} {text[:200]}".lower()
    if "daily_report:" in str(path) or "daily report" in lowered:
        return "daily_report"
    source_type_keywords = source_rule_map("source_type_keywords")
    for source_type, keywords in source_type_keywords.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return source_type
    return str(load_evidence_rules().get("default_source_type", "text_note"))


def extract_source_date(path: Path, text: str, fallback: str = "") -> str:
    candidates = [
        path.stem,
        path.name,
        text.splitlines()[0] if text.splitlines() else "",
        fallback,
    ]
    for candidate in candidates:
        match = re.search(r"(20\d{2})[-_/](\d{2})[-_/](\d{2})", candidate)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        compact = re.search(r"(20\d{2})(\d{2})(\d{2})", candidate)
        if compact:
            return f"{compact.group(1)}-{compact.group(2)}-{compact.group(3)}"
    if path.exists():
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    return datetime.now().strftime("%Y-%m-%d")


def detect_date_string(value: str) -> str | None:
    if not value:
        return None
    for pattern in [
        r"(20\d{2})[-_/](\d{1,2})[-_/](\d{1,2})",
        r"(20\d{2})(\d{2})(\d{2})",
        r"(20\d{2})年(\d{1,2})月(\d{1,2})日",
    ]:
        match = re.search(pattern, value)
        if not match:
            continue
        year, month, day = match.group(1), match.group(2), match.group(3)
        try:
            return date(int(year), int(month), int(day)).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def detect_daily_report_date(
    path: Path,
    raw_text: str,
    content_text: str,
    frontmatter: dict[str, Any],
    *,
    fallback: str = "",
) -> str:
    frontmatter_date = frontmatter.get("date")
    if isinstance(frontmatter_date, (date, datetime)):
        return frontmatter_date.strftime("%Y-%m-%d")
    if isinstance(frontmatter_date, str):
        detected = detect_date_string(frontmatter_date)
        if detected:
            return detected

    candidates = [path.name, path.stem]
    lines = content_text.splitlines()
    heading_line = next((line.strip() for line in lines if line.strip().startswith("#")), "")
    first_content_line = next((line.strip() for line in lines if line.strip()), "")
    candidates.extend([heading_line, first_content_line, raw_text[:120], fallback])
    for candidate in candidates:
        detected = detect_date_string(str(candidate))
        if detected:
            return detected

    if path.exists():
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    if fallback:
        detected = detect_date_string(fallback)
        if detected:
            return detected
    return datetime.now().strftime("%Y-%m-%d")


def infer_daily_report_kind(path: Path, frontmatter: dict[str, Any], content: str) -> str:
    type_value = frontmatter.get("type")
    if isinstance(type_value, str) and type_value.strip():
        return type_value.strip()

    lowered = f"{path.name}\n{content[:400]}".lower()
    keyword_map = {
        "daily": ["daily", "日報", "今日やったこと"],
        "weekly": ["weekly", "週次"],
        "worklog": ["worklog", "作業ログ", "作業メモ"],
        "retrospective": ["retrospective", "ふりかえり", "振り返り", "kpt"],
        "memo": ["memo", "note", "メモ"],
    }
    for kind, keywords in keyword_map.items():
        if any(keyword in lowered for keyword in keywords):
            return kind
    return "freestyle_report"


def split_source_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        for fragment in re.split(r"[•・;；]", raw_line):
            normalized = re.sub(r"\s+", " ", fragment).strip(" -\t")
            if normalized:
                lines.append(normalized)
    return lines


def detect_noise_categories(text: str) -> list[str]:
    lowered = text.lower()
    noise_keywords = source_rule_map("noise_keywords")
    categories = [
        category
        for category, keywords in noise_keywords.items()
        if any(keyword.lower() in lowered for keyword in keywords)
    ]
    return sorted(set(categories))


def has_work_signal(text: str) -> bool:
    lowered = text.lower()
    if any(keyword.lower() in lowered for keyword in source_rule_list("decision_keywords")):
        return True
    if any(keyword.lower() in lowered for keyword in source_rule_list("improvement_keywords")):
        return True
    category_keywords = source_rule_map("category_keywords")
    if any(keyword.lower() in lowered for keywords in category_keywords.values() for keyword in keywords):
        return True
    if re.search(r"(やった|進めた|進行|対応|実施|修正|見直し|見直した|分離|整理|決めた|決定|受けた|もらった|追加|追加した|試した)", text):
        return True
    return False


def is_noise_only_line(text: str) -> bool:
    lowered = text.lower()
    if not lowered.strip():
        return True
    noise_keywords = source_rule_map("noise_keywords")
    signal_keywords = source_rule_list("tag_keywords") + source_rule_list("tool_keywords")
    if any(keyword.lower() in lowered for keywords in noise_keywords.values() for keyword in keywords):
        has_signal = any(keyword.lower() in lowered for keyword in signal_keywords)
        has_work_term = has_work_signal(text)
        return not (has_signal or has_work_term)
    return False


def detect_category(text: str) -> str:
    lowered = text.lower()
    categories = source_rule_list("categories")
    category_keywords = source_rule_map("category_keywords")
    scores: dict[str, int] = {category: 0 for category in categories}
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword.lower() in lowered:
                scores[category] += 1
    if is_noise_only_line(text):
        return "noise"
    best = max((item for item in scores.items() if item[0] != "noise"), key=lambda item: item[1], default=("communication", 0))
    return best[0] if best[1] > 0 else "communication"


def extract_keyword_matches(text: str, keywords: list[str]) -> list[str]:
    found: list[str] = []
    lowered = text.lower()
    for keyword in keywords:
        if keyword.lower() in lowered:
            found.append(keyword)
    return found


def summarize_line(text: str) -> str:
    summary = re.sub(r"\[[^\]]+\]", "", text).strip()
    return summary[:140]


def collect_focus_terms(text: str, tags: list[str]) -> list[str]:
    tool_keywords = set(source_rule_list("tool_keywords"))
    terms = [tag for tag in tags if tag not in {"PR", "Issue", "GitHub", "Slack"} and tag not in tool_keywords]
    inferred_terms = [
        ("Resolver", "resolver"),
        ("GraphQL", "graphql"),
        ("Connector", "connector"),
        ("Slack", "slack"),
        ("schema", "schema"),
        ("Fragment", "fragment"),
    ]
    lowered = text.lower()
    for label, keyword in inferred_terms:
        if keyword in lowered:
            terms.append(label)
    if "設計" in text:
        terms.append("設計")
    if "リファクタ" in text:
        terms.append("リファクタ")
    return dedupe_preserving_order(terms)


def build_subject_phrase(text: str, tags: list[str]) -> str:
    focus_terms = collect_focus_terms(text, tags)
    if not focus_terms:
        return ""
    if "GraphQL" in focus_terms and "Resolver" in focus_terms:
        return "GraphQL Resolver"
    if "Slack" in focus_terms and "Connector" in focus_terms:
        return "Slack Connector"
    return " / ".join(focus_terms[:2])


def is_low_signal_line(text: str, *, tags: list[str], tools: list[str]) -> bool:
    if not tools:
        return False
    subject = build_subject_phrase(text, tags)
    if subject:
        return False
    if has_work_signal(text):
        return False
    return bool(re.search(r"(便利|聞いた|相談した|試した|メモ|気になる)", text))


def canonicalize_action(text: str, *, category: str, tags: list[str], tools: list[str]) -> str | None:
    subject = build_subject_phrase(text, tags)
    has_pr = "PR" in text or "pr" in text.lower()

    if is_low_signal_line(text, tags=tags, tools=tools):
        return None
    if "指摘" in text and re.search(r"(受けた|もらった|反映)", text):
        prefix = "PRレビューで" if has_pr else ""
        if "設計" in text:
            return f"{prefix}設計指摘を受領"
        return f"{prefix}レビュー指摘を受領"
    if "分離" in text:
        if subject:
            return f"{subject}分離を実施"
        return "責務分離を実施"
    if ("方針" in text or "方針を" in text) and re.search(r"(決めた|決定|整理|見直し)", text):
        if "リファクタ" in text:
            return "リファクタ方針を決定"
        if subject:
            return f"{subject}の方針を決定"
        return "実装方針を決定"
    if "レビュー" in text and re.search(r"(受けた|もらった|実施)", text):
        if has_pr:
            return "PRレビューを実施"
        return "レビュー対応を実施"
    if tools and re.search(r"(聞いた|相談した|整理)", text):
        tool_name = tools[0]
        if subject:
            return f"{tool_name}で{subject}の論点を整理"
        return None
    if subject:
        if category == "design":
            return f"{subject}の設計検討を実施"
        if category == "review":
            return f"{subject}のレビュー対応を実施"
        if category == "refactor":
            return f"{subject}のリファクタリングを実施"
        if category == "learning":
            return f"{subject}の技術調査を実施"
        return f"{subject}関連の実装・調査を実施"
    if category == "review":
        return "レビュー対応を実施"
    if category == "refactor":
        return "リファクタリングを実施"
    if category == "design":
        return "設計検討を実施"
    if category == "testing":
        return "検証を実施"
    if category == "operation":
        return "運用対応を実施"
    if category == "learning":
        return "技術調査を実施"
    return summarize_line(text)


def extract_decision_text(text: str) -> str | None:
    patterns = source_rule_list("decision_keywords")
    if not any(pattern in text for pattern in patterns):
        return None
    if "リファクタ" in text and re.search(r"(方針|決めた|決定)", text):
        return "リファクタ方針を決定"
    return summarize_line(text)


def extract_improvement_text(text: str) -> str | None:
    patterns = source_rule_list("improvement_keywords")
    if not any(pattern in text for pattern in patterns):
        return None
    if "リファクタ" in text:
        return "リファクタリング方針を整理"
    return summarize_line(text)


def confidence_level_from_score(score: int, rules: dict[str, Any]) -> str:
    levels = rules.get("levels", {})
    if not isinstance(levels, dict):
        return "low"
    ordered_levels = sorted(
        (
            (str(level), int(config.get("min_score", 0)))
            for level, config in levels.items()
            if isinstance(config, dict)
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    for level, min_score in ordered_levels:
        if score >= min_score:
            return level
    return "low"


def confidence_signal_value(rules: dict[str, Any], group: str, key: str, default: int = 0) -> int:
    values = rules.get(group, {})
    if not isinstance(values, dict):
        return default
    return int(values.get(key, default))


def known_source_types() -> set[str]:
    return {"file", "github", "slack", "teams", "daily_report"}


def calculate_source_confidence(
    *,
    raw_source: RawSource,
    source_type: str,
    actions: list[str],
    decisions: list[str],
    improvements: list[str],
    tags: list[str],
    tools: list[str],
    noise_removed: list[str],
    evidence_basis: str,
    guard_findings: list[dict[str, str]],
) -> SourceConfidence:
    rules = load_confidence_rules()
    score = 0
    reasons: list[str] = []
    normalized_source_type = source_type if source_type in known_source_types() else "unknown"
    source_type_weights = rules.get("source_type_weights", {})
    if isinstance(source_type_weights, dict):
        score += int(source_type_weights.get(normalized_source_type, source_type_weights.get("unknown", 0)))
    reasons.append(f"source_type:{normalized_source_type}")

    metadata_values = [value for value in raw_source.metadata.values() if value not in ("", None, [], {})]
    if raw_source.id.strip():
        score += confidence_signal_value(rules, "signals", "source_id_present")
        reasons.append("source_id:present")
    else:
        score += confidence_signal_value(rules, "penalties", "missing_source_id")
        reasons.append("source_id:missing")

    if actions:
        score += confidence_signal_value(rules, "signals", "action_present")
        reasons.append(f"actions:{len(actions)}")
        if len(actions) >= 2:
            score += confidence_signal_value(rules, "signals", "action_multiple_bonus")
            reasons.append("actions:multiple")
    else:
        score += confidence_signal_value(rules, "penalties", "no_actions")
        reasons.append("actions:0")

    if decisions:
        score += confidence_signal_value(rules, "signals", "decision_present")
        reasons.append(f"decisions:{len(decisions)}")
    if improvements:
        score += confidence_signal_value(rules, "signals", "improvement_present")
        reasons.append(f"improvements:{len(improvements)}")
    if not decisions and not improvements:
        score += confidence_signal_value(rules, "penalties", "no_decisions_or_improvements")
        reasons.append("decisions_improvements:0")

    if tags:
        score += confidence_signal_value(rules, "signals", "tags_present")
        reasons.append(f"tags:{len(tags)}")
    if tools:
        score += confidence_signal_value(rules, "signals", "tools_present")
        reasons.append(f"tools:{len(tools)}")

    if evidence_basis and evidence_basis != "有意な技術イベントなし":
        score += confidence_signal_value(rules, "signals", "evidence_present")
        reasons.append("evidence:present")
    else:
        score += confidence_signal_value(rules, "penalties", "weak_evidence")
        reasons.append("evidence:weak")

    if metadata_values:
        score += confidence_signal_value(rules, "signals", "metadata_present")
        reasons.append(f"metadata:{len(metadata_values)}")
        if len(metadata_values) >= 5:
            score += confidence_signal_value(rules, "signals", "metadata_rich_bonus")
            reasons.append("metadata:rich")

    if normalized_source_type in {"github", "daily_report"}:
        score += confidence_signal_value(rules, "signals", "structured_source_bonus")
        reasons.append("source:structured")

    if normalized_source_type == "unknown":
        score += confidence_signal_value(rules, "penalties", "unknown_source_type")
        reasons.append("penalty:unknown_source_type")

    if "low_signal" in noise_removed:
        score += confidence_signal_value(rules, "penalties", "low_signal_noise")
        reasons.append("noise:low_signal")
    if len(noise_removed) >= 3:
        score += confidence_signal_value(rules, "penalties", "many_noise_categories")
        reasons.append(f"noise_removed:{len(noise_removed)}")

    if len(guard_findings) >= 3:
        score += confidence_signal_value(rules, "penalties", "redaction_heavy")
        reasons.append(f"redaction_findings:{len(guard_findings)}")

    if len(raw_source.content.strip()) < 20:
        score += confidence_signal_value(rules, "penalties", "short_content")
        reasons.append("content:short")

    score = max(0, min(100, score))
    reasons.append(f"score:{score}")
    return SourceConfidence(
        level=confidence_level_from_score(score, rules),
        score=score,
        reasons=reasons,
    )


def build_source_reference_path(raw_source: RawSource) -> Path:
    origin_path = Path(raw_source.origin)
    if origin_path.exists():
        return origin_path
    source_reference = raw_source.metadata.get("source_reference")
    if isinstance(source_reference, str) and source_reference.strip():
        return Path(source_reference.strip())
    metadata_path = raw_source.metadata.get("path")
    if isinstance(metadata_path, str):
        return Path(metadata_path)
    return Path(raw_source.title or raw_source.id)


def build_canonical_event_from_raw_source(raw_source: RawSource) -> dict[str, Any]:
    source_path = build_source_reference_path(raw_source)
    raw_text = raw_source.content
    redacted_text, findings = redact_sensitive_text(raw_text)
    date_text = extract_source_date(source_path, redacted_text, fallback=raw_source.captured_at)
    source_type = raw_source.source_type or detect_source_type(source_path, redacted_text)
    lines = split_source_lines(redacted_text)

    kept_lines: list[str] = []
    actions: list[str] = []
    decisions: list[str] = []
    improvements: list[str] = []
    tags: list[str] = []
    tools: list[str] = []
    noise_categories: list[str] = []
    categories = source_rule_list("categories")
    category_scores: dict[str, int] = {category: 0 for category in categories}

    for line in lines:
        category = detect_category(line)
        category_scores[category] += 1
        line_noise = detect_noise_categories(line)
        if category == "noise" or is_noise_only_line(line):
            noise_categories.extend(line_noise or ["small_talk"])
            continue

        tags_for_line = extract_keyword_matches(line, source_rule_list("tag_keywords"))
        tools_for_line = extract_keyword_matches(line, source_rule_list("tool_keywords"))
        if not has_work_signal(line) and not tags_for_line and not tools_for_line:
            noise_categories.extend(line_noise or ["low_signal"])
            continue
        action_text = canonicalize_action(line, category=category, tags=tags_for_line, tools=tools_for_line)
        if action_text is None:
            noise_categories.extend(line_noise or ["low_signal"])
            continue

        if line_noise:
            noise_categories.extend(line_noise)

        kept_lines.append(line)
        actions.append(action_text)
        decision = extract_decision_text(line)
        if decision:
            decisions.append(decision)
        improvement = extract_improvement_text(line)
        if improvement:
            improvements.append(improvement)
        tags.extend(tags_for_line)
        tools.extend(tools_for_line)

    dominant_category = max(
        ((name, score) for name, score in category_scores.items() if name != "noise"),
        key=lambda item: item[1],
        default=("communication", 0),
    )[0]
    summary = actions[0] if actions else "作業上有意な技術イベントを抽出できなかった"
    evidence_basis = " / ".join(dedupe_preserving_order(actions[:3] + decisions[:2] + improvements[:2]))
    if not evidence_basis and raw_source.source_type not in {"github", "slack", "teams", "daily_report"}:
        evidence_basis = " / ".join(kept_lines[:3]) if kept_lines else "有意な技術イベントなし"
    if not evidence_basis:
        evidence_basis = "有意な技術イベントなし"
    evidence_excerpt = summarize_line(evidence_basis)[:200]
    confidence = calculate_source_confidence(
        raw_source=raw_source,
        source_type=source_type,
        actions=dedupe_preserving_order(actions),
        decisions=dedupe_preserving_order(decisions),
        improvements=dedupe_preserving_order(improvements),
        tags=dedupe_preserving_order(tags),
        tools=dedupe_preserving_order(tools),
        noise_removed=dedupe_preserving_order(sorted(set(noise_categories))),
        evidence_basis=evidence_basis,
        guard_findings=findings,
    )

    return {
        "schema": str(load_evidence_rules().get("schema", "canonical_event_v0")),
        "date": date_text,
        "source_id": raw_source.id,
        "source_type": source_type,
        "category": dominant_category if kept_lines else "noise",
        "summary": summary,
        "actions": dedupe_preserving_order(actions),
        "decisions": dedupe_preserving_order(decisions),
        "improvements": dedupe_preserving_order(improvements),
        "tags": dedupe_preserving_order(tags),
        "tools": dedupe_preserving_order(tools),
        "noise_removed": dedupe_preserving_order(sorted(set(noise_categories))),
        "confidence": confidence.level,
        "confidence_reasons": confidence.reasons,
        "evidence": [
            {
                "kind": str(load_evidence_rules().get("excerpt_kind", "redacted_excerpt")),
                "detail": evidence_excerpt,
            },
            {
                "kind": str(load_evidence_rules().get("source_reference_kind", "source_reference")),
                "detail": source_path.name,
            },
        ],
        "_guard_findings": findings,
        "_source_path": source_path,
        "_raw_source": raw_source,
    }


def build_canonical_event(source_path: Path) -> dict[str, Any]:
    resolved = source_path.resolve()
    stat = resolved.stat()
    raw_source = RawSource(
        id=resolved.name,
        source_type="file",
        origin=str(resolved),
        title=resolved.name,
        content=resolved.read_text(encoding="utf-8"),
        captured_at=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        metadata={
            "path": str(resolved),
            "size_bytes": stat.st_size,
        },
    )
    return build_canonical_event_from_raw_source(raw_source)


def normalize_raw_sources(
    raw_sources: list[RawSource],
    *,
    action_label: str,
) -> list[Path]:
    grouped_events: dict[str, list[dict[str, Any]]] = {}

    for raw_source in raw_sources:
        event = build_canonical_event_from_raw_source(raw_source)
        grouped_events.setdefault(event["date"], []).append(event)
        maybe_write_guard_report(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            report_date=event["date"],
            event_path=SOURCE_SYNC_DIR / f"{event['date']}.md",
            findings=event["_guard_findings"],
            redacted_message="\n".join(item["detail"] for item in event["evidence"] if item["kind"] == "redacted_excerpt"),
            action_label=action_label,
        )

    output_paths: list[Path] = []
    for target_date, events in sorted(grouped_events.items()):
        output_paths.append(write_source_sync_file(target_date, events))
    return output_paths


def format_canonical_event(event: dict[str, Any]) -> str:
    def render_list(values: list[str]) -> str:
        return "\n".join(f"  - {value}" for value in values) if values else "  - none"

    def render_evidence(items: list[dict[str, str]]) -> str:
        if not items:
            return "  - kind: none\n    detail: none"
        return "\n".join(
            [
                "  - kind: " + str(item.get("kind", "unknown")) + "\n    detail: " + str(item.get("detail", ""))
                for item in items
            ]
        )

    lines = [
        "- schema: " + str(event["schema"]),
        "- date: " + str(event["date"]),
        "  source_id: " + str(event.get("source_id", "unknown")),
        "  source_type: " + str(event["source_type"]),
        "  category: " + str(event["category"]),
        "  summary: " + str(event["summary"]),
        "  actions:",
        render_list(event["actions"]),
        "  decisions:",
        render_list(event["decisions"]),
        "  improvements:",
        render_list(event["improvements"]),
        "  tags:",
        render_list(event["tags"]),
        "  tools:",
        render_list(event["tools"]),
        "  noise_removed:",
        render_list(event["noise_removed"]),
        "  confidence: " + str(event["confidence"]),
        "  confidence_reasons:",
        render_list(event.get("confidence_reasons", [])),
        "  evidence:",
        render_evidence(event["evidence"]),
    ]
    return "\n".join(lines)


def read_source_sync_event_blocks(output_path: Path) -> tuple[str | None, list[str]]:
    if not output_path.exists():
        return None, []
    content = output_path.read_text(encoding="utf-8")
    date_match = re.search(r"(?m)^date:\s*(\d{4}-\d{2}-\d{2})\s*$", content)
    event_matches = list(re.finditer(r"(?m)^## Event \d+\s*$", content))
    if not event_matches:
        return (date_match.group(1) if date_match else None), []
    blocks: list[str] = []
    for index, match in enumerate(event_matches):
        start = match.end()
        end = event_matches[index + 1].start() if index + 1 < len(event_matches) else len(content)
        blocks.append(content[start:end].strip())
    return (date_match.group(1) if date_match else None), blocks


def extract_source_id_from_event_block(block: str) -> str | None:
    match = re.search(r"(?m)^  source_id:\s*(.+?)\s*$", block)
    if not match:
        return None
    source_id = match.group(1).strip()
    return source_id or None


def write_source_sync_file(target_date: str, events: list[dict[str, Any]]) -> Path:
    SOURCE_SYNC_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SOURCE_SYNC_DIR / f"{target_date}.md"
    _, existing_blocks = read_source_sync_event_blocks(output_path)
    existing_source_ids = {source_id for block in existing_blocks if (source_id := extract_source_id_from_event_block(block))}
    merged_blocks = list(existing_blocks)
    for event in events:
        source_id = str(event.get("source_id") or "").strip()
        if source_id and source_id in existing_source_ids:
            continue
        block = format_canonical_event(event)
        merged_blocks.append(block)
        if source_id:
            existing_source_ids.add(source_id)
    body = [
        "# Canonical Events",
        "",
        f"date: {target_date}",
        "",
    ]
    for index, block in enumerate(merged_blocks, start=1):
        body.append(f"## Event {index}")
        body.append(block)
        body.append("")
    output_path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
    return output_path


def normalize_source_file(file_path: str | Path) -> Path:
    source_path = resolve_input_path(str(file_path))
    event = build_canonical_event(source_path)
    output_path = write_source_sync_file(event["date"], [event])
    report_path = maybe_write_guard_report(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        report_date=event["date"],
        event_path=output_path,
        findings=event["_guard_findings"],
        redacted_message="\n".join(item["detail"] for item in event["evidence"] if item["kind"] == "redacted_excerpt"),
        action_label="normalize-source",
    )
    if report_path is not None:
        typer.echo(f"Guard report: {report_path.relative_to(ROOT)}")
    return output_path


def normalize_all_sources() -> list[Path]:
    adapter = build_source_adapter_registry().get("file")
    return normalize_raw_sources(adapter.discover(), action_label="normalize-sources")


def daily_report_root_for_file(path: Path) -> Path:
    resolved = path.resolve()
    reports_root = DAILY_REPORTS_DIR.resolve()
    try:
        resolved.relative_to(reports_root)
        return reports_root
    except ValueError:
        return resolved.parent


def inspect_daily_report_file(file_path: str | Path) -> RawSource:
    resolved = resolve_input_path(str(file_path))
    adapter = DailyReportSourceAdapter(daily_report_root_for_file(resolved))
    return adapter._build_raw_source(resolved)


def normalize_daily_report_file(file_path: str | Path) -> Path:
    raw_source = inspect_daily_report_file(file_path)
    output_paths = normalize_raw_sources([raw_source], action_label="import-daily-report")
    return output_paths[0]


def normalize_daily_reports_dir(directory: str | Path, limit: int | None = None) -> list[Path]:
    resolved_dir = resolve_optional_input_path(
        str(directory),
        root_candidates=[ROOT, REPO_ROOT],
    )
    adapter = DailyReportSourceAdapter(resolved_dir, limit=limit)
    return normalize_raw_sources(adapter.discover(), action_label="import-daily-reports")


def normalize_github_sources(repo: str, limit: int = 20, command_runner: CommandRunner | None = None) -> list[Path]:
    adapter = GitHubSourceAdapter(repo=repo, limit=limit, command_runner=command_runner)
    return normalize_raw_sources(adapter.discover(), action_label="normalize-github-source")


def parse_iso_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone()


def parse_cli_datetime(value: str | None) -> str | None:
    parsed = parse_iso_datetime(value)
    if parsed is None:
        return None
    return slack_datetime_to_api_ts(parsed)


def slack_ts_to_datetime(value: str) -> datetime:
    try:
        timestamp = float(value)
    except ValueError as exc:
        raise SourceAccessError(f"Invalid Slack timestamp: {value}") from exc
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone()


def slack_datetime_to_api_ts(value: datetime) -> str:
    return f"{value.timestamp():.6f}"


def sanitize_slack_error_message(message: str) -> str:
    sanitized = sanitize_command_error(message)
    sanitized = re.sub(r"xox[baprs]-[A-Za-z0-9-]+", "[REDACTED_SLACK_TOKEN]", sanitized)
    return sanitized.strip()


def teams_datetime_to_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SourceAccessError(f"Invalid Teams datetime: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone()


def teams_html_body_to_text(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</?(?:div|p|li|ul|ol|span|body|html)\b[^>]*>", " ", text)
    text = re.sub(r"(?i)</?at\b[^>]*>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return normalize_text_whitespace(text)


def normalize_text_whitespace(value: str) -> str:
    collapsed = re.sub(r"[ \t\r\f\v]+", " ", value)
    collapsed = re.sub(r"\s*\n\s*", "\n", collapsed)
    collapsed = re.sub(r"\n{2,}", "\n", collapsed)
    return collapsed.strip()


def sanitize_graph_error_message(message: str) -> str:
    sanitized = sanitize_command_error(message)
    sanitized = re.sub(r"\beyJ[a-zA-Z0-9_\-]+=*\.[a-zA-Z0-9_\-]+=*(?:\.[a-zA-Z0-9_\-+/=]*)?\b", "[REDACTED_MS_GRAPH_TOKEN]", sanitized)
    return sanitized.strip()


def normalize_slack_sources(
    channel: str,
    *,
    limit: int = 20,
    token_env: str = "SLACK_BOT_TOKEN",
    oldest: str | None = None,
    latest: str | None = None,
    api_caller: SlackApiCaller | None = None,
) -> list[Path]:
    adapter = SlackSourceAdapter(
        channel=channel,
        limit=limit,
        token_env=token_env,
        oldest=oldest,
        latest=latest,
        api_caller=api_caller,
    )
    return normalize_raw_sources(adapter.discover(), action_label="normalize-slack-source")


def normalize_teams_sources(
    team_id: str,
    channel_id: str,
    *,
    limit: int = 20,
    token_env: str = "MS_GRAPH_TOKEN",
    oldest: datetime | None = None,
    latest: datetime | None = None,
    api_caller: GraphApiCaller | None = None,
) -> list[Path]:
    adapter = TeamsSourceAdapter(
        team_id=team_id,
        channel_id=channel_id,
        limit=limit,
        token_env=token_env,
        oldest=oldest,
        latest=latest,
        api_caller=api_caller,
    )
    return normalize_raw_sources(adapter.discover(), action_label="normalize-teams-source")


def issue_resume(title: str, note: str, theme: str = "forest") -> Path:
    run_resume_agent_hook("issue")
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
    report_path = maybe_write_guard_report(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        report_date=today,
        event_path=path,
        findings=findings,
        redacted_message=redacted_message,
        action_label="add-log",
    )
    if report_path is not None:
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


@app.command("normalize-source")
def normalize_source(
    file: str = typer.Option(..., "--file", "-f", help="Raw source text file to normalize."),
) -> None:
    """Normalize one raw source text file into a canonical event markdown file."""
    output_path = normalize_source_file(file)
    typer.echo(f"Normalized source: {output_path.relative_to(ROOT)}")


@app.command("normalize-sources")
def normalize_sources() -> None:
    """Normalize all raw source text files under data/raw_sources/."""
    output_paths = normalize_all_sources()
    if not output_paths:
        typer.echo("No raw source files found.")
        return
    typer.echo(f"Normalized {len(output_paths)} day files")
    for path in output_paths:
        typer.echo(f"- {path.relative_to(ROOT)}")


@app.command("inspect-github-source")
def inspect_github_source(
    repo: str = typer.Option(..., "--repo", help="GitHub repository in owner/name format"),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of pull requests to inspect"),
) -> None:
    """Inspect GitHub pull requests as raw sources."""
    adapter = GitHubSourceAdapter(repo=repo, limit=limit)
    try:
        sources = adapter.discover()
    except SourceAdapterError as exc:
        typer.echo(f"GitHub source inspection failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"adapter: {adapter.name}")
    typer.echo(f"repo: {repo}")
    typer.echo(f"discovered_sources: {len(sources)}")
    for source in sources:
        typer.echo(f"- id: {source.id}")
        typer.echo(f"  title: {source.title}")
        typer.echo(f"  origin: {source.origin}")


@app.command("inspect-daily-report")
def inspect_daily_report(
    file: str = typer.Option(..., "--file", "-f", help="Daily report markdown or text file"),
) -> None:
    """Inspect one daily report as a raw source."""
    try:
        source = inspect_daily_report_file(file)
    except SourceAdapterError as exc:
        typer.echo(f"Daily report inspection failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo("adapter: daily_report")
    typer.echo(f"id: {source.id}")
    typer.echo(f"title: {source.title}")
    typer.echo(f"origin: {source.origin}")
    typer.echo(f"detected_date: {source.metadata.get('detected_date', source.captured_at)}")


@app.command("inspect-daily-reports")
def inspect_daily_reports(
    dir: str = typer.Option(str(DAILY_REPORTS_DIR), "--dir", help="Directory that stores daily reports"),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of reports to inspect"),
) -> None:
    """Inspect daily reports under a directory as raw sources."""
    reports_dir = resolve_optional_input_path(dir, root_candidates=[ROOT, REPO_ROOT])
    adapter = DailyReportSourceAdapter(reports_dir=reports_dir, limit=limit)
    try:
        sources = adapter.discover()
    except SourceAdapterError as exc:
        typer.echo(f"Daily report inspection failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"adapter: {adapter.name}")
    typer.echo(f"reports_dir: {display_path(reports_dir)}")
    typer.echo(f"discovered_sources: {len(sources)}")
    for source in sources:
        typer.echo(f"- id: {source.id}")
        typer.echo(f"  title: {source.title}")
        typer.echo(f"  origin: {source.origin}")


@app.command("inspect-slack-source")
def inspect_slack_source(
    channel: str = typer.Option(..., "--channel", help="Slack channel ID"),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of messages to inspect"),
    token_env: str = typer.Option("SLACK_BOT_TOKEN", "--token-env", help="Environment variable that holds the Slack bot token"),
    oldest: str | None = typer.Option(None, "--oldest", help="Oldest message time in ISO 8601"),
    latest: str | None = typer.Option(None, "--latest", help="Latest message time in ISO 8601"),
) -> None:
    """Inspect Slack messages as raw sources."""
    adapter = SlackSourceAdapter(
        channel=channel,
        limit=limit,
        token_env=token_env,
        oldest=parse_cli_datetime(oldest),
        latest=parse_cli_datetime(latest),
    )
    try:
        sources = adapter.discover()
    except SourceAdapterError as exc:
        typer.echo(f"Slack source inspection failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"adapter: {adapter.name}")
    typer.echo(f"channel: {channel}")
    typer.echo(f"discovered_sources: {len(sources)}")
    for source in sources:
        typer.echo(f"- id: {source.id}")
        typer.echo(f"  title: {source.title}")
        typer.echo(f"  origin: {source.origin}")


@app.command("inspect-teams-source")
def inspect_teams_source(
    team_id: str = typer.Option(..., "--team-id", help="Microsoft Teams team ID"),
    channel_id: str = typer.Option(..., "--channel-id", help="Microsoft Teams channel ID"),
    limit: int = typer.Option(20, "--limit", min=1, max=50, help="Maximum number of messages to inspect"),
    token_env: str = typer.Option("MS_GRAPH_TOKEN", "--token-env", help="Environment variable that holds the Microsoft Graph token"),
    oldest: str | None = typer.Option(None, "--oldest", help="Oldest message time in ISO 8601"),
    latest: str | None = typer.Option(None, "--latest", help="Latest message time in ISO 8601"),
) -> None:
    """Inspect Teams channel messages as raw sources."""
    adapter = TeamsSourceAdapter(
        team_id=team_id,
        channel_id=channel_id,
        limit=limit,
        token_env=token_env,
        oldest=parse_iso_datetime(oldest),
        latest=parse_iso_datetime(latest),
    )
    try:
        sources = adapter.discover()
    except SourceAdapterError as exc:
        typer.echo(f"Teams source inspection failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"adapter: {adapter.name}")
    typer.echo(f"team_id: {team_id}")
    typer.echo(f"channel_id: {channel_id}")
    typer.echo(f"discovered_sources: {len(sources)}")
    for source in sources:
        typer.echo(f"- id: {source.id}")
        typer.echo(f"  title: {source.title}")
        typer.echo(f"  origin: {source.origin}")


@app.command("normalize-github-source")
def normalize_github_source(
    repo: str = typer.Option(..., "--repo", help="GitHub repository in owner/name format"),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of pull requests to normalize"),
) -> None:
    """Normalize GitHub pull requests into canonical event markdown files."""
    try:
        output_paths = normalize_github_sources(repo=repo, limit=limit)
    except SourceAdapterError as exc:
        typer.echo(f"GitHub source normalization failed: {exc}", err=True)
        raise typer.Exit(1)

    if not output_paths:
        typer.echo("No GitHub pull requests found.")
        return
    typer.echo(f"Normalized {len(output_paths)} day files from GitHub")
    for path in output_paths:
        typer.echo(f"- {path.relative_to(ROOT)}")


@app.command("import-daily-report")
def import_daily_report(
    file: str = typer.Option(..., "--file", "-f", help="Daily report markdown or text file"),
) -> None:
    """Normalize one daily report into canonical event markdown."""
    try:
        output_path = normalize_daily_report_file(file)
    except SourceAdapterError as exc:
        typer.echo(f"Daily report import failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Imported daily report: {output_path.relative_to(ROOT)}")


@app.command("import-daily-reports")
def import_daily_reports(
    dir: str = typer.Option(str(DAILY_REPORTS_DIR), "--dir", help="Directory that stores daily reports"),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of reports to import"),
) -> None:
    """Normalize daily reports under a directory into canonical event markdown."""
    try:
        output_paths = normalize_daily_reports_dir(dir, limit=limit)
    except SourceAdapterError as exc:
        typer.echo(f"Daily report import failed: {exc}", err=True)
        raise typer.Exit(1)

    if not output_paths:
        typer.echo("No daily reports found.")
        return
    typer.echo(f"Imported {len(output_paths)} day files from daily reports")
    for path in output_paths:
        typer.echo(f"- {path.relative_to(ROOT)}")


@app.command("normalize-slack-source")
def normalize_slack_source(
    channel: str = typer.Option(..., "--channel", help="Slack channel ID"),
    limit: int = typer.Option(20, "--limit", min=1, help="Maximum number of messages to normalize"),
    token_env: str = typer.Option("SLACK_BOT_TOKEN", "--token-env", help="Environment variable that holds the Slack bot token"),
    oldest: str | None = typer.Option(None, "--oldest", help="Oldest message time in ISO 8601"),
    latest: str | None = typer.Option(None, "--latest", help="Latest message time in ISO 8601"),
) -> None:
    """Normalize Slack messages into canonical event markdown files."""
    try:
        output_paths = normalize_slack_sources(
            channel=channel,
            limit=limit,
            token_env=token_env,
            oldest=parse_cli_datetime(oldest),
            latest=parse_cli_datetime(latest),
        )
    except SourceAdapterError as exc:
        typer.echo(f"Slack source normalization failed: {exc}", err=True)
        raise typer.Exit(1)

    if not output_paths:
        typer.echo("No Slack messages found.")
        return
    typer.echo(f"Normalized {len(output_paths)} day files from Slack")
    for path in output_paths:
        typer.echo(f"- {path.relative_to(ROOT)}")


@app.command("normalize-teams-source")
def normalize_teams_source(
    team_id: str = typer.Option(..., "--team-id", help="Microsoft Teams team ID"),
    channel_id: str = typer.Option(..., "--channel-id", help="Microsoft Teams channel ID"),
    limit: int = typer.Option(20, "--limit", min=1, max=50, help="Maximum number of messages to normalize"),
    token_env: str = typer.Option("MS_GRAPH_TOKEN", "--token-env", help="Environment variable that holds the Microsoft Graph token"),
    oldest: str | None = typer.Option(None, "--oldest", help="Oldest message time in ISO 8601"),
    latest: str | None = typer.Option(None, "--latest", help="Latest message time in ISO 8601"),
) -> None:
    """Normalize Teams channel messages into canonical event markdown files."""
    try:
        output_paths = normalize_teams_sources(
            team_id=team_id,
            channel_id=channel_id,
            limit=limit,
            token_env=token_env,
            oldest=parse_iso_datetime(oldest),
            latest=parse_iso_datetime(latest),
        )
    except SourceAdapterError as exc:
        typer.echo(f"Teams source normalization failed: {exc}", err=True)
        raise typer.Exit(1)

    if not output_paths:
        typer.echo("No Teams messages found.")
        return
    typer.echo(f"Normalized {len(output_paths)} day files from Teams")
    for path in output_paths:
        typer.echo(f"- {path.relative_to(ROOT)}")


@app.command("list-source-adapters")
def list_source_adapters() -> None:
    """List registered source adapters."""
    registry = build_source_adapter_registry()
    for adapter_name in registry.list():
        typer.echo(adapter_name)


@app.command("inspect-source-adapter")
def inspect_source_adapter(
    adapter: str = typer.Option(..., "--adapter", help="Source adapter name"),
) -> None:
    """Inspect a registered source adapter and its discovered sources."""
    source_adapter = build_source_adapter_registry().get(adapter)
    try:
        sources = source_adapter.discover()
    except SourceAdapterError as exc:
        typer.echo(f"Source adapter inspection failed: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"adapter: {source_adapter.name}")
    typer.echo(f"discovered_sources: {len(sources)}")
    if not sources:
        return
    for source in sources:
        typer.echo(f"- id: {source.id}")
        typer.echo(f"  title: {source.title}")
        typer.echo(f"  origin: {source.origin}")


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
