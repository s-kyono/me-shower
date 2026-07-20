# Execute Interface

決まった内容を自律実行する

## 役割

- DESIGN_LOCK.mdを読む
- PLAN.mdとADRを読む
- repositoryの現在状態を確認する
- 実装Skillを呼ぶ
- 客観レビューSkillを呼ぶ
- 必要なら修正Skillを呼ぶ
- Release Gateを通す
- git add / commit / pushを進める
- PRを作成する
- 境界違反や重大逸脱で停止する

**Plan Interfaceとの大きな違いは、通常はHuman Gateを挟まないこと。**

ただし、以下だけは停止。

- Design Lockからの重大逸脱
- Scope変更
- source of truth境界変更
- persistence形式変更
- public APIの大幅変更
- 外部依存追加
- Safety Gate位置変更
- credentialやprivate情報の混入
- 3回の修正ループで解消しない
- Release Gate不合格
- Git競合や認証失敗

つまり次は、Plan Interfaceと同じ粒度で、

- Execute Interfaceの責務
- 入力
- 出力
- Human Gateの扱い
- execution-state.yamlの更新責務
- Skill呼び出し規則

## 全体像

```sh
.codex/harness/development
└── interfaces/
    └── execute/
        ├── SKILL.md
        └── workflow.yaml
```

### Execute Interfaceの全体像

```sh
PLAN.md
DESIGN_LOCK.md
ADR
Repository State
  ↓
Execute Interface
  ├─ 実装Skillを呼ぶ
  ├─ レビューSkillを呼ぶ
  ├─ 修正Skillを呼ぶ
  ├─ Release Gate Skillを呼ぶ
  ├─ Git Publish Skillを呼ぶ
  └─ PR Creation Skillを呼ぶ
        ↓
      Pull Request
```

基本原則はこれ。

```text
Execute Interface = 自律実行の進行管理
Execute Skill = 単一責務の実処理
Design Lock = 実装契約
Human = 重大逸脱時の判断者
```

## 1. Execute Interfaceの責務

**噛み砕くと:**

Execute Interfaceは、確定した設計どおりに作業を前へ進める役。

自分でコードを書くのではなく、Stateを見て適切なSkillを呼ぶ。

- ライフサイクル

```text
現在:
実装前

次:
implement Skill
```

```text
現在:
実装完了

次:
review-implementation Skill
```

```text
現在:
レビューで問題あり

次:
apply-scope-fix Skill
```

という交通整理を行う。

### 担当すること

- PLAN.mdを読む
- DESIGN_LOCK.mdを読む
- 関連ADRを読む
- repositoryの現在状態を確認する
- execution stateを読み込む
- 次に呼ぶExecute Skillを選ぶ
- Skillへ必要な入力だけ渡す
- Skill結果を検証する
- execution stateを更新する
- 修正ループ回数を管理する
- Design Lockとの逸脱を検知する
- Release Gate合格後だけGit公開へ進む
- push後にPR作成へ進む
- 停止条件で安全に止まる

### 担当しないこと

- Planを勝手に変更する
- ADRを勝手に変更する
- Scopeを追加する
- 実装方針を再決定する
- Skillの代わりにコードを書く
- レビュー結果を都合よく解釈する
- Release Gate不合格なのにpushする
- PRを自動マージする

### 方向性

```yaml
execute_interface:
  role: "Autonomous execution workflow coordinator"
  implementation_logic: false
  design_decision_authority: false
  autonomous_within_design_lock: true
```

---

## 2. Execute Interfaceの入力

入力は大きく3種類。

1. 確定した設計
2. repositoryの現在状態
3. Skillの実行結果

### 確定した設計

```yaml
execution_contract:
  epic_id: "02.SourceIngestionPOC"
  plan_path: "docs/development/plans/02.SourceIngestionPOC/PLAN.md"
  design_lock_path: "docs/development/plans/02.SourceIngestionPOC/DESIGN_LOCK.md"
  adr_paths:
    - "docs/development/adr/ADR-0001-example.md"
```

**必須:**

- Epic ID
- PLAN.md
- DESIGN_LOCK.md

ADRは関連するものだけ。

### Repository State

```yaml
repository_context:
  repository_root: "."
  base_branch: "feature/v0.5.0"
  working_branch: "02.SourceIngestionPOC"
  expected_remote: "origin"
```

実際には開始時に確認する。

- current branch
- git status
- baseとの差分
- remote
- GitHub認証
- 未コミット変更

### Skill Result

```yaml
skill_result:
  skill_id: "review-implementation"
  status: "completed"
  output: {}
  state_patch: {}
  warnings: []
  blocking_issues: []
  design_lock_deviations: []
```

Plan側と同様、Skillは構造化結果を返す。

---

## 3. Execute Interfaceの出力

出力は3種類。

- 実行中の状態
- 停止時の報告
- 完了時の成果

**実行中**

```yaml
execution_status:
  state: "reviewing"
  current_skill: "review-implementation"
  fix_loop_count: 2
  max_fix_loops: 5
  design_lock_status: "aligned"
  blocking_issues: []
```

**停止時**

停止地点
停止理由
実行済み操作
変更ファイル
未コミット変更
テスト結果
Design Lockとの差分
漏洩有無
安全な次アクション

**完了**

```yaml
execution_result:
  state: "pr_created"
  branch: "02.SourceIngestionPOC"
  commit_sha: "..."
  pull_request_url: "..."
  review_summary: {}
  release_gate_summary: {}
  remaining_risks: []
```

**最終成果物:**

- 実装差分
- REVIEW.md
- RELEASE_GATE.md
- commit
- remote branch
- PR

## 4. Human Gateの扱い

Plan Interfaceと違い、Execute Interfaceは通常は人間へ確認しない。

```text
Plan:
  人間が決める

Execute:
  AIが進める
```

人間へ戻すのは、実装詳細ではなく契約を変える必要がある場合だけ。

**Human Gateへ戻す条件**

- Scope変更が必要
- Non-goals変更が必要
- Design Lockと矛盾する
- ADRと矛盾する
- source of truth境界を変更する必要がある
- persistence形式を変更する必要がある
- public APIの重大変更が必要
- 外部依存の追加が必要
- Safety Gate位置の変更が必要
- Human Review境界を変更する必要がある

**この場合、**

```text
state: blocked_by_design_change
```

へ移行し、Plan Interfaceへ戻す。

**人間へ戻さず自律判断できるもの**

- private関数名
- module内部の分割
- 補助型
- fixtureの構成
- エラーメッセージ
- Scope内のリファクタリング
- テストケース追加
- lint修正
- 明白なバグ修正

**Git関連の停止**

以下も自律回避せず止める。

- GitHub認証失敗
- merge conflict
- non-fast-forward
- unrelatedな未コミット変更
- raw dataやcredentialのstage混入

## 5. execution-state.yamlの更新責務

Plan側と同じく、Stateを書き換えるのはExecute Interfaceだけ。
Skillは直接Stateを書かない。

```text
Skill
  ↓
state_patchを返す

Execute Interface
  ↓
検証する
  ↓
execution-state.yamlを更新する
```

**想定ファイル**

```text
docs/development/plans/<EPIC>/execution-state.yaml
```

`plan-state.yaml`とは分ける方が自然。

```text
plan-state.yaml
  何を作るか決めた記録

execution-state.yaml
  今どこまで作業が進んだか
```

```yaml
schema_version: "1.0"
epic: "02.SourceIngestionPOC"
state: "reviewing"
revision: 7

design_lock:
  status: "aligned"
  path: "DESIGN_LOCK.md"

execution:
  current_skill: "review-implementation"
  fix_loop_count: 2
  max_fix_loops: 5

git:
  branch: "02.SourceIngestionPOC"
  commit_sha: null
  pushed: false

pull_request:
  url: null

blocking_issues: []
warnings: []
```

**更新ルール**

1. execution-state.yamlを読む
2. revision確認
3. Skillを実行
4. state_patchを受け取る
5. Design Lockとの整合確認
6. state transitionを検証
7. schema validation
8. revisionを+1
9. atomic write
10. 再読込して検証

**修正ループ**

```yaml
execution:
  fix_loop_count: 3
  max_fix_loops: 5
```

回を超えたら停止。

ただし、境界違反は5回まで粘らない。

```text
通常の修正:
  最大5回

重大境界違反:
  即停止
```

## 6. Skill呼び出し規則

Plan側と同じ原則を使う。

- Skillは1責務
- 構造化Input
- 構造化Output
- Stateを直接書かない
- 他Skillを直接呼ばない
- blocking issueを返せる

**想定Skill**

```sh
skills/execute/
├── inspect-execution-context/
├── implement/
├── review-implementation/
├── apply-scope-fix/
├── run-release-gate/
├── publish-branch/
└── create-pull-request/
```

`inspect-execution-context`は必要。
いきなりimplementへ飛ぶと、Design LockやGit状態の確認まで実装Skillが抱えることになる。単一責務、開始5分で死亡。

**呼び出し順**

```sh
inspect-execution-context
  ↓
implement
  ↓
review-implementation
  ↓
問題あり
  └─ apply-scope-fix
       ↓
     review-implementation
       ↺ 最大5回
  ↓
run-release-gate
  ↓
publish-branch
  ↓
create-pull-request
```

**基本ルール**

- 1回にPrimary Skillは1つ
- Skill同士の直接呼び出し禁止
- Stateごとに呼べるSkillを制限
- blocking issueがあれば停止
- Design Lock deviationがあれば分類
- Release Gate合格前のGit公開禁止

**Routing例**

```yaml
routing:
  execution_started:
    allowed_skills:
      - "inspect-execution-context"

  execution_context_ready:
    allowed_skills:
      - "implement"

  implementation_completed:
    allowed_skills:
      - "review-implementation"

  review_changes_required:
    allowed_skills:
      - "apply-scope-fix"

  review_accepted:
    allowed_skills:
      - "run-release-gate"

  release_gate_passed:
    allowed_skills:
      - "publish-branch"

  branch_pushed:
    allowed_skills:
      - "create-pull-request"
```

## Execute InterfaceのState候補

詳細は`workflow.yaml`実装時に調整できるが、方向性はこれ。

```text
execution_started
execution_context_ready
implementing
implementation_completed
reviewing
changes_required
fixing
review_accepted
release_gate_running
release_gate_failed
release_gate_passed
publishing
branch_pushed
creating_pull_request
pr_created
blocked
```

**重要な遷移**

```sh
reviewing
  ↓ issues
changes_required
  ↓
fixing
  ↓
reviewing
```

```sh
reviewing
  ↓ accepted
review_accepted
  ↓
release_gate_running
```

```sh
release_gate_failed
  → publish不可
```

## Execute Interfaceの確定候補

```yaml
execute_interface:
  role: "Autonomous execution workflow coordinator"

  responsibilities:
    - "Design Lockを読み込む"
    - "repository状態を確認する"
    - "次に呼ぶExecute Skillを選ぶ"
    - "Skill結果を検証する"
    - "execution-state.yamlを更新する"
    - "修正ループを最大5回管理する"
    - "Release Gate合格後だけGit公開する"
    - "push後にPRを作成する"
    - "重大逸脱時に停止する"

  non_responsibilities:
    - "Plan変更"
    - "ADR変更"
    - "Scope変更"
    - "実装処理そのもの"
    - "レビュー処理そのもの"
    - "PR自動マージ"

  input:
    - "PLAN.md"
    - "DESIGN_LOCK.md"
    - "related ADRs"
    - "repository state"
    - "execution-state.yaml"
    - "skill results"

  output:
    - "execution status"
    - "blocking report"
    - "review result"
    - "release gate result"
    - "commit and pushed branch"
    - "pull request"

  state_mutation:
    owner: "execute_interface"
    file: "execution-state.yaml"
    atomic: true
    revision_checked: true
    schema_validated: true

  fix_loop:
    maximum: 5
    boundary_violation_stops_immediately: true

  skill_invocation:
    one_primary_skill_at_a_time: true
    direct_skill_calls_forbidden: true
    routing_by_state: true
    structured_result_required: true
```

これがExecute Interfaceの土台。
Plan Interfaceと左右対称にしつつ、Human Gate中心ではなくDesign Lock遵守中心になっている。設計会議は終わった。ここからは現場だ、という境界がちゃんと出ている。
