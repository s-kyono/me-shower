---
name: run-release-gate
version: "1.0"
interface: execute
responsibility: single
---

# RunReleaseGate

## Purpose

Review accepted済みの実装について、必須検証、安全境界、機密情報・個人情報・raw source非混入、Design Lock整合、Git差分範囲を確認し、公開可否を最終判定する。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- RepositoryとStateを変更しない。
- 他Skillを直接呼び出さない。
- `passed`、`failed`、`blocked`のいずれかを返す。
- Gate中にコードを修正しない。

## Inputs

- `design_lock`
- `accepted_review`
- `implementation_diff`
- `changed_files`
- `required_validations`
- `repository_status`
- `git_status`

## Outputs

- `gate_result`
- `precondition_results`
- `test_results`
- `static_validation_results`
- `secret_scan_result`
- `privacy_scan_result`
- `raw_source_scan_result`
- `design_lock_alignment`
- `publish_scope_result`
- `known_failures`
- `remaining_risks`
- `release_gate_document_content`
- `state_patch`

## Gate Result

Exactly one:

- `passed`
- `failed`
- `blocked`

## Required Checks

- latest Review is accepted
- focused and required full tests
- lint, formatter, schema validation, diff checks where applicable
- required smoke and negative cases
- secret and credential scan
- personal and private information scan
- raw source and derived-data leakage scan
- logs, fixtures, exceptions, generated artifacts inspection
- Design Lock alignment
- forbidden-path and unrelated-change inspection
- staged/publish scope readiness

## Responsibilities

- 実行した検証方法と対象Pathを記録する
- 除外Pathがある場合は理由を記録する
- false positiveの扱いを記録する
- Known FailureとRemaining Riskを区別する
- 公開可否を機械的に判定する
- RELEASE_GATE.md用の内容を生成する

## Non-responsibilities

- コード、テスト、ドキュメントを修正しない
- Reviewをやり直さない
- Findingを都合よく無視しない
- secret、個人情報、raw source混入をAccepted Riskにしない
- commit、push、PR作成を行わない

## Decision Rules

- secret detected: `failed`
- personal/private information detected: `failed`
- raw source detected: `failed`
- scan unavailable or incomplete: `blocked`
- Design Lock blocking deviation: `blocked`
- required validation failed: `failed`
- unrelated changes detected: `blocked`
- all required checks passed: `passed`

## Blocking Conditions

- Review acceptedを確認できない
- 必須検証やscanを実行できない
- 検証対象Pathを確定できない
- Design Lock照合不能
- Git差分が不明またはunrelated変更を含む
- 機密・個人・raw source検出結果を安全に記録できない

## State Patch Boundary

This Skill may only propose changes under:

- `/state`
- `/execution/current_skill`
- `/release_gate/result`
- `/release_gate/reference`
- `/release_gate/checks`
- `/release_gate/remaining_risks`
- `/warnings`
- `/blocking_issues`

The Skill must not modify implementation files or fix attempt counters.

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "run-release-gate"
  version: "1.0"
execution:
  status: "completed | failed | blocked"
  summary: "..."
output:
  gate_result: "passed | failed | blocked"
state_patch: null
human_interaction:
  required: false
  reason: null
  allowed_actions: []
warnings: []
blocking_issues: []
deviations: []
diagnostics:
  references: []
extensions: {}
```

## Invariants

- Release Gate passes before publish.
- Secret, privacy, and raw-source scans fail closed.
- Security and reproducibility take priority over performance.
- Gate validates and decides; it never fixes.
