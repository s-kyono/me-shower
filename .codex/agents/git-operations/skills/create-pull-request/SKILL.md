# Create Pull Request Skill

## Purpose

push済みの作業ブランチから、指定された起点ブランチへのPull Requestを作成する。

## Input

- `base_branch`
- `working_branch`
- `push.completed`
- `commit.sha`
- `pull_request.title`
- `pull_request.body`
- `pull_request.draft`
- `warnings`

## Preconditions

- `push.completed`が`true`
- commit SHAが存在する
- working branchがremoteへpush済み
- base branchとworking branchが異なる
- Pull Request titleとbodyが空ではない

## Procedure

1. remote branchの存在を確認する
2. 同一base/headの既存Pull Requestがないか確認する
3. 次の形式でPull Requestを作成する

```text
gh pr create --base <base_branch> --head <working_branch>
```

4. 必要に応じて`--draft`を付ける
5. 作成されたPull RequestのURLを返す

## Pull Request Body

Pull Request bodyには、少なくとも次を含める。

- 変更概要
- 実装内容
- Validation結果
- Release Gate結果
- 既知の制約
- 未解決の警告
- 関連するPlan、ADR、Design Lock

存在しない情報を推測で補完しない。

## Forbidden

- Pull Requestのmerge
- Pull Requestのclose
- branch削除
- base branchの変更
- force push
- GitHub App、Connector、MCPによる書き込み
- `gh auth login`の自動実行

## Blocking Conditions

- branchがpush済みであることを確認できない
- 同一base/headのPull Requestが既に存在する
- GitHub CLI認証エラー
- titleまたはbodyが不足している
- base branchが不明
- working branchが不明

## Output

```yaml
status: completed | failed | blocked
pull_request:
  created: boolean
  number: integer | null
  url: string | null
  draft: boolean
warnings: []
blocking_issues: []
```
