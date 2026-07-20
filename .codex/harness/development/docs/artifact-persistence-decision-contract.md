# Artifact Persistence Decision Contract

## Status

- Decision status: accepted design decision
- Scope: formal-adoption ownership, Human execution-authorization binding, immutable revision evidence, and Artifact type-to-path policy for Development Harness artifacts
- Implementation status: contract only
- Effective boundary: Artifact generation, persistence, and formal adoption are separate responsibilities

This contract uses **formal-adoption decision owner** instead of the less explicit term `canonicality owner`.

## Scope

This decision defines who may decide that an Artifact or Decision is formally adopted, how Plan readiness remains separate from Human implementation delegation, how revisioned evidence binds both decisions to the execution package, and how each registered Artifact type maps to a safe repository path.

It does not implement Path Policy, define Write Request or Reference Schemas, perform atomic persistence, persist State, or implement an Artifact Writer.

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

The filesystem has no canonical `current.json`, `latest` symlink, fixed-path copy, or other current pointer. Current Development Harness Artifact References are owned only by the relevant Workflow State. Development Execution State may eventually keep only an external, Agent-owned Repository Publish Result Reference; it does not store the Result body or absorb that Agent's publication State. The Reference Schema and State field are deferred. This avoids a second mutable source of truth and prevents a filesystem pointer from diverging from State.

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

The following remain future decisions:

- Artifact-first versus State-first update ordering;
- orphan Artifact policy;
- required Artifact Write Request fields;
- required Artifact Reference fields;
- required Artifact Write Result fields;
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
Required fields for Write Request, Artifact Reference, and Write Result
```

That decision must carry the registered type, derived repository path, revision and stale-write preconditions, content identity, subject binding, and persistence outcome without reopening the ownership, authorization, revision, or Path Policy decisions established here.
