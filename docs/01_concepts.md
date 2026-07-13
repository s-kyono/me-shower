# Concepts

This document defines the core concepts behind me-shower.

Its purpose is to keep the system centered on **Career Knowledge** rather than on output formats, agent workflows, or generated artifacts.

## Career Knowledge

Career Knowledge is the primary asset me-shower is designed to grow.

It is not just a list of career bullet points. It is structured knowledge about work, judgment, improvement, learning, evidence, and repeatable strengths.

Career Knowledge is conceptually above the Resume layer. A Resume is only one view built from it.

```text
Source
    ↓
Evidence
    ↓
Canonical Event
    ↓
Human Review
    ↓
Career Knowledge
    ↓
Claim Builder
    ↓
Claim Candidates
    ↓
Human Review / View Selection
    ↓
View Generation
    ↓
Views
```

## Career Knowledge Store

Career Knowledge Store is the future source of truth for reviewed Career Knowledge. It is downstream of Human Review and Review Decision Log and stores only the meaning a human accepted, supported by safe and traceable Evidence references.

It does not store raw Canonical Events, Source, Review Queue items, Review Decision Log records as knowledge, Resume wording, or generated output. In v0.4.0, `app/data/career_knowledge/` is only an empty storage boundary; no approved decision is automatically persisted because the current decision record does not yet contain `accepted_meaning`.

## Claim Builder

Claim Builder is a future transformation layer between Career Knowledge and Views. It turns reviewed Career Knowledge and its accepted meaning into presentation candidates that may later be considered for a Resume, Portfolio, Interview Story, or another View.

Claim Builder does not create or modify Career Knowledge, Source, Evidence, Review Decisions, or Resume output. It must not derive candidates directly from `source_sync`, Canonical Events, Review Queue items, Review Decision Log rows, or an `approved` decision alone. v0.4.0 defines only this boundary and a draft contract; it generates and persists no Claim Candidates.

## Claim Candidate

Claim Candidate is a candidate expression derived from Career Knowledge for possible use in a View. It is not truth, Source, Evidence, a Review Decision, Career Knowledge, Resume output, or another source of truth.

A Claim Candidate requires Human Review or View Selection before use. Even `approved_for_view` means only that the candidate may be used in a particular View context; it is not Career Knowledge approval, Promotion approval, or Career Knowledge persistence.

## Source

Source is a work trace.

Examples include:

- GitHub Pull Requests and commits
- Slack messages
- Teams messages
- Daily Reports
- Local memos

Source contains signals about what happened, what was discussed, what was decided, and what the human understood. Raw source is not Career Knowledge by itself.

## Evidence

Evidence supports Career Claims.

> Evidence comes before claims.

me-shower does not start by generating polished claims and then searching for support later. It starts from evidence-bearing traces, structures them into reviewable form, and only then allows claims or views to be derived.

Evidence does not mean storing raw text wholesale. It may be redacted, normalized, or canonicalized before further use.

## Evidence Traceability

Evidence Traceability is audit infrastructure, not generation infrastructure. It makes it possible to inspect which safe Evidence references support the meaning retained in Career Knowledge and projected through Claim Candidates, Views, and Resume output.

An Evidence Reference is a safe, traceability-only reference, not raw source content, Career Knowledge, a Claim Candidate, a View, or a source of truth. It may support audit, Human Review, and future coverage checks, but it must not generate Claim, View, Resume, Portfolio, or Interview Story wording and must not resolve raw source for public output.

Traceability records a support relationship; it does not establish review or approval. The existence of an Evidence Reference does not mean Human Review is complete, and the existence of a traceability chain does not approve Career Knowledge, a Claim Candidate, a View, or Resume delivery. Those decisions remain separate at their respective layers.

## Rejection / Defer Reason

Rejection / Defer Reason is audit metadata that explains why a review outcome is `rejected`, `deferred`, `needs_more_evidence`, or blocked by policy. It is not Source, Evidence, source of truth, Career Knowledge, a Claim Candidate, a View, Resume content, or a generation input.

`rejected` means the current review does not promote the candidate; it does not delete the candidate. `deferred` means the current decision is postponed; it does not mean approval will happen later. `needs_more_evidence` means support is insufficient; it does not mean Evidence exists or that the candidate is supported. A policy block stops processing until the blocking condition is resolved and must not be retried automatically.

Reason codes and safe explanations may support audit and a future explicit re-review request. They must not generate Claim, View, Resume, Portfolio, or Interview Story wording, and must not be treated as Evidence or approval. Reopening requires an explicit trigger, never implies approval, and cannot bypass Human Review.

## Canonical Event

Canonical Event is a reviewable event extracted from Source.

It is an intermediate representation that allows humans to inspect what happened and what it may mean. It is not yet Career Knowledge, but it is a candidate for it.

Canonical Events accumulate in `source_sync`.

A Canonical Event becomes Career Knowledge only after it passes the Promotion Criteria and Human Review. Source Confidence, appearance on the Source Timeline, or suitability for a Resume does not satisfy this boundary.

Promotion review keeps the following meanings distinct:

- `observed_fact`: what the supporting evidence directly shows
- `human_interpretation`: meaning explicitly accepted by the reviewer
- `ai_inference`: an AI-proposed interpretation that is not a fact
- `claim_candidate`: wording that may later be used in a View if its support and scope are safe

These categories may inform one another, but `ai_inference` and `claim_candidate` must not be persisted as `observed_fact`.

## source_sync

`source_sync` is the Canonical Event Store.

In v0.3.0, it is closer to source-of-truth than downstream outputs such as Resume or PDF, but it is still not identical to reviewed Career Knowledge.

It is the layer where normalized, reviewable fact candidates are accumulated before long-term knowledge promotion.

The promotion boundary and its decision statuses are defined in [Operating Model](03_operating_model.md#career-knowledge-promotion-criteria), with the machine-readable minimum model in `.codex/review-promotion/rules/promotion_criteria.yaml`.

## Source Intelligence

Source Intelligence is the ingestion and interpretation layer that turns Source into Career Knowledge candidates.

It is the center of v0.3.0. It is not just an import feature set. Its responsibilities are:

- receive source inputs
- convert them into a common `RawSource` shape
- suppress dangerous raw text and secrets
- reduce noise
- produce Canonical Events
- attach Source Confidence
- make review-oriented views such as Timeline possible
- prepare inputs for future Career Knowledge

## Source Confidence

Source Confidence is an operational measure of source strength, evidence quality, and extraction quality.

It is not a judgment of achievement value or human worth. It exists to help decide how safely information can be used and how urgently review is needed.

Typical interpretations:

- `high`: strong source and extraction
- `medium`: usable, but review is helpful
- `low`: noisy or weak, review first

## Source Timeline

Source Timeline is a derived operational view generated from `source_sync`.

It helps inspect the flow of Canonical Events over time. It is not itself the source of truth and must not replace upstream knowledge layers.

## Skills

> Skills are not Career Knowledge itself.

Skills are not the asset me-shower is trying to grow.

> Skills are operational knowledge that improves how agents read sources, detect issues, propose changes, and generate views.

Skills exist to improve source reading quality, review quality, and view generation quality. They are an operational support layer, not the core knowledge base.

## View

View is a generated, purpose-specific projection of Career Knowledge and reviewed Claim Candidates. It is not truth, Career Knowledge, a Claim Candidate, Source, Evidence, a Review Decision, or another source of truth. Selection and wording may change for an audience, but the accepted meaning must not.

Examples include:

- Resume
- Portfolio
- Interview Story
- Proposal Draft
- Skill Inventory
- Weekly Career Review

Views vary by audience and purpose. Durable knowledge should remain upstream in Career Knowledge, while views are generated as needed.

PDF is not a View type. It is one render format that may be used for a View such as Resume.

## View Generation

View Generation is the future projection layer from Career Knowledge and reviewed Claim Candidates to Views. It runs only after Human Review or View Selection has approved a candidate for a specific use; approval for Resume use does not imply approval for Portfolio or Interview Story use.

View Generation does not create or modify Career Knowledge, does not turn a Claim Candidate into Career Knowledge, and does not read `source_sync`, Review Decision Log rows, an approved decision alone, or an unreviewed Claim Candidate directly. `accepted_meaning` is accessed only through a Career Knowledge Entry; it is not sufficient alone. Safe Evidence references are traceability-only and cannot be resolved or used to generate text.

View Generation may select, reorder, summarize, and adjust tone only when meaning remains unchanged. It cannot create facts or causality, expand contribution scope, or merge Claims into new meaning. `timeline_view` projects reviewed Career Knowledge chronology and is distinct from the operational Source Timeline built from `source_sync`. PDF is a render format for a View, not a View type. v0.4.0 defines only these boundaries, constraints, and View types; it creates no actual View or generated output.

Every View requires a target type, a Career Knowledge reference, and purpose-specific permission. Structural facts may be projected directly from Career Knowledge, while claim-like wording requires a reviewed Claim Candidate. Attribution, scope, numbers, time, qualifiers, uncertainty, causality, and semantic category must be preserved. Approval never overrides safety, audit metadata is not View content, and personal information is excluded unless a separate explicit policy allows it.

View Generation outputs a future structured View; a separate Renderer may render it as Markdown, HTML, or PDF without changing accepted meaning. Missing inputs, conflicting Claims, unknown facts, and unresolved risks must not be filled by AI and instead fail closed or return to review.

## Resume Regeneration Policy

Resume Regeneration Policy controls when a Resume View may be regenerated and which reviewed, purpose-specific inputs may be used. Resume is a View: it is not Career Knowledge, a Claim Candidate, or source of truth. Previous Resume output, generated PDF, raw source, `source_sync`, Review Decision Log rows, approved decisions alone, and unreviewed Claim Candidates cannot be used to regenerate it.

A regenerated Resume is draft output until it passes review for delivery. Resume wording must preserve accepted meaning and must never flow back into Career Knowledge. If Resume review finds a problem, the finding returns upstream for Human Review and any necessary new Review Decision or Career Knowledge revision; the Resume itself is never promoted into knowledge. v0.4.0 defines only this policy boundary and creates no Resume or rendered output.

## Non-Goals

This section defines what me-shower is not trying to become.

- me-shower is not a generic resume builder
- me-shower is not an activity log system for storing every work trace forever
- me-shower is not a place to store confidential information, secrets, or private URLs
- me-shower is not a project for evaluating AI agent performance for its own sake
- me-shower is not a project whose purpose is to grow Skills for their own sake
- me-shower is not an automated career generation system that removes Human Review
- me-shower is not a system that distorts Career Knowledge to make Resume output look better
- me-shower is not a system for making unsupported claims look convincing
