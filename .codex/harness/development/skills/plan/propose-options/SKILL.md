---
name: propose-options
version: "1.0"
interface: plan
responsibility: single
---

# ProposeOptions

## Purpose

現在の1つのDecisionに対して、現実的に異なる1〜3案とAI推奨・トレードオフを提示する。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- `plan-state.yaml`を直接変更しない。
- 他Skillを直接呼び出さない。
- Blocking Issueを返せる。
- AI提案とHuman Decisionを区別する。

## Inputs

- `current_decision`
- `compressed_context`
- `accepted_decisions`
- `applicable_invariants`
- `human_feedback (optional)`

## Outputs

- `decision_id`
- `options`
- `recommendation`
- `comparison`
- `questions_for_human`
- `state_patch`

## Responsibilities

- 各Optionの利点・欠点・リスク・Revisit Triggerを示す
- Option同士を実質的に異なる案にする
- AI推奨と人間のDecisionを明確に分離する
- 必要なら再提案する

## Non-responsibilities

- Optionを選択済み扱いしない
- submitしない
- 複数Decisionを同時に処理しない
- 安全境界違反案を通常Optionとして推奨しない

## Blocking Conditions

- 安全境界を守る現実的Optionが存在しない
- Decision前提に重大な欠損がある
- 選択肢生成に機密・個人情報の保持が必要

## State Patch Boundary

This Skill may only propose changes under:

- `/decisions/*/options`
- `/decisions/*/recommendation`
- `/decisions/*/status`
- `/workflow`
- `/blocking_issues`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "propose-options"
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
