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
6. Human reviews important events
7. Reviewed events grow Career Knowledge
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

Even if a full review queue is not yet implemented in v0.3.0, this boundary should already be treated as fixed.

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
