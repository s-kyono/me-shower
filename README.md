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
