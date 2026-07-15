# me-shower Roadmap

## 0. このドキュメントの役割

このドキュメントは、`DIRECTION.md` で定義した思想を、どのような段階で実用化していくかを示す。

特定バージョンの詳細仕様は扱わない。  
各バージョンの役割、到達点、次へ進む条件を整理する。

---

## 1. これまでの進化

### v0.1.0 — Output MVP

Markdownから職務経歴書とPDFを生成する最初のMVP。

```text
Resume Markdown
  ↓
PDF
```

この時点ではResumeやPDFが主役に見えやすかった。

---

### v0.2.0 — Learning & Evidence Guard

Agent / Skillの改善ループとEvidence Guardを導入した。

```text
AI処理
  ↓
レビュー
  ↓
Skill改善
```

同時に、AIの提案を正本化しないこと、raw source・secret・private情報を長期保存しないことを強化した。

---

### v0.3.0 — Source Intelligence

日常のSourceから、Resumeとは独立したCanonical Eventを抽出する段階。

```text
Source
  ↓
Canonical Event
```

Resumeに使えるかではなく、仕事上何が起きたかを先に整理する方向へ進んだ。

---

### v0.4.0 — Human Review Boundary

Canonical Eventを人間が確認する境界を作った。

```text
Canonical Event
  ↓
Review Queue
  ↓
Human Review
  ↓
Review Decision Log
```

承認とCareer Knowledgeへの保存を分離した。

---

## 2. v0.5.0以降で実現したい体験

今後の中心は、内部境界を増やすことではない。

実際のSourceを使い、次の体験を成立させる。

```text
普段の仕事
  ↓
自然に残るSource
  ↓
定期・手動トリガー
  ↓
AIが経験候補を整理
  ↓
人間が確認
  ↓
Career Knowledgeが育つ
  ↓
必要なときに一言で取り出す
```

代表的な依頼。

```text
先月まで何やったっけ？

この案件で設計したものをまとめて。

この半年で改善したことを出して。

この案件の経歴、よしなにやっといて。

当時、何に興味を持っていたっけ？
```

---

## 3. v0.5.0 — Career Knowledge Loop POC

### 目的

実際の仕事のSourceからCareer Knowledgeまでの最小ループを動かし、必要になったときに振り返りや経歴のDraftとして取り出せることを検証する。

### 主なテーマ

```text
- 実データSourceの取り込み
- Canonical Event抽出
- Experience Context候補の抽出
- Human Review
- 最小Promotion
- Career Knowledge保存
- 月次振り返り
- 案件経歴Draft
```

### 到達点

```text
「先月まで何やったっけ？」
「この案件の経歴、よしなにやっといて」
```

に対して、ゼロから過去ログを掘り返すより明確に楽なDraftが返る。

---

## 4. v0.6.0以降の方向性候補

v0.5.0のPOC結果を踏まえて決定する。

### Source取り込みの拡張

```text
- AIチャット
- 会議文字起こし
- Slack
- Teams
- GitHub
- 日報
- 設計資料
```

Source Connectorの数を増やすこと自体を目的にしない。  
振り返りの価値が増えるSourceから優先する。

### Review体験の改善

```text
- 重複候補の統合
- まとめて承認
- 修正しやすいReview UI
- 月次レビュー
- 案件終了時レビュー
```

レビューの正確性だけでなく、続けられる軽さを重視する。

### Career Knowledgeの取得改善

```text
- 期間
- 案件
- 役割
- 技術
- 判断
- 改善
- 関心
- Experience Context
```

高度な検索基盤より先に、利用頻度の高い絞り込みを安定させる。

### Viewの拡張

```text
- 月次振り返り
- 案件経歴
- 職務経歴書
- 面接エピソード
- スキルの棚卸し
- 学習・関心の変化
```

ViewはCareer Knowledgeから生成する。  
Viewをsource of truthへ戻さない。

### Experience Contextの改善

```text
- 明示された感情表現
- 関心
- 発見
- 試行意欲
- 納得
- 迷い
- 音声の補助シグナル
```

感情認識の精度競争ではなく、後から当時を思い出せる価値を基準にする。

---

## 5. v1.0.0以降で検討すること

v0.xで最小運用ループの価値が確認できてから扱う。

```text
- 本格的なRAG基盤
- Vector Database
- Ragas
- DeepEval
- DSPy
- LLM-as-a-Judge
- 自動品質評価
- 生成パイプラインの最適化
- 高度な検索
- 品質の継続的改善
```

これらは品質を高める手段であり、プロダクトの目的ではない。

```text
RAGを作る
  ≠ 振り返りが楽になる

評価基盤を作る
  ≠ 経歴が育つ
```

最小ループが役立つと確認できるまでは導入を急がない。

---

## 6. バージョン判断の基準

次のバージョンへ進む際は、次の順番で判断する。

```text
1. ユーザーの振り返りや経歴作成の手間を減らせるか
2. Career Knowledgeが主役のままか
3. ユーザーへ新しい日次作業を増やしていないか
4. Evidence before Claimsを守れるか
5. Human Review before persistenceを守れるか
6. 実際のSourceで価値を確認できるか
7. 現段階で本当に必要な複雑さか
```

技術的に面白いことは、導入理由にならない。  
残念ながら、面白い技術は勝手に寄ってくるので、こちらから迎えに行く必要はない。

---

## 7. ロードマップ上の不変条件

```text
- Resume生成へ先祖返りしない
- AgentやSkillを主役にしない
- SourceをCareer Knowledgeへ直接保存しない
- AIによる自動Promotionを前提にしない
- Viewの表現をCareer Knowledgeへ逆流させない
- 感情推定を事実として扱わない
- 品質評価基盤を目的化しない
- Source Connectorの数を成功指標にしない
```

---

## 8. v0.5.0以降で得たい答え

```text
普段の仕事の記録を残しておけば、
必要になったときに過去のログを自分で掘り返さなくても、
やってきたことや当時考えていたことを、
一定水準で振り返れるか。
```

この問いへの答えがYesなら、`me-shower` は設計思想ではなく、実際に使える道具になる。
