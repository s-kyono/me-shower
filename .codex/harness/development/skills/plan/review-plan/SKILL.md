---
name: review-plan
version: "1.0"
interface: plan
responsibility: single
---

# ReviewPlan

## Purpose

Plan全体の前提・矛盾・未決・境界違反・トレードオフを問い直し、人間判断が必要な問題を返す。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- `plan-state.yaml`を直接変更しない。
- 他Skillを直接呼び出さない。
- Blocking Issueを返せる。
- AI提案とHuman Decisionを区別する。

## Inputs

- `plan_draft`
- `plan_state`
- `accepted_decisions`
- `invariants`
- `related_adrs`

## Outputs

- `preserved_principles`
- `implicit_assumptions`
- `findings`
- `required_decisions`
- `accepted_risks`
- `design_delegations`
- `review_status`
- `state_patch`

## Responsibilities

- 全体整合をレビューする
- 重大度ではなく意思決定必要性と境界影響を明示する
- 複数Findingを返してよい
- Material issueは一つずつDecision Loopへ戻せる形にする

## Non-responsibilities

- 点数を付けない
- 正解を断定しない
- Planを直接修正しない
- 人間の代わりにsubmit_planしない

## Blocking Conditions

- Source of Truth境界違反
- Human Review before persistence違反
- Evidence before Claims違反
- 解消不能なAccepted Decision間矛盾

## State Patch Boundary

This Skill may only propose changes under:

- `/decisions/*/review`
- `/open_questions`
- `/blocking_issues`
- `/workflow`
- `/notes`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "review-plan"
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
