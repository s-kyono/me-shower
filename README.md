# me-shower

職務経歴書の原本管理と提出用PDF生成を分離して運用するためのワークスペースです。

- ルートディレクトリ: 原本、運用ルール、エージェント指示を置く
- `app/`: YAMLからMarkdown/PDFを生成するCLIアプリ本体

原本Excelは参考テンプレートとして扱い、成果物は `app/generated/職務経歴書.pdf` とします。

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

`app/data/raw_sources/*.txt` の 1 ファイルを読み、Evidence Guard で秘匿情報を redaction したうえで、抽象化済みの Canonical Event / Evidence を `app/data/source_sync/YYYY-MM-DD.md` に保存します。raw source の本文は `source_sync` に保存しません。分類キーワードやノイズ判定は `.codex/source-intelligence/rules/` 配下の用途別 YAML で管理します。

### `uv run me-shower normalize-sources`

```bash
uv run me-shower normalize-sources
```

`app/data/raw_sources/*.txt` をまとめて正規化し、日付ごとの `app/data/source_sync/YYYY-MM-DD.md` を生成します。Learning Loop はこの `source_sync` を入力として利用します。resume 向けの選別や言い換えはここでは行わず、`generate-md` / `issue` の Resume Agent Hook で扱う前提です。

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
