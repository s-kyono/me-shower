---
name: implement
version: "1.0"
interface: execute
responsibility: single
---

# Implement

## Purpose

Design Lockで固定されたScope、Architecture、Data Boundary、Acceptance Mappingに従って実装し、必要なテストと最小限の関連ドキュメントを更新する。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- `execution-state.yaml`を直接変更しない。
- 他Skillを直接呼び出さない。
- Blocking IssueとDeviationを返せる。
- Review、Release判定、Git公開を行わない。

## Inputs

- `execution_context`
- `plan_reference`
- `design_lock`
- `related_adrs`
- `repository_root`
- `working_branch`
- `existing_diff`
- `required_validations`

## Outputs

- `implementation_summary`
- `changed_files`
- `added_files`
- `removed_files`
- `tests_added_or_updated`
- `focused_validation_results`
- `recorded_deviations`
- `unresolved_items`
- `state_patch`
- `implementation_artifact_content`

## Responsibilities

- Design Lock内の実装を完了する
- Acceptance Criteriaを検証可能にするテストを追加・更新する
- セキュリティ、再現性、安定稼働をパフォーマンスより優先する
- Scope内で必要な最小リファクタリングだけを行う
- 実装後にfocused testsと差分確認を実行する
- Design Lock内の軽微な差異をRecorded Deviationとして返す

## Non-responsibilities

- Plan、ADR、Design Lockを変更しない
- Scopeを追加しない
- public API、外部依存、persistence、source of truth、Safety Gate、Human Review境界を再決定しない
- 自分の実装をReview acceptedと判定しない
- Release Gateを通さない
- commit、push、PR作成を行わない
- unrelated refactoringを行わない

## Autonomous Decisions

- private関数名
- private helperの分割
- internal typeの追加
- fixture名とテスト内部構成
- Scope内のエラーメッセージ
- Acceptance Criteriaを補強する追加テスト

## Blocking Conditions

- Design Lockを越えないと実装できない
- public APIの重大変更が必要
- 外部依存追加が必要
- persistence、source of truth、Safety Gate、Human Review境界の変更が必要
- secret、credential、個人情報、raw sourceの保存が必要になる
- unrelated変更やGit conflictにより安全に編集できない
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

The Skill must not modify fix attempt counters.
Implementation summary、validation log、diff本文、deviationsはSkill OutputとImplementation Artifactへ保存する。

Requested transition: `execution_context_ready` → `implementation_completed`.

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "implement"
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

- Execution stays within Design Lock.
- Security and reproducibility take priority over performance.
- Raw source, secrets, credentials, and private data are not persisted.
- Generated output is derived, not canonical.
- Validation fails closed.
