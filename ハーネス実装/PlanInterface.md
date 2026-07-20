# Plan Interface

## 要するに

- 「設計会議の司会」 だと思えばいい。

```sh
自分で設計案を考えるのではなく、

現在地を確認する
↓
必要なSkillを呼ぶ
↓
結果を人間へ見せる
↓
人間の回答を受け取る
↓
plan-state.yamlへ記録する
↓
次のSkillを呼ぶ
```

- これだけ。司会が勝手に議決まで始めると会議が独裁国家になるので、そこは分ける。

```sh
Human
  ↓ 回答・submit
Plan Interface
  ├─ plan-state.yamlを読む
  ├─ 現在の状態を判断する
  ├─ 必要なPlan Skillを1つ呼ぶ
  ├─ Skillの結果を人間へ提示する
  └─ 確定した内容だけplan-state.yamlへ記録する
        ↓
      Design Lock
```

## 1. Plan Interfaceの責務

**噛み砕くと:**

Plan Interfaceが担当するのは、Plan作成の順番と状態を管理すること。

たとえば現在が、

Sourceの対象範囲を決めている途中

なら、次に呼ぶべきSkillは「選択肢を提案するSkill」。

人間がsubmitした後なら、「決定を記録するSkill」。

Plan全体ができた後なら、「Plan Review Skill」。

という具合に、現在地から次の処理を決める。

- 担当すること
  - Plan Stateを読み込む
  - 現在のPlanning状態を判定する
  - 次に実行するSkillを選ぶ
  - Skillへ必要な情報だけ渡す
  - Skillの結果を人間向けに表示する
  - Human Gateで停止する
  - 人間の入力を受け取る
  - 検証済みの変更だけPlan Stateへ反映する
  - Design LockまでPlanフローを進行する

- 担当しないこと
  - 選択肢を自分で考える
  - AI推奨を自分で決める
  - Plan Reviewを自分で行う
  - ADR本文を自分で作る
  - 実装設計を自分で作る
  - submitされていない案を確定する
  - 実装を開始する

- 決定

```text
plan_interface:
  responsibility: "Planフローの状態管理とSkill呼び出し"
  decision_maker: false
  business_logic: false
  implementation_allowed: false
```

## 2. Plan Interfaceの入力

**噛み砕くと:**

Plan Interfaceへ渡すものは2種類。

1. 今回何を計画したいか
2. 人間が何と回答したか

毎回リポジトリ全体を巨大Promptとして渡す必要はない。必要なものだけ。コンテキストを倉庫みたいに積み上げても、賢くなるより先に散らかる。

```sh
Planning開始時の入力
request:
  epic_id: "02.SourceIngestionPOC"
  goal: |
    実データSourceを安全に取り込むPOCを設計する。
  repository_root: "."
  base_branch: "feature/v0.5.0"
  references:
    issues:
      - "#51"
    pull_requests:
      - "#54"
    files: []
```

最低限必要なのは、

- Epic ID
- 目的
- repository
- base branch

関連IssueやADRなどは任意。

対話中の入力

人間からの入力を、そのまま自由文として処理するのではなく、種類を判定する。

```sh
human_input:
  type: "select_option"
  value: "option_2"
```

**候補となる入力種別:**

select_option
question
free_text
request_reproposal
submit_decision
reopen_decision
submit_plan
submit_design

人間が書く文面は自然なままでよい。

案2
質問: なぜ案1では駄目？
自由記述: Adapterだけ分離したい
再提案: もっと小さな構成にして
submit

Interfaceが内部的に種別へ変換する。

決定
plan_interface_input:
  planning_request:
    required:
      - "epic_id"
      - "goal"
      - "repository_root"
      - "base_branch"

  human_input_types:
    - "select_option"
    - "question"
    - "free_text"
    - "request_reproposal"
    - "submit_decision"
    - "reopen_decision"
    - "submit_plan"
    - "submit_design"

## 3. Plan Interfaceの出力

**噛み砕くと:**

出力は、人間へ見せるものと、次のSkillへ渡すものの2種類。

人間向け出力

毎回、少なくとも次を表示する。

- 現在どこにいるか
- 何を決めようとしているか
- Skillが出した提案やレビュー
- 何が仮決定か
- 次に人間が入力できるもの

例:

Current State:
DECISION_PROPOSAL

Current Decision:
Source Adapterの責務境界

Current Candidate:
案2 専用moduleへ分離

Pending:
まだsubmitされていません

Available Actions:
案1 / 案2 / 案3
質問: ...
自由記述: ...
再提案: ...
submit
機械向け出力

次のSkillやExecute Interfaceが読むもの。

interface_result:
  state: "decision_proposal"
  invoked_skill: "propose-options"
  human_action_required: true
  allowed_actions:
    - "select_option"
    - "question"
    - "free_text"
    - "request_reproposal"
    - "submit_decision"
  state_patch: null

state_patchは、Plan Stateへ反映してよい変更候補。

ただし、人間のsubmit前なら確定内容として書き込まない。

Design Lock完了時の最終出力
PLAN.md
DESIGN_LOCK.md
正式ADR
plan-state.yaml

Execute Interfaceへ渡すもの:

execution_handoff:
  epic_id: "02.SourceIngestionPOC"
  plan_path: "docs/development/plans/02.SourceIngestionPOC/PLAN.md"
  design_lock_path: "docs/development/plans/02.SourceIngestionPOC/DESIGN_LOCK.md"
  adr_paths: []
  state: "design_locked"
決定
plan_interface_output:
  human_view:
    - "current_state"
    - "current_decision"
    - "skill_result"
    - "provisional_decisions"
    - "pending_items"
    - "allowed_human_actions"

  machine_view:
    - "invoked_skill"
    - "human_action_required"
    - "allowed_actions"
    - "state_patch"

  final_handoff:
    - "PLAN.md"
    - "DESIGN_LOCK.md"
    - "accepted ADRs"
    - "plan-state.yaml"

## 4. Human Gateの扱い

**噛み砕くと:**

Human Gateは、AIが勝手に次へ進まないための改札。

切符に当たるのがsubmit。

3つのGate

今回の決定どおり、3種類に分ける。

Decision Gate
submit

1つの意思決定を暫定確定する。

Source Adapterは専用moduleへ分離する

など。

この段階ではPlan全体としてはまだ確定していない。

Plan Gate
submit plan

Plan全体を確定し、実装方針・実装設計へ進める。

Design Gate
submit design

実装設計とADRを確定し、Design Lockする。

これ以降はExecute Interfaceへ移る。

Gateのルール
AIの推奨だけではGateを通過しない
案の選択だけでもGateを通過しない
人間の明示的submitが必要

たとえば、

案2でいいね

は候補選択。

submit

で初めて暫定決定。

再オープン

submit plan前なら、暫定決定を再検討可能。

reopen: source-adapter-boundary

submit plan後に変更する場合は、Plan Revisionとして扱う。

submit design後に重要な変更が必要なら、Executeへ進まずPlanningへ戻す。

決定
human_gates:
  decision:
    command: "submit"
    effect: "1つのDecisionをprovisional acceptedにする"

  plan:
    command: "submit plan"
    effect: "Plan全体をacceptedにする"

  design:
    command: "submit design"
    effect: "Design LockしExecuteへ引き渡す"

  rules:
    explicit_submission_required: true
    option_selection_is_not_submission: true
    ai_recommendation_is_not_submission: true
    reopen_before_plan_submit: true

## 5. plan-state.yamlの更新責務

**噛み砕くと:**

plan-state.yamlを書き換えてよいのは、Plan Interfaceだけ。

Skillは「こう変えるべき」という結果を返すだけ。

Skill:
  このDecisionをacceptedへ変更してください

Interface:
  内容を検証
  ↓
  plan-state.yamlへ書き込む

Skill自身が勝手に書き込むと、複数Skillが同時に状態を触り始める。分散システムでもないのに整合性問題を自作する必要はない。

更新の流れ

1. plan-state.yamlを読む
2. revisionを確認
3. Skillを呼ぶ
4. Skillからstate_patchを受け取る
5. Human Gate条件を確認
6. schemaを検証
7. revisionを+1する
8. atomic writeする
9. 書き込み後に再読込して検証する

Skillが返す変更案
state_patch:
  expected_revision: 4
  operations:
    - op: "replace"
      path: "decisions.source-adapter-boundary.status"
      value: "provisional_accepted"

    - op: "replace"
      path: "decisions.source-adapter-boundary.selected_option"
      value: "option_2"

Interfaceは、現在のrevisionが4の場合だけ適用する。

別の更新でrevisionが5になっていたら拒否する。地味だけど大事。状態ファイルの上書き事故は、だいたい静かに起こって後から盛大に困らせる。

未submit情報の扱い

未submitの内容も、会話再開のために候補として保存してよい。

ただし、確定Decisionと明確に分ける。

current_decision:
  id: "source-adapter-boundary"
  status: "candidate"
  selected_option: "option_2"
  submitted: false

submit後:

current_decision:
  id: "source-adapter-boundary"
  status: "provisional_accepted"
  selected_option: "option_2"
  submitted: true
決定
plan_state_mutation:
  owner: "plan_interface"
  skills_may_write_directly: false

  requirements:
    - "expected revision check"
    - "schema validation"
    - "state transition validation"
    - "atomic write"
    - "post-write validation"

  candidate_data_may_persist: true
  candidate_and_accepted_must_be_distinguishable: true

## 6. Skill呼び出し規則

**噛み砕くと:**

Plan Interfaceは、好き勝手に複数Skillを呼ばない。

現在のState
  ↓
呼べるSkillが決まる

関数呼び出しのルーティング表を持つ。

基本ルール
1回に1つのSkill
1 interaction = 1 primary Skill

複数Skillを一気に呼ぶと、どの結果でStateが変わったか追いにくい。

ただし、read-onlyなvalidationなどは補助処理として許可してよい。

Skill同士は直接呼ばない
Skill A → Skill B

は禁止。

必ずInterfaceへ戻す。

Interface → Skill A
Skill A → Interface
Interface → Skill B
Stateごとに呼べるSkillを制限

例:

routing:
  planning_started:
    allowed_skills:
      - "inspect-context"

  context_ready:
    allowed_skills:
      - "discover-decisions"

  decision_discovered:
    allowed_skills:
      - "propose-options"

  option_selected:
    allowed_skills:
      - "answer-question"
      - "refine-options"
      - "submit-decision"

  plan_draft_ready:
    allowed_skills:
      - "review-plan"

  plan_accepted:
    allowed_skills:
      - "design-implementation"

  design_ready:
    allowed_skills:
      - "build-adr-candidates"
      - "lock-design"
Skillは構造化結果を返す

最低限:

skill_result:
  skill_id: "propose-options"
  status: "completed"
  output: {}
  state_patch: null
  human_action_required: true
  allowed_human_actions: []
  warnings: []
  blocking_issues: []
blocking issueがあれば進めない
blocking_issues:
  - code: "BOUNDARY_CONFLICT"
    message: "提案されたPlanがHuman Review境界と矛盾しています"

Interfaceは次のSkillを呼ばず、人間へ返す。

Plan Review時の例外

Plan Reviewは全体を確認するため、複数論点を返してよい。

ただし、Human Gateへ戻すときは重要論点を一問ずつ処理する。

review-plan
  ↓
論点A・B・Cを発見
  ↓
Interfaceが優先順位をつける
  ↓
論点Aだけpropose-optionsへ渡す

Interface自身が選択肢を作るわけではない。

決定
skill_invocation:
  one_primary_skill_per_interaction: true
  direct_skill_to_skill_calls: false
  routing_by_state: true
  structured_result_required: true
  blocking_issue_stops_flow: true

  state_mutation:
    skill_returns_patch: true
    interface_applies_patch: true

  plan_review:
    may_return_multiple_topics: true
    material_topics_returned_to_human_one_at_a_time: true

## Plan Interfaceの確定設計

- 全部まとめるとこう。

```yaml
plan_interface:
  role: "Planning workflow coordinator"

  responsibilities:
    - "plan-state.yamlを読み込む"
    - "現在Stateを判定する"
    - "次に呼ぶSkillを決める"
    - "Skillへ必要なContextだけ渡す"
    - "Skill結果を人間へ提示する"
    - "Human Gateで停止する"
    - "検証済みstate patchを適用する"
    - "Design Lockまで進行する"

  non_responsibilities:
    - "選択肢生成"
    - "Plan Review"
    - "ADR作成"
    - "実装設計"
    - "実装"
    - "人間の代わりの意思決定"

  input:
    - "planning request"
    - "human input"
    - "plan-state.yaml"

  output:
    - "human-readable response"
    - "machine-readable interface result"
    - "Design Lock handoff"

  human_gates:
    - "submit"
    - "submit plan"
    - "submit design"

  state_mutation:
    owner: "plan_interface"
    atomic: true
    revision_checked: true
    schema_validated: true

  skill_invocation:
    one_primary_skill_at_a_time: true
    direct_skill_calls_forbidden: true
    routing_by_state: true
    structured_result_required: true
```

## 動作例

```text
ユーザー:
02.SourceIngestionPOCのPlanを始めたい
```

```text
Plan Interface:
1. plan-state.yamlを確認
2. stateが存在しない
3. inspect-context Skillを呼ぶ
4. Contextを保存
5. discover-decisions Skillを呼べる状態にする
```

```text
discover-decisions Skill:
最初に決めるべき論点はSourceの対象範囲
```

```text
Plan Interface:
propose-options Skillを呼ぶ
```

```text
propose-options Skill:
案1 / 案2 / 案3と推奨を返す
```

```text
Plan Interface:
人間へ提示して停止
```

```text
ユーザー:
案2
```

```text
Plan Interface:
候補としてplan-state.yamlへ保存
まだ次へ進まない
```

```text
ユーザー:
submit
```

```text
Plan Interface:
submit-decision Skillを呼ぶ
State遷移を検証
provisional_acceptedへ更新
次のDecisionへ進む
```
