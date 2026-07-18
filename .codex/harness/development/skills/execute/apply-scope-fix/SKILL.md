---
name: apply-scope-fix
version: "1.0"
interface: execute
responsibility: single
---

# ApplyScopeFix

## Purpose

最新Reviewで明示されたFindingだけを対象に、Design Lockと既存Scopeを維持したまま実装を修正し、再提出可能な状態へ戻す。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- `execution-state.yaml`を直接変更しない。
- 他Skillを直接呼び出さない。
- Blocking IssueとDeviationを返せる。
- fix attempt countを変更しない。

## Inputs

- `design_lock`
- `latest_review`
- `review_findings`
- `current_diff`
- `changed_files`
- `required_validations`

## Outputs

- `fix_summary`
- `addressed_findings`
- `unresolved_findings`
- `changed_files`
- `regression_tests_added_or_updated`
- `focused_validation_results`
- `recorded_deviations`
- `state_patch`

## Responsibilities

- Review Findingを1件ずつ追跡可能に修正する
- Findingの再現テストまたは回帰テストを追加する
- Scope内で必要な最小変更だけを行う
- 修正後のfocused validationを実行する
- 解消できないFindingを明示する
- Design Lock内の軽微な差異をRecorded Deviationとして返す

## Non-responsibilities

- 指摘されていない改善を追加しない
- unrelated refactoringを行わない
- Review結果を書き換えない
- Reviewerを直接呼び出さない
- 修正・再提出回数を管理しない
- Plan、ADR、Design Lockを変更しない
- Release Gate、Git公開、PR作成を行わない

## Blocking Conditions

- Finding解消にDesign Lock変更が必要
- Scope追加、public API変更、外部依存追加が必要
- source of truth、persistence、Safety Gate、Human Review境界変更が必要
- secret、credential、個人情報、raw sourceを安全に除去できない
- Findingと実差分の対応を確認できない
- focused validationを実行できない

## State Patch Boundary

This Skill may only propose changes under:

- `/state`
- `/execution/current_skill`
- `/execution/implementation/artifact`
- `/execution/implementation/revision`
- `/execution/implementation/changed_files`
- `/execution/implementation/snapshot_hash`
- `/warnings`
- `/blocking_issues`

The Execute Interface, not this Skill, increments fix attempt count.
Fix summary、addressed/unresolved findings、validation log、deviationsはSkill Outputと更新Implementation Artifactへ保存する。Review resultを変更しない。

Requested transition: `fixing` → `implementation_completed`.

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "apply-scope-fix"
  version: "1.0"
execution:
  status: "completed | partial | failed | blocked"
  summary: "..."
output: {}
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

- Fixes address explicit findings only.
- Execution stays within Design Lock.
- Security and reproducibility take priority over performance.
- Raw source, secrets, credentials, and private data are not persisted.
- Validation fails closed.
