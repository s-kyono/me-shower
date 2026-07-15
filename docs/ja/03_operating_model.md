# Operating Model

この文書では、me-shower を日々どう運用するかを整理します。

目的は、都度 Resume を作ることではありません。仕事の痕跡から inspection 可能な Career Knowledge を継続的に育てることです。そのために、evidence 境界と Human Review を運用上の前提に置きます。

## Daily Inputs

- GitHub: 実装、Pull Request、変更履歴
- Slack / Teams: 議論、レビュー、意思決定の痕跡
- Daily Report: 文脈、判断、詰まり、学び、意図
- local memo: 補助的な記録、軽いメモ

Freestyle な入力は二級市民ではありません。

GitHub には「何が変わったか」が残りやすく、Slack / Teams には「何が議論されたか」が残りやすく、Daily Report には「本人が何を理解し、なぜそう判断したか」が残りやすいです。Career Knowledge を育てるには、その両方が必要です。

## Operating Flow

番号付きフローへ入る前に、実データSourceをメモリ内で検査する。`pass` または `pass_with_sanitization` のCandidateだけをSource Intelligenceへ渡し、`blocked` inputからCanonical Eventや出力を作らない。

### Real Data Ingestion Safety

- 実データは永続化前に検査する。
- blocked inputは保存せず、Canonical Eventも作らない。
- sanitize可能な値だけを決定的placeholderへ置換する。
- audit report、ログ、例外、CLIへraw値やmatched substringを含めない。
- rule load、detector、再検査、最終assertionの失敗はfail closedとする。
- placeholderをCareer Knowledgeの事実やEvidenceとして扱わない。
- Source関連writeは`persist_text_safely`だけを使用し、現在値をprivate atomic write直前に再検査する。wrapperはAPI補助でありsecurity boundaryとして信用しない。
- Source inspection CLIは順序とcategory-level metadataだけを表示し、rawのID、title、origin、contentを表示しない。
- inspection / normalization失敗時は固定safe error codeだけを返し、Adapter例外本文やSource識別子を表示しない。

```text
1. Work happens
2. Sources are collected
3. Source Intelligence normalizes them
4. Canonical Events are stored in source_sync
5. Timeline is generated for inspection
6. Human reviews important events
7. Reviewed events grow Career Knowledge
8. Views are generated when needed
```

この順番を崩さないことが重要です。雑な入力から直接 Resume Claim を作らない、という運用ルールでもあります。

## Confidence の読み方

- `high`: 強い source と extraction
- `medium`: 使用可能だが review があると安心
- `low`: review 優先

Source Confidence は成果の価値判断ではありません。source quality と extraction reliability を表す運用指標です。

## Human Review の役割

AI proposal をそのまま Career Knowledge にしないために Human Review があります。

Human Review の主な役割:

- 誇張を止める
- 機密情報の混入を止める
- 誤抽出を止める
- 長期知識として残すべきかを判断する

運用原則:

```text
AI proposes.
Human reviews.
Career Knowledge persists.
```

v0.3.0 時点で完全な review queue が未実装でも、この境界は concept として先に固定しておきます。

## generated output の扱い

- `generated/` は基本 PR に混ぜない
- Timeline、PDF、Resume preview は再生成可能な artifact とみなす
- generated output を source of truth にしない

出力物は必要なときに作るものであり、長期的に守るべき正本ではありません。

## raw source の扱い

- raw source を長期正本にしない
- secret、token、private URL、機微な社内情報を保存しない
- Evidence Guard を bypass しない

raw source は入力として有用ですが、そのまま長期保存層へ置くには危険で不安定です。長期的に扱うのは、正規化と review の境界を通った後の情報です。

## Skills の扱い

- Skills は Career Knowledge の正本ではない
- Skills は Agent の運用知である
- Skills は Source を読む精度、review 観点、View 生成品質を改善するために使う

Skills が充実しても、それ自体が Career Knowledge になるわけではありません。主役は変わらず Career Knowledge です。

## v0.x Operating Policy

- 機能検証と運用学習を優先する
- ただし Concept と Boundary は崩さない
- 実装が太っても v1.0.0 で整理する前提で進める
- 意思決定は log や changelog に残す

---
