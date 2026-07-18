# Create Pull Request Skill

## Purpose

push済みworking branchから明示されたbase branchへのPull Requestを`gh` CLIで作成する。

## Preconditions

- publish resultがcompleted
- commit SHAがremote headと一致
- base/headが明示され、異なる
- titleとbody contextが完全
- 同一base/headの既存Open Pull Requestがない

## Procedure

1. push済みbranchとremote headを確認する
2. 同一base/headの既存PRを確認する
3. handoffのbody contextだけから本文を構成し、未確認情報を補完しない
4. `gh pr create --base <base> --head <working> --title <title> --body <body>`を実行する
5. handoffで指定された場合だけ`--draft`を付ける
6. PR number、URL、draft状態をResultへ記録する

## Forbidden

- GitHubへの`gh`以外の書き込み
- merge、close、branch削除、base変更、追加commit、push、force push、認証login

push状態、remote head、入力、重複PRを検証できない場合または認証エラーは`blocked`とする。
