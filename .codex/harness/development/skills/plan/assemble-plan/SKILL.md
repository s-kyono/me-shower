---
name: assemble-plan
version: "1.0"
interface: plan
responsibility: single
---

# AssemblePlan

## Purpose

暫定確定済みDecisionを統合し、PLAN.md DraftとPlan State更新案を生成する。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- `plan-state.yaml`を直接変更しない。
- 他Skillを直接呼び出さない。
- Blocking Issueを返せる。
- AI提案とHuman Decisionを区別する。

## Inputs

- `goal`
- `accepted_decisions`
- `open_questions`
- `adr_candidates`
- `invariants`
- `plan_template`
- `artifact_paths`

## Outputs

- `plan_draft`
- `plan_summary`
- `unresolved_items`
- `artifact_write_request`
- `state_patch`

## Responsibilities

- Goal・Scope・Non-goals・受入条件・Trade-offを一貫したPlanへ統合する
- 未submit DecisionをAccepted Decisionへ含めない
- 未解決事項とDesign委譲事項を明示する
- PLAN templateに従う

## Non-responsibilities

- 未決事項を推測で解消しない
- AI推奨をHuman Decisionとして書かない
- 実装設計を完成させない
- PLAN.mdを直接書き換えない

## Blocking Conditions

- 必須Decisionが未submit
- GoalとAccepted Decisionsが矛盾する
- Acceptance Criteriaを構成できない
- Invariant違反を含む

## State Patch Boundary

This Skill may only propose changes under:

- `/artifacts/plan_path`
- `/workflow`
- `/open_questions`
- `/blocking_issues`
- `/notes`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "assemble-plan"
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
