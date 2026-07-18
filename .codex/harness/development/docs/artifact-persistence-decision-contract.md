# Artifact Persistence Decision Contract

## Status

- Decision status: accepted design decision
- Scope: formal-adoption ownership, Human execution-authorization binding, and immutable Artifact revision evidence for Development Harness artifacts
- Implementation status: contract only
- Effective boundary: Artifact generation, persistence, and formal adoption are separate responsibilities

This contract uses **formal-adoption decision owner** instead of the less explicit term `canonicality owner`.

## Scope

This decision defines who may decide that an Artifact or Decision is formally adopted, how Plan readiness remains separate from Human implementation delegation, and how revisioned evidence binds both decisions to the execution package.

It does not define storage paths, Write Request or Reference Schemas, atomic persistence, State persistence, or an Artifact Writer implementation.

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

The compatibility result binds both the originally authorized Plan and the successor revision/hash. It creates a new immutable authorization-continuation record, with its own authorization revision, without altering the original Human grant or generating a new Human `granted` decision.

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

## Artifact Revision Model and Evidence Chain

The canonical evidence used to reach Execute is a chain of immutable, revision-addressed records. It preserves decisions, concretization, verification, delegation, and the selected execution target. It does not preserve complete conversations, reasoning traces, or raw work logs.

```text
Accepted Decision / ADR Decision Record
  → Plan Artifact Reference
  → Plan Review and Design Review References
  → Design Lock Reference
  → Readiness Evidence Reference
  → Human Authorization or Authorization Continuation Reference
  → Execute Handoff
```

Every Artifact Reference in this chain identifies at least:

```yaml
logical_artifact_id: string
artifact_revision: integer
content_hash: string
```

`content_hash` is a SHA-256 identity over a canonical Artifact envelope containing the exact persisted content bytes and all immutable Artifact metadata. It performs no semantic or newline normalization. The future Schema decision must fix the envelope serialization so independent readers produce the same hash; changing either content bytes or covered metadata changes the hash and requires a new revision.

A record that evaluates, locks, or hands off another subject also identifies:

```yaml
subject_logical_artifact_id: string
subject_revision: integer
subject_hash: string
```

An Execute Handoff must carry or reference enough of this chain to prove that the accepted Decisions, reviewed Plan, locked design, readiness result, Human authorization, and selected execution target all refer to the same revisions and hashes. Execute fails closed if a reference is missing, stale, superseded without valid continuation evidence, or inconsistent with another link.

### Distinct Revision Domains

The following revision domains are independent:

```text
Artifact revision
≠ Subject revision
≠ State revision
≠ Decision revision
≠ Authorization revision
```

Equal numeric values do not imply identity or synchronization. These domains must not be collapsed into one generic `revision` field.

| Revision or identifier | Meaning |
| --- | --- |
| Artifact revision | A version of immutable content and immutable Artifact metadata within one logical Artifact series |
| Subject revision | The version of the Plan, implementation, or other subject evaluated or locked by an Artifact |
| State revision | The optimistic-concurrency version of Workflow State; it does not version Artifact bytes |
| Decision revision | A version of one Decision's meaning, constraints, or selected option |
| Authorization revision | A version in the immutable authorization/continuation record series |
| Accepted Decision-set hash | A deterministic identity for the normalized set of accepted Decision IDs, Decision revisions, and decision-content hashes |

The accepted Decision-set hash is computed from a canonical, order-independent representation of the accepted Decision set. Exact serialization and Schema are deferred, but implementations must sort by stable Decision identity and must not depend on presentation order.

### Immutable Artifact Rule

Persisted Artifact revisions are immutable and create-only. A change to any content byte or immutable Artifact metadata creates a new Artifact revision, even when the change appears editorial. Neither AI nor the Writer may classify a change as harmless and overwrite the existing revision.

The canonical source is the revision-addressed Artifact Reference, not a fixed filename. A future fixed path such as `PLAN.md` may be a current view, generated view, pointer, or convenience copy, but State, Review, Design Lock, Human Authorization, and Execute Handoff must not use that path alone as canonical identity.

This contract does not select the final directory layout. A path such as a revisioned Plan location is illustrative only and does not establish Path Policy.

### Logical Artifact Identity

A logical Artifact is a stable series serving one purpose; an Artifact revision identifies one immutable member of that series.

```yaml
logical_artifact_id: main-plan
artifact_revision: 4
```

Logical IDs are stable within their Artifact type and repository scope. Revisions are positive, monotonically increasing integers allocated independently within a logical Artifact series. A gap is permitted after an abandoned allocation, but an existing revision is never reused for different bytes.

### Revision Allocation Ownership

Revision allocation belongs to the Interface acting through a future Persistence Orchestrator:

```text
Skill
  → generates an Artifact Candidate without assigning a final revision

Interface / Persistence Orchestrator
  → resolves the logical Artifact series
  → verifies expected latest revision and hash
  → allocates the next Artifact revision
  → issues a create-only persistence request

Artifact Writer
  → writes only the assigned revision
  → never chooses, increments, or reuses a revision independently
```

The allocation and persistence mechanics are not implemented by this decision.

### Artifact, Workflow State, and Authorization Separation

Artifact revisions change only when Artifact content or immutable metadata changes. Workflow status changes do not rewrite the Artifact or create a new Artifact revision by themselves.

```text
Plan Artifact revision 4 remains immutable
Workflow State may move drafting → reviewing → ready_for_delegation
Human Authorization remains a separate immutable record series
```

Workflow State owns current status and current references. Human authorization owns delegation evidence. Neither status nor authorization is written back into Plan Artifact content.

### Human Authorization Revision Binding

An authorization record binds to a specific Plan logical ID, Artifact revision, content hash, accepted Decision-set hash, and readiness evidence:

```yaml
authorization_revision: 1
authorized_plan_logical_id: main-plan
authorized_plan_revision: 4
authorized_plan_hash: string
authorized_decision_set_hash: string
readiness_evidence_reference: object
```

The original Human authorization record is immutable. When a later Plan qualifies for automatic delegation continuation under the previously defined compatibility rules, the Harness produces a new immutable authorization-continuation record with the next authorization revision. That record references the original Human grant, the preceding effective authorization revision, the successor Plan revision/hash, its Decision-set hash, fresh readiness evidence, and the compatibility evidence. It records derived continuity; it does not impersonate a new Human grant.

When continuation conditions fail, no continuation record may be created. The old authorization remains historical evidence but is ineffective for the new Plan, and Human reauthorization is required.

### Artifact-specific Revision Bindings

| Artifact or record | Revision identity | Required subject binding |
| --- | --- | --- |
| Decision / ADR Artifact | Logical ADR ID and Artifact revision; Decision ID and Decision revision are distinct | Decision content hash; Human accept/reject/defer remains a separate immutable Decision Record |
| Plan | Plan logical ID and Artifact revision | Accepted Decision-set hash |
| Plan Review | Review logical ID and Artifact revision | Plan logical ID, Plan revision/hash, accepted Decision-set hash |
| Design Review / Guardrail Validation | Evidence logical ID and Artifact revision | Plan logical ID, Plan revision/hash, accepted Decision-set hash |
| Design Lock | Design Lock logical ID and Artifact revision | Plan logical ID, Plan revision/hash, accepted Decision-set hash |
| Implementation Review | Review logical ID and Artifact revision | Implementation revision and repository snapshot hash |
| Release Gate | Gate logical ID and Artifact revision | Implementation revision and checked repository snapshot hash |
| Repository Publish Handoff | Handoff logical ID and Artifact revision | Accepted Decision-set hash, Plan reference, Plan Review and Design Lock references, readiness reference, authorization/effective binding reference, implementation revision/hash, Implementation Review reference, and Release Gate reference |

Re-reviewing unchanged Plan or implementation content does not change the subject revision. It creates a new Review Artifact revision in the relevant Review series. Changing the Plan creates a new Plan Artifact revision and makes prior Plan Review and Design Lock evidence stale for that new revision.

ADR content and Human Decision status are also separate: changing an ADR's prose or metadata creates a new ADR Artifact revision, while accept, reject, or defer is recorded in an immutable Decision Record bound to the Decision revision and hash. Approval is never implemented by editing status inside the persisted ADR revision.

### Superseded Artifacts

Creating a new revision does not delete or modify an older revision. Current State may point to the new reference, and the new Artifact metadata or a separate relationship record may identify the predecessor:

```yaml
supersedes:
  logical_artifact_id: main-plan
  artifact_revision: 3
  content_hash: string
```

Supersession is a relationship, not an in-place status update to the old Artifact. Historical revisions remain addressable for evidence and audit. An older revision cannot be used as current execution evidence unless the Workflow explicitly selects it and all dependent evidence and authorization bind to that exact revision.

### Stale-write Prevention

A future create request must carry at least the following concurrency preconditions at the contract level:

```yaml
logical_artifact_id: main-plan
new_artifact_revision: 5
expected_latest_revision: 4
expected_latest_hash: string
content_hash: string
```

The Persistence Orchestrator verifies the expected latest revision and hash before allocation and again as part of the create-only operation. Any mismatch is blocked; last-writer-wins is forbidden. A stale State revision cannot authorize a write merely because its requested new revision is not yet visible to the caller.

### Idempotency

Write outcomes are determined by revision and hash:

| Existing condition | Required outcome |
| --- | --- |
| Same logical ID, same revision, same content hash | `already_written`; idempotent success returning the existing reference |
| Same logical ID, same revision, different content hash | `blocked`; never overwrite |
| New revision with stale expected latest revision or hash | `blocked` |
| New revision with current expected latest revision/hash and no target collision | Eligible for create-only persistence |

`already_written` must verify the persisted bytes and immutable metadata represented by the hash; matching only a caller-supplied value is insufficient.

### Evidence Retention Boundary

Revisioned persistence is limited to formal evidence needed to reconstruct execution eligibility:

- accepted Decisions and their decision records;
- Plan concretization;
- Review, Design Lock, readiness, and guardrail evidence;
- Human authorization and continuation records; and
- Execute and repository-publish handoff evidence.

It must not retain complete conversations, hidden reasoning, complete Tool output, temporary experiments, unnecessary intermediate generations, raw source, credentials, secrets, private information, or personal information. Revision history is not permission to persist prohibited content.

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
Artifact type and Path Policy
```

That decision must map each Artifact type and logical series to allowed repository-relative locations without changing the immutable revision model established here.
