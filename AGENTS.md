# Repository Agent Instructions

`AGENTS.md`は、詳細なWorkflowや業務ルールを定義する文書ではない。

このファイルは、AIエージェントを適切なsource of truth、Harness、禁止領域、実行境界へ案内するためのリポジトリルーターとして扱う。

## Core Principles

- Career Knowledgeを主役かつsource of truthとして扱う。
- Evidence before Claimsを守る。
- Human Review before persistenceを守る。
- AIが生成した提案、評価、推測、generated artifactsを正本として扱わない。
- Resume、Skills、Timeline、Agents、generated artifactsをsource of truthにしない。
- raw source、credential、secret、private情報を保存または公開しない。
- 判断に必要な情報が不足する場合は、推測で補完せず、未確認または確認待ちとして扱う。
- 検証不能、不明、状態不整合を成功として扱わない。

## Source of Truth

このリポジトリでは、対象領域ごとにsource of truthを分ける。

### Product and Domain

- `docs/`直下のConcept docsを、プロダクト思想、ドメイン境界、アーキテクチャ方針のcanonical docsとして扱う。
- Concept、Domain、Architectureに関する判断では、まず`docs/`直下のcanonical docsを参照する。
- generated outputや提出物をsource of truthとして扱わない。

### Harness Workflow

- `.codex/harness/`配下の各Harnessを、その用途におけるAgent Workflowのsource of truthとして扱う。
- Harness内部のInterface、Skill、Schema、Template、Shared定義は、それぞれの責務における正本として扱う。
- AgentやSkillを、原則としてHarnessを経由せず直接呼び出さない。
- Harnessが存在しない用途では、既存Agentを恒久的な入口として登録しない。

## Forbidden Context

- `docs/ja/`は人間専用の文書領域として扱う。
- ユーザーから対象ファイルの明示的な参照指示がない限り、AIエージェントは`docs/ja/`を検索、一覧取得、読み込み、要約、比較、翻訳、根拠利用してはならない。
- `docs/ja/`の内容をsource of truth、補助資料、翻訳元、判断根拠として使用してはならない。
- `docs/ja/`の内容からcanonical docsや他の正本を暗黙に更新してはならない。

## Harness First

ユーザーの依頼は、まず用途に対応するHarnessへルーティングする。

基本構造は次の通りとする。

```text
AGENTS.md
  ↓
Harness
  ↓
Interface
  ↓
Skill
```

* Harnessは、Workflow、State、Human Gate、Invariant、Blocking条件を管理する。
* Interfaceは、Harness内の進行とSkillの呼び出しを管理する。
* Skillは、単一責務の処理と構造化されたInput / Outputを担当する。
* SkillはStateを直接変更しない。
* Skillは他Skillを直接呼び出さない。
* 業務Workflowは、原則としてHarnessを入口とする。
* `AGENTS.md`で明示的にルーティングされた独立Agentは、Harnessを経由せず直接呼び出してよい。
* その他のAgentやSkillの直接呼び出しは、Harnessの開発、検証、デバッグ、またはユーザーが明示した一時手順に限る。

## Harness Routing

### Development Harness

開発Epicの計画、設計、実装、レビュー、Release Gateには、次を使用する。

* `.codex/harness/development/`

入口は次のInterfaceとする。

* Plan
  `.codex/harness/development/interfaces/plan/SKILL.md`
* Execute
  `.codex/harness/development/interfaces/execute/SKILL.md`

詳細なWorkflow、Human Gate、State遷移、Skill責務、Review、Release Gateの規則は、Development Harness内の定義を参照する。

`AGENTS.md`側で同じ規則を再定義しない。

### Output Harness

職務経歴書、Skills、Timeline、PDF、応募先別成果物などの出力生成には、Output Harnessを使用する。

Output Harnessが未実装の場合は、既存の出力関連Skillまたはユーザーが明示した一時手順を使用する。

出力固有の業務ルールを`AGENTS.md`へ追加しない。

### Future Harnesses

用途ごとに専用Harnessを追加できる。

例:

- Ingestion Harness
- Knowledge Review Harness
- Knowledge Persistence Harness
- Export Harness

新しい用途を追加する場合は、Agentを直接入口にせず、Harnessの責務、Input、Output、State、Human Gate、Invariantを定義する。

## Boundary Changes

* ProductまたはDomainのsource of truth境界を変更する場合は、PlanとADRを通じて明示する。
* Harnessの責務、Workflow、State、Human Gate、Invariantの境界を変更する場合は、対象HarnessのPlanとDesign Lockを通じて明示する。
* generated artifactsから正本を暗黙に更新しない。
* 実行中にHarnessの責務またはDesign Lockを越える変更が必要になった場合は、処理を停止し、対応するPlanへ戻す。

## Repository Security

次の情報を、リポジトリ内のファイル、ログ、fixture、例外、generated artifacts、Git差分へ残さない。

* credential
* secret
* API key
* access token
* password
* private key
* 実在する機密情報
* 実在する個人情報を転用したfixture

検出、確認、検証ができない場合はfail closedとし、commit、push、Pull Request作成を停止する。

知識の取り込み、Review、永続化、raw source、個人情報の取扱規則は、対象HarnessのInvariant、Schema、Workflowをsource of truthとする。

`AGENTS.md`側で、知識運用固有のSecurityおよびPrivacy規則を再定義しない。

## Change and Release History

* リリースとして見える変更、バージョン付きのプロジェクト履歴、利用者に影響する変更は`CHANGELOG.md`へ記録する。
* `v1.0.0`未満では、Release Notesの作成を必須としない。
* `v1.0.0`以降のVersion Releaseでは、`CHANGELOG.md`の更新に加えてRelease Notesを作成する。
* Release Notesには、該当する範囲で次を記載する。

  * 主要な変更
  * 利用者への影響
  * 破壊的変更
  * Migration
  * 既知の制約
* 該当事項が存在しない項目を、推測や定型文で埋めない。
* Release Notesの保存場所および公開手順は、対象HarnessのRelease Workflowをsource of truthとする。
* Plan、ADR、Design Lock、Review、Release Gateは、対象HarnessのTemplateに従う。
* generated artifactsを変更履歴、Release Notes、設計判断のsource of truthとして扱わない。

## Repository Operations

Git操作が必要な場合は、次のGit Operations Agentを参照する。

- `.codex/agents/git-operations/AGENT.md`

`AGENTS.md`側でGit操作の詳細を定義しない。
