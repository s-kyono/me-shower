from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import os
import re
import tempfile
from typing import Any, Callable, Generic, TypeVar

import yaml


GATE_VERSION = "real_data_ingestion_safety_gate_v0_5"
OUTCOMES = frozenset({"pass", "pass_with_sanitization", "blocked"})
SUPPORTED_CATEGORIES = frozenset({
    "credential", "source_raw_content", "unknown_sensitive_candidate", "email", "phone",
    "ip_address", "private_url", "local_absolute_path", "personal_identifier",
    "organization_internal_identifier",
})
SUPPORTED_ACTIONS = frozenset({"block", "sanitize", "sanitize_or_block", "sanitize_or_manual_cleanup"})
_CONSTRUCTION_TOKEN = object()
T = TypeVar("T")


class IngestionSafetyError(Exception):
    """A deliberately non-sensitive fail-closed ingestion error."""


class IngestionSafetyBlockedError(IngestionSafetyError):
    pass


@dataclass(frozen=True)
class SafetyFinding:
    category: str
    action: str
    field_path: str
    rule_id: str
    confidence: str


@dataclass(frozen=True)
class SafetyAuditReport:
    gate_version: str
    rule_version: str
    finding_counts: dict[str, int]
    blocked_categories: list[str]
    sanitized_categories: list[str]
    raw_value_included: bool = False


class SanitizedContent(Generic[T]):
    __slots__ = ("_value",)

    def __init__(self, value: T, token: object | None = None) -> None:
        if token is not _CONSTRUCTION_TOKEN:
            raise TypeError("SanitizedContent can only be created by the safety gate.")
        self._value = value

    def unwrap(self) -> T:
        return self._value

    def __repr__(self) -> str:
        return "SanitizedContent(<safe-value>)"


class PersistableText:
    __slots__ = ("_value",)

    def __init__(self, value: str, token: object | None = None) -> None:
        if token is not _CONSTRUCTION_TOKEN:
            raise TypeError("PersistableText can only be created by the safety gate.")
        self._value = value

    def _unwrap_for_atomic_write(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "PersistableText(<safe-text>)"


@dataclass(frozen=True, init=False)
class SafetyGateResult:
    outcome: str
    sanitized_content: SanitizedContent[Any] | None
    findings: tuple[SafetyFinding, ...]
    audit_report: SafetyAuditReport

    def __init__(
        self, outcome: str, sanitized_content: SanitizedContent[Any] | None,
        findings: tuple[SafetyFinding, ...], audit_report: SafetyAuditReport,
        token: object | None = None,
    ) -> None:
        if token is not _CONSTRUCTION_TOKEN:
            raise TypeError("SafetyGateResult can only be created by the safety gate.")
        if outcome not in OUTCOMES:
            raise IngestionSafetyError("Safety gate produced an invalid outcome.")
        if (outcome == "blocked") != (sanitized_content is None):
            raise IngestionSafetyError("Safety gate produced an invalid content state.")
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "sanitized_content", sanitized_content)
        object.__setattr__(self, "findings", findings)
        object.__setattr__(self, "audit_report", audit_report)


@dataclass(frozen=True)
class DetectionRule:
    category: str
    rule_id: str
    action: str
    placeholder: str | None
    confidence: str
    pattern: re.Pattern[str]


def _pattern_contracts() -> list[tuple[str, str, str, re.Pattern[str]]]:
    flags = re.IGNORECASE
    return [
        ("credential", "credential.authorization", "high", re.compile(r"\bAuthorization\s*:\s*(?:Bearer|Basic)\s+[^\s]+", flags)),
        ("credential", "credential.bearer", "high", re.compile(r"\bBearer\s+[A-Za-z0-9_./+\-=]{8,}", flags)),
        ("credential", "credential.named_value", "high", re.compile(r"\b(?:api[_ -]?key|token|password|passwd|secret|client[_ -]?secret|aws_secret_access_key)\s*[:=]\s*[\"']?[^\s\"']{8,}", flags)),
        ("credential", "credential.known_prefix", "high", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{8,}|github_pat_[A-Za-z0-9_]{8,}|xox[baprs]-[A-Za-z0-9-]{8,}|AKIA[A-Z0-9]{12,})\b")),
        ("unknown_sensitive_candidate", "unknown.explicit_high_risk", "high", re.compile(r"\b(?:TEST_ONLY_)?UNKNOWN_(?:HIGH_)?RISK(?:_[A-Z0-9_]+)?\b", flags)),
        ("email", "email.address", "high", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags)),
        ("phone", "phone.number", "medium", re.compile(r"(?<!\d)(?:\+\d{1,3}[ -]\d{2,4}(?:[ -]\d{2,4}){1,3}|0\d{1,4}-\d{1,4}-\d{4}|\(\d{2,4}\)[ -]\d{3,4}[ -]\d{3,4}|\d{3}[ -]\d{3}[ -]\d{4})(?!\d)")),
        ("ip_address", "ip.ipv4", "high", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
        ("ip_address", "ip.ipv6", "medium", re.compile(r"(?<![\w:])(?:[A-F0-9]{1,4}:){2,7}[A-F0-9]{0,4}(?![\w:])", flags)),
        ("private_url", "url.private_or_signed", "high", re.compile(r"https?://[^\s)\]>]*(?:localhost|127\.0\.0\.1|intranet|private|internal|\.local\b|\.corp\b|token=|signature=|x-amz-(?:signature|credential)=|access_token=)[^\s)\]>]*", flags)),
        ("local_absolute_path", "path.local_absolute", "high", re.compile(r"(?<![\w.])(?:/(?:Users|home)/[^\s:;,]+|[A-Z]:\\Users\\[^\s:;,]+)", flags)),
        ("personal_identifier", "identifier.explicit_person", "medium", re.compile(r"(?im)\b(?:person|employee|user|account|社員|氏名|ユーザー|アカウント)[ _-]?(?:name|id|名|番号)?\s{0,3}[:=]\s{0,3}[A-Za-z0-9_\-一-龠々ぁ-んァ-ヶ]{2,}")),
        ("organization_internal_identifier", "identifier.explicit_internal", "medium", re.compile(r"(?im)\b(?:internal|customer|client|project|channel|tenant|顧客|案件|社内)[ _-]?(?:name|id|名|番号)?\s{0,3}[:=]\s{0,3}[A-Za-z0-9_\-一-龠々ぁ-んァ-ヶ]{2,}")),
    ]


def load_safety_contract(path: Path) -> dict[str, Any]:
    failed = False
    document: Any = None
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        failed = True
    if failed:
        raise IngestionSafetyError("Safety rules could not be loaded; persistence was denied.")
    if not isinstance(document, dict) or not isinstance(document.get("version"), str):
        raise IngestionSafetyError("Safety rules are invalid; persistence was denied.")
    if set(document.get("outcomes", [])) != OUTCOMES:
        raise IngestionSafetyError("Safety outcomes are invalid; persistence was denied.")
    categories = document.get("protected_categories")
    if not isinstance(categories, dict) or set(categories) != SUPPORTED_CATEGORIES:
        raise IngestionSafetyError("Safety category contract is invalid; persistence was denied.")
    for category, config in categories.items():
        if not isinstance(config, dict) or config.get("default_action") not in SUPPORTED_ACTIONS:
            raise IngestionSafetyError("Safety action contract is invalid; persistence was denied.")
        action = str(config["default_action"])
        if action != "block" and not isinstance(config.get("placeholder"), str):
            raise IngestionSafetyError("Safety placeholder contract is invalid; persistence was denied.")
    return document


def _compiled_rules(contract: dict[str, Any]) -> list[DetectionRule]:
    categories = contract["protected_categories"]
    rules: list[DetectionRule] = []
    for category, rule_id, confidence, pattern in _pattern_contracts():
        config = categories[category]
        configured_action = str(config["default_action"])
        action = "block" if configured_action == "block" else "sanitize"
        rules.append(DetectionRule(category, rule_id, action, config.get("placeholder"), confidence, pattern))
    return rules


def _validate_findings(findings: list[SafetyFinding], contract: dict[str, Any]) -> None:
    categories = contract["protected_categories"]
    for finding in findings:
        if finding.category not in categories or finding.action not in {"block", "sanitize"}:
            raise IngestionSafetyError("Detector returned an unsupported safety finding; persistence was denied.")
        expected = "block" if categories[finding.category]["default_action"] == "block" else "sanitize"
        if finding.action != expected:
            raise IngestionSafetyError("Detector action conflicts with safety policy; persistence was denied.")


def _sanitize_text(value: str, field_path: str, rules: list[DetectionRule]) -> tuple[str, list[SafetyFinding], bool]:
    sanitized = value
    findings: list[SafetyFinding] = []
    blocked = False
    for rule in rules:
        if rule.placeholder and sanitized == rule.placeholder:
            continue
        matches = list(rule.pattern.finditer(sanitized))
        if not matches:
            continue
        findings.extend(SafetyFinding(rule.category, rule.action, field_path, rule.rule_id, rule.confidence) for _ in matches)
        if rule.action == "block":
            blocked = True
        else:
            sanitized = rule.pattern.sub(rule.placeholder or "", sanitized)
    return sanitized, findings, blocked


def _walk(value: Any, field_path: str, rules: list[DetectionRule]) -> tuple[Any, list[SafetyFinding], bool]:
    if isinstance(value, str):
        return _sanitize_text(value, field_path, rules)
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        findings: list[SafetyFinding] = []
        blocked = False
        for key, item in value.items():
            child, child_findings, child_blocked = _walk(item, f"{field_path}.{key}", rules)
            result[str(key)] = child
            findings.extend(child_findings)
            blocked = blocked or child_blocked
        return result, findings, blocked
    if isinstance(value, list):
        result_list: list[Any] = []
        findings: list[SafetyFinding] = []
        blocked = False
        for index, item in enumerate(value):
            child, child_findings, child_blocked = _walk(item, f"{field_path}[{index}]", rules)
            result_list.append(child)
            findings.extend(child_findings)
            blocked = blocked or child_blocked
        return result_list, findings, blocked
    return value, [], False


def inspect_before_persistence(
    content: Any, *, rule_path: Path, persistence_intent: str = "sanitized",
    detector: Callable[[Any, str, list[DetectionRule]], tuple[Any, list[SafetyFinding], bool]] | None = None,
) -> SafetyGateResult:
    contract = load_safety_contract(rule_path)
    rules = _compiled_rules(contract)
    failed = False
    sanitized: Any = None
    findings: list[SafetyFinding] = []
    blocked = False
    try:
        sanitized, findings, blocked = (detector or _walk)(content, "$", rules)
    except Exception:
        failed = True
    if failed:
        raise IngestionSafetyError("Safety inspection failed; persistence was denied.")
    _validate_findings(findings, contract)
    if persistence_intent == "raw":
        findings.append(SafetyFinding("source_raw_content", "block", "$", "source.raw_persistence_request", "high"))
        blocked = True
    elif persistence_intent != "sanitized":
        raise IngestionSafetyError("Safety persistence intent is invalid; persistence was denied.")
    counts = dict(sorted(Counter(item.category for item in findings).items()))
    audit = SafetyAuditReport(
        GATE_VERSION, str(contract["version"]), counts,
        sorted({item.category for item in findings if item.action == "block"}),
        sorted({item.category for item in findings if item.action == "sanitize"}),
    )
    outcome = "blocked" if blocked else ("pass_with_sanitization" if findings else "pass")
    if not blocked:
        recheck_failed = False
        rechecked: Any = None
        remaining: list[SafetyFinding] = []
        recheck_blocked = False
        try:
            rechecked, remaining, recheck_blocked = _walk(sanitized, "$", rules)
        except Exception:
            recheck_failed = True
        if recheck_failed:
            raise IngestionSafetyError("Sanitized output recheck failed; persistence was denied.")
        _validate_findings(remaining, contract)
        if recheck_blocked or remaining or rechecked != sanitized:
            raise IngestionSafetyError("Sanitized output did not pass reinspection; persistence was denied.")
    wrapped = None if blocked else SanitizedContent(sanitized, _CONSTRUCTION_TOKEN)
    return SafetyGateResult(outcome, wrapped, tuple(findings), audit, _CONSTRUCTION_TOKEN)


def require_persistable(result: SafetyGateResult) -> SanitizedContent[Any]:
    if not isinstance(result, SafetyGateResult) or result.outcome not in {"pass", "pass_with_sanitization"}:
        raise IngestionSafetyBlockedError("Safety gate blocked persistence.")
    if not isinstance(result.sanitized_content, SanitizedContent):
        raise IngestionSafetyBlockedError("Safety gate did not produce persistable content.")
    return result.sanitized_content


def inspect_text_for_persistence(content: str, *, rule_path: Path) -> PersistableText:
    wrapped = require_persistable(inspect_before_persistence(content, rule_path=rule_path))
    value = wrapped.unwrap()
    if not isinstance(value, str):
        raise IngestionSafetyError("Persistence content is not text; persistence was denied.")
    return PersistableText(value, _CONSTRUCTION_TOKEN)


def _atomic_write_verified_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    failed = False
    try:
        descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        temporary_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except Exception:
        failed = True
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    if failed:
        raise IngestionSafetyError("Atomic persistence failed; no input was retained.")


def persist_text_safely(path: Path, content: str | PersistableText, *, rule_path: Path) -> None:
    """The only public persistence boundary: recheck the current value immediately before writing."""
    if isinstance(content, PersistableText):
        current_value = content._unwrap_for_atomic_write()
    elif isinstance(content, str):
        current_value = content
    else:
        raise TypeError("persist_text_safely requires text or PersistableText.")
    verified = inspect_text_for_persistence(current_value, rule_path=rule_path)
    immutable_verified_value = str(verified._unwrap_for_atomic_write())
    _atomic_write_verified_text(path, immutable_verified_value)
