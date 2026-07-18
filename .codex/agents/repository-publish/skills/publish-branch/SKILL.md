# Publish Branch Skill

## Purpose

検証済みhandoffの対象ファイルだけをstageし、staged diff検証後にcommitしてworking branchを`origin`へpushする。

## Input

- validated Repository Publish Handoff
- validated current snapshot hash and changed file list
- `repository_publish_run_id`

## Preconditions

- Agentの`input_validation`全guardがpassed
- current snapshot hashがhandoffのchecked diff hashと一致
- current branchが明示されたworking branch
- scope外変更、scope外staging、conflictがない
- `.codex/tools/repository_snapshot/build_snapshot.py`で再計算したhashがchecked diff hashと一致し、`unexpected_files`が空

## Procedure

1. branch、status、conflict、staged filesを再確認する
2. 共通Snapshot Toolをstage直前に再実行し、hash、included files、unexpected filesを検証する
3. `git add -- <explicit paths>`でincluded pathだけをstageする
4. staged file setがexpected changed filesと完全一致することを確認する
5. cached diffのcheck、stat、内容とsecret/privacy/raw-source非混入を確認する
6. 明示されたmessageで通常commitを作成する
7. working branchだけを`origin`へ通常pushする
8. local HEADとremote HEADの一致を確認してResultを返す

## Forbidden

- broad staging、commit amend、base branch push、force push
- conflict解消、実装変更、認証login

検証不能、不一致、空commit、commit/push失敗、認証エラーは`blocked`とする。
同一`repository_publish_run_id`が処理中または完了済みの場合はGit writeを行わず既存Resultを返す。
