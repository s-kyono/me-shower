---
name: create-repository-publish-handoff
version: "1.0"
interface: execute
responsibility: single
---

# CreateRepositoryPublishHandoff

## Purpose

passed Release Gateと同一の実装差分について、Repository Publish Agentがfail closedで検証できる構造化handoffを生成する。

## Contract

- Repositoryと`execution-state.yaml`を直接変更しない。
- 他Skillを呼び出さない。
- Git staging、commit、push、Pull Request作成、GitHub認証確認を行わない。
- Repository Publish Agentを直接起動しない。
- `.codex/harness/development/schemas/repository-publish-handoff.schema.yaml`に適合するhandoffだけを返す。
- Snapshot Hashとrun IDは`.codex/tools/repository_snapshot/build_snapshot.py`だけで生成する。

## Inputs

- passed `release_gate`
- accepted `review`
- `design_lock_revision`
- `implementation_revision`
- `reviewed_diff_hash`
- `checked_diff_hash`
- `base_branch`
- `working_branch`
- `approved_changed_files`
- `excluded_paths`
- commit metadata
- Pull Request body context
- blocking issues
- warnings
- `repository_id`
- `handoff_revision`
- Agent起動方針

## Preconditions

- Release Gate、secret scan、privacy scan、raw-source scanがすべて`passed`
- implementation revisionが1以上
- reviewed diff hashとchecked diff hashが同一
- approved changed filesが明示され、Release Gate対象と一致する
- base branchとworking branchが明示され、異なる
- unresolved Blocking Issueがない
- 共通Snapshot Toolの`unexpected_files`が空
- handoff revision、repository ID、決定的repository publish run IDが明示される

検証不能または不一致の場合は`blocked`を返し、handoffを生成しない。

## Outputs

- `repository_publish_handoff`
- `handoff_reference`
- `state_patch`
- `next_action`

## State Patch Boundary

This Skill may only propose changes under:

- `/state`
- `/execution/current_skill`
- `/downstream/agent`
- `/downstream/handoff_reference`
- `/downstream/status`
- `/downstream/run_id`
- `/downstream/next_action`
- `/warnings`
- `/blocking_issues`

`downstream.status`はhandoff生成時に`invocation_requested`とする。`next_action.type`は`invoke_agent`、targetは`repository-publish`、`automatic`は`true`、`requires_human_confirmation`は`false`とする。上位Agent Routerが実際の起動主体であり、同一run IDの処理中・完了Runを重複起動してはならない。起動失敗はRouter-owned Invocation Resultの`invocation_failed`として返し、RouterはExecution Stateを直接変更しない。Repository Publish Agentの内部状態やGit公開結果を追加してはならない。

## Required Result Shape

共通Skill Result形式を使用し、`output.repository_publish_handoff`を必須とする。

## Invariants

- Release Gate passes before handoff.
- Review and Gate cover the exact same diff.
- Execution State stores only a downstream reference.
- `development_completed` means Development Harness completion only.
- Validation fails closed.
