# me-shower v0.5.0 POC Sheet

## 0. このシートの役割

このシートは、v0.5.0で実際に検証する範囲を定義する。

`DIRECTION.md` はプロジェクト全体の思想、`ROADMAP.md` はv0.5.0以降の展開方針を扱う。

このシートでは、v0.5.0で何を作り、何を作らず、何をもって成功とするかだけを扱う。

---

## 1. リリーステーマ

```text
Career Knowledge Loop POC
```

---

## 2. v0.5.0の一言定義

> v0.5.0は、普段の仕事で自然に残った記録を実際に取り込み、人間の確認を通してCareer Knowledgeとして蓄積し、「先月まで何をやったか」「この案件の経歴」「当時何に関心を持っていたか」を取り出せる最小運用ループを検証するPOCリリースである。

---

## 3. POCで検証する問い

```text
普段の仕事の記録を残しておけば、
必要になったときに過去のログを自分で掘り返さなくても、
やってきたことや当時考えていたことを、
一定水準で振り返れるか。
```

完璧なデータモデルや高度なAI品質を証明することは目的ではない。

---

## 4. 対象範囲

```text
対象ユーザー:
  開発者本人

対象案件:
  1案件

対象期間:
  2週間〜1か月

Source:
  AIチャットログ
  会議文字起こし
  必要に応じて元音声参照

出力:
  月次振り返り
  案件経歴のMarkdown Draft
  Experience Contextを含む振り返り
```

過去9年分や複数案件を一度に扱わない。

まず、直近の実データで使えるかを確認する。

---

## 5. 最小運用ループ

```text
実際のSource
  ↓
定期または手動トリガー
  ↓
Sourceの取得・正規化
  ↓
Canonical Eventの抽出
  ↓
Experience Contextの抽出・推定
  ↓
Review Queue
  ↓
Human Review
  ↓
Promotion
  ↓
Career Knowledgeへ保存
  ↓
期間・案件による取得
  ↓
振り返り・経歴Draft
```

---

## 6. 代表ユースケース

### Use Case 1: 月次の振り返り

```text
先月まで何やったっけ？
```

期待する内容。

```text
- 主に取り組んだ案件
- 担当した内容
- 判断したこと
- 改善したこと
- 使用した技術
- 関心を持っていたこと
- 発見や試したいと思っていたこと
- 確認が必要な項目
```

### Use Case 2: 案件経歴の下書き

```text
この案件の経歴、よしなにやっといて。
```

期待する内容。

```text
- 案件概要
- 役割
- 担当業務
- 判断・工夫
- 変化・成果
- 技術スタック
- 根拠が不足している情報
- 人間による確認が必要な箇所
```

### Use Case 3: 当時の関心を振り返る

```text
この案件で、当時何に興味を持っていた？
```

期待する内容。

```text
- 強く反応していた技術や考え方
- 試したいと発言していたこと
- 参考にしようとしていた事例
- 迷いや違和感を持っていた点
- その後の行動につながった関心
```

---

## 7. v0.5.0で実装するもの

```text
1. 外部トリガーから実行できる入口
2. 実データSource Adapterを1〜2種類
3. Sourceの正規化
4. Canonical Event抽出
5. Experience Context Candidate抽出
6. 既存Review Queueへの接続
7. 人間による確認・修正・承認
8. 最小Promotion処理
9. 最小Career Knowledge Store
10. 期間・案件による取得
11. 月次振り返りDraft
12. 案件経歴Draft
13. Experience Contextを含む振り返り
14. end-to-end POC
```

---

## 8. v0.5.0で実装しないもの

```text
- 本格的なRAG基盤
- Vector Database
- Ragas
- DeepEval
- DSPy
- LLM-as-a-Judge
- 自動品質最適化
- 感情認識モデルの独自学習
- 感情の自動確定
- 自動Promotion
- 完全なCareer Ontology
- 高度なGUI
- 本格的なReview UI
- Source Connectorの網羅
- 音声認識エンジンの開発
- 完全なsupersession / stale / re-review運用
- Resume PDFの自動生成・提出
```

これらは、最小ループの価値を確認した後に扱う。

---

## 9. Experience ContextのPOC境界

v0.5.0では、当時の温度を次の3種類に分ける。

```text
explicit_expression
  本人が明示した反応

linguistic_inference
  発言内容からAIが推定した反応

acoustic_inference
  音声の特徴からAIが推定した補助シグナル
```

### 対象候補

```text
- discovery
- surprise
- interest
- curiosity
- motivation
- adoption_intent
- inspiration
- conviction
- uncertainty
- frustration
- discomfort
- confidence
```

### 不変条件

```text
感情推定 ≠ 本人の感情の事実

感情・熱量 ≠ 能力

感情・熱量 ≠ 成果

acoustic_inferenceだけで正本化しない

Experience ContextはCareer Eventを置き換えない

Human Review前に確定しない
```

---

## 10. Promotionの最小境界

v0.5.0では完全なPromotionDecisionRecord仕様を完成させない。

ただし、次の境界は必ず守る。

```text
- Review Decisionがapprovedである
- 対象Canonical Eventが一致する
- blocked_by_policyではない
- raw source本文が混入していない
- private情報やsecretが混入していない
- Evidence Referenceを追跡できる
- 同じEventを無制限に重複保存しない
```

```text
approved ≠ persisted Career Knowledge
```

Review DecisionとCareer Knowledge保存の間には、明示的なPromotion処理を置く。

---

## 11. Career Knowledge Storeの最小範囲

最低限、次の情報を保存する。

```text
- career_knowledge_entry_id
- project
- period
- role
- actions
- decisions
- improvements
- outcomes
- tools
- evidence_refs
- confidence
- fact_inference_status
- experience_context
- promotion_reference
- created_at
```

Career Knowledge Entryはappend-onlyを基本とする。

完全なLifecycle管理は行わないが、将来のsupersessionを妨げる構造にはしない。

---

## 12. 「一定水準」のPOC基準

### 必須

```text
- 根拠のない経験・成果・数値を追加しない
- 単なる作業ログの羅列にしない
- 事実と推測を区別する
- 指定された期間・案件を守る
- private情報を出力しない
- 出力をDraftとして扱う
```

### 不合格例

```text
- 会議をした
- APIを修正した
- レビューをした
```

### 目標とする整理

```text
- どの案件・文脈で
- どのような役割を担い
- 何を実施し
- 何を判断・工夫し
- 何が変わり
- どの技術を使ったか
```

v0.5.0では自動品質評価基盤を導入しない。

Human Reviewと既存のEvidence Guardを中心に品質を確認する。

---

## 13. システム上の成功条件

```text
- 実際のSourceを処理できる
- 同じSourceを再処理しても無制限に重複しない
- Canonical Eventをレビューできる
- Experience Contextを確認・修正できる
- Human Review前にCareer Knowledgeへ保存されない
- approvedだけで保存済み扱いされない
- Career Knowledgeから元Sourceまで追跡できる
- raw sourceやprivate情報がViewへ露出しない
- 期間・案件でCareer Knowledgeを取得できる
```

---

## 14. ユーザー体験上の成功条件

実データを処理した後に、

```text
先月まで何やったっけ？
```

と聞くことで、ユーザー自身がSourceを読み返さなくても役に立つ振り返りが返る。

さらに、

```text
この案件の経歴、よしなにやっといて。
```

と依頼することで、ゼロから書くより明確に楽なDraftが返る。

また、

```text
当時、何に興味を持っていたっけ？
```

に対して、本人が明示した発言や確認済みのExperience Contextから、当時の温度を思い出せる。

成功の基準は、そのまま提出可能な文章が出ることではない。

> ユーザーの作業が「思い出してゼロから書く」から、「出てきたものを確認して直す」に変わること。

---

## 15. 実装判断の優先順位

```text
1. 振り返りや経歴作成の手間を減らせるか
2. ユーザーへ新しい日次作業を強制していないか
3. Career Knowledgeが主役のままか
4. Evidence before Claimsを守っているか
5. Human Review before persistenceを守っているか
6. 感情推定を事実として扱っていないか
7. 実データでPOCを回せる単純さか
8. 将来拡張を妨げないか
```

将来の完全性より、現在のPOCを安全に回せる単純さを優先する。

ただし、source of truthの境界を壊してまで単純化しない。

---

## 16. POC完了時に得たい答え

```text
普段の仕事の記録を残しておけば、
必要になったときに過去のログを自分で掘り返さなくても、
やってきたことや当時考えていたことを、
一定水準で振り返れるか。
```

この問いにYesと答えられた場合、v0.5.0は完了とする。
