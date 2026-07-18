---
name: lock-design
version: "1.0"
interface: plan
responsibility: single
---

# LockDesign

## Purpose

Plan・Implementation Design・ADR・Invariantの整合を確認し、DESIGN_LOCK.md候補を生成する。

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
- `implementation_design`
- `accepted_adrs`
- `invariants`
- `human_action`
- `design_lock_template`

## Outputs

- `lock_validation`
- `design_lock_draft`
- `execution_contract`
- `handoff_manifest`
- `artifact_write_request`
- `state_patch`

## Responsibilities

- Scope・Architecture・Type Boundary・Change Boundary・Verification・Deviation Ruleを固定する
- submit_designを明示的に検証する
- Execute Handoffに必要な参照を揃える
- Lock revisionとPlan revisionの対応を残す

## Non-responsibilities

- submit_designなしにLockしない
- 未解決Blocking Issueを隠さない
- Planを上書きしない
- Repository実装を開始しない

## Blocking Conditions

- Plan・Design・ADRが不整合
- 必須検証や禁止変更が未定義
- Open Blocking Issueがある
- Human submit_designを確認できない

## State Patch Boundary

This Skill may only propose changes under:

- `/artifacts/design_lock_path`
- `/submission/design_submitted`
- `/workflow`
- `/blocking_issues`
- `/extensions/design_lock`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "lock-design"
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
