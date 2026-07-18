# Execute Skills

Execute Skillsは、承認済み`PLAN.md`と`DESIGN_LOCK.md`に従い、実装からRepository Publish Handoff生成までの単一責務を担当する。

## Common Contract

すべてのExecute Skillは次を守る。

- 1 Skill = 1責務
- 構造化Inputを受け取る
- 共通`skill-result`形式で構造化Outputを返す
- `execution-state.yaml`を直接変更しない
- 他Skillを直接呼び出さない
- Blocking IssueとDeviationを返せる
- Design Lockを実行契約として扱う
- secret、credential、個人情報、raw sourceを永続化・出力しない
- 検証不能を成功扱いしない

## Skills

- `inspect-execution-context`: 実行前提とRepository状態を確認する
- `implement`: Design Lock内の実装と必要テストを行う
- `review-implementation`: 実装を独立して1回評価する
- `apply-scope-fix`: 明示された指摘だけをScope内で修正する
- `run-release-gate`: 公開可否を最終検証・判定する
- `create-repository-publish-handoff`: passed Release Gateと同一差分に対する公開handoffを生成する
