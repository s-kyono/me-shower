---
name: review-implementation
version: "1.0"
interface: execute
responsibility: single
---

# ReviewImplementation

## Purpose

現在の実装差分をDesign Lock、Invariants、Acceptance Criteria、実行結果に照らして独立に1回評価し、`accepted`、`changes_required`、`blocked`のいずれかを返す。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- RepositoryとStateを変更しない。
- 他Skillを直接呼び出さない。
- Blocking Issueを返せる。
- 修正・再提出回数を所有しない。

## Inputs

- `plan_reference`
- `design_lock`
- `related_adrs`
- `implementation_diff`
- `changed_files`
- `focused_validation_results`
- `previous_review_reference (optional)`

## Outputs

- `review_result`
- `summary`
- `design_lock_alignment`
- `verified_boundaries`
- `findings`
- `trade_off_assessment`
- `validation_performed`
- `remaining_risks`
- `review_document_content`
- `state_patch`

## Review Result

Exactly one:

- `accepted`
- `changes_required`
- `blocked`

## Review Priorities

1. Security
2. Reproducibility and operational stability
3. Maintainability and boundary clarity
4. Performance
5. Delivery speed and implementation size

## Responsibilities

- 実差分を確認する
- `.codex/tools/repository_snapshot/build_snapshot.py`でReview対象Snapshotを生成し、implementation revisionとreviewed diff hashを記録する
- 必要なテストや再現を独立して実行する
- Design Lock、ADR、Acceptance Criteriaとの整合を確認する
- source of truth、Evidence、Human Review、persistence、安全境界を確認する
- Findingを根拠・影響・必要修正とともに示す
- パフォーマンスを含むTrade-offを明示する
- 許容したTrade-offとRevisit Triggerを記録する
- REVIEW.md用の1回分の判定内容を生成する

## Non-responsibilities

- 実装を修正しない
- 再レビューを自分で呼び出さない
- 修正回数や残り回数を管理しない
- Plan、ADR、Design Lockを変更しない
- Release可否を判定しない
- Security、secret、privacy、raw source、source of truth、Human Review境界違反をAccepted Trade-offにしない

## Finding Categories

- `security`
- `privacy`
- `raw_source`
- `source_of_truth`
- `human_review`
- `design_lock`
- `correctness`
- `reproducibility`
- `operational_stability`
- `maintainability`
- `performance`
- `test_coverage`
- `documentation`

## Blocking Conditions

- secret、credential、個人情報、raw sourceを検出した
- source of truth、persistence、Safety Gate、Human Review境界違反がある
- Design Lockを越える修正が必要
- 差分または検証結果を確認できない
- Review対象外のunrelated変更が混入している
- 検証不能で判定根拠を作れない
- 共通Snapshot Toolを実行できない、または`unexpected_files`が存在する

## State Patch Boundary

This Skill may only propose changes under:

- `/state`
- `/execution/current_skill`
- `/review/latest_result`
- `/review/latest_artifact`
- `/review/implementation_revision`
- `/review/reviewed_snapshot_hash`
- `/warnings`
- `/blocking_issues`

The Skill must not modify fix attempt counters.
Findings、remaining risks、Review本文は`REVIEW.md` Artifactへ保存し、Execution Stateへ複製しない。

Requested transitions:

- `implementation_completed` → `review_accepted`
- `implementation_completed` → `changes_required`
- `implementation_completed` → `blocked`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "review-implementation"
  version: "1.0"
execution:
  status: "completed | failed | blocked"
  summary: "..."
output:
  review_result: "accepted | changes_required | blocked"
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

- Reviewer performs one independent evaluation per invocation.
- Reviewer does not own the fix cycle.
- Evidence before Claims applies to every finding.
- Security and reproducibility take priority over performance.
- Validation fails closed.
