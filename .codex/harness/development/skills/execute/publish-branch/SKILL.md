---
name: publish-branch
version: "1.0"
interface: execute
responsibility: single
---

# PublishBranch

## Purpose

Release Gate passed済みの承認対象差分だけを明示的にstageし、検証後にcommitしてworking branchをremoteへpushする。

## Contract

- 1責務のみを持つ。
- 構造化Inputを受け取る。
- 構造化Skill Resultを返す。
- `execution-state.yaml`を直接変更しない。
- 他Skillを直接呼び出さない。
- Pull Requestを作成しない。
- broad stagingとforce pushを行わない。

## Inputs

- `release_gate_result`
- `approved_changed_files`
- `repository_root`
- `base_branch`
- `working_branch`
- `remote_name`
- `commit_message`
- `git_status`

## Outputs

- `staged_files`
- `pre_commit_validation`
- `commit_sha`
- `push_result`
- `local_head`
- `remote_head`
- `state_patch`

## Preconditions

- Release Gate result is `passed`
- secret, privacy, and raw-source scans are `passed`
- current branch is the approved working branch
- working branch is not the base branch
- approved file list is explicit and non-empty
- no Git conflict or unrelated changes exist

## Responsibilities

- `git status --short`相当で状態を確認する
- approved file listだけを個別にstageする
- broad staging commandsを使用しない
- staged diff、diff check、statを確認する
- commit messageを明示してcommitする
- working branchだけをremoteへpushする
- local HEADとremote HEADの一致を確認する
- 実際にstage・commit・pushした対象を返す

## Non-responsibilities

- 実装を修正しない
- Release Gateを再判定しない
- unrelated変更をstageしない
- `.env`、secret、個人情報、raw sourceをstageしない
- base branchへ直接pushしない
- force pushしない
- PRを作成・mergeしない

## Forbidden Commands and Behaviors

- `git add .`
- `git add -A`
- `git add --all`
- force push
- base branchへのpush
- unrelated fileのstage
- failed/blocked Gateからのpublish

## Blocking Conditions

- Release Gateがpassedでない
- current branchがapproved working branchでない
- approved file listと実差分が一致しない
- unrelated変更、Git conflict、non-fast-forwardがある
- secret、個人情報、raw source混入を検出した
- commitまたはpushに失敗した
- 認証が無効である
- local/remote HEAD一致を確認できない

## State Patch Boundary

This Skill may only propose changes under:

- `/state`
- `/execution/current_skill`
- `/git/staged_files`
- `/git/commit_sha`
- `/git/branch`
- `/git/remote`
- `/git/pushed`
- `/git/remote_head`
- `/warnings`
- `/blocking_issues`

## Required Result Shape

```yaml
schema_version: "1.0"
skill:
  id: "publish-branch"
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

- Release Gate passes before publish.
- Only approved files are staged.
- Base branch and force push are forbidden.
- Raw source, secrets, credentials, and private data are never published.
