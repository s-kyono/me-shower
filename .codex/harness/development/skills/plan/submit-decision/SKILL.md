---
name: submit-decision
version: "1.0"
interface: plan
responsibility: single
---

# SubmitDecision

## Purpose

人間の明示的submitを検証し、選択済みDecisionを暫定確定するState Patchを返す。

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
- `human_action`
- `current_revision`
- `applicable_invariants`

## Outputs

- `submission_validation`
- `normalized_rationale`
- `decision_status`
- `state_patch`

## Responsibilities

- Human Actionがsubmit_decisionであることを検証する
- selected optionとrationaleの存在を確認する
- AI推奨と人間の選択を区別したまま保存する
- 再open履歴を維持する

## Non-responsibilities

- 選択だけでsubmit扱いしない
- 人間のrationaleを捏造しない
- 未提示Optionを暗黙採用しない
- Plan全体を承認しない

## Blocking Conditions

- selected optionが存在しない
- 選択Optionが現在の候補に存在しない
- 未解決のcritical conflictがある
- Human submitを確認できない

## State Patch Boundary

This Skill may only propose changes under:

- `/decisions/*/status`
- `/decisions/*/selected_option_id`
- `/decisions/*/submission`
- `/decisions/*/rationale`
- `/workflow`
- `/blocking_issues`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "submit-decision"
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
