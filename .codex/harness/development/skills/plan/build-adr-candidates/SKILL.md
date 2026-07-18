---
name: build-adr-candidates
version: "1.0"
interface: plan
responsibility: single
---

# BuildAdrCandidates

## Purpose

長期的に「なぜ」を残す価値があるAccepted DecisionをADR候補として抽出・整形する。

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
- `accepted_decisions`
- `plan_review`
- `existing_adrs`
- `adr_template`

## Outputs

- `adr_candidates`
- `formalization_recommendations`
- `deferred_candidates`
- `artifact_write_requests`
- `state_patch`

## Responsibilities

- 複数の現実的選択肢があったDecisionを候補化する
- Rejected Alternatives・Trade-offs・Consequences・Revisit Triggersを保持する
- 既存ADRとの重複・supersede関係を確認する
- ADR化不要な局所判断を除外する

## Non-responsibilities

- ADRを大量生産しない
- Decision履歴を改変しない
- 人間が選んでいない理由を事実化しない
- ADRファイルを直接書かない

## Blocking Conditions

- 採用理由またはRejected理由が復元できない
- 既存ADRと重大な矛盾がある
- ADR化対象のDecisionが未submit

## State Patch Boundary

This Skill may only propose changes under:

- `/adr_candidates`
- `/artifacts/adr_paths`
- `/workflow`
- `/blocking_issues`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "build-adr-candidates"
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
