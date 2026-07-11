# Concepts

この文書では、me-shower を支える中心概念を定義します。

目的は、Resume や PDF のような出力形式ではなく、**Career Knowledge** を軸にシステム全体を理解できるようにすることです。

## Career Knowledge

Career Knowledge は、me-shower が最終的に育てたい主役です。

それは単なる職務経歴の箇条書きではなく、仕事で起きたこと、どう判断したか、どのように改善したか、何を学んだか、どの証跡がそれを支えるかを構造化した知識です。

Career Knowledge は Resume より上位にあります。Resume はその一部を特定の相手向けに切り出した View にすぎません。

```text
Source
    ↓
Evidence
    ↓
Canonical Event
    ↓
Human Review
    ↓
Career Knowledge
    ↓
Views
```

## Source

Source は仕事の痕跡です。

たとえば次のようなものを含みます。

- GitHub Pull Request や commit
- Slack message
- Teams message
- Daily Report
- local memo

Source には「何が起きたか」「何が議論されたか」「何が決まったか」「本人がどう理解したか」の断片が含まれます。ただし、raw source をそのまま Career Knowledge とみなしてはいけません。

## Evidence

Evidence は Career Claim を支える根拠です。

> Evidence comes before claims.

me-shower では、先に見栄えのよい主張を作ってから後で根拠を探す、という順番を取りません。まず evidence があり、その evidence をもとに review 可能な形へ整え、その後で必要に応じて claim や View に落とします。

Evidence は raw text の丸ごと保存を意味しません。必要に応じて redaction し、canonicalize し、安全に扱える形へ変換して使います。

## Canonical Event

Canonical Event は、Source から抽出された review 可能な出来事です。

履歴書向けの最終文面ではなく、あとから人間が見て「この出来事はどういう意味を持つか」を判断できる中間表現です。Career Knowledge そのものではありませんが、その候補になる重要な単位です。

Canonical Event は `source_sync` に蓄積されます。

## source_sync

`source_sync` は Canonical Event Store です。

v0.3.0 時点では、Resume や PDF のような下流出力よりも source of truth に近い層ですが、最終的な reviewed Career Knowledge と完全に同一ではありません。

言い換えると、`source_sync` は「正規化済みで review 可能な事実候補をためる場所」であり、そこからさらに Human Review を経て長期知識へ昇格する前段にあります。

## Source Intelligence

Source Intelligence は、Source を Career Knowledge 候補へ変換する ingestion / interpretation layer です。

v0.3.0 の中心はここにあります。単なる import 機能ではありません。役割は次の通りです。

- source を受け取る
- 共通の `RawSource` へ変換する
- 危険な raw text や secret を抑える
- ノイズを落とす
- Canonical Event に整える
- Source Confidence を付与する
- Timeline のような review 用 view を作れる状態にする
- 将来の Career Knowledge へ渡す土台を作る

## Source Confidence

Source Confidence は、source の強さ、evidence の質、抽出品質を表す運用指標です。

これは成果の価値や人の優劣を判定するものではありません。あくまで「この情報をどの程度そのまま使ってよいか」「どの程度 review を優先すべきか」を判断するための指標です。

目安は次の通りです。

- `high`: source と extraction が強い
- `medium`: 使用可能だが review があると安心
- `low`: ノイズや弱さがあるため review 優先

## Source Timeline

Source Timeline は `source_sync` から生成される derived operational view です。

Canonical Event の流れを時系列で見渡すためのレンズであり、source of truth そのものではありません。Timeline は inspection や review のために使うもので、上流の知識層を置き換えるものではありません。

## Skills

> Skills are not Career Knowledge itself.

Skills は Career Knowledge そのものではありません。

> Skills are operational knowledge that improves how agents read sources, detect issues, propose changes, and generate views.

Skills は、Agent が Source を読み、問題を検出し、変更を提案し、View を生成するための運用知です。

つまり Skills は、Career Knowledge を育てるための補助レイヤーです。Source の読み取り精度、review 観点、View 生成品質を上げるために重要ですが、主役ではありません。主役はあくまで Career Knowledge です。

## View

View は、Career Knowledge から生成される目的別の出力です。

例:

- Resume
- PDF
- Portfolio
- Interview Story
- Proposal Draft
- Skill Inventory
- Weekly Career Review

View は audience や目的に応じて形を変えます。長期的に持つべき知識は Career Knowledge 側に残し、View はその都度生成するものとして扱います。

---
