# Publish Branch Skill

## Purpose

公開対象ファイルだけをstageし、検証後にcommitを作成し、作業ブランチを`origin`へpushする。

## Input

- `base_branch`
- `working_branch`
- `release_gate`
- `publish_scope.included_paths`
- `publish_scope.excluded_paths`
- `publish_scope.expected_changed_files`
- `commit.message`
- `commit.summary`

## Preconditions

- Release Gateが`passed`
- working branchがbase branchと異なる
- included pathsが空ではない
- scope外変更がstageされていない
- unresolved conflictが存在しない

## Procedure

1. 現在のブランチとworking branchが一致することを確認する
2. `git status --short`で変更を確認する
3. included pathsだけを明示的にstageする
4. 次を確認する
   - `git status --short`
   - `git diff --cached --check`
   - `git diff --cached --stat`
   - `git diff --cached`
5. staged filesがpublish scopeと一致することを確認する
6. commit messageを指定してcommitする
7. 作業ブランチを`origin`へpushする
8. commit SHAとpush結果を返す

## Forbidden

- `git add .`
- `git add -A`
- `git add --all`
- base branchへの直接push
- force push
- scope外ファイルのstage
- commit amend
- conflictの自動解消
- 実装内容の修正
- `gh auth login`の自動実行

## Blocking Conditions

- staged filesがscopeと一致しない
- staged diffに機密情報が含まれる
- commit対象が空
- conflictが存在する
- pushが拒否される
- 認証エラーが発生する
- remoteが`origin`ではない、または確認できない

## Output

```yaml
status: completed | failed | blocked
staged_files: []
commit:
  created: boolean
  sha: string | null
push:
  completed: boolean
  remote: origin
  branch: string
warnings: []
blocking_issues: []
```
