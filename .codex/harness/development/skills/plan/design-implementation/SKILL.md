---
name: design-implementation
version: "1.0"
interface: plan
responsibility: single
---

# DesignImplementation

## Purpose

Accepted Planを、Executeが迷わず自律実行できる実装方針・境界・検証戦略へ具体化する。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- `plan-state.yaml`を直接変更しない。
- 他Skillを直接呼び出さない。
- Blocking Issueを返せる。
- AI提案とHuman Decisionを区別する。

## Inputs

- `accepted_plan`
- `accepted_adrs`
- `repository_context`
- `invariants`
- `design_lock_template`

## Outputs

- `implementation_design`
- `component_boundaries`
- `data_type_boundaries`
- `change_boundaries`
- `verification_mapping`
- `deviation_policy`
- `state_patch`

## Responsibilities

- Module・責務・依存方向・Integration Pointを具体化する
- Allowed・Conditional・Forbidden Changesを定義する
- Acceptance Criteriaを検証手段へ写像する
- 自律判断とBlocking Deviationを分離する

## Non-responsibilities

- コードを実装しない
- Accepted PlanのScopeを変更しない
- ADRを勝手に変更しない
- 人間の代わりにDesign Lockを承認しない

## Blocking Conditions

- Planを満たすにはScope変更が必要
- 外部依存追加など未承認Decisionが必要
- Source of TruthまたはPersistence境界が確定できない
- 検証不能なAcceptance Criteriaがある

## State Patch Boundary

This Skill may only propose changes under:

- `/workflow`
- `/open_questions`
- `/blocking_issues`
- `/extensions/implementation_design`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "design-implementation"
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

- Career Knowledge is primary.
- Evidence before Claims.
- Human Review before persistence.
- Raw source, secrets, credentials, and private data are not persisted.
- Validation fails closed.
