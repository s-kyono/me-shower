# Future Epic: Agent Runtime Supervisor

## Status

- Lifecycle: future consideration
- Implementation status: not implemented
- Decision status: not approved or design-locked
- Relationship to current work: independent from the Development Harness Execute State fixed-guard work

This document records a future Epic candidate. It is not a runtime contract, an accepted architecture decision, an implementation plan, or a source of truth for current Execution State behavior. Any implementation requires a future Plan, Human Review, ADR where appropriate, and Design Lock.

## Background

The Development Harness runs on a host machine. Future operation may include:

- concurrent Agent and Subagent runs;
- long-running jobs;
- stalled reasoning or Tool execution;
- abnormal termination of Codex or Claude CLI processes;
- Session rollover as a Context limit approaches;
- continuation in another Session; and
- auditable execution history.

Execution State represents current Workflow state, but it is not intended to own process liveness, heartbeat, Session lifecycle, crash recovery, or append-only runtime audit history. Those concerns require a separate runtime supervision boundary.

## Candidate Outcomes

The future Epic should evaluate:

- Agent and Subagent heartbeat;
- Parent and Child Run tracking;
- Context usage monitoring;
- Session rollover;
- structured Checkpoint generation;
- crash-safe resume;
- append-only audit logging;
- Stale Run detection;
- Orphaned Subagent detection;
- idempotent restart; and
- recovery history suitable for Human Review.

## Candidate Responsibility Boundaries

```text
OS Process Supervisor
  → Codex / Claude CLI Process liveness and process lifecycle

Agent Runtime Supervisor
  → Run, Heartbeat, Context, Checkpoint, and Resume coordination

Development Harness
  → Development Workflow execution

Execution State
  → Canonical current Workflow state

Transition Journal
  → Append-only State transition and execution history

Checkpoint
  → Structured continuation information for a new Session
```

These boundaries are candidates, not accepted ownership assignments. In particular, the Agent Runtime Supervisor must not silently become the source of truth for Development Workflow state.

## Candidate Transition Journal Event

```yaml
event_id: string
run_id: string
agent_id: string
parent_agent_id: string | null

timestamp: string
event_type: string

state_before: string | null
state_after: string | null
revision_before: integer | null
revision_after: integer | null

action: string | null
skill: string | null
artifact_references: []

status: started | completed | failed | blocked | timed_out
error_reference: string | null
```

The journal candidate is append-only audit history. It must not authorize transitions, replace Execution State, or make generated Agent output authoritative.

## Candidate Checkpoint

```yaml
run_id: string
workflow: string
current_state: string
state_revision: integer

completed_steps: []
pending_step: string | null

canonical_artifacts: []
unresolved_blocking_issues: []
decisions: []

repository:
  head: string
  working_tree_snapshot_hash: string

resume_instruction: string
```

A Checkpoint is a continuation aid, not a replacement for canonical State, Human decisions, Design Lock, or referenced artifacts. Resume must validate all references and revisions and fail closed on missing, stale, or inconsistent inputs.

## Candidate Context Monitoring Policy

- Prepare a Checkpoint when Context usage reaches a warning threshold.
- Do not begin a new Workflow step when approaching the hard limit.
- Finish the current step only at a safe boundary.
- Generate a structured Continuation Artifact.
- Hand off to a new Session.
- Resume from validated State, decisions, artifact references, and incomplete work.
- Do not make a full conversation transcript the resume contract.

Thresholds, Context measurement mechanisms, supported CLIs, and Session handoff behavior remain undecided.

## Safety and Audit Constraints

- Raw source, credentials, secrets, access tokens, private information, and personal information must not enter heartbeat records, journals, Checkpoints, errors, or continuation artifacts.
- Audit and Checkpoint records should contain references and minimum structured metadata, not copied artifact bodies, full Tool output, or conversation history.
- AI-generated recovery instructions are proposals until validated against canonical State and artifacts.
- Unknown liveness, stale State, revision mismatch, missing artifacts, or inconsistent repository snapshots must fail closed.
- Restart and resume must be idempotent and must not duplicate irreversible actions.
- Recovery history must remain inspectable by a human.

## Explicitly Not Implemented

This Epic record does not implement or modify:

- Supervisor processes;
- heartbeat;
- Transition Journal;
- Checkpoint persistence;
- Session rollover;
- automatic recovery;
- Context usage monitoring;
- OS process management;
- Development Harness Workflow;
- current Execute State fixed guards; or
- Execution State fields or Schema.

## Reconsideration Triggers

Reconsider this Epic when one or more of the following becomes true:

- concurrent Agent or Subagent execution becomes a supported operating mode;
- a long-running job requires reliable liveness or timeout detection;
- a real run is lost or cannot be resumed after CLI, host, or Session failure;
- Context limits repeatedly force manual continuation;
- stale or orphaned runs cannot be distinguished safely;
- audit requirements exceed what current Execution State and artifacts can explain;
- restart can cause duplicate actions; or
- operational evidence justifies defining persistence, retention, privacy, and recovery guarantees.

Before implementation, create a dedicated Plan that defines ownership, State and Journal consistency, persistence and locking, retention, security and privacy boundaries, failure modes, Human Gates, migration, and tests. Accept any architecture boundary changes through the repository's required Human Review and ADR process.
