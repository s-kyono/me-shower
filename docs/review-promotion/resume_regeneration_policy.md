# Resume Regeneration Policy

## Purpose

Resume Regeneration Policy is the contract that defines when a Resume View may be regenerated, which inputs it may use, which conditions prohibit regeneration, and what review is required afterward. v0.4.0 defines this policy boundary only. It does not generate a Resume, Markdown, PDF, structured View, or other output.

## What Resume Regeneration Policy Is

The policy is a safety gate between purpose-specific View Generation inputs and a future Structured Resume View. It controls regeneration; it is not a generator, Renderer, lifecycle implementation, or persistence layer.

```text
Career Knowledge Entry
  ↓
reviewed Claim Candidate
  ↓
purpose-specific Resume View Permission / View Approval
  ↓
Resume Regeneration Policy
  ↓
Structured Resume View
  ↓
Renderer
  ↓
Markdown / PDF
```

## What Resume Is

Resume is a purpose-specific View: a regenerable projection downstream of Career Knowledge and reviewed Claim Candidates. It may select, order, summarize, and adjust tone for an application while preserving accepted meaning.

## What Resume Is Not

Resume is not Career Knowledge, a Claim Candidate, Source, Evidence, a Review Decision, or source of truth. PDF is only a render format. Neither Resume wording nor a rendered artifact can become authoritative input for Career Knowledge or later Resume regeneration.

## Allowed Inputs

Future Resume regeneration may use only:

- Career Knowledge Entries
- reviewed Claim Candidates
- purpose-specific Resume View Permission or View Approval
- Resume View policy
- Resume template
- safe traceability metadata

Safe traceability metadata exists only for audit and tracking. It cannot generate Resume text, resolve raw content, or replace a reviewed input.

## Forbidden Inputs

Resume regeneration must not directly use raw source content, `source_sync`, Canonical Events, Review Queue items, Review Decision Log rows, an approved decision alone, a PromotionDecisionRecord alone, Daily Reports, raw Slack / Teams / GitHub text, or unreviewed Claim Candidates.

It must also not use a previous Resume, generated Resume, generated PDF, or generated or structured View created for another purpose. These artifacts are downstream output; using them as inputs would allow a View to behave as source of truth and could import approval from the wrong audience or purpose.

## Allowed Regeneration Triggers

Regeneration may be requested when Career Knowledge, a reviewed Claim Candidate, Resume-specific permission, Resume policy, Resume template, or render format changes. These triggers only permit creation of a new draft. They do not authorize delivery, submission, or publication.

## Forbidden Regeneration Triggers

Regeneration must not be triggered only because raw source, `source_sync`, Review Queue, Review Decision Log, an approved decision, a PromotionDecisionRecord, an unreviewed Claim Candidate, a previous Resume, a generated PDF, or another generated View changed.

Upstream activity becomes eligible only after it passes the required Human Review, Career Knowledge, Claim review, and purpose-specific permission boundaries.

## Draft and Review-Before-Delivery Rule

Every regenerated Resume is draft output. It remains non-authoritative and requires review before delivery, submission, or publication. Regeneration permission and delivery permission are distinct:

```text
regeneration allowed != delivery allowed
```

## Resume Backflow Prohibition

The allowed flow is one-way:

```text
Career Knowledge → reviewed Claim Candidate → Resume View
Resume View -X-> Career Knowledge
```

Resume output must not update Career Knowledge, and Resume wording must not become `accepted_meaning` or future generation input. If Resume review finds an error or missing detail, the finding is routed upstream for Human Review and, when necessary, a new Review Decision or Career Knowledge revision. The future Resume Review Finding and Upstream Review Request schemas are outside v0.4.0.

## Resume Optimization Constraints

Resume optimization may select, reorder, summarize, or adjust tone only when accepted meaning remains intact. It must not:

- present a team result as an individual result
- change support into leadership
- expand a partial improvement into a complete improvement
- remove conditions or uncertainty to strengthen a Claim
- invent causality
- add an outcome absent from reviewed Career Knowledge

Attribution, contribution scope, qualifiers, uncertainty, numbers, time scope, and causality must be preserved.

## Resume Safety

Resume regeneration must exclude raw source content, secrets, private URLs, confidential content, AI inference presented as fact, unsupported Claims, and overstatement. An unresolved blocking or confidentiality risk rejects regeneration. Unresolved overstatement requires review. Personal information requires a separate explicit policy and is not introduced by this policy.

## Relationship to View Generation

View Generation defines the general projection boundary for all purpose-specific Views. Resume Regeneration Policy adds Resume-specific trigger, input, draft, delivery-review, and backflow rules. Resume-specific permission cannot be inferred from approval for Portfolio, Interview Story, or another View.

## Relationship to Renderer

A future View Generation runtime will produce a Structured Resume View, and a separate Renderer may render it as Markdown or PDF without changing accepted meaning. This policy implements neither component and creates no output.

## Future Dependencies

Runtime regeneration depends on actual Career Knowledge Entries, actual reviewed Claim Candidates, a purpose-specific View Approval or View Selection schema, Structured View output, and a Renderer. Resume lifecycle, Resume Review Finding, upstream review requests, diff review, and a View or Resume Manifest with source, Claim, permission references, and content hashes remain future work.
