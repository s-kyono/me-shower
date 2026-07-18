---
name: discover-decisions
version: "1.0"
interface: plan
responsibility: single
---

# DiscoverDecisions

## Purpose

Contextから、人間が明示的に判断すべき意思決定ポイントを発見し、優先順を付ける。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- `plan-state.yaml`を直接変更しない。
- 他Skillを直接呼び出さない。
- Blocking Issueを返せる。
- AI提案とHuman Decisionを区別する。

## Inputs

- `compressed_context`
- `goal`
- `scope_candidates`
- `applicable_invariants`
- `existing_decisions`

## Outputs

- `decision_candidates`
- `decision_order`
- `delegated_to_design`
- `non_decisions`
- `state_patch`

## Responsibilities

- 目的・Scope・境界・安全性・受入条件に影響する論点を抽出する
- 人間判断と実装詳細を分離する
- 依存関係と優先順を付ける
- Decisionごとに必要性を説明する

## Non-responsibilities

- Optionを生成しない
- AIだけでDecisionを確定しない
- 実装詳細をDecisionへ昇格しすぎない
- Plan本文を生成しない

## Blocking Conditions

- Invariant同士または既存Decisionとの解消不能な矛盾を検出した
- Goalが不明でDecision候補を評価できない
- 重大なSource of Truth境界が不明

## State Patch Boundary

This Skill may only propose changes under:

- `/decisions`
- `/workflow`
- `/open_questions`
- `/blocking_issues`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "discover-decisions"
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
