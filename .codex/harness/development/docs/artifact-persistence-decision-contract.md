# Artifact Persistence Decision Contract

## Status

- Decision status: accepted design decision
- Scope: formal-adoption ownership, Human execution-authorization binding, immutable revision evidence, Artifact type-to-path policy, persistence boundary contracts, Artifact-first State consistency, orphan recovery, and pre-persistence Candidate security policy for Development Harness artifacts
- Implementation status: contract only
- Effective boundary: Artifact generation, persistence, and formal adoption are separate responsibilities

This contract uses **formal-adoption decision owner** instead of the less explicit term `canonicality owner`.

## Scope

This decision defines who may decide that an Artifact or Decision is formally adopted, how Plan readiness remains separate from Human implementation delegation, how revisioned evidence binds both decisions to the execution package, how each registered Artifact type maps to a safe repository path, the required fields that cross the Artifact Persistence boundary, how a verified Artifact Reference is reflected into Workflow State, how an incomplete State connection is recovered safely, and how a Development Artifact Candidate is cleared for persistence.

It does not implement Path Policy, Schema files, atomic persistence, State persistence, or an Artifact Writer.

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
  → Agent-owned Repository Publish Result Reference
```

The final link is an external ownership boundary. The Repository Publish Agent generates, persists, and owns the formal state of the Repository Publish Result body. The Development Harness generates the Repository Publish Handoff and may retain only an Agent-owned Repository Publish Result Reference. It must not generate, modify, persist, or Git-manage the Result body. The future Reference contract may carry `owner`, `result_id`, `result_revision`, `content_hash`, and `location_reference`, but this decision does not define a Reference Schema or State field and does not register `repository_publish_result_reference` as a Development Harness Artifact type.

The following is conceptual only:

```yaml
repository_publish_result_reference:
  owner: repository_publish_agent
  result_id: string
  result_revision: integer
  content_hash: string
  location_reference: string
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

The canonical source is the revision-addressed Artifact Reference, not a fixed filename. A future fixed path such as `PLAN.md` may only be a generated Convenience View, but State, Review, Design Lock, Human Authorization, and Execute Handoff must not use that path alone as canonical identity.

The registered directory layout and Path Policy are defined below. They preserve this immutable revision rule; changing the layout requires a new accepted Path Policy decision and must not silently reinterpret existing references.

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

ADR content and Human Decision status are also separate. The ADR Artifact contains the Decision background, problem, options, rationale, and technical content. Its `status` describes only the document lifecycle and is limited to `draft`, `proposed`, or `superseded`; `accepted`, `rejected`, and `deferred` are forbidden ADR lifecycle values. Changing ADR prose, metadata, or lifecycle status creates a new ADR Artifact revision.

Human accept, reject, or defer is recorded only in an immutable `decision_record` bound to the Decision revision and hash. When an ADR carries the Decision content, the record must also bind to and verify the subject ADR logical ID, ADR revision, and ADR content hash. An ADR revision and its `decision_record` belong to separate revision domains. Editing an ADR body to say `accepted` does not pass the Human Gate, and an ADR without a valid `decision_record` must not enter the Accepted Decision Set. ADR lifecycle status is never a substitute for Human Decision status. The current ADR Template body is outside this change's scope; when that Template contract is implemented, a Schema or validator must enforce the lifecycle vocabulary.

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

A lower-level trusted create command, produced only after the Persistence Orchestrator accepts a Write Request and allocates a revision, must carry at least the following values:

```yaml
logical_artifact_id: main-plan
new_artifact_revision: 5
expected_latest_revision: 4
expected_latest_hash: string
content_hash: string
```

The boundary Write Request defined below does not carry `new_artifact_revision` or caller-supplied `content_hash`; those values are derived after its preconditions pass. The Persistence Orchestrator verifies the expected latest revision and hash before allocation and again through the trusted create-only operation. Any mismatch is blocked; last-writer-wins is forbidden. A stale State revision cannot authorize a write merely because its allocated new revision is not yet visible to the caller.

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

## Artifact Type and Path Policy

### Artifact Root

The repository-relative Artifact Root is fixed as:

```text
.codex/harness/development/artifacts/
```

All canonical revisioned Artifacts owned by the Development Harness must be stored below this root according to the registered type pattern. Externally owned result bodies are not stored below this root merely because the Harness retains a reference to them. A repository-relative Artifact Reference for a Development Harness Artifact includes this full path. An absolute path, a path outside the repository, `..`, an empty segment, a backslash separator, or any normalized or symlink-resolved destination outside Artifact Root is invalid.

Artifact Root itself must resolve inside the real Repository Root. A Skill, model response, Human-supplied title, or other untrusted input cannot supply a target path.

### Artifact Classifications

| Classification | Purpose | Registered types |
| --- | --- | --- |
| Decision Artifact | Preserve important Decision content, rationale, selection, and Human disposition evidence | `adr`, `decision_record`, `authorization_grant`, `authorization_continuation`, `authorization_revocation` |
| Planning Artifact | Concretize accepted Decisions and prove Plan readiness | `plan`, `plan_review`, `design_review`, `guardrail_validation`, `design_lock`, `readiness_evidence` |
| Execution Evidence | Prove implementation review, correction need, release eligibility, and repository-publish handoff | `implementation_review`, `release_gate`, `fix_request`, `repository_publish_handoff` |
| Convenience View | Optional regenerated Human-readable display; never canonical evidence | No registered canonical type in the initial implementation |

`decision_record` is the single structured type for Human accept, reject, or defer actions, including an ADR decision. Separate `adr_decision_record` and `human_decision_record` types are not registered because they would duplicate that responsibility. Generic ambiguous types such as `review` are also prohibited; Plan, design, and implementation reviews remain distinct.

Authorization records are classified with Decision evidence because they preserve Human delegation or its derived continuation/revocation. They remain distinct registered types because their provenance and transition semantics differ.

The Agent-owned Repository Publish Result body and its future external Reference are outside this registry. Retaining an external Result Reference does not transfer content, persistence, formal-state, or Git-management ownership to the Development Harness.

### Closed Artifact Type and Format Registry

Artifact type is a closed enum, not a free string. Each type has one canonical format and extension:

| Artifact type | Canonical format | Extension | Primary content owner |
| --- | --- | --- | --- |
| `adr` | Markdown | `.md` | Plan Skill candidate; Human Decision remains separate |
| `decision_record` | JSON | `.json` | Plan Interface recording a Human Action |
| `plan` | Markdown | `.md` | Plan Skills |
| `plan_review` | Markdown | `.md` | Plan Reviewer |
| `design_review` | Markdown | `.md` | Design Reviewer |
| `guardrail_validation` | JSON | `.json` | Guardrail Validator |
| `design_lock` | Markdown | `.md` | Plan Interface from validated design evidence |
| `readiness_evidence` | JSON | `.json` | Plan Interface aggregation |
| `implementation_review` | Markdown | `.md` | Implementation Reviewer |
| `release_gate` | Markdown | `.md` | Release Gate Skill |
| `fix_request` | JSON | `.json` | Review or Gate workflow decision owner |
| `repository_publish_handoff` | JSON | `.json` | Execute Interface |
| `authorization_grant` | JSON | `.json` | Interface recording a Human Action |
| `authorization_continuation` | JSON | `.json` | Harness compatibility aggregation |
| `authorization_revocation` | JSON | `.json` | Interface recording Human Action or material Safety Guard |

A type cannot select another format or extension. An extension/content-type mismatch is blocked. Markdown types use their registered Markdown Template when one exists and must expose future machine-verifiable immutable metadata. JSON types use their future Schema or, until that Schema is defined, the structured contract in this document; JSON has no Markdown co-canonical copy.

### Path Derivation Ownership

```text
Skill
  → emits registered Artifact type, logical ID, content, and subject binding
  → does not emit target path or extension

Interface / Persistence Orchestrator
  → validates type and identifiers
  → allocates the revision
  → invokes Path Policy

Path Policy
  → derives one repository-relative path from the registered pattern

Writer
  → accepts only that derived path and performs create-only persistence
```

The canonical extension is derived from Artifact type, not accepted as a candidate choice. Paths are derived only from registered type, validated logical identity, Artifact revision, required subject identity/revision, and the type's fixed format. Workflow status, Decision disposition, Human name, free-form title, content hash, timestamp, current display name, and a Skill-provided `target_path` never participate in path derivation.

### Directory Layout and Path Patterns

The following patterns are canonical. Every shown path is relative to the repository and begins with `.codex/harness/development/artifacts/`.

| Artifact type | Repository-relative path pattern |
| --- | --- |
| `adr` | `.codex/harness/development/artifacts/decisions/{logical_id}/r{artifact_revision}.md` |
| `decision_record` | `.codex/harness/development/artifacts/decisions/{subject_decision_id}/records/record-r{artifact_revision}.json` |
| `plan` | `.codex/harness/development/artifacts/plans/{logical_id}/r{artifact_revision}.md` |
| `plan_review` | `.codex/harness/development/artifacts/plan-reviews/{subject_plan_id}/plan-r{subject_revision}/review-r{artifact_revision}.md` |
| `design_review` | `.codex/harness/development/artifacts/design-reviews/{subject_plan_id}/plan-r{subject_revision}/review-r{artifact_revision}.md` |
| `guardrail_validation` | `.codex/harness/development/artifacts/guardrail-validations/{subject_plan_id}/plan-r{subject_revision}/validation-r{artifact_revision}.json` |
| `design_lock` | `.codex/harness/development/artifacts/design-locks/{subject_plan_id}/plan-r{subject_revision}/lock-r{artifact_revision}.md` |
| `readiness_evidence` | `.codex/harness/development/artifacts/readiness/{subject_plan_id}/plan-r{subject_revision}/readiness-r{artifact_revision}.json` |
| `implementation_review` | `.codex/harness/development/artifacts/implementation-reviews/{subject_implementation_id}/implementation-r{subject_revision}/review-r{artifact_revision}.md` |
| `release_gate` | `.codex/harness/development/artifacts/release-gates/{subject_implementation_id}/implementation-r{subject_revision}/gate-r{artifact_revision}.md` |
| `fix_request` | `.codex/harness/development/artifacts/fix-requests/{subject_implementation_id}/implementation-r{subject_revision}/request-r{artifact_revision}.json` |
| `repository_publish_handoff` | `.codex/harness/development/artifacts/repository-publish-handoffs/{subject_implementation_id}/implementation-r{subject_revision}/handoff-r{artifact_revision}.json` |
| `authorization_grant` | `.codex/harness/development/artifacts/authorizations/{subject_plan_id}/plan-r{subject_revision}/grant-r{artifact_revision}.json` |
| `authorization_continuation` | `.codex/harness/development/artifacts/authorizations/{subject_plan_id}/plan-r{subject_revision}/continuation-r{artifact_revision}.json` |
| `authorization_revocation` | `.codex/harness/development/artifacts/authorizations/{subject_plan_id}/plan-r{subject_revision}/revocation-r{artifact_revision}.json` |

Authorization types share the plan/revision directory and use distinct fixed filename prefixes. This keeps all authorization evidence for one Plan revision together without conflating grant, continuation, and revocation semantics. Their Artifact revision and authorization revision remain separate metadata domains even if their numeric values happen to match.

The persistent top-level directories are therefore limited to:

```text
decisions/
plans/
plan-reviews/
design-reviews/
guardrail-validations/
design-locks/
readiness/
implementation-reviews/
release-gates/
fix-requests/
repository-publish-handoffs/
authorizations/
```

No permanent `misc/`, `other/`, `temp/`, or status directory is permitted.

For subject-scoped types, Path Policy fixes the logical series deterministically from type and subject identity; callers cannot create arbitrary parallel series. For example, all `plan_review` revisions for `main-plan` revision 4 belong to the single logical series derived as `plan-review:main-plan:r0004`, and all Decision Records for one Decision ID belong to its single `decision-record` series. The logical Artifact ID remains present in the Artifact Reference even where the path encodes it through the registered type and subject segments rather than a separate directory. This rule prevents two logical series from claiming the same canonical path.

### Logical Artifact ID Policy

All logical and subject IDs used in paths are ASCII lowercase and must match:

```regex
^[a-z0-9][a-z0-9-]{0,63}$
```

ADR IDs therefore use a normalized form such as `adr-0007`; uppercase `ADR-0007` is display metadata, not a path ID. IDs cannot contain `/`, `\`, `.`, `..`, whitespace, control characters, NUL, Unicode, Unicode confusables, percent-encoded separators, a leading or trailing hyphen, or more than 64 characters. In addition to the regular expression, a trailing hyphen and case-insensitive filesystem-reserved base names (`con`, `prn`, `aux`, `nul`, `com1` through `com9`, and `lpt1` through `lpt9`) are rejected.

User input may propose a display title but is never copied into a logical ID. The responsible Interface selects or validates the ID under the registered Artifact-type contract.

### Revision Path Representation

Every Artifact and subject revision path segment uses a lowercase `r` and at least four decimal digits. Validation must apply this regular expression as a complete match to the revision segment alone:

```regex
^r[0-9]{4,}$
```

For example, the revision segment is `r0004`, while a Markdown filename containing it is `r0004.md`. Examples of valid segments are `r0001`, `r0002`, and `r10000`. Revisions are positive integers only. `r0000`, leading signs, whitespace, decimals, hexadecimal, and timestamps or timestamp substitution are invalid. The same representation is used for all Artifact types. Partial-match validation is forbidden. A future implementation must reject values that cannot be represented safely rather than truncate or wrap them, and must never reuse a past revision number.

### Status and Hash Separation

Paths encode identity and revision, not status. `draft`, `accepted`, `rejected`, `deferred`, `blocked`, and `superseded` directories are prohibited. Status changes update State or an immutable Decision/Authorization record; they never move, rename, or copy a canonical Artifact.

Content hashes also remain in Artifact References and immutable metadata, not paths:

```yaml
repository_path: .codex/harness/development/artifacts/plans/main-plan/r0004.md
content_hash: sha256:...
```

This preserves readable, stable identity paths while hash verification detects content mismatch.

### Fixed Paths and Convenience Views

Fixed files such as `PLAN.md`, `DESIGN_LOCK.md`, `REVIEW.md`, and `RELEASE_GATE.md` are never canonical Artifact References. The initial implementation will not generate Convenience Views.

Before the new Artifact Persistence implementation or any new Artifact Writer is enabled, every existing fixed-path field and fixed-path identity use must migrate to a revisioned Artifact Reference. The migration contract is:

- fixed-path strings must not be used as new canonical References, and every existing fixed-path field is a migration target;
- fixed paths and Artifact References must not be dual-written after Artifact References are introduced;
- a Convenience View is not a substitute for an Artifact Reference;
- the Execute Interface must not trust a fixed path as canonical identity;
- Human Authorization must not bind only to a fixed path;
- Review and Design Lock must not identify their subject Plan by fixed path alone;
- the new Artifact Writer must remain disabled until this migration is complete;
- any mismatch between a legacy fixed path and a new Artifact Reference fails closed;
- existing fixed-path content must not be promoted automatically to a formal Artifact;
- migration requires validation of existing content and Human Review; and
- after migration, canonical identity is determined only by the Artifact Reference held in State.

This contract does not implement the related Schema, Runtime, Workflow, State field, or migration tooling.

A future Convenience View may be generated only from a canonical revisioned Artifact, must be reproducible, must state that it is non-canonical and manually uneditable, and must never bind State, Human Authorization, Review, Design Lock, Execute Handoff, or repository publication. View generation or refresh failure cannot corrupt canonical evidence and does not by itself invalidate an otherwise valid Workflow transition.

Template paths are also not Artifact paths:

```text
.codex/harness/development/templates/PLAN.md
≠ .codex/harness/development/artifacts/plans/main-plan/r0004.md
```

The existing `PLAN.md`, `DESIGN_LOCK.md`, `REVIEW.md`, and `RELEASE_GATE.md` Templates correspond to `plan`, `design_lock`, `implementation_review`, and `release_gate`. The current `REVIEW.md` is specifically an Implementation Review Template; it does not govern `plan_review` or `design_review`. Those two Markdown types require future type-specific structured Markdown contracts or Templates before persistence implementation. JSON types require their future JSON Schema.

The current `ADR.md` Template contains a mutable-looking `status` field. Under this accepted policy, that field can express only the `draft`, `proposed`, or `superseded` document lifecycle and cannot serve as Human accept/reject/defer evidence or trigger a status-based path. Before ADR persistence is implemented, the Template contract must be aligned so Human disposition exists only in `decision_record`, with the vocabulary restriction enforced by Schema or validator; this design commit does not modify the Template itself.

### Current Reference Policy

The filesystem has no canonical `current.json`, `latest` symlink, fixed-path copy, or other current pointer. Current Development Harness Artifact References are owned only by the relevant Workflow State. Development Execution State may eventually keep only an external, Agent-owned Repository Publish Result Reference; it does not store the Result body or absorb that Agent's publication State. Reference Schema implementation and the State field remain deferred. This avoids a second mutable source of truth and prevents a filesystem pointer from diverging from State.

### Symlink and Containment Policy

String validation alone is insufficient. Before any future write, Path Policy and Writer contracts must require:

1. resolve the real Repository Root;
2. resolve Artifact Root and prove it is inside that Repository Root;
3. reject Artifact Root if it is a symlink escaping the repository;
4. walk every existing parent component without following a link outside Artifact Root;
5. reject an existing target that is a symlink;
6. derive and normalize the repository-relative path, then prove the resolved destination remains beneath the real Artifact Root; and
7. perform the future create operation in a way that prevents a symlink swap between validation and creation.

Writing through a symlink to another repository, a home directory, or any location outside Artifact Root is prohibited. Race-safe descriptor-relative creation is a future Writer implementation requirement; this decision fixes the fail-closed containment contract but does not implement it.

### Git Management Policy

Canonical Decision, Planning, Execution Evidence, and Authorization Artifacts owned by the Development Harness under Artifact Root are Git-managed in the initial local single-repository model. The Repository Publish Result body is Agent-owned, is not a Development Harness Artifact, and must not be stored under Artifact Root or Git-managed by the Development Harness.

Temporary files, lock files, partial or failed writes, temporary scan results, raw source, secrets, credentials, private or personal information, complete conversations, complete Tool output, and unnecessary intermediate candidates must never be staged or committed. This decision does not modify `.gitignore`; future Writer storage for transient material must be outside canonical Artifact paths and comply with the security boundary before any Git operation.

Retention, archive, and garbage-collection policy remain future decisions. Immutability does not authorize indefinite storage of prohibited data.

### Artifact Type Registration Rule

New Artifact types cannot be introduced by a Skill or free-form request. Adding a type requires one coordinated design and implementation change defining:

- type name and classification;
- purpose, content owner, persistence owner, and formal-adoption owner;
- canonical format, extension, and content contract;
- unique Path Policy pattern;
- logical ID and revision model;
- required subject binding;
- canonicality and State-reference behavior;
- Git and retention policy;
- security and privacy requirements; and
- enum, Path Policy, Schema, and tests.

Registration must prove that its path cannot collide with an existing type. Until those elements are accepted together, the type is unknown and persistence fails closed.

## Artifact Persistence Boundary Contracts

This section fixes the required fields for the three contracts that cross the Artifact Persistence boundary. It does not define a Schema file or runtime implementation.

In Human terms:

```text
Write Request
  → what to save

Artifact Reference
  → a bookmark identifying which saved Artifact is meant

Write Result
  → whether persistence succeeded or did not succeed
```

For an Artifact Reference, identity and location remain separate:

```text
Reference identifies "what to read."
Path identifies "where to read it from."
```

The repository path is required location evidence, but it is not the primary identity and must never be parsed to reconstruct missing identity fields.

### Write Request

A Write Request is the internal structured input presented to the Artifact Persistence boundary. It is not a Human approval request. Within a valid execution authorization and its bound Plan and Design Lock, the responsible Interface may request persistence without a separate Human approval for each Artifact.

Every Write Request has exactly these required top-level fields:

| Field | Meaning and required validation |
| --- | --- |
| `request_schema_version` | Closed contract version used to reject unknown or incompatible request shapes. |
| `request_id` | Globally unique immutable identifier for this request. Reuse is valid only with the same verified request fingerprint. |
| `idempotency_key` | Stable retry key. Reuse is valid only with the same `request_id` and verified request fingerprint. |
| `request_fingerprint` | SHA-256 over the canonical request-fingerprint envelope defined below. The Persistence Orchestrator recomputes it rather than trusting the supplied value. |
| `artifact_type` | Member of the closed Artifact Type Registry. It determines the only valid format, extension, subject-binding variant, and Path Policy rule. |
| `logical_artifact_id` | Stable logical series identity validated under the registered type contract. It is not a repository path. |
| `payload` | Exact byte sequence to persist, or a lossless transport representation decoded to that exact sequence. No newline, Unicode, key-order, whitespace, or semantic normalization is allowed. |
| `payload_format` | Registered canonical format identifier for `artifact_type`; it must equal the registry value and cannot select an extension. |
| `payload_hash` | SHA-256 of the exact decoded `payload` bytes, allowing transport or preprocessing changes to be detected before envelope construction. |
| `subject_binding` | The registered, discriminated subject-binding object required by `artifact_type`, including every applicable subject logical ID, subject revision, and subject content hash. A type with no external subject uses the registry's explicit `none` variant rather than an omitted field. |
| `expected_latest` | Discriminated stale-write precondition defined below. It is always present and is never inferred from State or filesystem contents. |
| `source_binding` | Discriminated provenance object naming the authorized generating boundary and its stable source reference or references. Its variant is fixed by `artifact_type`; it must not contain raw source, payload copies, complete Tool output, secrets, credentials, or private information. |
| `development_security_scan_binding` | Complete binding to valid Development Artifact scan evidence, accepted Policy versions, derived final security decision, and the immutable Human Review Record when required. It must bind to the same type, logical ID, format, and payload hash. |

These fields are necessary, rather than general tracing metadata. Without the schema version the shape cannot be interpreted safely; without request identity, idempotency, and the fingerprint, retries and identifier reuse cannot be distinguished; without type, logical ID, payload, format, and payload hash, the intended series and exact bytes cannot be validated; without subject and source bindings, the Artifact's meaning and authorized provenance cannot be verified; without `expected_latest`, initial creation and stale updates cannot fail closed; and without `development_security_scan_binding`, unscanned or policy-incompatible bytes could enter Artifact Root.

Artifact-type variation is expressed only through registered discriminated variants of `subject_binding` and `source_binding`. Free-form optional field collections are prohibited. A binding field required by the selected variant must be present and non-null; an inapplicable field must be absent. The registry must reject an unknown variant.

The request-fingerprint envelope includes, in fixed canonical serialization, all meaning-bearing request inputs:

```yaml
request_schema_version: string
artifact_type: string
logical_artifact_id: string
payload_format: string
payload_hash: sha256:string
subject_binding: object
expected_latest: object
source_binding: object
development_security_scan_binding: object
```

`request_id`, `idempotency_key`, and `request_fingerprint` itself are excluded from the fingerprint envelope so identifiers do not define the requested content. The exact payload need not be duplicated in that envelope because its verified `payload_hash` commits to the exact bytes. Canonical serialization is a future Schema detail, but it must be fixed before implementation and must not depend on map presentation order.

The stale-write precondition has exactly one of these two forms:

```yaml
# First revision only: the logical series is expected not to exist.
expected_latest:
  state: absent
```

```yaml
# Successor revision: both values are mandatory and must match.
expected_latest:
  state: present
  artifact_revision: 4
  content_hash: sha256:string
```

`state: absent` is valid only when no revision exists for the logical series. `state: present` requires both the exact latest positive Artifact revision and its verified content hash; matching only one is insufficient. Null, omitted, wildcard, latest-by-time, revision-only, and hash-only preconditions are invalid. The Persistence Orchestrator verifies both values against the current canonical Artifact before allocating the next revision. Missing, stale, unknown, or contradictory evidence is `blocked`.

The Write Request never contains a caller-selected new Artifact revision. AI, Skills, and Human input provide meaning and bytes; the Interface / Persistence Orchestrator resolves the logical series, verifies `expected_latest`, and allocates the next positive monotonically increasing revision. Any lower-level create command carrying that allocation is an implementation detail outside these three boundary contracts and cannot be accepted from an untrusted caller.

The following request fields and equivalents are forbidden:

```text
target_path
absolute_path
repository_path
extension
new_artifact_revision
artifact_revision
revision_path_segment
```

No caller-controlled value may indirectly select them. Repository path, extension, and the `r[0-9]{4,}` representation are derived only after revision allocation from the registered Artifact Type and Path Policy.

`payload_hash` and `content_hash` have different scopes:

```text
payload_hash
  = SHA-256 of the exact persisted payload bytes

content_hash
  = SHA-256 of the canonical immutable Artifact envelope,
    including the exact payload bytes and all immutable Artifact metadata
```

The immutable envelope includes at least its envelope/schema version, Artifact type, logical Artifact ID, allocated Artifact revision, registered payload format, subject binding, source binding, and exact payload bytes. Operational response metadata such as `request_id`, `idempotency_key`, `result_id`, repository path, and status is not immutable Artifact metadata and is excluded. This preserves identical content identity independent of retry identifiers while ensuring that a metadata or payload change changes `content_hash`. No unrequested normalization may occur before either hash is computed.

### Artifact Reference

An Artifact Reference is the complete bookmark for one persisted canonical Artifact revision. Every Development Harness Artifact Reference has exactly these required fields:

| Field | Meaning and required validation |
| --- | --- |
| `reference_schema_version` | Closed contract version for interpreting and validating the Reference. |
| `artifact_type` | Registered type, independently represented rather than parsed from the path. |
| `logical_artifact_id` | Logical series identity, independently represented rather than parsed from the path. |
| `artifact_revision` | Positive allocated revision for this immutable member, independently represented rather than parsed from the path. |
| `subject_binding` | Complete registered subject-binding variant copied from the verified immutable envelope. |
| `repository_path` | Repository-relative location derived by the selected Path Policy; it must begin below Artifact Root and is never identity by itself. |
| `payload_hash` | SHA-256 of the exact stored payload bytes. |
| `content_hash` | SHA-256 of the canonical immutable Artifact envelope. |
| `payload_format` | Registered canonical format identifier; it must match `artifact_type` and the path extension. |
| `path_policy_version` | Exact accepted Path Policy version used to derive and later re-derive `repository_path`. |

No separate `reference_id` is required because the tuple of `artifact_type`, `logical_artifact_id`, `artifact_revision`, and `content_hash` is the immutable identity. No `created_from_request_id` is required because request tracing does not identify the Artifact and must not make otherwise identical content request-dependent. The corresponding Write Result provides request binding.

A reader must validate all Reference fields before returning canonical content. It must:

1. validate the Reference shape and closed versions;
2. validate `artifact_type`, logical ID, revision, format, and the complete `subject_binding` independently of the path;
3. re-derive the only allowed repository path from those identity fields and `path_policy_version`, then require exact equality with `repository_path`;
4. resolve the real Repository Root and Artifact Root, reject absolute paths, traversal, invalid separators, symlinks escaping the root, and any normalized or resolved location outside Artifact Root;
5. require the registered extension and content format for the type;
6. read the exact bytes and verify `payload_hash`;
7. reconstruct the canonical immutable envelope from independently validated metadata and exact bytes, then verify `content_hash`; and
8. require the envelope's Artifact revision and subject binding to equal the Reference values.

Failure of any check is fail closed. A reader must not trust `repository_path` alone, parse identity from it, accept an unverified hash supplied beside it, or fall back to a fixed filename or filesystem current pointer. Both hashes are required; `payload_hash` detects byte changes directly and `content_hash` proves the bytes and immutable metadata belong to the identified Artifact.

### Write Result

A Write Result reports only the Artifact persistence operation. It does not report State update, workflow completion, orphan status, release readiness, or repository publication.

Every Write Result has these common required fields:

| Field | Meaning |
| --- | --- |
| `result_schema_version` | Closed contract version for interpreting the result. |
| `result_id` | Globally unique immutable identifier for this result record. |
| `request_id` | Exact `request_id` of the processed Write Request. |
| `idempotency_key` | Exact `idempotency_key` of the processed Write Request. |
| `request_fingerprint` | Verified fingerprint of the processed Write Request, binding the result to its meaning-bearing inputs. |
| `status` | Exactly one of `written`, `already_written`, `blocked`, or `failed`. |

Status meanings and status-specific required fields are exclusive:

| Status | Meaning | Required status-specific fields | Forbidden status-specific fields |
| --- | --- | --- | --- |
| `written` | A newly allocated revision was created, its exact stored bytes and immutable envelope were verified, and its Reference can be returned. | `artifact_reference` | `error_code`, `error_message` |
| `already_written` | The same verified request, or the same allocated Artifact identity and content hash, already resolved to a fully verified existing Artifact. No new write occurred and its existing Reference is returned. | `artifact_reference` | `error_code`, `error_message` |
| `blocked` | Persistence was refused because input, identity, concurrency, binding, Path Policy, content, safety precondition, or idempotency evidence violated the contract or was missing, unknown, stale, or inconsistent. The request is not eligible for the attempted write unless the cause is corrected or a fresh valid request is made. | `error_code`, `error_message` | `artifact_reference` |
| `failed` | A contract-valid and eligible persistence attempt encountered an execution failure such as an I/O, permission, capacity, or unavailable-filesystem error. The status does not claim that a canonical Artifact was verified. | `error_code`, `error_message` | `artifact_reference` |

`blocked` is a deterministic refusal based on an unmet contract or safety condition. Retrying the identical request without changing the conflicting condition must not turn it into `written`. `failed` is an operational failure after eligibility was established; an identical retry may succeed when the external failure is removed. Unknown classification fails closed as `failed` only when contract validation passed and the operational outcome cannot be verified; otherwise it is `blocked`.

`error_code` is a closed machine-readable code and is the primary error discriminator. `error_message` is a required safe Human-readable summary of that code, not the sole basis for handling. Neither field nor any other Result field may contain payload bytes, raw source, secrets, credentials, private or personal information, raw exception text, stack traces, absolute paths, hash values, or complete Tool output. Error details may identify only safe contract field names, registered identifiers, repository-relative derived paths when safe, and sanitized failure categories.

The following fields and equivalents are forbidden in every Write Result:

```text
state_updated
workflow_completed
orphaned
release_ready
publish_succeeded
```

The Writer does not know or decide these facts. A `written` or `already_written` result says nothing about whether State later references the Artifact. The Artifact-first update order and orphan recovery policy are defined below; the final transaction boundary remains deferred.

### Binding and Idempotency

The Persistence Orchestrator verifies `payload_hash`, then recomputes and verifies `request_fingerprint` before processing. It binds `request_id` and `idempotency_key` to that fingerprint. Reuse of either identifier with a different fingerprint, or reuse of an idempotency key with a different request ID, is `blocked`. Neither last-writer-wins nor identifier rebinding is permitted.

For an exact retry, identifier and fingerprint binding is resolved before evaluating whether the original `expected_latest` still describes the post-write series. A previously verified successful result is replayed as `already_written`; the changed latest revision caused by that same successful request is not treated as a stale-write conflict. If no verified successful result exists, normal precondition validation applies. This semantic precedence does not decide atomic-write mechanics or the final transaction boundary.

A `written` or `already_written` Result binds to the Request through the exact common `request_id`, `idempotency_key`, and `request_fingerprint`, and returns the complete Artifact Reference. A `blocked` or `failed` Result retains the same three bindings but returns no Reference. Result replay for the same verified Request must reproduce the same status and Reference when a verified successful result exists; it must not allocate another revision.

Before returning `already_written`, persistence must verify the existing Reference, exact stored payload bytes, immutable envelope, both hashes, type, logical ID, revision, subject binding, format, and derived path. Equality of caller-supplied hashes alone is insufficient. A different request that reaches the same allocated identity and verified `content_hash` may return `already_written`; if identity matches but content hash does not, it must return `blocked` and must never overwrite.

The minimum required outcome matrix is:

| Case | Required status | Required code or result |
| --- | --- | --- |
| 1. First revision, `expected_latest.state: absent`, and no series exists | `written` | Reference to allocated revision 1 after full verification |
| 2. Successor revision with both current expected revision and hash | `written` | Reference to the next allocated revision after full verification |
| 3. Exact same Request is executed again | `already_written` | Same fully verified Reference; no new allocation or write |
| 4. Same allocated identity and same verified content hash already exist | `already_written` | Existing fully verified Reference; no new write |
| 5. Same logical identity and allocated revision exist with a different content hash | `blocked` | `artifact_identity_content_conflict` |
| 6. Expected latest revision is stale or otherwise differs | `blocked` | `expected_latest_revision_mismatch` |
| 7. Expected latest content hash differs | `blocked` | `expected_latest_content_hash_mismatch` |
| 8. Subject binding is missing, unknown, stale, or inconsistent | `blocked` | `subject_binding_mismatch` |
| 9. Supplied/recorded location differs from the Path Policy derivation, or containment/type/extension checks fail | `blocked` | `path_policy_mismatch` |
| 10. Reconstructed canonical envelope does not match the claimed or recorded content hash | `blocked` | `content_hash_mismatch` |

Case 9 does not authorize a Write Request to supply a location; it covers an existing target, persisted metadata, or Reference that conflicts with the Writer's independently derived path. For cases 6 and 7, the Persistence Orchestrator must evaluate both present-state preconditions and may report both closed error codes when both differ; it must never accept one matching value as sufficient. A filesystem error encountered only after all relevant contract checks pass is `failed`, with an operational code such as `filesystem_io_failure`, rather than any `blocked` code above.

### Responsibility Boundary for These Contracts

```text
Skill
  → may generate candidate Artifact content and meaning-bearing bindings
  → does not choose path, extension, or revision
  → does not change State

Interface / Persistence Orchestrator
  → constructs and validates the Write Request
  → verifies subject binding against current State and authorized evidence
  → verifies expected latest revision and hash
  → allocates the next Artifact revision
  → requests create-only persistence under Path Policy

Artifact Writer
  → validates the trusted persistence inputs produced at that boundary
  → derives or verifies the Path Policy result
  → rechecks create-only identity and revision preconditions
  → persists and verifies exact bytes and the immutable envelope
  → returns the Artifact Reference and Write Result through the Persistence Orchestrator
  → does not change State
```

The Persistence Orchestrator remains the existing allocation and coordination responsibility; this decision introduces no new owner. The lower-level call boundary between it and the Artifact Writer is not a fourth public contract and is deferred to implementation design. Neither component may decide formal adoption, Human authorization, Workflow transition, or security-scan ownership. The Writer never classifies an orphan; the Orchestrator coordinates the recovery classification defined below through the responsible Interface.

## Artifact-first State Consistency Model

Artifact persistence and Workflow State mutation form an ordered two-result process. They are not one Writer operation and neither result implies the other.

In Human terms:

```text
先に本を棚へ置く。
実際に置けたことを確認してから、
台帳へ登録する。
```

The reverse order is prohibited. State must never announce a current Artifact before that exact Artifact revision exists and has passed identity, path, byte, and hash verification.

```text
Artifact保存成功
≠ State更新成功

両方が成功して、初めて保存処理全体が完了する。
```

### Mandatory Update Order

The update order is fixed as follows:

```text
Validate Write Request
  → allocate Artifact revision
  → persist Artifact with immutable create-only semantics
  → verify persisted bytes, payload hash, content hash, and Path Policy
  → generate the verified Artifact Reference
  → return written or already_written Write Result
  → validate State update preconditions
  → apply that Artifact Reference to the exact State field
  → re-read and verify the resulting State
```

No State mutation may occur when the Write Result is `blocked` or `failed`, when the Artifact Reference is missing, or before all Artifact verification completes. State-first reservation, placeholder Reference, pending path, predicted revision, and compensating creation after State mutation are prohibited.

An `already_written` result enters the State phase with the same fully verified Artifact Reference as `written`; it does not allocate or persist another revision.

### Three Completion Boundaries

The following completion facts remain distinct:

| Completion fact | Required meaning |
| --- | --- |
| Artifact write completed | Write Result is `written` or `already_written`; a complete Artifact Reference was returned; existence, exact bytes, hashes, format, subject binding, and derived Path Policy location were verified. State may still not contain the Reference. |
| State reference update completed | All State compare-and-set preconditions passed; the exact target field contains the supplied Artifact Reference; the post-update State was re-read or equivalently verified. |
| Workflow persistence completed | Both preceding facts are verified for the same Write Request, Write Result, Artifact Reference, target State identity, and target field. |

Artifact write completion alone is never Workflow persistence completion. Sending a State update request, receiving a Tool success, starting an Agent, or obtaining an unverified State response is also insufficient. Unknown or contradictory State evidence fails closed.

Write Result remains limited to Artifact persistence. It must not acquire `state_updated`, `workflow_completed`, `orphaned`, or any equivalent field. The Interface / Persistence Orchestrator keeps the Artifact Write Result and State update result as separate evidence and derives Workflow persistence completion only after both validate.

### Required Validation Immediately Before State Update

Immediately before State mutation, the Interface / Persistence Orchestrator must verify all of the following against current evidence rather than trusting the path inside the Reference:

1. Write Result status is exactly `written` or `already_written`.
2. `artifact_reference` is present and contains every required field under its supported Reference contract version.
3. Write Result `request_id`, `idempotency_key`, and `request_fingerprint` match the verified Write Request.
4. Reference type, logical ID, payload format, payload hash, and subject binding match the Write Request; its allocated revision and content hash match the verified Write Result outcome.
5. The repository path re-derived from type, logical identity, revision, subject binding, format, and `path_policy_version` exactly equals `repository_path`.
6. The resolved target exists beneath the real Artifact Root and passes containment, symlink, registered extension, and format checks.
7. The exact stored bytes match `payload_hash`, and the reconstructed immutable envelope matches `content_hash`.
8. The complete subject binding matches the current target State, bound Plan, and applicable authorization/readiness evidence.
9. The target Workflow State identity, expected State revision, and expected State hash match the current State.
10. The exact registered target field is authorized for the Artifact type and subject; a free-form or caller-selected State path is prohibited.
11. The field's current Artifact Reference matches the explicit expected-current precondition.

Failure, absence, staleness, or an unknown value in any check prevents mutation. A valid repository path alone cannot authorize State update, and identity must never be reconstructed from that path.

### State Compare-and-set Preconditions

Every State reference update requires one complete compare-and-set precondition set:

```yaml
state_update_precondition:
  target_state_id: string
  expected_state_revision: positive-integer
  expected_state_hash: sha256:string
  target_field: registered-field-identifier
  expected_current_artifact_reference:
    state: absent
```

or:

```yaml
state_update_precondition:
  target_state_id: string
  expected_state_revision: positive-integer
  expected_state_hash: sha256:string
  target_field: registered-field-identifier
  expected_current_artifact_reference:
    state: present
    artifact_reference: object
```

All fields are mandatory. The `present` variant contains the complete expected Reference, not only a path, revision, or hash. The State mutation owner compares the current State identity, revision, deterministic State hash, target field, and complete current Reference. All must match in one compare-and-set-equivalent validation before applying the desired verified Reference.

The State hash canonicalization and concrete Schema are implementation details deferred from this contract, but the chosen serialization must be deterministic and cover every State field whose change could affect the authorization or meaning of this update. An implementation may use an equivalent stronger primitive only if it proves the same conditions without weakening any comparison.

If State revision or hash changed, the field contains a different Reference, an expected absence is no longer absent, or the target field is not the registered field, the State update is `blocked`. It must not overwrite, merge around, or silently accept the conflict. It must not delete, rewrite, rename, or move the already persisted Artifact to manufacture consistency. The Artifact remains immutable, and its classification or recovery remains deferred to the next decision.

### State Update Result Semantics

The State update result is separate from Write Result. Its conceptual outcomes are:

| Outcome | Meaning |
| --- | --- |
| `applied` | Preconditions passed, the exact Reference was written to the target field, and post-update verification succeeded. |
| `already_applied` | An idempotent replay of the same bound operation finds the exact complete Reference in the target field, and current subject, authorization, State integrity, and field invariants all verify; no mutation is needed. |
| `blocked` | A precondition, target-field, current-Reference, binding, or State consistency check deterministically failed; State is not overwritten. |
| `failed` | An eligible State operation encountered an execution failure and has not yet been resolved by mandatory re-read verification. It is not success. |

These are design-level semantics, not a new Schema in this change. A State write acknowledgement alone cannot produce `applied`. The resulting State must be re-read or verified by an equivalent authoritative mechanism.

When a State write reports an execution failure or its acknowledgement is lost, the Interface must re-read current State and classify only from verified evidence:

- exact desired Reference present in the exact target field, the retry binds to the same original Write Request and State-update intent, and all current subject, authorization, State integrity, and field invariants still pass: `already_applied`;
- original preconditions still hold and desired Reference is absent: `failed`, eligible for a controlled retry with the same Reference;
- a different Reference or other precondition change is present: `blocked` conflict;
- State cannot be read or its integrity cannot be established: unresolved `failed`, never success.

This classification does not determine whether an unreferenced Artifact is an orphan or how it is recovered.

### Failure Boundaries

| Failure point | Artifact condition | State condition | Required handling |
| --- | --- | --- | --- |
| Before Artifact creation | Not created | Unchanged | Return `blocked` or `failed` as appropriate; do not enter State phase. |
| During Artifact persistence | Not verified as canonical; partial or temporary material may exist | Unchanged | Never return a Reference or treat partial material as canonical. Atomic-write mechanics remain deferred. |
| After Artifact verification and before State update | Verified immutable Artifact exists | Does not yet reference it | Do not report Workflow success. This possible unreferenced intermediate state is input to the next orphan-policy decision; this contract does not classify it. |
| State compare-and-set mismatch | Verified immutable Artifact exists | Unchanged | State update is `blocked`; do not force overwrite or alter the Artifact. |
| During State write | Verified immutable Artifact exists | Update outcome initially unknown or incomplete | Re-read and verify as defined above; unresolved evidence remains `failed`. |

No failure after Artifact write completion authorizes deletion, overwrite, revision reuse, rename, or content modification as compensation. This contract fixes safety behavior without deciding retention, marker, reuse, or recovery policy.

### Retry and Idempotency Across Both Phases

Retry reuses the original Artifact identity and Reference:

```text
1. Verify the original Write Request identifiers and fingerprint.
2. Resolve its verified Write Result and obtain the same Reference through already_written when necessary.
3. Revalidate the Artifact and current State preconditions.
4. If State lacks the Reference and all preconditions still match, retry only the State update with that same Reference.
5. If State already holds that exact Reference, verify the original operation binding and all current invariants, then return already_applied.
6. If State holds a different Reference or another precondition changed, return blocked and fail closed.
```

A State-only retry must not submit a new Write Request, allocate a new Artifact revision, change the idempotency binding, or mutate the existing Artifact. `already_written` is a valid Artifact write success for proceeding to State reflection. A failed or ambiguous State operation never makes a new Artifact revision the repair mechanism.

### Responsibility Boundary for Artifact and State Consistency

The existing responsibilities remain separated:

```text
Artifact Writer
  → validates the trusted Artifact persistence input
  → saves and verifies the immutable Artifact
  → returns Artifact Reference and Write Result
  → does not read or change Workflow State
  → does not classify State update or Workflow completion

Interface / Persistence Orchestrator
  → receives and separately retains Write Result and State update result
  → performs the required pre-State validation
  → constructs the complete compare-and-set preconditions
  → coordinates reflection of the verified Reference into the exact State field
  → declares Workflow persistence completed only when both phases verify

Responsible Plan or Execute Interface
  → remains the existing mutation owner for its Workflow State
  → validates compare-and-set preconditions and allowed State patch paths
  → applies only the supplied verified Reference to the exact target field
  → re-reads and validates the resulting State
  → returns the separate State update result
  → never saves, changes, deletes, renames, or repairs an Artifact
```

No independent State Writer is introduced because the existing Interfaces already own their respective Workflow State mutation boundaries. Skills and the Artifact Writer never mutate State. The Persistence Orchestrator coordinates the two phases but cannot bypass the responsible Interface's State invariants or allowed-path validation.

### Persistence Success Invariant

The success terms are fixed as:

```text
Artifact write success
  = the Artifact is saved and fully verified, and its Reference is returned

State update success
  = State holds that exact Reference and post-update verification is complete

Persistence success
  = Artifact write success AND State update success for the same operation
```

Artifact success alone, a sent State request, an unknown State result, Writer success, Agent startup, or Tool execution success must never be reinterpreted as Persistence success or Workflow completion.

### Deliberately Unresolved Follow-on Boundaries

This consistency model establishes that a verified Artifact may exist without a State Reference after interruption or conflict. The orphan policy below classifies and handles that intermediate state without changing Artifact-first ordering. Filesystem locks, concrete atomic-write mechanics, and a transaction implementation spanning Artifact and State remain unresolved and cannot be inferred as successful, safe, or absent.

## Orphan Acceptance, Identification, and Recovery Policy

An orphan is not garbage. In Human terms:

```text
orphanはゴミではなく、Stateとの接続が完了していない迷子のArtifactである。

未参照Artifact
≠ orphan

保存処理の途中でState接続が完了しなかったArtifact
= orphan候補
```

Artifact-first persistence necessarily permits a temporary orphan candidate when Artifact write succeeds but State connection does not complete. Temporary occurrence is allowed; indefinite invisible abandonment is not. An orphan candidate is never Persistence success, and automatic deletion without complete safety evidence is prohibited.

The recovery order is fixed as:

```text
再接続できるか確認する
  ↓
再接続できるなら同じReferenceでつなぐ
  ↓
今はつなげないなら保留する
  ↓
安全に不要と証明できるまで削除しない
```

### Operation-bound Orphan Candidate Definition

An unreferenced Artifact is not by itself an orphan candidate. Historical revisions, superseded Artifacts, immutable audit history, non-current Evidence Chain members, and Artifacts referenced by Decision or Authorization Records may correctly be absent from a current-reference field.

An orphan candidate is identified only when one bound Persistence operation satisfies all of the following:

1. its verified Write Result is `written` or `already_written`;
2. that Result returns a fully verified Artifact Reference;
3. the intended target State identity and exact target field are known;
4. the corresponding State reference update is not verified as `applied` or `already_applied`; and
5. Workflow Persistence success for that same operation has not been established.

The binding must connect the Write Request identifiers and fingerprint, Write Result identity, Artifact Reference, original State target and compare-and-set preconditions, and the State update or recovery evidence. Filesystem or Artifact Root traversal may locate material for investigation, but path presence or absence alone can never classify an orphan candidate, prove provenance, authorize reconnection, or authorize deletion.

### Candidate-producing Cases

| Case | Candidate condition | Why it is not immediate success |
| --- | --- | --- |
| Process stops after Artifact verification | A verified Reference exists and no verified State update result exists | Artifact success does not prove State connection. |
| State compare-and-set conflict | Artifact is verified but current State revision, hash, field, or current Reference differs | Forced overwrite is prohibited and the intended connection no longer has valid preconditions. |
| Authorization becomes ineffective before State update | Artifact was validly saved but current authorization is revoked, stale, or bound to different evidence | Historical creation authority does not grant current reconnection authority. |
| State write fails | Artifact is verified and the State result is operationally failed or initially unknown | State must be re-read; an acknowledgement failure cannot be interpreted as either success or absence. |
| Post-update State re-read fails | A State write may have occurred but the exact Reference and invariants cannot be verified | An unverifiable result remains failed, never success. |
| Material subject, Plan, or Design Lock change | Saved binding differs from the current subject or execution package | The old Artifact may remain valid history but cannot be attached to changed current meaning automatically. |

Each case becomes a normal orphan candidate only when creation-time legitimacy can be verified. Missing or contradictory provenance changes its classification to `invalid_or_unknown` rather than making it reconnectable.

### Creation-time Legitimacy

Creation-time legitimacy answers only whether the Artifact was allowed to be created at the time of its Write Request. The recovery assessment must verify the following evidence to the extent required by the registered Artifact type and its lifecycle position:

- the complete Write Request and its identifier/fingerprint binding;
- a `written` or `already_written` Write Result bound to that Request;
- the complete, currently readable Artifact Reference and both hashes;
- the Plan and Design Lock revisions and hashes effective for creation;
- the immutable Human Authorization evidence effective for creation;
- exact subject binding and source binding; and
- the Development Artifact scan evidence and final security-decision binding effective for the exact payload; and
- the registered Artifact type, format, and Path Policy result.

This applicability rule prevents circular evidence. A Plan, Design Lock, Decision Record, or Authorization Record being created cannot bind to itself as already persisted evidence; it instead binds to the registered predecessor, subject, accepted Decision set, trusted Human Action, or Harness evidence required for that type. For a later execution Artifact, the effective Plan, Design Lock, and Human Authorization bindings are all mandatory. Missing an applicable binding is `unknown`, never silently inapplicable.

The assessment has exactly three outcomes:

| Creation legitimacy | Meaning |
| --- | --- |
| `verified` | All required creation-time evidence exists, matches, and proves the write was authorized then. The operation may be assessed as a normal orphan candidate. |
| `unknown` | Required provenance or binding evidence is missing, unreadable, or cannot be verified. Classify `invalid_or_unknown` and fail closed. |
| `invalid` | Evidence is present but mismatches or proves that creation was outside its authority or contract. Classify `invalid_or_unknown` and fail closed. |

Neither `unknown` nor `invalid` permits automatic State connection, reuse, deletion, or promotion to normal history. It requires isolation from reconnection and Human Review. A concrete quarantine directory or mechanism is not defined here.

### Current Reconnection Eligibility

Creation-time legitimacy and current reconnection eligibility are separate gates. A historically valid Artifact is reconnectable only when all of the following are currently true:

- Authorization is effective and binds the current Plan, Decision set, Design Lock, and readiness evidence;
- current Plan, Design Lock, subject, and source meanings remain compatible with the saved bindings;
- the Artifact Reference, payload hash, content hash, format, Path Policy, and Artifact Root containment revalidate;
- target State identity, expected revision, expected hash, and registered target field are current;
- the complete expected current Artifact Reference precondition matches;
- no different Reference has already won the target-field compare-and-set;
- the same Reference is not already connected, except as an idempotent `already_connected` result; and
- no unresolved material change or required Human decision remains.

All current State comparisons use the complete compare-and-set contract fixed above. Creation authorization alone is never enough. Any missing, stale, unknown, or conflicting current evidence prevents automatic reconnection.

### Orphan Candidate Classification

After creation-time legitimacy and current eligibility are evaluated, every candidate receives exactly one classification:

| Classification | Required conditions | Allowed next action |
| --- | --- | --- |
| `reconnectable` | Creation legitimacy is `verified`; the Artifact revalidates; current Authorization, Plan, Design Lock, subject, target field, and complete State CAS all pass. | Retry only the State connection with the same Artifact Reference. No Human approval is required for this ordinary in-scope retry. |
| `deferred` | Creation legitimacy is `verified`, but current reconnection is unavailable or awaits a legitimate decision, including revocation, CAS conflict, different current Reference, material change, or Human Review. | Retain without claiming success; reassess after the blocking condition or Human decision changes. |
| `invalid_or_unknown` | Creation legitimacy is `invalid` or `unknown`, or the Artifact/Reference integrity cannot be proven. | Fail closed, isolate from automatic reconnection, and require Human Review. |

`deferred` is not Persistence success and is not permission to overwrite current State. `invalid_or_unknown` is not a normal orphan category and cannot be auto-reconnected merely because its bytes parse or its path matches a registered pattern.

### Reconnection Outcomes

Only a `reconnectable` candidate may enter automatic reconnection. Before each attempt, the complete Reference, exact bytes, payload hash, content hash, Path Policy, containment, subject binding, current Authorization, and full State CAS are revalidated.

The attempt uses the same Artifact Reference and has exactly one outcome:

| Outcome | Meaning |
| --- | --- |
| `reconnected` | The exact Reference was newly applied to the exact target field and the post-update State and all current invariants were verified. Persistence success is now established. |
| `already_connected` | The same bound recovery operation finds the exact Reference already present, and the original operation binding plus all current Authorization, subject, State integrity, and field invariants revalidate. Persistence success is confirmed without another write. |
| `still_deferred` | Creation legitimacy remains verified, but a non-final current condition such as revoked authorization, material-change review, or changed CAS prevents reconnection now. It remains deferred and is not success. |
| `blocked` | A deterministic conflict, invalidation, integrity mismatch, different winning Reference, forbidden target, or rejected Human decision prevents this reconnection. It is not success and must not force State mutation. |
| `failed` | The contract-valid reconnection encountered an operational failure. Mandatory State re-read cannot yet prove `reconnected` or `already_connected`; unresolved outcome remains failed. |

`already_connected` requires more than Reference equality. It requires the same Persistence and recovery-operation binding and current invariant validation. Sending a State request, receiving a Tool acknowledgement, or observing the Artifact on disk never resolves a candidate.

Reconnection never rewrites the Artifact phase:

```text
Artifact re-save
  → unnecessary

new Artifact revision
  → prohibited

State CAS retry with the same Reference
  → permitted only for reconnectable
```

### Recovery Tracking State

Orphan classification is mutable operational status and must not be written into immutable Artifact content, metadata, repository path, or Artifact Reference. It is represented in a separate recovery tracking State with its own revision and deterministic hash, and is mutated only by the same responsible Plan or Execute Interface that owns the applicable Workflow State. Keeping the recovery State in a separate revision domain prevents a tracking update from invalidating the target Workflow State CAS it records. This introduces no new Artifact type, current pointer, or State mutation owner.

After a `written` or `already_written` Result and before the target current-Reference update, the Orchestrator must cause a `state_update_pending` tracking entry to be written and re-read under the recovery State's own CAS. This occurs after Artifact persistence, so it does not violate Artifact-first ordering, and it does not set the target current Reference or establish Persistence success. The target State update may proceed only after the entry is verified. If tracking persistence fails or its result is unknown, the target update does not proceed; the Artifact remains an incomplete candidate, and any later recovery without a verified entry must follow the `invalid_or_unknown` fail-closed rule below.

Each recovery tracking entry has these required top-level fields:

| Field | Required meaning |
| --- | --- |
| `recovery_record_schema_version` | Closed contract version for interpreting the entry. |
| `recovery_record_id` | Stable unique identity for this recovery entry. |
| `persistence_operation_id` | Stable identity joining the Artifact and State phases of one Persistence operation. |
| `request_binding` | Required object containing `request_id`, `idempotency_key`, `request_fingerprint`, and `write_result_id`. |
| `artifact_reference` | Complete verified Reference; never only a path. |
| `state_target_binding` | Required object containing `target_state_id`, registered `target_field`, `expected_state_revision`, `expected_state_hash`, and complete `expected_current_artifact_reference`. |
| `creation_authority_binding` | Registered discriminated object containing every Plan, Design Lock, Human Authorization, predecessor, subject, source, Development security-scan, Human Action, or Harness-evidence binding applicable to the Artifact type at write time. |
| `artifact_write_completed_at` | Trusted timestamp of verified `written` or `already_written` completion; it is evidence, not identity or ordering authority. |
| `state_update_evidence` | Discriminated object: `not_attempted`, or `attempted` with trusted attempt time, State result, and safe reason code. |
| `recovery_evidence` | Discriminated object: `not_attempted`, or `attempted` with trusted attempt time, exclusive reconnection outcome, and safe reason code. |
| `lifecycle_status` | Exactly `state_update_pending`, `under_assessment`, `recovery_pending`, or `resolved`; it records process stage, not eligibility. |
| `candidate_classification` | Exactly `pending`, `reconnectable`, `deferred`, or `invalid_or_unknown`; `pending` is allowed only until required evidence is assessed. |
| `reason_code` | Closed machine-readable reason for the current lifecycle and classification; Human prose alone is insufficient. |

The discriminated evidence objects avoid a large nullable timestamp and error-field collection: fields required by the selected variant are present, and inapplicable fields are absent. The independent recovery State revision and hash protect creation and updates of the tracking entry under the existing State mutation rules; they do not replace or relax the separately captured target Workflow State preconditions.

The entry preserves which write produced the Artifact, which exact Artifact is involved, which State field was intended, the creation-time authority, current classification, and the latest State/recovery attempt. It contains references and safe identifiers only; it must not contain payload bytes, raw source, secrets, credentials, private information, raw exception output, or complete Tool output.

If a recovery tracking entry cannot be found or verified, filesystem discovery cannot replace it. The Artifact may be investigated using its immutable envelope and other evidence, but it remains `invalid_or_unknown` unless the full operation and authority binding is independently reconstructed and Human-reviewed. An inventory check may raise such a discovered Artifact as an unclassified safety exception, but Path scanning alone cannot promote, reconnect, resolve, or delete it. This fail-closed limitation does not decide the future cross-resource transaction implementation.

### Recovery State Transitions

The minimum transitions are:

```text
artifact_written
  → state_update_pending
  → reconnectable
  → reconnected
  → resolved
```

```text
artifact_written
  → state_update_pending
  → deferred
```

```text
artifact_written
  → provenance_invalid_or_unknown
  → invalid_or_unknown
```

`artifact_written → state_update_pending` describes the operation stage. Assessment then sets `candidate_classification` to `reconnectable`, `deferred`, or `invalid_or_unknown`; a reconnectable entry uses lifecycle `recovery_pending`. `reconnected` or `already_connected` changes lifecycle to `resolved` after full verification. `still_deferred` retains classification `deferred`; `blocked` sets or keeps `deferred` when creation legitimacy remains verified, and otherwise sets `invalid_or_unknown`. `failed` retains the last safe classification and records only sanitized attempt evidence; it never becomes success by itself.

A candidate ceases to be an orphan candidate only when `reconnected` or `already_connected` establishes Persistence success for the same operation. Artifact existence, request dispatch, Reference equality without invariant checks, `deferred`, or an unknown result cannot resolve it.

### Deletion and Disposal Boundary

No orphan candidate is automatically deleted by this policy. The following are explicitly insufficient grounds for deletion:

- State has not yet reflected a newly saved Artifact;
- current State does not reference the Artifact;
- the Artifact is an older or superseded revision;
- filesystem traversal finds no current pointer;
- Evidence Chain, Decision Record, or Authorization Record references have not been exhaustively checked;
- creation authority or provenance has not been verified;
- reconnection eligibility has not been evaluated; or
- a candidate is `deferred` or `invalid_or_unknown`.

The required policy is:

```text
orphan candidate
  → assess reconnection first

not reconnectable now
  → retain as deferred or invalid_or_unknown

disposal
  → wait for a future retention, Human Review, and garbage-collection decision
```

Final deletion conditions, retention duration, archive policy, automatic versus manual disposal, garbage collection, quarantine location, and physical deletion mechanics remain undecided. Human approval is required before any future final disposal policy acts on material whose safety and reference closure have not been deterministically proven. This design authorizes no deletion.

Until such a future disposition policy exists, every unresolved tracking entry remains an explicit incomplete Persistence condition in recovery tracking State and must remain discoverable for reassessment. It cannot be silently dropped, marked successful, or omitted from required recovery review. This liveness requirement prohibits indefinite invisible abandonment without choosing a retention duration or deletion mechanism here.

### Responsibility and Human Boundaries

| Responsibility | Allowed duties | Prohibited duties |
| --- | --- | --- |
| Artifact Writer | Persist and verify Artifact; return Reference and Write Result | Classify orphan, mutate State, reconnect, delete, move, or rewrite Artifact |
| Interface / Persistence Orchestrator | Bind Artifact and State results; detect incomplete Persistence; construct tracking evidence; coordinate classification and same-Reference retry | Directly delete Artifact, bypass State owner, invent missing provenance, or declare unknown evidence successful |
| Responsible Plan or Execute Interface | Own CAS for its Workflow State and separate recovery tracking State; update and re-read each State; validate current Plan, Authorization, subject, target field, and recovery tracking entry | Alter Artifact or bypass current invariants |
| Human | Decide treatment of provenance-unknown material, reuse after material change when a new Human decision is required, and any future final disposal authorization | Not required for ordinary reconnection when every `reconnectable` invariant passes |

No recovery Agent, recovery Skill, or new State mutation owner is created by this decision. Human Review cannot retroactively rewrite invalid provenance; it may decide safe isolation, whether a new authorized operation should be created, or future disposal handling.

## Development Artifact Candidate Security Scan

The Development Artifact scan is the exit inspection immediately before a Candidate may enter:

```text
.codex/harness/development/artifacts/
```

In Human terms:

```text
Development Artifact scanは、
開発中のArtifactを棚へ置く直前に、
PromptやTool出力に混ざった秘密を持ち込まないための検査である。
```

It is distinct from Domain ingestion safety:

```text
Development Artifact scan
  → determines whether exact Candidate bytes may enter Development Harness Artifact Root

Domain ingestion safety
  → determines whether material may enter Career Knowledge or Domain State
```

Development Artifact scan does not decide Career Knowledge persistence, Resume correctness, claim evidence, or Domain raw-source ingestion. Evidence before Claims remains a governing product/workflow invariant and is not collapsed into a security classification. Development scan does not replace or weaken it. A scan `pass` or Human-reviewed eligibility can never be reused as Domain persistence authorization. The same bytes intended for a Domain destination must independently pass that Domain's ingestion contract.

### Policy Ownership and Responsibility Split

The Development Harness is the formal owner of the global Development Artifact Security Policy, its versioning and hard blocks, and the requirement that each registered Artifact type have a versioned type policy. It does not delegate policy ownership to the Scanner or Writer. A material global or type-policy change follows the existing Plan and Human Decision boundary; Human approval changes the policy contract, not one blocked Candidate's result.

```text
Development Security Scanner
  → inspects the exact final Candidate payload bytes
  → returns machine-readable scan facts and evidence
  → does not decide final persistence eligibility
  → does not modify Candidate bytes
  → does not persist the Artifact or mutate Workflow State
  → does not originate Human Authorization

Responsible Plan or Execute Interface
  → verifies evidence integrity, policy versions, type policy, and Candidate binding
  → derives whether Write Request generation is allowed
  → requests Human Action only for review_required
  → never forwards blocked, unknown, or unresolved review_required

Artifact Writer
  → mechanically verifies the Request, evidence, accepted policy versions, final decision, and exact byte hash
  → writes only an eligible Candidate
  → never owns Security Policy, scans content, edits Candidate bytes, interprets context, or approves exceptions

Human
  → acts only on review_required or a material policy-design question
  → may confirm a false positive or require minimization, anonymization, removal, replacement, or policy work
  → cannot override a hard block or unknown result for one Candidate
```

The Scanner reports detection facts. The Interface applies the Harness-owned policy and Human evidence to decide whether the Write Request may be constructed. The Writer enforces that already-derived decision without reinterpreting Scanner findings or Human intent.

### Mandatory Pre-persistence Position and Byte Binding

The only normal order is:

```text
generate Artifact Candidate
  → finalize exact Candidate payload bytes
  → compute payload hash
  → run Development Artifact security scan
  → produce scan evidence
  → verify evidence-to-Candidate binding
  → derive final security decision
  → construct Write Request
  → Artifact Writer verifies the same bytes and persists
```

Post-persistence scanning is not a primary path and cannot cure an unscanned write. Unscanned Candidate bytes, scan staging material, temporary scan output, and review material must never be placed beneath Artifact Root.

The following equality is mandatory at Interface and Writer boundaries:

```text
scan_evidence.payload_hash
= Write_Request.payload_hash
= SHA-256(exact payload bytes received by Artifact Writer)
```

One changed byte invalidates the old evidence and any Human Review Record bound to its hash. The revised Candidate has a new payload hash and requires a new scan. No newline, encoding, Unicode, whitespace, or semantic normalization may occur between hashing, scanning, and writing.

### Scan Surface

The mandatory semantic and secret scan surface is the exact payload byte sequence intended for persistence, regardless of whether its source is Human Prompt, Agent, Skill, Tool output, repository inspection, Review, Plan, ADR, Design Lock, Authorization, Decision, or Handoff generation. No source receives an implicit trust exemption.

The immutable envelope is handled in two layers:

- exact Candidate payload bytes receive the full Development Security scan;
- caller-supplied meaning-bearing metadata receives deterministic hard-block, format, minimization, and registered-field validation before Write Request construction;
- fixed metadata derived exclusively from closed schemas, registry values, revision allocation, hashes, and Path Policy does not require the same semantic scanner, but is structurally validated; and
- any metadata field capable of carrying free-form or source-derived text must either be included in the scanned payload or receive separately hash-bound scan evidence under its registered type policy.

This distinction avoids rescanning fixed machine metadata while preventing secret-bearing text from bypassing the payload scan through an envelope field.

### Exclusive Security Classifications

Every completed scan evidence has exactly one classification:

| Classification | Exclusive meaning | Persistence consequence |
| --- | --- | --- |
| `pass` | All required checks completed; no prohibited data or unresolved ambiguous finding exists; global and type-specific policies pass. | Interface may automatically derive `automatic_pass` and construct a Write Request. |
| `review_required` | A contextual private, internal, or possibly sensitive finding cannot be safely resolved by Scanner policy alone and may be a false positive or permitted minimized field. | Automatic persistence is prohibited until a valid bound Human Action resolves it. |
| `blocked` | A hard-block value, definite prohibited content, forbidden raw material, or non-permitted type/field condition was detected. | Save is prohibited. Candidate-level Human override is impossible. |
| `unknown` | Scanner execution, format support, policy identity, evidence completeness, timeout, integrity, or required-check proof is unavailable. | Save is prohibited and Human intuition cannot convert it to pass. |

```text
blocked
  → save prohibited

unknown
  → save prohibited

review_required
  → save prohibited until the permitted Human Action is complete
```

`blocked` is a positive policy prohibition. `unknown` is inability to establish safety. `review_required` is a bounded contextual question. These meanings do not overlap.

### Hard Blocks, Contextual Review, and Raw Content

The global hard-block policy includes at least actual password values, access tokens, API keys, session secrets, private keys, authentication cookies, Authorization header values, credential-file contents, environment secret values, signing keys, encryption keys, and recovery codes. A Human cannot authorize those bytes as-is.

If such content is needed for explanation, the Candidate must remove, redact, replace, or reference it without reproducing the value, then compute a new hash and run a new scan. Safe category labels and placeholders are allowed only when they cannot reconstruct the protected value.

Contextual findings may include a real person's name, company or customer name, internal project name, non-public URL, repository identifier, email address, user identifier, organization-internal information, or private business context. Their presence is not automatically pass or block. `review_required` is based on the registered Artifact type, purpose, required field, allowed field, minimization, available substitute, and whether raw material is being retained.

Development Artifacts must not persist raw Prompt transcripts, complete conversations, complete Tool or terminal output, environment dumps, HTTP headers, secret-bearing configuration, or complete logs. A necessary excerpt must be minimized, structured, or replaced by a safe reference under the type policy. Even when an excerpt is legitimate evidence, hard-block bytes remain prohibited.

The policy is explicitly layered:

```text
global hard-block policy
  + registered Artifact type-specific allowance policy
  + data-minimization policy
  + raw-content prohibition policy
```

A single forbidden-word list is insufficient. Every closed-registry Artifact type must bind to a defined type-policy version. An unregistered type or a registered type lacking an applicable policy fails closed.

Type policy may, under minimization, permit repository paths and technical identifiers in a Plan, trusted actor identity in an Authorization Record, safe finding locations in a Review, and branch names or commit SHAs in a Handoff. Those examples are not blanket allowlists: the registered field, purpose, raw-content rule, global hard blocks, and current type-policy version still govern each value.

### Scan Evidence Contract

Scan evidence is an immutable operational record in the separate scan tracking State, outside Artifact Root. It is not a canonical Development Artifact and cannot itself serve as security policy or Human decision.

Every evidence record has these required fields:

| Field | Required meaning |
| --- | --- |
| `scan_evidence_schema_version` | Closed evidence contract version. |
| `scan_evidence_id` | Globally unique immutable evidence identity. |
| `evidence_hash` | SHA-256 of the canonical evidence record excluding this field, used with trusted Scanner identity verification. |
| `scanner_id` | Trusted registered Scanner implementation identity. |
| `scanner_version` | Exact Scanner version used. |
| `security_policy_version` | Exact global Development Artifact Security Policy version evaluated. |
| `artifact_type_policy_version` | Exact registered type-policy version evaluated. |
| `artifact_type` | Closed-registry Candidate type. |
| `logical_artifact_id` | Candidate logical series identity. |
| `payload_hash` | SHA-256 of the exact scanned payload bytes. |
| `payload_format` | Registered Candidate format. |
| `source_binding` | Safe reference-only provenance binding matching the Candidate; never source content. |
| `scan_status` | Exactly `pass`, `review_required`, `blocked`, or `unknown`. |
| `completed_checks` | Closed set of check identifiers and completion states required by both policy versions. Missing or unknown required checks prevent `pass`. |
| `reason_codes` | Required list of safe closed codes; it may be empty only for `pass`. |
| `safe_locations` | Discriminated object: `none`, or safe section identifiers, field paths, or line ranges that cannot reproduce finding values. |
| `review_requirement` | Discriminated object: `not_required`, or `human_review_required` with allowed action types and safe reason codes. |
| `scan_started_at` | Trusted scan start timestamp; not identity or ordering authority. |
| `scan_completed_at` | Trusted scan completion timestamp. |

Evidence canonicalization must be fixed before implementation. The Interface and Writer recompute `evidence_hash`, authenticate the registered Scanner identity through the trusted execution boundary, and reject unknown schema, Scanner, or policy versions.

The evidence combinations are closed: `review_required` requires `review_requirement: human_review_required`; `pass`, `blocked`, and `unknown` require `review_requirement: not_required`. A hard-block reason code cannot coexist with `pass` or `review_required`. Any impossible combination makes the evidence invalid and persistence unavailable.

Evidence, errors, logs, and review summaries must never contain Candidate payload, a detected value, credential text, private-information text, raw Prompt, raw Tool output, environment dumps, secret-bearing stack arguments, or a content-reconstructing excerpt. Reasons use codes such as `credential_pattern_detected`, never a value-bearing message. Consistent with Write Result, safe errors also omit payload hash values; a hash remains in the structured evidence binding, not logs or messages.

Safe error and log output is limited to a closed machine-readable code, a sanitized message, registered Scanner or policy identifiers, a retryable flag, and a safe location identifier. Raw exceptions and stack traces must be sanitized before any persistence or display.

### Human Review Contract

`review_required` permits exactly these Human Actions:

| Action | Meaning and next step |
| --- | --- |
| `false_positive_confirmed` | Human confirms the safe category/location is not prohibited content. The immutable Record applies only to the exact evidence, type, and payload hash; Interface may derive `human_false_positive_confirmed`. |
| `candidate_revision_required` | Human requires removal, anonymization, minimization, replacement, or reference conversion. Changed bytes form a new Candidate hash and must be scanned again. |
| `policy_decision_required` | The policy cannot express a legitimate general rule. Candidate persistence stops until an accepted policy change creates a new version and the Candidate is rescanned. |

Every immutable Human Review Record has exactly:

```yaml
human_action_id: string
human_action_record_hash: sha256:string
actor_identity: trusted-human-identity
action_type: false_positive_confirmed | candidate_revision_required | policy_decision_required
scan_evidence_id: string
scan_evidence_hash: sha256:string
payload_hash: sha256:string
artifact_type: registered-type
security_policy_version: string
artifact_type_policy_version: string
reason_code: safe-closed-code
created_at: trusted-timestamp
```

`human_action_record_hash` covers the canonical immutable Record excluding itself; without it the Writer could not verify that the reviewed action and bindings were unchanged. The policy versions and evidence hash prevent the action from being rebound to different policy semantics or altered evidence.

The Record is an append-only event in scan tracking State, not a rewrite of scan evidence. `false_positive_confirmed` is accepted only when the original evidence is `review_required`, its review requirement allows that action, and neither evidence nor current policy contains a hard-block reason. It does not change `scan_status` to `pass`; final persistence eligibility is derived from both immutable records. Candidate changes invalidate the Record because its payload hash no longer matches.

Review UI and records expose only safe category, safe location, code, type, and purpose. They must not show or replicate the suspected secret or private value.

These actions are prohibited:

```text
save_anyway
ignore_security_scan
force_pass
override_blocked
override_unknown
```

A blocked Candidate must be revised and rescanned. Unknown requires Scanner recovery, another registered Scanner accepted by policy, or a policy/version repair followed by a new scan. Human judgment cannot substitute for scan evidence.

### Bounded Retry and Candidate Lineage

Scan lifecycle evidence is held in a separate versioned scan tracking State owned by the responsible Plan or Execute Interface. It records a stable `candidate_lineage_id`, every distinct payload hash, scan evidence IDs, Scanner execution attempts, Candidate revision cause, Human Action references, policy versions, lifecycle status, and the latest classification. Durable State revision and hash make limits survive process restart.

The mandatory loop controls are:

- the same payload hash and accepted policy versions reuse existing valid scan evidence instead of rescanning;
- a Scanner runtime `unknown` may retry only up to the finite `max_scanner_execution_retries_per_payload` declared by Security Policy;
- retry attempts are counted per lineage, payload hash, Scanner identity/version, and policy versions, not by process memory;
- changed Candidate bytes create a new hash within the same lineage and require a new scan;
- automatic Candidate modification, if a future authorized modifier exists, is limited to one new Candidate revision per lineage;
- after the applicable retry or automatic-revision limit, lifecycle becomes `human_action_required`, not `blocked`; and
- Human-requested revision, same-Candidate retry, Scanner execution retry, and policy-version rescan remain distinct recorded causes.

No Scanner modifies bytes. This decision creates no automatic modifier. The one-revision ceiling constrains any future modifier without authorizing one. A Human may request another explicit Candidate revision, but each changed payload is rescanned and the durable lineage remains visible; no automatic loop restarts from zero.

In Human terms:

```text
同じCandidateを何度もscanしない。
Candidateが変わった場合だけ新しくscanする。
自動修正と再scanは有限回で停止する。
```

### Scan Lifecycle and Classification Separation

Lifecycle and security result are independent fields. Scan evidence always contains one of the four security classifications; tracking State represents pre-scan and control flow separately.

```text
lifecycle_status:
  candidate_created | scan_pending | human_review_pending |
  candidate_revision_pending | ready_for_write |
  human_action_required | terminated

latest_scan:
  state: absent
  OR
  state: present
  scan_evidence_id: string
  security_classification: pass | review_required | blocked | unknown
```

Required flows include:

```text
candidate_created → scan_pending → pass → ready_for_write

candidate_created → scan_pending → review_required
  → human_review_pending → false_positive_confirmed → ready_for_write

candidate_created → scan_pending → review_required
  → candidate_revision_pending → candidate_created → scan_pending

candidate_created → scan_pending → blocked → terminated

candidate_created → scan_pending → unknown
  → bounded_retry → human_action_required
```

`bounded_retry` is an event/cause within scan tracking State, not a security classification. Exhaustion means automation cannot continue; it does not assert that the Candidate is dangerous.

For an `unknown` result, `human_action_required` requests operational intervention to restore a registered Scanner, resolve policy/version support, or request a safe Candidate revision. It is not `false_positive_confirmed`, cannot authorize persistence, and cannot convert unknown evidence into pass.

### Write Request Security Binding

The required `development_security_scan_binding` has exactly these fields:

```yaml
development_security_scan_binding:
  scan_evidence_id: string
  scan_evidence_hash: sha256:string
  scanned_payload_hash: sha256:string
  security_policy_version: string
  artifact_type_policy_version: string
  scan_status: pass | review_required
  final_security_decision: automatic_pass | human_false_positive_confirmed
  human_review_binding:
    state: not_required
    # or:
    # state: required
    # human_action_id: string
    # human_action_record_hash: sha256:string
```

`scan_status: pass` requires `automatic_pass` and `human_review_binding.state: not_required`. `scan_status: review_required` requires `human_false_positive_confirmed` and a complete valid `false_positive_confirmed` Record. Every other combination is invalid. `blocked` and `unknown` cannot appear in a Write Request binding because no Write Request may be generated for them.

Before Request construction, the Interface verifies evidence integrity and Scanner identity, all required checks, logical ID, type, format, source binding, payload hash, accepted policy versions, final decision, and any Human Record. The following must all match the Write Request:

```text
scan evidence payload hash = Write Request payload hash
scan evidence artifact type = Write Request artifact type
scan evidence logical ID = Write Request logical ID
scan evidence payload format = Write Request payload format
scan evidence source binding = Write Request source binding
```

Every policy release declares whether evidence from an earlier version remains accepted, requires additional checks, or is revoked. A security-critical update marks affected earlier versions `rescan_required`; those versions cannot produce a new Write Request. Unchanged compatible policy may explicitly accept earlier evidence. Missing, unknown, or ambiguous compatibility fails closed. Detailed compatibility storage and migration are implementation design, but unconditional validity and unconditional invalidation are both prohibited.

### Artifact Writer Save Gate

The responsible Interface / Persistence Orchestrator resolves the immutable evidence and any Human Review Record from scan tracking State and supplies them through the trusted persistence boundary. The Writer does not independently mutate or interpret that State. It saves only when all of these mechanically verifiable conditions pass:

1. the complete Write Request and request fingerprint validate;
2. exact received bytes match Request `payload_hash`;
3. scan evidence exists, authenticates, and its canonical evidence hash validates;
4. evidence type, logical ID, format, source binding, and payload hash match the Request;
5. Scanner, global policy, and type-policy versions are registered and currently accepted;
6. every required check completed;
7. final decision is `automatic_pass` for original `pass`, or `human_false_positive_confirmed` for original `review_required` with a valid exact-hash Human Record;
8. neither evidence nor current policy indicates `blocked` or `unknown`; and
9. all existing revision, Path Policy, and create-only preconditions pass.

The Writer does not reinterpret findings, downgrade a hard block, decide false positives, repair evidence, or infer Human intent. Any invalid combination returns `blocked` under the existing Write Result contract. Scanner execution failure remains `unknown` before Write Request generation and must not be mislabeled as Writer filesystem `failed`.

### Security and Persistence Success Separation

```text
Security scan success
≠ Artifact write success
≠ State update success
≠ Persistence success
```

`pass` or a valid Human-reviewed final decision means only that the exact Candidate may proceed to Write Request. It does not prove an Artifact exists, a Reference is valid, State is connected, or the Persistence operation completed. Artifact-first write, recovery tracking, State update, and orphan contracts remain unchanged.

### Fail-closed Save Conditions

Candidate persistence is prohibited when any of the following holds:

- scan evidence is absent, incomplete, unauthenticated, or has an invalid evidence hash;
- payload hash, type, logical ID, format, or source binding differs;
- Scanner, Security Policy, type-policy, or compatibility version is unknown or unacceptable;
- any mandatory check is incomplete or unknown;
- status is `blocked` or `unknown`;
- status is `review_required` without an exact-hash valid `false_positive_confirmed` Record;
- Human Action type, evidence ID, payload hash, or Artifact type differs;
- Candidate bytes changed after scan;
- a hard block is paired with any Human override attempt;
- Artifact type is unregistered or lacks a type policy; or
- lifecycle has not reached `ready_for_write`.

Failure never authorizes placement of Candidate bytes, temporary scan files, review copies, or logs beneath Artifact Root. Pre-scan Candidate holding and quarantine implementation remain outside this design; Artifact Root is not a staging area.

### Implementation-ready Security Contract Decisions

The following decisions close the contract questions that must be settled before Security Schemas or Runtime are implemented. They refine, and do not replace, the ownership, evidence, Human Review, and Write Request rules above.

#### Adopted implementation boundary

The adopted boundary is **Interface-first**. The next implementation may define the source-binding Schema, Security Policy Registry, Scan Evidence Schema, Human Review Schema, Write Request Security Binding Schema, trusted Scanner interface, and validators. It must not select or implement a secret-detection engine, regular-expression set, entropy detector, remote product, Scan Skill, or retry constant as part of that work. A concrete Scanner requires a later accepted decision that versions its detection behavior, false-positive behavior, synthetic fixtures, and policy compatibility.

The rejected alternative is a minimally specified local Scanner. Even a small Scanner would silently make detection rules and false-positive semantics part of the security boundary without an accepted versioned engine decision. A three-classification model is also rejected: `review_required` and `unknown` remain independent fail-closed facts and `invalid` remains a validator result, never scan evidence classification.

The previously unresolved questions and their adopted decisions are:

| Question | Adopted decision |
| --- | --- |
| Security classification | Preserve the exclusive four-status model; Schema or integrity failure is a validator result |
| Final decision | Keep only the two existing eligibility decisions and generate neither for ineligible evidence |
| Evidence shape and canonicalization | Fix the exact closed Record, deterministic list ordering, and hash envelope below |
| Source provenance | Add a distinct hashed `source_binding`; require but do not equate it with `generated_by` |
| Type-policy ownership | Use a Harness-owned Security Registry keyed by the existing closed Artifact Type identifiers |
| Human Review | Reuse the existing immutable Human Action Record and bind it to exact evidence and payload |
| Scanner trust | Use an interface-only Scanner plus composition-root-installed opaque adapter attestation |
| Scanner engine and rules | Defer to a separate accepted implementation decision |

Rejected alternatives are:

- merging `review_required` into `blocked`, or treating `unknown` as a retryable allow state;
- adding `invalid` as persisted scan classification;
- converting `blocked` or `unknown` through Human confirmation;
- treating Candidate `generated_by` as complete source provenance;
- merging global Security Policy and Artifact type-policy versions;
- merging Scan Evidence, Human Action, and Write Request Security Binding into one mutable Record;
- adding duplicated Candidate or Scanner fields or a redundant hash to the exact Write Request Security Binding;
- selecting a minimally specified detection engine or rule set during Schema work; and
- placing security tracing in Artifact Reference rather than resolving evidence through the Write Request and Writer boundary.

#### Exclusive classification and disposition matrix

| `scan_status` | Scanner may return it | Human Review | Write Request Security Binding | `final_security_decision` | Retry and fail-closed treatment |
| --- | --- | --- | --- | --- | --- |
| `pass` | Yes, only after every applicable required check completed | Not required | Eligible when evidence, policy compatibility, source binding, and Candidate binding validate | `automatic_pass` | No identical rescan; reuse valid evidence for the same payload and accepted policy versions |
| `review_required` | Yes, only after every applicable required check completed and only for contextual findings allowed by type policy | Required before eligibility | Ineligible until an exact-evidence, exact-payload `false_positive_confirmed` Record validates | `human_false_positive_confirmed` only after that Record; otherwise absent | Human action is required; unchanged evidence is not rescanned merely to seek a different result |
| `blocked` | Yes, only for a closed hard-block or definite prohibited-content reason | Cannot override | Never generated | Absent | Save is prohibited; only changed Candidate bytes under a new hash may be rescanned |
| `unknown` | Yes, for execution, support, policy, completeness, timeout, or integrity uncertainty | Cannot convert it to eligibility | Never generated | Absent | Fail closed; bounded operational retry is allowed only under durable policy-controlled tracking |

`final_security_decision` is an eligibility derivation, not a second four-way scan classification. Its closed vocabulary is exactly `automatic_pass` and `human_false_positive_confirmed`. There is no `allow`, `block`, `rejected`, or unresolved value in a Write Request binding. A rejected Review, `candidate_revision_required`, `policy_decision_required`, `blocked`, `unknown`, invalid evidence, or unresolved `review_required` produces no Security Binding and no final decision.

#### Security Policy Registry ownership and exact contract

The Development Harness owns a dedicated closed Security Policy Registry. It is separate from the canonicality metadata while using the same closed Artifact Type identifiers. Its top-level contract contains exactly:

```yaml
security_policy_registry_schema_version: "1.0"
accepted_security_policy_versions: [string]
allowed_scanners:
  - scanner_id: string
    scanner_version: string
accepted_scan_evidence_schema_versions: [string]
global_required_checks: [check_id]
reason_code_vocabulary:
  reason_code:
    classification: contextual | hard_block | operational_unknown
    allowed_scan_statuses: [review_required | blocked | unknown]
safe_location_policy_version: string
policy_compatibility:
  prior_security_policy_version:
    disposition: accepted | additional_checks_required | rescan_required
    additional_required_checks: [check_id]
artifact_type_policies:
  artifact_type:
    artifact_type_policy_version: string
    accepted_source_binding_variants: [generated_only | artifact_references | repository_snapshot]
    required_checks: [check_id]
    contextual_review_categories: [reason_code]
    raw_content_policy: prohibited | minimized_registered_fields_only
```

All mappings are closed and all lists are duplicate-free. Check identifiers and reason codes are closed registry values, not free-form Scanner output. Effective required checks are the duplicate-free union of `global_required_checks`, the selected type policy's `required_checks`, and any compatibility-required checks. An unregistered Artifact type, absent type policy, unknown version, ambiguous compatibility entry, unknown reason code, or unknown Scanner fails closed.

The global `security_policy_version` governs hard blocks, global required checks, Scanner acceptance, safe-location rules, and compatibility. Each `artifact_type_policy_version` governs type-specific allowed provenance variants, additional checks, contextual-review categories, registered-field allowances, minimization, and raw-content treatment. They remain separate versions because a type-policy change must not silently redefine global hard blocks, and a global emergency revocation must not require unrelated type versions to be renumbered.

#### Source binding contract

`generated_by` and `source_binding` are distinct. `generated_by` identifies the registered Skill or Interface execution identity that produced the Candidate. `source_binding` proves which safe, immutable provenance facts that execution used. The source binding's `generator_identity` must exactly equal Candidate `generated_by`, but neither Record substitutes for the other.

Every source binding begins with these fields and has no additional properties outside its selected variant:

```yaml
source_binding_schema_version: "1.0"
binding_type: generated_only | artifact_references | repository_snapshot
generator_identity:
  source_id: string
  source_version: string
generator_execution_id: string
source_binding_hash: sha256:string
```

The variant-specific fields are exactly:

```yaml
# generated_only
generation_input_fingerprint_schema_version: "1.0"
generation_input_policy_version: generation-input-v1
generation_input_domain: development-artifact-generation-input
generation_input_fingerprint: sha256:string

# artifact_references
source_references:
  - artifact_type: registered-type
    logical_artifact_id: string
    logical_series:
      identity_type: logical_id | subject_id | subject_id_revision
      # closed variant fields required by the selected identity_type
    artifact_revision: positive-integer
    content_hash: sha256:string
source_reference_set_hash: sha256:string

# repository_snapshot
repository_identity:
  provider: github
  repository_id: stable-registered-id
snapshot_kind: canonical_worktree_snapshot
snapshot_policy_version: repository-snapshot-v1
repository_snapshot_hash: sha256:string
```

`source_binding_hash` is SHA-256 of canonical JSON for the complete binding excluding that field. `generation_input_fingerprint` is SHA-256 of a versioned, domain-separated canonical envelope containing the fingerprint Schema version, policy version, fixed domain, generator identity, generator execution ID, and the sorted hashes of registered safe immutable inputs. It never hashes a caller-supplied fingerprint as evidence and never retains or enables reconstruction of raw Prompt, raw source, private material, complete Tool output, environment content, or payload copies.

Each source Artifact Reference carries the complete closed Path Policy `logical_series`. Its immutable identity is `(artifact_type, logical_series, artifact_revision)`; `logical_artifact_id` must agree with that series. `content_hash` authenticates that identity but is not part of its duplicate key. The same identity and hash repeated is a duplicate, while the same identity with a different hash is an integrity conflict. References are sorted by immutable identity with logical ID and content hash only as deterministic tie-breakers. `source_reference_set_hash` commits only to this canonical Reference set so later evidence can compare the input set independently; `source_binding_hash` additionally commits to the generator, execution, and binding variant.

A repository snapshot is identified by the complete tuple `(repository_identity, snapshot_kind, snapshot_policy_version, repository_snapshot_hash)`. Repository identity is a closed stable provider identifier, never a local or absolute path, display name, branch name, or unvalidated remote URL. The initial registered kind is `canonical_worktree_snapshot`; other snapshot kinds remain unsupported until their canonical hash policy is accepted.

A hash is necessary but not sufficient provenance. Structural validation checks Schema, canonical ordering, conflicts, and integrity. Separate authority validation resolves `(generator_identity, generator_execution_id)` through the composition-root-installed execution index and requires byte-for-byte equality with exactly one immutable source binding. Reusing that execution identity with the same binding is idempotent; rebinding it to a different binding is rejected. Caller-authored mappings, caller-installed stores, and arbitrary resolver subclasses are not production authority. Until the formal Artifact Reference resolver and snapshot producer are installed, their production variants fail closed even though their structural Schemas exist.

Production Candidate validation never accepts an authority argument. It closes over the exact authority installed by the production composition root. A separate internal/test validation entrypoint may accept a test authority implementing the same comparison contract, but that entrypoint is not callable by a production Interface and cannot establish production trust. The in-memory execution index is a single-threaded test utility only; production uniqueness belongs to the installed durable execution store contract.

For `generated_only`, the installed authority resolves safe execution evidence containing the fingerprint Schema version, policy version, fixed domain, generator identity, generator execution ID, and duplicate-free safe immutable input hashes. The validator canonicalizes those hashes and recomputes `generation_input_fingerprint`; a completed fingerprint string without that evidence is insufficient. Canonicality and Revision resolve source provenance through this independent authority and do not accept a binding copied into their own caller-supplied context or snapshot as source authority.

The Python object boundary does not claim tamper resistance after an attacker already has arbitrary code execution in the same interpreter. Class monkey patching, `object.__setattr__` against private fields, and direct mutation of module globals are outside this contract's threat model. Public API injection, arbitrary subclasses, caller-authored contexts or snapshots, caller-created indexes, and caller-supplied fingerprints remain within scope and must fail closed.

Candidate Schema implementation adds the complete `source_binding`. Scan Request, Scan Evidence, and Write Request carry the same binding byte-for-byte after independent Schema and integrity validation. Candidate `generated_by` equals `source_binding.generator_identity`; Scan Evidence never derives one from the other or accepts a caller-authored provenance claim as trusted execution evidence.

#### Exact Scan Evidence Record shape

Every immutable evidence record has exactly these top-level fields and `additionalProperties: false`:

```yaml
scan_evidence_schema_version: "1.0"
scan_evidence_id: string
evidence_hash: sha256:string
scanner_id: string
scanner_version: string
security_policy_version: string
artifact_type_policy_version: string
artifact_type: registered-type
logical_artifact_id: string
payload_hash: sha256:string
payload_format: registered-format
source_binding: source-binding-object
scan_status: pass | review_required | blocked | unknown
completed_checks:
  - check_id: registered-check-id
    completion_status: completed | not_completed | unknown
reason_codes: [registered-safe-reason-code]
safe_locations:
  state: none
  # or state: present with locations as defined below
review_requirement:
  state: not_required
  # or state: human_review_required with allowed actions and reasons
scan_started_at: trusted-date-time
scan_completed_at: trusted-date-time
```

`evidence_hash` covers canonical JSON for every field except itself. Mapping keys are lexicographically sorted. `completed_checks` are sorted by `check_id`, contain every effective required check exactly once, and contain no other check. `reason_codes` are unique and lexicographically sorted. Safe locations are sorted by their canonical tuple. These ordering rules make list presentation deterministic rather than relying on Scanner insertion order.

`pass`, `review_required`, and `blocked` require every effective check to have `completion_status: completed`. `unknown` requires at least one `not_completed` or `unknown` check, or an operational-unknown reason that proves why complete safety evidence is unavailable. `pass` requires empty `reason_codes`, `safe_locations.state: none`, and `review_requirement.state: not_required`. `review_required` requires at least one contextual reason, a present safe location, and `human_review_required`. `blocked` requires at least one hard-block reason and `not_required`. `unknown` requires at least one operational-unknown reason and `not_required`. Impossible combinations are invalid validator results, not a fifth scan status.

Safe locations have exactly one of these closed forms:

```yaml
safe_locations:
  state: none
```

```yaml
safe_locations:
  state: present
  locations:
    - location_type: section_id
      section_id: safe-ascii-identifier
    # or
    - location_type: field_path
      field_path: [safe-ascii-field-segment]
    # or
    - location_type: line_range
      start_line: positive-integer
      end_line: positive-integer
```

Locations never contain matched text, field values, absolute paths, source excerpts, payload fragments, or content-reconstructing offsets. A `field_path` names registered structural fields only. Line ranges identify positions without retaining the line. The policy-defined safe ASCII patterns and maximum list sizes are closed Schema constants.

Timestamps prove scan execution interval only. `scan_started_at` must not be after `scan_completed_at`; neither timestamp establishes Candidate identity, latest status, retry ordering, or authorization.

#### Human Review Record and binding

The existing immutable Human Action Record shape above is retained exactly; no second Review Record vocabulary is introduced. `false_positive_confirmed` means only that an authorized Human determined the contextual finding identified by the exact evidence is not prohibited under the accepted policy. It cannot waive a hard block, cure `unknown`, or change the immutable `scan_status`.

The review authority is a registered Human Action boundary whose trusted actor identity and action authorization validate under the existing Human Gate contract. The Record binds to `scan_evidence_id`, `scan_evidence_hash`, `payload_hash`, `artifact_type`, `security_policy_version`, and `artifact_type_policy_version`. Any evidence change, policy incompatibility, Candidate byte change, or payload-hash change invalidates reuse and requires a new scan and, when still required, a new Human Action.

The evidence `review_requirement` variants are exactly:

```yaml
review_requirement:
  state: not_required
```

```yaml
review_requirement:
  state: human_review_required
  allowed_action_types:
    - false_positive_confirmed
    - candidate_revision_required
    - policy_decision_required
  reason_codes: [registered-contextual-reason-code]
```

The Write Request Security Binding does not embed the Human Record. It retains only the exact immutable ID and hash pair, while the Interface and Writer resolve and fully validate the Record through the trusted Human Action boundary.

#### Exact Write Request Security Binding shape

The existing exact field set remains unchanged and is implemented with `additionalProperties: false`:

```yaml
development_security_scan_binding:
  scan_evidence_id: string
  scan_evidence_hash: sha256:string
  scanned_payload_hash: sha256:string
  security_policy_version: string
  artifact_type_policy_version: string
  scan_status: pass | review_required
  final_security_decision: automatic_pass | human_false_positive_confirmed
  human_review_binding:
    state: not_required
    # or exactly:
    # state: required
    # human_action_id: string
    # human_action_record_hash: sha256:string
```

No separate binding hash is added. The future Write Request fingerprint covers the complete Security Binding; `scan_evidence_hash` and any `human_action_record_hash` independently protect the referenced immutable records. Adding Candidate or Scanner identity to this binding is rejected because the Write Request already holds Candidate identity and the resolved Scan Evidence authenticates Scanner identity. Duplicating them would create drift without adding authority.

`pass` requires `automatic_pass` and `not_required`. `review_required` requires `human_false_positive_confirmed`, `required`, and a fully validated `false_positive_confirmed` Human Action Record. `blocked`, `unknown`, invalid Evidence, incompatible policy, unresolved Review, rejected Review, `candidate_revision_required`, and `policy_decision_required` produce no binding. Evidence is always resolved and revalidated; the binding is never accepted as a self-authenticating summary.

#### Trusted Scanner provenance boundary

The production boundary has an interface-only `DevelopmentSecurityScanner` and an opaque adapter-issued Scanner execution attestation. The attestation binds Scanner ID/version, accepted global and type-policy versions, exact payload hash, scan evidence ID/hash, execution interval, and registered adapter identity. The Validator accepts neither raw mappings nor caller booleans and performs the three-way equality:

```text
Scan Evidence scanner identity
= trusted adapter execution identity
= Security Policy Registry allowed Scanner identity
```

The public Scanner interface has no `_mint_context`, token-bearing constructor, receipt factory, or protected helper that an arbitrary subclass can use to create trusted evidence. Only the composition root may install a production adapter backed by the future accepted Scanner implementation. Tests use a separate test authority supplied at the validator composition boundary; it cannot instantiate the production attestation type or register itself as a production Scanner. This is an architectural provenance boundary, not a claim that Python object privacy is cryptographic authentication.

#### Write Request eligibility and implementation order

A Security Binding may be constructed only after the complete Evidence, trusted Scanner attestation, current policy compatibility, source binding, and any Human Action Record independently validate. The Interface must additionally prove exact equality of type, logical ID, payload format, source binding, and payload hash with the future Write Request. `blocked`, `unknown`, invalid Evidence, policy mismatch, payload mismatch, source mismatch, and unresolved Review remain ineligible.

The implementation order is fixed as:

1. source-binding Schema and Candidate integration;
2. Security Policy Registry Schema and closed initial policy metadata, without detection rules;
3. Scan Evidence Schema and validator contract;
4. Human Action Record Schema reuse and Security-specific binding validation;
5. `development_security_scan_binding` Schema and eligibility validator;
6. trusted Scanner interface and adapter-attestation boundary;
7. a separate accepted Scanner implementation decision covering engine, rules, false positives, fixtures, and versioning;
8. Security validation Runtime and scan tracking integration; and
9. Write Request Schema and Runtime.

This order does not authorize Runtime, Scanner rules, Human Review UI, scan tracking State, Write Request, Writer, or persistence implementation in the contract-clarification change.

### Remaining Implementation Boundaries

This decision does not select a secret-detection engine, regex or entropy rules, external security product, Scanner implementation, Scan Skill, staging or quarantine mechanism, Human Review UI, or concrete retry constant. It does not implement Schemas, Runtime, Workflow, Writer changes, scan tracking State, or policy compatibility storage. It also does not modify Domain ingestion, Career Knowledge, Resume generation, retention, or garbage collection.

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

The Repository Publish Result is deliberately excluded from this Development Harness ownership matrix. The Repository Publish Agent generates and persists its body and owns its formal state. The Development Harness owns only the Handoff and may retain a future Agent-owned Result Reference without generating, changing, saving, or Git-managing the Result body.

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

The following remain future implementations:

- atomic Writer behavior;
- State persistence;
- `submit_plan` execution implementation;
- ADR Human Gate implementation;
- Artifact Writer implementation;
- Schema additions; and
- Workflow changes.

## Artifact Persistence Design Completion

The eight planned Artifact Persistence decision areas are now defined at contract level: formal-adoption ownership, immutable revisions, Artifact-first State consistency, orphan recovery, persistence boundary fields, Artifact type and Path Policy, Development Candidate security-scan ownership, and Human Gate/status binding. Implementation, Schema, Runtime, Workflow, and the final cross-resource transaction boundary remain separate future work and must preserve these decisions.
