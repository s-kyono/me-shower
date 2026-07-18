---
name: inspect-context
version: "1.0"
interface: plan
responsibility: single
---

# InspectContext

## Purpose

Planningに必要なRepository・既存成果物・制約を収集し、後続Skillが扱える最小Contextへ圧縮する。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- `plan-state.yaml`を直接変更しない。
- 他Skillを直接呼び出さない。
- Blocking Issueを返せる。
- AI提案とHuman Decisionを区別する。

## Inputs

- `epic_id`
- `goal`
- `repository_root`
- `base_branch`
- `references (optional)`
- `constraints (optional)`
- `existing_plan_path (optional)`

## Outputs

- `repository_summary`
- `relevant_artifacts`
- `applicable_invariants`
- `known_constraints`
- `known_unknowns`
- `context_confidence`
- `state_patch`

## Responsibilities

- 対象Epicに関係する既存コード・テスト・設計資料・履歴を確認する
- canonicalとderivedを区別する
- 矛盾・欠損・古い参照を明示する
- 後続Skillへ必要な情報だけを要約する

## Non-responsibilities

- Decisionを発見・確定しない
- Optionを提案しない
- PlanやDesignを生成しない
- Repositoryを変更しない

## Blocking Conditions

- repository rootを特定できない
- canonical sourceを判別できない
- 必要資料に機密・個人情報が混入し安全に要約できない
- 参照間の重大な矛盾によりPlanning前提を確定できない

## State Patch Boundary

This Skill may only propose changes under:

- `/workflow`
- `/notes`
- `/blocking_issues`
- `/extensions/context`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "inspect-context"
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
