# Artifact Persistence Decision Contract

## Status

- Decision status: accepted design decision
- Scope: formal-adoption ownership and Human execution-authorization binding for Development Harness artifacts
- Implementation status: contract only
- Effective boundary: Artifact generation, persistence, and formal adoption are separate responsibilities

This contract uses **formal-adoption decision owner** instead of the less explicit term `canonicality owner`.

## Scope

This decision defines who may decide that an Artifact or Decision is formally adopted, how Plan readiness remains separate from Human implementation delegation, and how both decisions bind to the execution package.

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
= the Plan is eligible for Human delegation, but implementation is not yet authorized
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

When every condition is verifiably satisfied, the Harness may mark the Plan `ready_for_delegation` without requesting line-by-line Human approval of the complete Plan text. This does not authorize Execute. Missing, unknown, stale, or contradictory evidence fails closed.

## Human Authorization and Artifact Status Binding

Plan completion and Human delegation are independent state dimensions.

```text
ready_for_delegation
= implementation is sufficiently specified and guarded

execution_authorization.status == granted
= a Human has delegated implementation of the bound Plan
```

Neither condition implies the other. Execute may start only when both are valid and mutually consistent.

### Plan Completion Status

The design-level Plan completion statuses are:

| Plan status | Meaning | Update owner |
| --- | --- | --- |
| `drafting` | Plan, implementation strategy, design, or guardrails are being created or revised | Plan Interface |
| `reviewing` | Specialist validation and readiness evidence are being produced | Plan Interface |
| `changes_required` | Review found a correctable issue within accepted Decisions | Plan Interface |
| `ready_for_delegation` | All readiness conditions for one Plan revision and hash passed | Plan Interface after Harness aggregation |
| `blocked` | AI and Harness cannot resolve the issue without another authority or missing input | Interface Guard |
| `superseded` | A newer Plan revision replaced this Plan | Plan Interface |

AI may generate the evidence used by these statuses, but no individual Skill may directly declare `ready_for_delegation`. The Plan Interface may set it only after deterministic aggregation of all required evidence.

During `drafting`, repository inspection, design work, accepted-Decision concretization, guardrail definition, and design-document generation do not require repeated Human authorization. A `changes_required` result may return to `drafting` without Human involvement when the correction stays within accepted Decisions and the existing delegation boundary.

### Human Execution Authorization Status

The separate Human delegation status is:

| Authorization status | Meaning | Update owner |
| --- | --- | --- |
| `not_granted` | No Human implementation delegation is effective | Initial state, or an explicit Human decision not to delegate |
| `granted` | A Human explicitly delegated implementation of the bound Plan and Decisions | Human Action only |
| `revoked` | A previous delegation is no longer effective | Human Action or a material Safety Guard |
| `revoked → granted` | Delegation is restored after another explicit evaluation | Human Action only |

AI, Skills, the Plan Interface, the Execute Interface, Harness aggregation, and the Artifact Writer must not originate a `granted` status.

A material Safety Guard automatically changes an effective authorization to `revoked` and stops execution. This is a protective invalidation, not a claim about Human intent. It applies when an accepted Decision changes, Decision Drift occurs, scope materially expands, a source-of-truth or security boundary changes, guardrails weaken, an irreversible operation is added, external-publication scope changes, or another defined material safety precondition fails. Only a subsequent Human Action may restore `granted`.

### Implementation Start Condition

Execute may begin only when:

```text
current_plan.status == ready_for_delegation
AND
execution_authorization.status == granted
AND
effective authorization binding matches the current Plan, Decision set, and readiness evidence
```

`ready_for_delegation` alone is never sufficient. A valid Human grant bound to a stale, superseded, or different Plan is also insufficient.

## Authorization Binding

A Human Action is not represented by an unbound `GO` string. The immutable Human grant must identify at least:

```yaml
execution_authorization:
  status: granted
  authorized_by: human
  authorization_grant_id: string
  authorized_plan_revision: integer
  authorized_plan_hash: string
  authorized_decision_set_hash: string
  readiness_evidence_reference: string
  granted_at: string
  revoked_at: string | null
  revocation_reason_reference: string | null
```

The Human Action is accepted only through the trusted Human interaction boundary. The Plan Interface validates that the action came from that boundary, was explicit, targeted a currently `ready_for_delegation` Plan, and matched its revision, content hash, Decision-set hash, and readiness evidence. The Interface records the action; it does not infer, recommend, or synthesize it.

The Human grant record is immutable. Revocation is a separate status change with a reason reference; it must not rewrite who granted the authorization or what was originally authorized.

## Readiness Verification Separation

No single Skill or Agent may subjectively establish readiness. Specialist checks produce evidence only:

| Verification | Responsibility | Required binding |
| --- | --- | --- |
| Decision Drift Check | Verify that the Plan remains within accepted Decisions | Plan revision, Plan hash, Decision-set hash |
| Plan Review | Verify completeness, internal consistency, clarity, and unresolved items | Plan revision, Plan hash, Decision-set hash |
| Design Review | Verify implementation strategy and design are executable | Plan revision, Plan hash, Decision-set hash |
| Guardrail Validation | Verify allowed changes, prohibitions, validation, and stop conditions | Plan revision, Plan hash, Decision-set hash |

These are required evidence categories, not new Skills or Schemas introduced by this contract. Each result must be independently identifiable and must not set Plan status or Human authorization.

The Plan Interface aggregates the results and must verify:

- every required evidence category exists and passed;
- all results bind to the same Plan revision and Plan hash;
- all results bind to the same accepted Decision-set hash;
- no result is stale or superseded;
- all required Decisions are accepted;
- no unresolved Decision remains; and
- no unresolved Blocking Issue remains.

Only then may the Plan Interface set `ready_for_delegation`. It still may not create Human delegation.

## Plan Revision and Authorization Continuation

An authorization is initially bound to the exact Plan revision and hash presented to the Human. A later Plan revision does not automatically inherit authorization.

To avoid unnecessary Human Gates for implementation detail, the original immutable Human grant may remain effective for a successor Plan only when the Harness produces a deterministic delegation-compatibility result proving all of the following:

- the accepted Decision-set hash is unchanged;
- there is no Decision Drift;
- scope is not expanded;
- source-of-truth, security, privacy, and publication boundaries are unchanged;
- responsibility ownership is unchanged;
- guardrails are not weakened;
- no irreversible operation is added;
- changes are limited to technical detail within the granted direction; and
- the successor Plan is reviewed again and reaches `ready_for_delegation` with fresh evidence.

The compatibility result binds both the originally authorized Plan and the successor revision/hash. It creates an **effective authorization binding** for the successor without altering the immutable Human grant or generating a new `granted` status.

Examples that may qualify include file selection, function or class naming, additional tests, implementation order, and error-handling detail within accepted Decisions.

Any failed, missing, or unknown compatibility condition invalidates carry-forward and changes authorization to `revoked`. A Human must explicitly grant authorization again for the successor Plan.

Human reauthorization is always required for:

- an accepted Decision change or Decision Drift;
- material scope expansion;
- source-of-truth change;
- security, privacy, or external-publication boundary change;
- responsibility-owner change;
- guardrail weakening;
- an added irreversible operation; or
- a Plan whose relation to the original authorization cannot be verified.

## Execute Interface Final Verification

The Execute Interface does not repeat Plan or Design Review. Before implementation it verifies only that:

- the current Plan is `ready_for_delegation` and is not superseded;
- authorization is `granted` and not revoked;
- the effective authorized Plan revision equals the current Plan revision;
- the effective authorized Plan hash equals the current Plan hash;
- the authorized Decision-set hash equals the current accepted Decision-set hash;
- readiness evidence is present, current, and bound to the same revision and hashes; and
- any authorization-continuation evidence is valid when the current Plan differs from the original Human grant.

Any mismatch, missing evidence, stale reference, unknown status, Decision Drift, or unresolved Blocking Issue fails closed before Execute begins.

## Status Update Owner Matrix

| Status | Update owner | Condition |
| --- | --- | --- |
| `drafting` | Plan Interface | Plan creation or revision starts |
| `reviewing` | Plan Interface | Specialist validation starts |
| `changes_required` | Plan Interface | Review evidence requires correction |
| `ready_for_delegation` | Plan Interface | All evidence for one revision/hash/Decision set passed |
| `blocked` | Interface Guard | The issue cannot be resolved automatically within authority |
| `superseded` | Plan Interface | A new Plan revision replaces the old Plan |
| `not_granted` | Initial state or Human Action | No delegation has been granted |
| `granted` | Human Action only | Explicit delegation bound to the ready Plan |
| `revoked` | Human Action or material Safety Guard | Explicit withdrawal or automatic protective invalidation |
| `revoked → granted` | Human Action only | Explicit reauthorization |

## Fail-closed Conditions

Execution authorization is ineffective when any of the following is true:

- Plan status is not `ready_for_delegation`;
- authorization is absent, `not_granted`, or `revoked`;
- Plan revision, Plan hash, or Decision-set hash does not match;
- readiness evidence is missing, stale, inconsistent, or mixed across revisions;
- Plan or Design Review did not pass;
- Decision Drift exists;
- a successor Plan lacks valid delegation-compatibility evidence;
- a guardrail weakened or a protected boundary changed;
- an unresolved Decision or Blocking Issue exists; or
- Human Action provenance cannot be verified.

Artifact persistence success cannot override any fail-closed condition.

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

Future Workflow alignment must preserve this accepted ownership rule: Human Actions adopt important Decisions, Harness Execution Readiness establishes that a Plan is eligible for delegation, and a bound Human execution authorization establishes that implementation may proceed. Execute requires both readiness and authorization. Alignment work must not silently reinterpret persisted files as Human approval.

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
