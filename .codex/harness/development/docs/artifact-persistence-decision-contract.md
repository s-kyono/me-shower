# Artifact Persistence Decision Contract

## Status

- Decision status: accepted design decision
- Scope: formal-adoption ownership for Development Harness artifacts
- Implementation status: contract only
- Effective boundary: Artifact generation, persistence, and formal adoption are separate responsibilities

This contract uses **formal-adoption decision owner** instead of the less explicit term `canonicality owner`.

## Scope

This decision defines only who may decide that an Artifact, decision, or execution package is formally adopted or executable.

It does not define storage paths, revision history, Write Request fields, atomic persistence, State persistence, or an Artifact Writer implementation.

The governing separation is:

```text
Skill
  → generates content or a candidate

Future Artifact Writer
  → persists a validated request and returns a reference

Human Action or Harness Guard
  → decides formal adoption or execution eligibility
```

The following statements are invariants:

```text
Artifact Written
≠ Artifact Accepted

Human Decision Approval
≠ Human approval of every line of a Plan

Plan Completed
≠ Execution-ready

Execution Readiness Passed
= implementation may start from the accepted Decisions and locked execution contract
```

## Formal-adoption Decision Owners

Formal adoption is never an Artifact Writer responsibility.

- A human formally adopts important Decisions presented through the Plan decision loop.
- A human formally adopts an ADR when that ADR requires a durable architecture decision.
- The Harness determines whether the complete planning package is execution-ready.
- Workflow Review and Release Gate decisions determine whether implementation may advance, but their Artifacts do not become the implementation source of truth.
- The Repository Publish Handoff becomes eligible for downstream invocation only through a passed Release Gate and Runtime Guards.

Artifact existence, successful persistence, valid Markdown, valid metadata, or a returned Artifact Reference does not by itself grant any of these statuses.

## Human Decision Approval

Human approval applies to important choices, not to a second line-by-line approval of the generated Plan.

```text
AI-assisted decision discovery
  → realistic options
  → Human selects an option
  → Interface records the accepted Decision
```

The accepted Decision is the formal basis for downstream planning. A generated recommendation, selected UI value, persisted candidate, or AI summary is not equivalent to a Human Decision.

Human involvement is required primarily for:

- selection of an important Decision;
- a change to an accepted Decision;
- a source-of-truth or responsibility-boundary change;
- a material security, privacy, personal-information, or external-publication judgment;
- an irreversible operation; or
- an ADR explicitly governed by a Human Gate.

The Harness must not request another general approval merely because the Plan text, implementation strategy, or implementation design was refined within accepted Decisions.

## AI Concretization Responsibility

After the required Decisions are accepted, Plan Skills may:

- turn accepted Decisions into a complete Plan;
- complete the implementation strategy;
- complete the implementation design;
- identify unresolved questions and contradictions;
- detect deviation from accepted Decisions;
- produce reviewable Plan, ADR, and Design Lock candidates; and
- refine technical details within the accepted direction.

AI may not formally adopt a new important Decision or materially change an accepted Decision under the label of implementation detail.

## Harness Execution Readiness

The Harness, not a Skill and not the Artifact Writer, owns the execution GO decision.

Execution Readiness requires all of the following conditions:

```yaml
execution_readiness:
  required_decisions_accepted: true
  unresolved_decisions: 0
  plan_review: accepted
  implementation_strategy_complete: true
  implementation_design_complete: true
  design_lock: locked
  decision_drift: false
  unresolved_blocking_issues: 0
```

This is a design-level condition set, not a Schema introduced by this commit.

The Harness may proceed to Execute without a second Human approval of the complete Plan text only when every condition is verifiably satisfied. Missing, unknown, stale, or contradictory evidence fails closed.

## Decision Drift

Decision Drift is a material change to the direction, constraint, responsibility boundary, or source of truth established by an accepted Human Decision.

Concretization remains within the accepted direction:

```text
Accepted Decision:
Store in local files

Concretization:
Store as revisioned Markdown files
```

Decision Drift changes the accepted direction:

```text
Accepted Decision:
Store in local files

Drift:
Store in PostgreSQL
```

When Decision Drift is detected:

1. Execution Readiness fails.
2. Automatic transition to Execute stops.
3. The affected important Decision returns to Human decision-making.
4. AI may explain the drift and present options, but may not adopt the replacement.

The Artifact Writer must not resolve or waive Decision Drift.

## Artifact Ownership Matrix

| Artifact or record | Content generator | Persistence owner | Formal-adoption or execution decision owner |
| --- | --- | --- | --- |
| Decision Candidate | Plan Skills | Future Artifact Writer | Human |
| Accepted Decision | Plan Interface records the Human Action | Future Artifact Writer | Human |
| Plan Candidate | `assemble-plan` | Future Artifact Writer | Not independently adopted |
| Execution-ready Plan | Plan Skills, based on accepted Decisions | Future Artifact Writer | Harness Execution Readiness |
| ADR Candidate | `build-adr-candidates` | Future Artifact Writer | Not independently adopted |
| Accepted ADR | Future Human Action handling through the Plan Interface | Future Artifact Writer | Human |
| Design Lock Candidate | `lock-design` | Future Artifact Writer | Not independently adopted |
| Locked Design Lock | Plan Interface records the ready execution contract | Future Artifact Writer | Harness Guard; Decision Drift returns to Human |
| Plan Review | `review-plan` | Future Artifact Writer | Review record; not a source of truth |
| Implementation Review | `review-implementation` | Future Artifact Writer | Workflow review decision; not the implementation source of truth |
| Release Gate | `run-release-gate` | Future Artifact Writer | Workflow release decision; not the implementation source of truth |
| Repository Publish Handoff | `create-repository-publish-handoff` under the Execute Interface | Future Artifact Writer | Passed Release Gate and Runtime Guards |

Persisted candidates remain candidates. Review and Gate Artifacts remain records of evaluation. They do not replace the Plan, Design Lock, accepted Decisions, implementation diff, or repository as their respective sources of truth.

## Responsibilities Denied to the Artifact Writer

The future Artifact Writer must not decide or alter:

- Decision adoption;
- Plan execution eligibility;
- ADR accept, reject, or defer status;
- Design Lock validity;
- Review result;
- Release Gate result;
- formal or canonical status;
- Human Action authenticity;
- Decision Drift disposition; or
- Workflow State transition.

The Writer's maximum responsibility is to validate a persistence request within its future contract, persist the supplied candidate safely, validate the stored bytes, and return an Artifact Reference. Successful write completion does not imply formal adoption.

## Current Workflow Alignment

The current Plan Workflow and Schema remain unchanged by this decision. Existing `submit_plan` and `submit_design` actions are not implemented or redefined here.

Future Workflow alignment must preserve this accepted ownership rule: Human Actions adopt important Decisions, while Harness Execution Readiness decides whether the complete package may enter Execute. Alignment work must not silently reinterpret persisted files as Human approval.

## Decisions Intentionally Deferred

The following remain future decisions:

- revision history versus fixed-path replacement;
- Artifact-first versus State-first update ordering;
- orphan Artifact policy;
- required Artifact Write Request fields;
- required Artifact Reference fields;
- required Artifact Write Result fields;
- Artifact type and Path Policy;
- security scan ownership;
- atomic Writer behavior;
- State persistence;
- `submit_plan` execution implementation;
- ADR Human Gate implementation;
- Artifact Writer implementation;
- Schema additions; and
- Workflow changes.

## Next Design Decision

The next Artifact Persistence design decision is:

```text
revision history versus fixed-path replacement
```

That decision must be made before defining final Path Policy, replacement preconditions, or Artifact Reference structure.
