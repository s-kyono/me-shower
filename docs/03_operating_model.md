# Operating Model

This document describes how me-shower should be operated day to day.

The goal is not to produce Resume output after every change. The goal is to continuously grow inspectable Career Knowledge from work traces while preserving evidence boundaries and Human Review.

## Daily Inputs

- GitHub: implementation, Pull Requests, change history
- Slack / Teams: discussion, review, and decision traces
- Daily Report: context, judgment, blockers, learning, and intent
- local memo: lightweight supporting notes

Freestyle inputs are first-class sources.

GitHub often shows what changed. Slack and Teams often show what was discussed. Daily Reports often show what the human understood, why they made a decision, and where they were blocked. Career Knowledge needs all of these.

## Operating Flow

```text
1. Work happens
2. Sources are collected
3. Source Intelligence normalizes them
4. Canonical Events are stored in source_sync
5. Timeline is generated for inspection
6. Human reviews candidate events against the Promotion Criteria
7. Only approved events grow Career Knowledge
8. Views are generated when needed
```

This sequence matters. me-shower should not jump directly from noisy inputs to Resume claims.

## How to Read Confidence

- `high`: strong source and extraction
- `medium`: usable, but review is helpful
- `low`: review first

Source Confidence is not a judgment of achievement value. It is an operational measure of source quality and extraction reliability.

## The Role of Human Review

Human Review exists so AI proposals do not become Career Knowledge automatically.

Its main roles are:

- stop exaggeration
- stop confidential leakage
- stop incorrect extraction
- decide whether an event should become long-term knowledge

The operating rule is:

```text
AI proposes.
Human reviews.
Career Knowledge persists.
```

Even if a full review queue is not yet implemented, this boundary should already be treated as fixed.

## Career Knowledge Promotion Criteria

A Canonical Event is not Career Knowledge. When it is stored in `source_sync`, it is only a reviewable candidate. Promotion Criteria are not a score of how impressive the work is; they are the persistence gate for deciding whether the candidate is safe and useful as reviewed, long-term Career Knowledge.

Promotion requires all of the following:

1. Supporting Evidence exists.
2. Source Confidence is `high` or `medium`; confidence never replaces Human Review, and `low` cannot be approved without stronger evidence and reassessment.
3. A human has reviewed the candidate and accepted the meaning of its summary, actions, decisions, and improvements.
4. Secrets, private URLs, confidential information, and sensitive internal names have been removed.
5. `observed_fact`, `human_interpretation`, `ai_inference`, and `claim_candidate` remain distinguishable; AI inference is not stored as fact.
6. The meaning has not been exaggerated or reshaped merely to improve a Resume or another View.
7. The reviewer confirms career relevance: the event contributes to long-term understanding of the person's work, judgment, learning, improvement, or repeatable strengths.

Career relevance is a retention decision, not a judgment that the work is prestigious or high-value. A routine event may be relevant, while an impressive-sounding but unsupported claim is not promotable.

Promotion review produces exactly one status:

- `approved`: all required checks pass; the accepted meaning may become Career Knowledge
- `rejected`: the candidate must not become Career Knowledge, including unsupported or misleading claims
- `deferred`: no current decision is appropriate, but the candidate may be reviewed later
- `needs_more_evidence`: the candidate has potential relevance but lacks sufficient support for approval

Only `approved` permits promotion. A failed required check must never be converted into approval because the wording is Resume-ready. `rejected`, `deferred`, and `needs_more_evidence` are valid outcomes, not errors to hide or auto-upgrade.

The minimum decision model is defined in `.codex/review-promotion/rules/promotion_criteria.yaml`. It is a contract for future Review Queue, Decision Log, and Career Knowledge Store work, not a runtime validation engine in v0.4.0.

## Log Responsibilities

- `CHANGELOG.md`: project-level release and change history
- `LOG.md`: design rationale, strict review results, and notes that connect to future improvements
- `app/data/daily_reports/*.md`: daily work, interests, learning, and technology-stack summaries treated as Source input
- future Review Decision Log: `approved`, `rejected`, `deferred`, and `needs_more_evidence` decisions for Canonical Events

These records are not interchangeable. A Daily Report or Daily Digest is Source, not Career Knowledge. It must pass through Source Intelligence, Promotion Criteria, and Human Review before any accepted meaning can become Career Knowledge. `CHANGELOG.md` records project changes, not individual promotion decisions, and `.codex/steering_sheets/change_log.md` is not an official project log.

## Handling Generated Output

- `generated/` should generally stay out of normal PR scope
- Timeline, PDF, and Resume previews are regenerable artifacts
- generated output must not become source of truth

Outputs are disposable compared with the underlying knowledge structure.

## Handling Raw Source

- raw source must not become long-term truth
- secrets, tokens, private URLs, and sensitive internal information must not be stored
- Evidence Guard must not be bypassed

Raw traces are useful as input material, but they are too unsafe and unstable to serve directly as long-term knowledge.

## Handling Skills

- Skills are not the authoritative career record
- Skills are agent operational knowledge
- Skills are used to improve source reading quality, review quality, and view generation quality

Even when Skills improve, the thing being grown is still Career Knowledge.

## Failure Modes

This section makes likely failure patterns explicit. Even if a change seems useful, it should be treated carefully if it pushes the system toward one of these failure modes.

### Resume Optimization Drift

If Resume wording is optimized too aggressively, Career Knowledge becomes subordinate to Resume presentation. This must be avoided.

### source_sync Over-Trust

`source_sync` is a Canonical Event Store, not reviewed Career Knowledge itself. Unreviewed extracted results must not be treated as final truth.

### Skills Expansion Drift

If Skills improvement becomes too central, the project drifts toward agent optimization. Skills are support infrastructure. Career Knowledge is the asset being grown.

### Timeline Canonization

Timeline is a derived view for inspecting flow. Appearing on the Timeline does not make something reviewed Career Knowledge.

### Daily Report Vacuum

Daily Reports are important freestyle inputs, but they are not meant to absorb an entire life log. They should focus on context, judgment, learning, and blockers relevant to Career Knowledge.

### AI Plausibility Trap

AI can produce plausible language. Plausibility is not evidence. AI inference must not be preserved as if it were the person’s actual experience.

### Convenience Drift

Convenience alone must not justify collapsing source-of-truth boundaries. Convenience matters, but it is not more important than Career Knowledge integrity.

## v0.x Operating Policy

- prioritize feature validation and operational learning
- do not collapse Concept or Boundary
- tolerate implementation density temporarily and reorganize at v1.0.0
- leave important decisions in logs and changelog where appropriate
