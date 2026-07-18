---
name: inspect-execution-context
version: "1.0"
interface: execute
responsibility: single
---

# InspectExecutionContext

## Purpose

承認済みPlan、ADR、Design Lock、Execution State、Repository、Git状態を確認し、安全に実装開始できる最小Execution Contextへ圧縮する。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- `execution-state.yaml`を直接変更しない。
- 他Skillを直接呼び出さない。
- Blocking Issueを返せる。
- Repositoryを変更しない。

## Inputs

- `epic_id`
- `repository_root`
- `base_branch`
- `working_branch`
- `plan_path`
- `design_lock_path`
- `adr_paths`
- `execution_state`

## Outputs

- `execution_contract_summary`
- `implementation_scope`
- `non_goals`
- `allowed_changes`
- `forbidden_changes`
- `acceptance_mapping`
- `required_validations`
- `repository_status`
- `git_status`
- `known_constraints`
- `known_unknowns`
- `state_patch`
- `context_artifact_content`

## Responsibilities

- Plan、ADR、Design Lockの存在と承認状態を確認する
- Design Lock revisionとExecution State参照の整合を確認する
- current branch、base branch、remote、working treeを確認する
- unrelatedな未コミット差分を検出する
- 実装対象・禁止対象・必須検証を簡潔にまとめる
- 実装開始を妨げる問題をBlocking Issueとして返す

## Non-responsibilities

- 実装しない
- Design Lockを補完・変更しない
- PlanやADRを再解釈してScopeを増やさない
- Git操作を行わない
- 機密情報やraw source本文をContextへ転記しない

## Blocking Conditions

- accepted PlanまたはDesign Lockが存在しない
- Plan、ADR、Design Lock間に重大な矛盾がある
- Design Lock revisionがExecution Stateと一致しない
- base branchまたはworking branchを特定できない
- unrelatedな未コミット変更が存在する
- Git conflictが存在する
- secret、credential、個人情報、raw source混入を検出した
- 必要な検証手段を確認できない

## State Patch Boundary

This Skill may only propose changes under:

- `/state`
- `/execution/current_skill`
- `/execution/context/artifact`
- `/execution/context/repository_revision`
- `/execution/context/design_lock_revision`
- `/warnings`
- `/blocking_issues`

Repository Context、allowed/forbidden changes、validation detailsはSkill OutputとContext Artifactへ保存し、Execution Stateへ本文を複製しない。

Requested transition: `execution_started` → `execution_context_ready`.

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "inspect-execution-context"
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
- Validation fails closed.
- Raw source, secrets, credentials, and private data are not persisted.
- State mutation is Interface-owned.
