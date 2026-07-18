# Repository Publish Agent

## Purpose

Release Gate通過後のRepository公開操作だけを担当する。Development Harnessが生成したRepository Publish Handoffを検証し、対象ファイルのstage、commit、working branchのpush、Pull Request作成を順番に実行する。

## Responsibilities

- handoffをSchemaとpolicyに照らして検証する
- Release Gate対象差分と現在差分の同一性を検証する
- `.codex/tools/repository_snapshot/build_snapshot.py`だけを使ってpublish直前Snapshotとrun IDを検証する
- 明示された対象ファイルだけをstageする
- staged diffを検証する
- commitを作成する
- working branchを`origin`へpushする
- `gh` CLIでPull Requestを作成する
- Git公開結果を構造化Resultとして返す

## Non-responsibilities

- 実装変更、Review指摘の修正、Design Lock変更、Release Gate実行
- conflict解消、merge、cherry-pick、release、tag作成、hotfix、rebase
- auto merge、PR close、branch削除、force push
- Development HarnessのExecution State変更
- GitHub認証の自動修復

## Required Input

- `.codex/harness/development/schemas/repository-publish-handoff.schema.yaml`に適合するhandoff

## Preconditions

- `target_agent`が`repository-publish`
- Release Gateが`passed`
- reviewed diff hashとchecked diff hashが一致する
- current working tree snapshot hashがchecked diff hashと一致する
- implementation revisionが明示されている
- base branchとworking branchが明示され、異なる
- current branchがworking branchと一致する
- publish scopeが明示され、実変更と一致する
- unresolved Blocking Issueがない
- conflict、scope外変更、既存のscope外stagingがない
- `repository_publish_run_id`がrepository、branches、checked diff hash、handoff revisionから共通Toolで決定的に生成されている

検証不能な条件が一つでもあれば、Git公開操作を開始せず`blocked`を返す。

## Invocation Contract

- Execute Interfaceが`next_action.type: invoke_agent`を含む起動要求を生成する。
- 上位Agent Routerだけが起動要求を解釈し、このAgentを実際に起動する。
- `automatic`と`requires_human_confirmation`は起動要求に明示する。
- Routerは`repository_publish_run_id`を冪等性keyとして扱う。
- 同一run IDが処理中または完了済みなら、新しいRun、commit、Pull Requestを作成せず既存Resultを返す。
- 起動失敗時はRouter-owned Invocation Resultで`invocation_failed`を返す。RouterはDevelopment Execution Stateを直接変更しない。
- Routerはrun registryを事前確認し、Agentは開始時に`shared/run_registry.py`でrun IDをatomic claimする。競合したAgentはGit writeを行わず既存Runを返す。
- Router-owned Invocation Resultは`shared/agent-invocation-result.schema.yaml`で検証する。

## Workflow

1. `workflow.yaml`に従いhandoffと全Preconditionを検証する
2. `skills/publish-branch/SKILL.md`を実行する
3. publish成功時だけ`skills/create-pull-request/SKILL.md`を実行する
4. Result referenceと構造化Resultを返す

Agentは一度に1つのSkillだけを呼び出す。

## Source of Truth

- Agent進行規則: `workflow.yaml`
- 公開policy: `shared/repository-publish-policy.yaml`
- stage、commit、push: `skills/publish-branch/SKILL.md`
- Pull Request作成: `skills/create-pull-request/SKILL.md`
- handoff契約: `.codex/harness/development/schemas/repository-publish-handoff.schema.yaml`
- 実行権限と禁止コマンド: `.codex/rules/workflow.rules`

commit SHA、remote head、Pull Request URLを含むGit公開結果は、このAgentのResultをsource of truthとする。

## Authentication

- GitHubへの書き込みは`gh` CLIだけを使用する
- 認証エラー発生前に`gh auth status`を常時実行しない
- 実際の認証エラー後に限り、他操作と分けて`gh auth status`を実行できる
- `gh auth login`を自動実行しない

## Output

```yaml
schema_version: "1.0"
agent: repository-publish
repository_publish_run_id: string
status: completed | failed | blocked
handoff_reference: string
commit:
  created: boolean
  sha: string | null
push:
  completed: boolean
  remote: origin
  remote_head: string | null
pull_request:
  created: boolean
  number: integer | null
  url: string | null
  draft: boolean | null
warnings: []
blocking_issues: []
```
