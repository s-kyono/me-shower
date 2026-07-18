# Plan Skills

Plan Interfaceからのみ呼び出される単一責務Skill群。

| Skill | Responsibility |
|---|---|
| inspect-context | Planningに必要な既存情報を収集・圧縮する |
| discover-decisions | 人間が判断すべき意思決定ポイントを発見する |
| propose-options | 1つのDecisionに対して案1〜3とAI推奨を提示する |
| submit-decision | Human submitを検証し暫定DecisionへのPatchを返す |
| assemble-plan | 暫定DecisionをPLAN Draftへ統合する |
| review-plan | Plan全体の前提・矛盾・未決・境界違反を問い直す |
| build-adr-candidates | 長期的な「なぜ」をADR候補として抽出する |
| design-implementation | Accepted Planを実装設計へ具体化する |
| lock-design | 整合性を確認しDesign Lock候補を生成する |

All Skills:

- do not mutate State directly
- do not invoke other Skills
- return structured Skill Result
- may return Blocking Issues
