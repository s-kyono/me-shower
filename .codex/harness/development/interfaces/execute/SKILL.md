---
name: execute-interface
version: "1.0"
role: autonomous-execution-workflow-coordinator
---

# Execute Interface

## Purpose

Design Lockを実行契約として、Repository実装、独立Review、修正再提出、Release Gate、Repository Publish Agent向けhandoff生成までを自律的に進行する。

## Responsibilities

- `PLAN.md`、関連ADR、`DESIGN_LOCK.md`、`execution-state.yaml`を読み込む。
- RepositoryとGitの現在状態を確認する。
- 現在のstateに対して許可されたPrimary Skillを1つだけ呼び出す。
- Skill Result、State Patch、Blocking Issue、Deviationを検証する。
- `execution-state.yaml`を唯一のExecution現在地として更新する。
- Implementation側の修正・再提出回数を最大5回まで管理する。
- Review accepted後にのみRelease Gateへ進める。
- Release Gate passed後にのみRepository Publish Handoffを生成する。
- handoff生成後、上位Agent Router向けの構造化Agent Invocation Requestを返してDevelopment Workflowを終了する。
- Design Lock逸脱、安全境界違反、Git競合などで安全に停止する。

## Non-responsibilities

- Plan、ADR、Design Lockを勝手に変更しない。
- Scope、public API、persistence境界、source of truth境界を再決定しない。
- Skillの代わりに実装・Review・Release判定を行わない。
- Review findingを都合よく解釈しない。
- `git add`、commit、push、Pull Request作成、GitHub認証確認を行わない。
- Repository Publish Agentの内部状態やGit公開結果を所有しない。
- Repository Publish Agentを直接起動しない。実際の起動主体は上位Agent Routerとする。

## Inputs

Required:

- accepted `PLAN.md`
- accepted `DESIGN_LOCK.md`
- related ADRs
- repository root
- base branch
- working branch
- `execution-state.yaml`

## Outputs

### Runtime Status

- current state
- current Skill
- fix attempt count
- Design Lock alignment
- warnings
- blocking issues

### Safe-stop Report

- stop point
- stop reason
- completed operations
- changed files
- validation results
- Design Lock deviations
- safe next action

### Completion Result

- implementation diff
- accepted `REVIEW.md`
- passed `RELEASE_GATE.md`
- Repository Publish Handoff reference
- Agent Invocation Request
- downstream status
- remaining risks

## Human Gates

Normal execution does not require Human Action.

Human Action is required when:

- Scope or Non-goals must change.
- Design Lock or ADR conflicts with required implementation.
- source of truth, persistence, Safety Gate, or Human Review boundary must change.
- a major public API change or external dependency is required.
- sensitive data is detected and cannot be safely removed within Scope.
- fix attempt count reaches 5 without Review acceptance.
- Git conflictまたはunrelated changesによりhandoff対象差分を確定できない。

## State Mutation Rules

- Only this Interface may write `execution-state.yaml`.
- Skills return `state_patch`; they never write State directly.
- Validate revision, permissions, target schema, invariants, transition, and postconditions.
- Apply atomically and increment revision only after success.
- Re-read and validate State after writing.
- Fix attempt count belongs to the implementation/re-submission process, not the reviewer.

## Skill Invocation Rules

- Invoke exactly one Primary Skill per interaction.
- Skills may not invoke other Skills.
- Reviewer performs one independent evaluation per invocation.
- Review returns `accepted`, `changes_required`, or `blocked`.
- `apply-scope-fix` fixes only explicit Review findings within Design Lock.
- Release Gate validates and decides; it never modifies implementation.
- `create-repository-publish-handoff`はpassed Gateと同一差分に対するhandoffだけを生成する。
- Blocking deviation stops execution immediately.

## Review Priorities

1. Security
2. Reproducibility and operational stability
3. Maintainability and boundary clarity
4. Performance
5. Delivery speed and implementation size

Review may accept explicit trade-offs, but security, secret, privacy, raw-source, source-of-truth, and Human Review boundary violations are never accepted risks.

## Repository Publish Handoff Rules

- Release Gate must be `passed`.
- Secret, privacy, and raw-source scans must be `passed`.
- Reviewed diff hash and Release Gate checked diff hash must be explicit and identical.
- Implementation revision and approved changed files must be explicit.
- Base branch and working branch must be explicit and different.
- No unresolved Blocking Issue may remain.
- The Interface does not stage, commit, push, create a Pull Request, or check GitHub authentication.
- Commit SHA、remote head、Pull Request URLはRepository Publish Agent Resultをsource of truthとし、Execution Stateへ複製しない。
- Terminal State `development_completed`はDevelopment Harnessの責務完了だけを意味し、Git公開またはPull Request作成完了を意味しない。
- Agent Invocation Requestは`invoke_agent`、target、handoff reference、決定的run ID、自動起動可否、Human確認要否を明示する。
- 上位Agent RouterだけがInvocation Requestを解釈してRepository Publish Agentを起動する。
- Routerは共通run registryを参照し、同じrun IDが処理中または完了済みの場合は重複起動しない。
- 起動失敗時、RouterはRouter-owned Agent Invocation Resultを`invocation_failed`として返し、Execution Stateを直接変更しない。
- Development完了状態をAgent起動成功、Git公開成功、またはPull Request作成成功へ読み替えない。
