# me-shower

職務経歴書の原本管理と提出用PDF生成を分離して運用するためのワークスペースです。

- ルートディレクトリ: 原本、運用ルール、エージェント指示を置く
- `app/`: YAMLからMarkdown/PDFを生成するCLIアプリ本体

原本Excelは参考テンプレートとして扱い、成果物は `app/generated/職務経歴書.pdf` とします。

## Concept Docs

me-shower は、仕事の痕跡・証跡・Human Review から Career Knowledge を育てる Personal Career Operating System です。

詳しくは以下を参照してください。

- `docs/ja/00_vision.md`
- `docs/ja/01_concepts.md`
- `docs/ja/02_architecture.md`
- `docs/ja/03_operating_model.md`

Career Knowledge Store は、レビュー済み Career Knowledge を将来永続化する正本領域です。v0.4.0 では境界と `app/data/career_knowledge/` ディレクトリだけを定義し、`approved` の Review Decision を自動保存しません。将来の入力は Human Review で受理された `accepted_meaning` であり、Canonical Event 全体や generated output ではありません。

Claim Builder は、レビュー済み Career Knowledge を View 向けの表現候補へ変換する将来レイヤーです。v0.4.0 では境界と Claim Candidate 契約だけを定義し、Claim、Resume、PDF、View の生成や永続化は行いません。Claim Candidate は Career Knowledge、Resume、source of truth のいずれでもなく、利用前に Human Review または View Selection が必要です。

View Generation は、レビュー済み Career Knowledge と reviewed Claim Candidate を用途別 View へ投影する将来レイヤーです。新しい事実・因果・貢献範囲・意味は作らず、Evidence reference は追跡専用です。用途別承認は安全制約を上書きせず、不足情報はAIで補完しません。v0.4.0 では境界と View 種別だけを定義し、Resume、PDF、Portfolio、Interview Story、その他の generated output は生成しません。View Generationは将来のstructured Viewまでを担当し、PDFは別Rendererのrender formatです。

## ディレクトリ構成

```text
me-shower/
  AGENTS.md
  README.md
  .codex/
  職務経歴書原本.xlsx
  app/
    pyproject.toml
    src/
    templates/
    data/
    tests/
    generated/
    uv.lock
```

## 公開対象と非公開対象

- 公開対象: `README.md`, `AGENTS.md`, `app/`, `.codex/agents/`
- 非公開対象: `.codex/steering_sheets/`, `app/data/`, `app/generated/`, `app/CHANGELOG.md`, 原本Excelや各種ローカル生成物

## 実行場所

各種コマンドは `app/` 配下で実行します。

```bash
cd app
```

## セットアップ

```bash
cd app
uv sync
```

## よく使うコマンド

```bash
cd app

# データ概要を確認
uv run me-shower analyze

# 手動ログを追加
uv run me-shower add-log --message "職務経歴データを更新"

# raw source を 1 件正規化
uv run me-shower normalize-source --file app/data/raw_sources/sample.txt

# raw source を一括正規化
uv run me-shower normalize-sources

# Daily Report を 1 件 inspect
uv run me-shower inspect-daily-report --file app/data/daily_reports/2026-07-11.md

# Daily Report を 1 件 import
uv run me-shower import-daily-report --file app/data/daily_reports/2026-07-11.md

# Daily Report を一覧 inspect
uv run me-shower inspect-daily-reports --dir app/data/daily_reports --limit 20

# Daily Report を一括 import
uv run me-shower import-daily-reports --dir app/data/daily_reports --limit 20

# Source Timeline を生成
uv run me-shower build-source-timeline

# Source Timeline を確認
uv run me-shower inspect-source-timeline --limit 20
uv run me-shower inspect-source-timeline --from 2026-07-01 --to 2026-07-31 --min-confidence medium

# Human Review 用の Review Queue を生成・確認
uv run me-shower build-review-queue
uv run me-shower inspect-review-queue --readiness ready_for_review --limit 20

# Human Review の判断を追記・確認（実行例は安全なローカル参照のみ）
uv run me-shower add-review-decision --source-sync-file app/data/source_sync/2026-07-10.md --event-index 1 --status approved --reviewer-id self --reason "Evidence is traceable and the meaning is acceptable." --evidence-ref "daily_report:2026-07-10.md"
uv run me-shower inspect-review-decisions --status approved --limit 20

# Slack source を inspect
uv run me-shower inspect-slack-source --channel C0123456789 --limit 20 --token-env SLACK_BOT_TOKEN

# Slack source を正規化
uv run me-shower normalize-slack-source --channel C0123456789 --limit 20 --token-env SLACK_BOT_TOKEN

# Teams source を inspect
uv run me-shower inspect-teams-source --team-id TEAM_ID --channel-id CHANNEL_ID --limit 20 --token-env MS_GRAPH_TOKEN

# Teams source を正規化
uv run me-shower normalize-teams-source --team-id TEAM_ID --channel-id CHANNEL_ID --limit 20 --token-env MS_GRAPH_TOKEN

# Skill改善提案を生成
uv run me-shower loop-skills

# Skill改善提案を一覧表示
uv run me-shower list-skill-reviews

# Skill改善提案を1件反映
uv run me-shower apply-skill-review --file reviews/skills/2026-07-09/career_architect.md

# Markdownを生成
uv run me-shower generate-md

# PDFを生成
uv run me-shower generate-pdf --theme forest

# 発行履歴付きで保存
uv run me-shower issue --title "初回発行" --note "今日時点のMarkdownを原本として初回PDFを発行" --theme forest

# テスト実行
uv run --python .venv/bin/python -m pytest
```

## コマンド説明

### `uv run me-shower analyze`

プロフィール、プロジェクト、スキル、イベントの件数を確認します。

### `uv run me-shower add-log`

```bash
uv run me-shower add-log --message "職務経歴データを更新"
```

ログは `app/data/events/` にYAMLとして保存されます。

### `uv run me-shower normalize-source`

```bash
uv run me-shower normalize-source --file app/data/raw_sources/sample.txt
```

`app/data/raw_sources/*.txt` の 1 ファイルを読み、Evidence Guard で秘匿情報を redaction したうえで、抽象化済みの Canonical Event / Evidence を `app/data/source_sync/YYYY-MM-DD.md` に保存します。raw source の本文は `source_sync` に保存しません。感想だけの tool メモや生活ノイズは除外し、`Resolver分離した` のような雑な記述は downstream で扱いやすい Canonical action に寄せます。分類キーワードやノイズ判定は `.codex/source-intelligence/rules/` 配下の用途別 YAML で管理します。

### `uv run me-shower normalize-sources`

```bash
uv run me-shower normalize-sources
```

`app/data/raw_sources/*.txt` をまとめて正規化し、日付ごとの `app/data/source_sync/YYYY-MM-DD.md` を生成します。Learning Loop はこの `source_sync` を入力として利用します。resume 向けの選別や言い換えはここでは行わず、`generate-md` / `issue` の Resume Agent Hook で扱う前提です。

Source Confidence は、Canonical Event の evidence quality を `high` / `medium` / `low` で表します。これは成果の価値判断ではなく、source / metadata / extraction quality / noise の強さを表す運用指標です。

### `uv run me-shower build-source-timeline`

```bash
uv run me-shower build-source-timeline
```

Source Timeline は `source_sync` から生成される derived view です。Canonical Event を日付順に見渡すための index であり、source of truth ではありません。

### `uv run me-shower inspect-source-timeline`

```bash
uv run me-shower inspect-source-timeline --limit 20
uv run me-shower inspect-source-timeline --from 2026-07-01 --to 2026-07-31 --min-confidence medium
```

Timeline item を CLI で確認します。`--from` / `--to` / `--source-type` / `--min-confidence` / `--limit` で絞り込みできます。raw source text は表示しません。

### `uv run me-shower build-review-queue` / `inspect-review-queue`

Review Queue is a generated worklist for Human Review. It is not Career Knowledge. It does not approve or reject candidates, and it does not mutate `source_sync`. Queue は再生成可能な derived output であり、手編集や source of truth としての利用を前提にしません。

### `uv run me-shower add-review-decision` / `inspect-review-decisions`

Canonical Event に対する Human Review の結果を `app/data/review_decisions/YYYY-MM-DD.jsonl` へ追記し、status・source ID・review date・件数で確認します。Decision Log は append-only な判断履歴であり、Review Queue、Source、Career Knowledge、`CHANGELOG.md` の代替ではありません。過去の行は編集・削除せず、判断が変わった場合も新しい decision を追加します。`approved` でも Career Knowledge Store には保存しません。

### `uv run me-shower inspect-daily-report`

```bash
uv run me-shower inspect-daily-report --file app/data/daily_reports/2026-07-11.md
```

`app/data/daily_reports/` 配下の `.md` / `.txt` を 1 件 `RawSource` として確認します。Daily Report は固定テンプレート不要で、frontmatter・ファイル名・見出し・本文冒頭から日付を推定します。inspect 出力には raw report text を出しません。

### `uv run me-shower import-daily-report`

```bash
uv run me-shower import-daily-report --file app/data/daily_reports/2026-07-11.md
```

1 件の freestyle report を `daily_report` source として取り込み、Evidence Guard と Noisy Input Normalization を通して `app/data/source_sync/YYYY-MM-DD.md` に追記します。raw report text は `source_sync` に保存せず、既存の同日イベントを消さずに `source_id` ベースで重複を防ぎます。

### `uv run me-shower inspect-daily-reports`

```bash
uv run me-shower inspect-daily-reports --dir app/data/daily_reports --limit 20
```

`app/data/daily_reports/` を再帰走査し、Markdown / text の freestyle report 一覧を `RawSource` として確認します。ディレクトリ名やファイル名は固定しません。

### `uv run me-shower import-daily-reports`

```bash
uv run me-shower import-daily-reports --dir app/data/daily_reports --limit 20
```

`app/data/daily_reports/` 配下の `.md` / `.txt` をまとめて import します。Daily Report は Resume に直接反映せず、既存の Source Normalizer / Evidence Guard / Noisy Input Normalization を通した Canonical Event / Evidence としてのみ保存します。

### `uv run me-shower inspect-slack-source`

```bash
uv run me-shower inspect-slack-source --channel C0123456789 --limit 20 --token-env SLACK_BOT_TOKEN
```

Slack channel history を `RawSource` として確認します。token は CLI 引数ではなく環境変数名で指定し、inspect 出力には raw message text を出しません。

### `uv run me-shower normalize-slack-source`

```bash
uv run me-shower normalize-slack-source --channel C0123456789 --limit 20 --token-env SLACK_BOT_TOKEN
```

Slack message を `RawSource` として取得し、Evidence Guard と Noisy Input Normalization を通して `app/data/source_sync/YYYY-MM-DD.md` に追記します。raw Slack message 本文や token は保存せず、既存の同日 `source_sync` を消さずに `source_id` ベースで重複を防ぎます。

### `uv run me-shower inspect-teams-source`

```bash
uv run me-shower inspect-teams-source --team-id TEAM_ID --channel-id CHANNEL_ID --limit 20 --token-env MS_GRAPH_TOKEN
```

Microsoft Teams channel messages を `RawSource` として確認します。token は CLI 引数ではなく環境変数名で指定し、inspect 出力には raw message text や raw HTML を出しません。

### `uv run me-shower normalize-teams-source`

```bash
uv run me-shower normalize-teams-source --team-id TEAM_ID --channel-id CHANNEL_ID --limit 20 --token-env MS_GRAPH_TOKEN
```

Teams channel messages を `RawSource` として取得し、HTML body を text 化したうえで Evidence Guard と Noisy Input Normalization を通して `app/data/source_sync/YYYY-MM-DD.md` に追記します。raw Teams message 本文、raw HTML、token は保存せず、既存の同日 `source_sync` を消さずに `source_id` ベースで重複を防ぎます。

### `uv run me-shower loop-skills`

```bash
uv run me-shower loop-skills
```

`.codex/loop-skills/rules/`、`app/data/events/`、`app/data/source_sync/`、`app/generated/resume.md`、`CHANGELOG.md` を読み、各 agent の `SKILLS.md` 改善提案を `app/reviews/skills/YYYY-MM-DD/` に出力します。

### `uv run me-shower list-skill-reviews`

```bash
uv run me-shower list-skill-reviews
```

生成済みの Skill 改善提案を一覧表示します。

### `uv run me-shower apply-skill-review`

```bash
uv run me-shower apply-skill-review --file reviews/skills/2026-07-09/career_architect.md
```

指定した 1 件の proposal だけを人間レビュー前提で `SKILLS.md` に反映し、`CHANGELOG.md` に履歴を残して `app/reviews/skills_applied/YYYY-MM-DD/` にコピーします。同じ proposal を再度適用すると `already applied` で終了します。

### `uv run me-shower generate-md`

```bash
uv run me-shower generate-md
```

`app/templates/resume.md.j2` と `app/data/` 配下のYAMLを使い、`app/generated/resume.md` を生成します。

### `uv run me-shower generate-pdf`

```bash
uv run me-shower generate-pdf --theme forest
```

`app/generated/resume.md` をMarkdownからHTMLへ変換し、`app/templates/resume.css` を適用して `app/generated/職務経歴書.pdf` を生成します。

テーマCSSは `app/templates/themes/` 配下で管理します。現在のテーマは `forest` です。

### `uv run me-shower issue`

```bash
uv run me-shower issue --title "初回発行" --note "今日時点のMarkdownを原本として初回PDFを発行" --theme forest
```

`issue` は最新のMarkdownとPDFを生成し、発行版として `app/generated/releases/` 配下に保存します。

保存例:

```text
app/generated/releases/2026-07-07_初回発行/resume.md
app/generated/releases/2026-07-07_初回発行/職務経歴書.pdf
```

発行履歴は `CHANGELOG.md` に追記されます。`CHANGELOG.md` には、発行物、発行理由、生成内容サマリー、ルールベースのフィードバックエージェント結果、次回改善ポイントが残ります。

### `uv run --python .venv/bin/python -m pytest`

テストを実行します。現時点ではこの環境で `uv run pytest` が不安定なため、仮想環境のPython経由で実行します。

## 見た目の変更

PDFの余白、フォント、見出し、表、ページ区切りは `app/templates/resume.css` で調整できます。色やテーマ固有の値は `app/templates/themes/forest.css` で管理します。
