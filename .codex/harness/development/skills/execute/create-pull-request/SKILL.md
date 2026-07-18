---
name: create-pull-request
version: "1.0"
interface: execute
responsibility: single
---

# CreatePullRequest

## Purpose

push済みworking branchから指定base branchへのPull Requestを、Plan、Design Lock、Review、Release Gate、残存リスクを要約して作成する。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- `execution-state.yaml`を直接変更しない。
- 他Skillを直接呼び出さない。
- Pull Requestをmerge、close、ready化しない。

## Inputs

- `repository`
- `base_branch`
- `working_branch`
- `commit_sha`
- `plan_reference`
- `design_lock_reference`
- `adr_references`
- `review_reference`
- `release_gate_reference`
- `implementation_summary`
- `validation_summary`
- `known_failures`
- `remaining_risks`
- `draft_preference`

## Outputs

- `pull_request_number`
- `pull_request_url`
- `title`
- `body_summary`
- `base_branch`
- `head_branch`
- `draft`
- `state_patch`

## Responsibilities

- base/head branchとcommit SHAを確認する
- branchがremoteへpush済みであることを確認する
- 既存Open PRの重複を確認する
- PR titleとbodyを生成する
- PR bodyへSummary、Why、Scope、Non-goals、Design Lock、ADR、Validation、Known Failures、Remaining Risksを含める
- Draft設定に従ってPRを作成する
- PR referenceを返す

## Non-responsibilities

- 新しいcommitやpushを行わない
- 実装、Review、Release Gateを変更しない
- base branchを推測しない
- Known FailureやRemaining Riskを隠さない
- PRをmerge、close、auto-merge設定しない
- branchを削除しない

## Blocking Conditions

- branchがpush済みでない
- commit SHAとremote headが一致しない
- base branchまたはworking branchが不明
- baseとheadが同一
- Release Gate passedを確認できない
- secret、個人情報、raw sourceがPR本文に混入する
- 重複PRの扱いを安全に判断できない
- PR作成APIまたはCLIが認証エラーになる

## State Patch Boundary

This Skill may only propose changes under:

- `/state`
- `/execution/current_skill`
- `/pull_request/number`
- `/pull_request/url`
- `/pull_request/base`
- `/pull_request/head`
- `/pull_request/draft`
- `/pull_request/created`
- `/warnings`
- `/blocking_issues`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "create-pull-request"
  version: "1.0"
execution:
  status: "completed | failed | blocked"
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

- Release Gate passes before PR creation.
- Base branch is explicit and never guessed.
- Pull Request is not automatically merged.
- Known failures and remaining risks are not hidden.
- Raw source, secrets, credentials, and private data are not included.
