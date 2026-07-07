# me-shower

`me-shower` は、職務経歴書を長く育てるためのフレームAIエージェント用リポジトリです。

YAMLで経歴・スキル・プロジェクトを管理し、Jinja2でMarkdownを生成し、Markdown + CSS + WeasyPrintで提出用PDFを作ります。公開リポジトリで扱いやすいよう、このリポジトリには架空のサンプルデータだけを含めています。

## 目的

- 職務経歴書の内容を構造化して管理する
- Markdownを中間成果物として残し、差分を追いやすくする
- CSSテーマを差し替えて、応募先に合わせたPDFを生成する
- 発行履歴を `CHANGELOG.md` に残し、いつ・どんな内容で発行したかを管理する

## セットアップ

```bash
uv sync
```

## データ編集

サンプルデータは `data/` 配下にあります。実運用では個人情報や実案件情報を扱うため、公開リポジトリへコミットする前に必ず内容を確認してください。

```text
data/
  events/
  projects/
  skills/
  profile.yaml
```

## ログ追加

```bash
uv run me-shower add-log --message "職務経歴データを更新"
```

ログは `data/events/` にYAMLとして保存されます。

## 分析

```bash
uv run me-shower analyze
```

プロフィール、プロジェクト、スキル、イベントの件数を確認します。

## Markdown生成

```bash
uv run me-shower generate-md
```

`templates/resume.md.j2` と `data/` 配下のYAMLを使い、`generated/resume.md` を生成します。

## PDF生成

```bash
uv run me-shower generate-pdf --theme forest
```

`generated/resume.md` をMarkdownからHTMLへ変換し、`templates/resume.css` と `templates/themes/forest.css` を適用して `generated/職務経歴書.pdf` を生成します。

## 経歴書発行

```bash
uv run me-shower issue --title "初回発行" --note "今日時点のMarkdownを原本として初回PDFを発行" --theme forest
```

`issue` は最新のMarkdownとPDFを生成し、発行版として `generated/releases/` 配下に保存します。発行履歴は `CHANGELOG.md` に追記されます。

## テーマ

テーマCSSは `templates/themes/` 配下で管理します。現在のテーマは `forest` です。

CSSを編集すれば、余白、フォント、見出し、表、色、ページ区切りなどPDFの見た目を変更できます。

## 公開リポジトリ運用の注意

このリポジトリは公開前提です。以下はコミットしないでください。

- 実名や連絡先などの本人識別情報
- 実案件名、会社名、顧客名、機密情報
- 生成済みPDF、Markdown、発行履歴
- 原本Excel、スクリーンショット、添付画像

## 確認コマンド

```bash
uv sync
uv run me-shower analyze
uv run me-shower generate-md
uv run me-shower generate-pdf --theme forest
uv run pytest
```
