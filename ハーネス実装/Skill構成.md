# Decision

## 採用方針

```text
Plan Interface
  └─ Plan系の単一責務Skillを順番に呼び出す

Execute Interface
  └─ Execute系の単一責務Skillを順番に呼び出す
```

```text
Skill:
  1つの入力を受け取り
  1つの責務を実行し
  構造化された結果を返す

Interface:
  現在のStateを読み
  次に呼ぶSkillを判断し
  入出力を受け渡す
```

## 全体構造

```sh
Human
  ↓
Plan Interface
  ├── Decision Discovery Skill
  ├── Option Proposal Skill
  ├── Decision Submission Skill
  ├── Plan Assembly Skill
  ├── Plan Review Skill
  ├── ADR Candidate Skill
  ├── Implementation Design Skill
  └── Design Lock Skill
          ↓
      DESIGN_LOCK
          ↓
Execute Interface
  ├── Implementation Skill
  ├── Objective Review Skill
  ├── Scope Fix Skill
  ├── Release Gate Skill
  ├── Git Publish Skill
  └── PR Creation Skill
```

**ディレクトリ案:**

- 既存案を少し修正して、InterfaceとSkillを明確に分ける。

```sh
.codex/harness/development
├── interfaces/
│   ├── plan/
│   │   ├── SKILL.md
│   │   └── workflow.yaml
│   └── execute/
│       ├── SKILL.md
│       └── workflow.yaml
│
├── skills/
│   ├── plan/
        ├── inspect-context/
        │   └── SKILL.md # Planningに必要な既存情報を収集・圧縮する
        ├── discover-decisions/
        │   └── SKILL.md # 人間が判断すべき意思決定ポイントを発見する
        ├── propose-options/
        │   └── SKILL.md # 1つの意思決定に対して案1〜3とAI推奨を提示する
        ├── submit-decision/
        │   └── SKILL.md # 人間の明示的submitを検証し、暫定決定への変更案を返す
        ├── assemble-plan/
        │   └── SKILL.md # 暫定決定を一つのPlan Draftへ統合する
        ├── review-plan/
        │   └── SKILL.md # Plan全体の前提・矛盾・未決・境界違反を問い直す
        ├── build-adr-candidates/
        │   └── SKILL.md # 長期的に「なぜ」を残すべき判断を候補化する
        ├── design-implementation/
        │   └── SKILL.md # 確定Planを実装方針・実装設計へ具体化する
        └── lock-design/
            └── SKILL.md # Plan・設計・ADRの整合性を確認しDesign Lockを生成する
│   │
│   └── execute/
│       ├── inspect-execution-context/
│       │   └── SKILL.md # Design Lock・ADR・Git状態・既存差分を確認し、実行可能なContextへ圧縮する
│       ├── implement/
│       │   └── SKILL.md # Design Lockと確定Planに従い、Scope内の実装とテスト追加を行う
│       ├── review-implementation/
│       │   └── SKILL.md # 実差分と動的再現から、実装品質・境界違反・Design Lock逸脱を客観レビューする
│       ├── apply-scope-fix/
│       │   └── SKILL.md # レビューで確認された問題だけを対象に、Design Lockを維持して修正する
│       ├── run-release-gate/
│       │   └── SKILL.md # テスト・再現・禁止ファイル・差分を確認し、公開可能か最終判定する
│       ├── publish-branch/
│       │   └── SKILL.md # Release Gate合格後、対象ファイルだけをstage・commit・pushする
│       └── create-pull-request/
│           └── SKILL.md # push済みブランチから、検証結果と残存リスクを含むPRを作成する
├── schemas/
│     ├── plan-state.schema.yaml
│     ├── decision.schema.yaml
│     ├── adr.schema.yaml
│     ├── design-lock.schema.yaml
│     └── execution-state.schema.yaml
├── templates/
│     ├── PLAN.md
│     ├── ADR.md
│     ├── DESIGN_LOCK.md
│     ├── REVIEW.md
│     └── RELEASE_GATE.md
└── shared/
      ├── invariants.yaml
      ├── input-types.yaml
      ├── skill-result.schema.yaml
      ├── blocking-issue.schema.yaml
      └── state-patch.schema.yaml
```

次はまずschemas/からで自然。
ここで決めるべきなのは、細かいフィールド全部ではなく、

- 何をschemaで縛るか
- 何は柔軟に残すか
- PlanとExecuteで何を共通化するか
- validation失敗時にどう止めるか
の4つ。Schemaを増やしすぎると、開発HarnessがYAML管理Harnessに転職するので、最低限でいこう。

### Interfaceがやってよいこと

- plan-state.yamlを読む
- 現在のStateを判断する
- 次に実行可能なSkillを選ぶ
- Skillへ必要な入力だけ渡す
- Skillの結果をStateへ反映する
- Human Gateで停止する
- Design Lock後にExecuteへ引き渡す

### Interfaceがやってはいけないこと

- 自分で選択肢を考える
- 自分でPlan Reviewする
- 自分で実装する
- 自分でADRを書く
- Skillの結果を勝手に意味変更する
- submitされていないDecisionを確定する

**Interfaceは交通整理:**

```text
Interface != Business Logic
Interface != Decision Maker
Interface == Workflow Coordinator
```

### Plan InterFace 大まかな呼び出し順

```sh
inspect-context
  ↓
discover-decisions
  ↓
propose-options
  ↓
submit-decision
  ↺ 次のDecision
  ↓
assemble-plan
  ↓
review-plan
  ↺ 重要論点はpropose-optionsへ戻す
  ↓
submit plan
  ↓
build-adr-candidates
  ↓
design-implementation
  ↓
submit design
  ↓
lock-design
```

review-planから重要論点が見つかった場合は、新しい専用Skillを増やさず、

```sh
review-plan
  → discover-decisions相当のDecisionを返す
  → propose-options
  → submit-decision
  → assemble-plan
```

へ戻せばいい。再検討するたびSkillを増やしていたら、すぐに関数の動物園になる。
次は順番どおり、inspect-context/SKILL.mdの責務・入力・出力・禁止事項から決める。

### Skill間の契約

各Skillは、ほかのSkillを直接呼ばないほうがよい。

```text
Plan Interface
  ↓
Skill A
  ↓ structured result
Plan Interface
  ↓
Skill B
```

Skill同士が直接呼び合うと、どこで状態が変わったか追えなくなる。再利用可能な関数群のはずが、裏でこっそり電話し合う部署になる。
各Skillの基本契約はこんな形。

```yaml
skill:
  id: "propose-options"
  responsibility: "1つのDecisionに対して比較可能な選択肢を提示する"

input:
  decision:
    id: "source-adapter-boundary"
  context: {}
  constraints: []

output:
  options: []
  recommendation: {}
  open_questions: []

side_effects:
  allowed: false
```

State更新はInterface側だけが行う。

### Plan / Executeの境界

```text
Plan Interfaceの最終出力:
- accepted PLAN.md
- accepted ADR
- DESIGN_LOCK.md
- plan-state.yaml: state=design_locked

Execute Interfaceの入力:
- PLAN.md
- DESIGN_LOCK.md
- 関連ADR
- 現在のrepository state
```

Execute側はPlan中の会話履歴全部を読む必要はない。確定した契約だけを読む。これでコンテキスト量も減り、AIが昔の却下案に心変わりする事故も防げる。

### このDecisionで確定すること

```yaml
skill_architecture:
  model: "interface_orchestrates_single_responsibility_skills"

  interfaces:
    - "plan"
    - "execute"

  skill_rules:
    single_responsibility: true
    direct_skill_to_skill_calls: false
    structured_input_output: true
    state_mutation_by_interface_only: true

  handoff:
    boundary: "design_lock"
    plan_output_is_execution_contract: true
```

次の実装設計Decisionは、Plan Interface配下のSkillをどこまで細かく分けるか。ここは関数の粒度そのものなので、一つずつ責務を切り分ける。

各Skill:
- 1責務
- 構造化Input
- 構造化Output
- 直接Stateを書き換えない
- 他Skillを直接呼ばない
- blocking issueを返せる