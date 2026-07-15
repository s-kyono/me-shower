# 職務経歴書運用エージェント指示

このワークスペースでは、`職務経歴書原本.xlsx` を壊さずに参照し、Markdownで経歴データ、判断根拠、応募先別の編集方針を管理する。

エージェントの目的は、単に文章をよくすることではない。

原本との差分を管理し、根拠のある経験だけをCareer Knowledgeとして整理し、応募先に合わせて再構成することを目的とする。

## 最優先原則

* Career Knowledgeを主役とする。
* Evidence before Claimsを守る。
* AIが生成した文章、評価、推測を正本として扱わない。
* Human Review before persistenceを守る。
* raw source、credential、secret、private情報を保存しない。
* Resume、Skills、Timeline、Agents、generated artifactsをsource of truthにしない。
* 判断に迷う場合は、情報を補完せず「確認待ち」として扱う。

## Source of Truth

* `職務経歴書原本.xlsx` は現行原本として扱い、勝手に上書きしない。
* `docs/` 直下のConcept docsはcanonical docsとして扱う。
* `docs/ja/` は人間向けのJapanese companion docsとして扱う。
* AIエージェントは、明示指示がない限り `docs/ja/` をsource of truthとしない。
* Conceptや設計判断が必要な場合は、まず `docs/` 直下のcanonical docsを参照する。
* `docs/ja/` は、canonical docsの理解を補助する目的でのみ参照する。
* generated outputや提出物を正本として扱わない。

## Career Knowledgeの管理

* 原本Excelから読み取った内容を、直接提出物へ流さない。

* 原本から取得した情報は、まず次のSteering Sheetsへ整理する。

  * `.codex/steering_sheets/career_profile.md`
  * `.codex/steering_sheets/work_history.md`

* 原本との差分、確認待ち、表現リスクは次に記録する。

  * `.codex/steering_sheets/review_notes.md`

* 職務要約、強み、所属履歴、スキルは `career_profile.md` で管理する。

* 案件ごとの職務経歴は `work_history.md` で管理する。

* 編集方針や運用ルールは `resume_policy.md` を参照する。

* 経験は次の要素に分解して管理する。

  * 案件
  * 役割
  * 技術
  * 行動
  * 成果
  * 根拠
  * 再現できる強み

## 事実と根拠

* 数値、期間、会社名、役割、使用技術は事実確認を優先する。
* 根拠がない成果、評価、スキルを補完しない。
* 推測から具体的な実績を作らない。
* 経歴を誇張しない。
* 未確認の内容は「確認待ち」として扱う。
* AIによる提案は、人間の確認前に永続化された事実として扱わない。

## 個人情報と機密情報

* 個人情報や機密情報を外部へ送る作業は、必ずユーザー確認を前提にする。

* 次の情報は、提出用Markdown、PDF、Excel、ログ、レビュー出力へ載せない。

  * 氏名
  * 住所
  * 電話番号
  * メールアドレス
  * 生年月日
  * 顔写真
  * 学歴
  * 資格
  * credential
  * secret
  * private情報

* raw sourceに含まれる機密情報を、そのまま保存または転記しない。

## 応募先別の編集

* 応募先ごとに、強調する経験、削る経験、言い換える表現を設計する。

* 提案は次の区分で整理する。

  * 元の事実
  * 根拠
  * 編集意図
  * 提出用文面
  * 確認待ち

* 修正理由は、採用担当者と現場エンジニアの両方が理解できる粒度で簡潔に説明する。

* 応募先に合わせるために、事実そのものを変更してはならない。

## 成果物と変更履歴

* リリースとして見える変更、バージョン付きのプロジェクト履歴、プロジェクト向け変更は `CHANGELOG.md` に記録する。
* 最終提出物を作成する前に、未確認事項を明示する。
* 最終提出物を作成する前に、個人情報や機密情報が含まれていないことを確認する。
* generated outputを正本として保存しない。

## 自律実行の権限

実装およびGit操作を伴う場合は、次のルールに従う。

- 今回のタスクスコープに含まれるワークスペース内のファイルは、承認なしで参照、作成、更新、移動、削除してよい。
- 起点ブランチは、ユーザーから明示されたブランチを使用する。推測しない。
- 指定された起点ブランチから作業ブランチを作成してよい。
- ステージング対象は、今回のタスクスコープに含まれるファイルまたはディレクトリだけとする。
- `git add .`、`git add -A`、`git add --all` は使用しない。
- commit前に `git status --short` と `git diff --cached` を確認する。
- commitには変更内容が分かるメッセージを必ず指定する。
- 現在の作業ブランチを `origin` へpushしてよい。
- 起点ブランチへの直接pushとforce pushは禁止する。
- push後、指定された起点ブランチへのPull Requestを作成してよい。
- Pull Requestのmerge、close、ブランチ削除は行わない。
- GitHubへの書き込み操作は、GitHub App、Connector、MCPではなく `gh` CLIを使用する。
- Pull Requestは `gh pr create --base <起点ブランチ> --head <作業ブランチ>` で作成する。
- ローカルGit操作の前提として `gh auth status` を毎回実行しない。
- `gh auth status` は、GitHub CLIで実際に認証エラーが発生した場合に限り、Git操作とは分けて実行する。
- GitHub認証が無効な場合、`gh auth login` を自動実行せずユーザーへ報告する。
- `gh auth status` と `git add`、`git commit`、`git push` を同一の `&&` コマンド列へ混在させない。
- ステージング後の確認には `git status --short`、`git diff --cached --check`、`git diff --cached --stat` を使用してよい。
- `.codex/rules/workflow.rules` に定義された実行権限と禁止事項に従う。