# v0.4.0 Review & Promotion Concept

## Purpose

v0.4.0 makes the promotion boundary explicit. It defines how a Canonical Event may approach future Career Knowledge persistence without allowing Source, review worklists, decisions, audit metadata, or generated artifacts to be mistaken for Career Knowledge.

```text
v0.4.0 defines the Review & Promotion boundary.
v0.4.0 does not implement full Career Knowledge persistence.
v0.4.0 does not implement downstream Claim / View / Resume generation.
```

Career Knowledge is the central asset. Career Knowledge Store defines the future source-of-truth boundary for reviewed, accepted career meaning. v0.4.0 prepares Career Knowledge promotion; it does not operate a completed Career Knowledge persistence system.

## Relationship to v0.3.0 and v0.5.0

```text
v0.3.0 — Source Intelligence
Source → Canonical Event

v0.4.0 — Review & Promotion Boundary
Canonical Event → Review Queue → Human Review → Decision → Promotion Boundary

v0.5.0+ — Mechanically checkable promotion records
PromotionDecisionRecord → Career Knowledge persistence → Claim / View / Resume generation
```

v0.3.0 normalizes work traces into reviewable Canonical Events. v0.4.0 prevents those events from becoming durable career meaning without Human Review, Evidence, a reasoned decision, and an explicit promotion boundary. v0.5.0+ must make that handoff mechanically checkable.

## Safe Promotion Flow

```text
Source
  ↓
Canonical Event
  ↓
Review Queue
  ↓
Human Review
  ↓
Review Decision / Reason
  ↓
PromotionDecisionRecord
  ↓
Career Knowledge Store
  ↓
Claim Candidate
  ↓
View / Resume
```

This is the architecture across releases. v0.4.0 defines it as boundary and policy; v0.4.0 does not implement the entire runtime flow. In particular, Review Decision alone is not a PromotionDecisionRecord and does not write Career Knowledge.

Evidence Traceability and Rejection / Defer Reason are cross-cutting audit metadata. They remain beside the flow for inspection and accountability; they do not create meaning, approve promotion, or provide wording.

## What v0.4.0 Defines

- Promotion Criteria
- Review Queue
- Review Decision Log boundary
- Career Knowledge Store boundary
- Claim Builder boundary
- View Generation boundary
- Resume Regeneration Policy
- Evidence Traceability boundary
- Rejection / Defer Reason boundary
- the overall Review & Promotion concept

## Responsibility Map

### 01. Promotion Criteria

Defines eligibility for becoming a promotion candidate from Canonical Event to Career Knowledge. It neither approves by itself nor persists Career Knowledge.

### 02. Review Queue

Defines the derived worklist that opens Human Review. It is a worklist, not a Review Decision and not Career Knowledge.

### 03. Review Decision Log

Defines the append-only boundary for Human Review decision history. A Review Decision alone is not PromotionDecisionRecord and does not write Career Knowledge.

### 04. Career Knowledge Store

Defines the future persistence and source-of-truth boundary for reviewed career meaning. v0.4.0 does not create actual Career Knowledge entries or complete persistence.

### 05. Claim Builder

Defines the future boundary for deriving purpose-specific Claim Candidates from Career Knowledge. Claim Candidate is not Career Knowledge. Raw Source and Evidence References are not wording inputs.

### 06. View Generation From Career Knowledge

Defines the future boundary for projecting Career Knowledge and reviewed Claim Candidates into purpose-specific Views. It does not create meaning or update Career Knowledge, and v0.4.0 generates no Views.

### 07. Resume Regeneration Policy

Defines when, from what, and under which conditions a Resume View may be regenerated. Resume is a View, not source of truth, and Resume output must not update Career Knowledge. v0.4.0 performs no regeneration.

### 08. Evidence Traceability

Defines the audit boundary for tracing Career Knowledge, Claims, Views, and Resume output to safe Evidence References. It is audit infrastructure, not generation or claim-verification infrastructure. Evidence References are traceability-only and must not generate wording.

### 09. Rejection / Defer Reason

Defines safe reason categories for `rejected`, `deferred`, `needs_more_evidence`, and `blocked_by_policy`. Reason is audit metadata, not Career Knowledge, Evidence, approval, or wording input.

## Source-of-Truth Boundary

The future source of truth is the Career Knowledge Store for reviewed, accepted career meaning. v0.4.0 defines this future boundary without claiming that persistence is complete.

The following are not Career Knowledge sources of truth:

- Source
- Canonical Event
- Review Queue
- Review Decision alone
- Rejection / Defer Reason
- Evidence Traceability and Evidence References
- Claim Candidate
- View
- Resume
- generated PDF
- generated Markdown

Resume is a View. PDF is a render artifact. Generated Markdown is an output artifact. None of them becomes Career Knowledge or flows back into accepted meaning.

## What v0.4.0 Does Not Implement

- full PromotionDecisionRecord implementation
- full Career Knowledge persistence or Career Knowledge data
- Evidence DB, resolver, or coverage checker
- Reason Record data
- ReReviewRequest
- Claim generation runtime
- View generation runtime
- Resume regeneration runtime
- Renderer or Manifest
- Review UI
- CLI workflow
- generated output

No runtime code, source synchronization behavior, or v0.5.0 schema is added by this concept update.

## Handoff to v0.5.0+

The next phase must define and validate the contracts that make promotion mechanically checkable:

- PromotionDecisionRecord schema
- `accepted_meaning` persistence contract
- Evidence Reference schema
- `support_edges`
- `evidence_set_fingerprint`
- Reason Record schema
- `allowed_reason_codes_by_status`
- ReReviewRequest
- supersession, stale, and lifecycle policy
- contract validation tests

Until those contracts exist, an `approved` Review Decision remains only a future promotion candidate. It must not be represented as a completed Career Knowledge entry.

## Non-Goals

v0.4.0 does not add runtime code, CLI commands, Review UI, Career Knowledge data, Evidence or Reason data, Claim/View/Resume generation, Renderer/Manifest behavior, generated output, source synchronization changes, or v0.5.0 schemas. It does not promote Resume wording, Views, PDFs, generated Markdown, reasons, Evidence References, or Review Queue items into Career Knowledge.
