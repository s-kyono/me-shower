# Rejection / Defer Reason

## Purpose

Rejection / Defer Reason defines safe, reviewable explanations for outcomes that do not approve a candidate. v0.4.0 defines the categories, safety boundary, and re-review policy only.

> Reason is audit metadata. Reason is not Career Knowledge.

## What Rejection / Defer Reason Is

A Reason records why Human Review or a promotion check did not approve a subject. It may later be associated with a Review Decision or Promotion Decision through reason codes and a minimal safe explanation. It preserves review accountability without converting the explanation into durable career meaning.

A future minimal record may identify a reason, subject, decision status, reason codes, reviewer, review time, and explicit re-review conditions. This phase does not implement that schema or create records.

## What It Is Not

A Reason is not Source, Evidence, source of truth, Career Knowledge, a Claim Candidate, a View, Resume content, or approval. A reason code describing missing or conflicting Evidence is not itself Evidence and does not prove that Evidence exists.

## Status Semantics

- `rejected`: the current review does not promote or adopt the candidate. The item is not deleted and may be reconsidered only after an explicit trigger.
- `deferred`: the current review makes no approval or rejection decision. It is not approved later by default and needs an explicit re-review trigger.
- `needs_more_evidence`: the required Evidence or support is insufficient. It does not mean Evidence exists, the subject is supported, or approval is pending.
- `blocked_by_policy`: safety, privacy, confidentiality, or scope policy stops processing. It is not waiting for approval, must not be retried automatically, and cannot be reviewed again until the policy block is resolved.

`blocked_by_policy` may classify a policy stop at the review boundary without adding a new runtime status or changing existing Review Decision Log data in this phase.

## Reason Categories

### Rejection Reasons

- `unsupported_by_evidence`
- `contradicted_by_evidence`
- `overstates_contribution`
- `ambiguous_meaning`
- `not_career_relevant`
- `duplicate_or_subsumed`
- `outside_scope`
- `contains_raw_source_risk`
- `contains_confidential_content`
- `contains_private_url`
- `contains_secret_or_credential`
- `contains_personal_information_risk`
- `violates_policy`

### Defer Reasons

- `needs_human_clarification`
- `needs_source_cleanup`
- `needs_semantic_review`
- `needs_safety_review`
- `waiting_for_related_decision`
- `depends_on_future_policy`
- `insufficient_context`
- `unclear_career_relevance`

### Needs More Evidence Reasons

- `missing_evidence_reference`
- `insufficient_evidence_coverage`
- `evidence_conflict_requires_review`
- `evidence_traceability_missing`
- `source_not_reviewed`
- `support_edge_missing`

### Blocked By Policy Reasons

- `raw_source_leakage_risk`
- `confidential_content_risk`
- `personal_information_risk`
- `secret_or_credential_risk`
- `private_url_risk`
- `unsafe_public_disclosure`
- `outside_current_scope`
- `requires_future_policy`

## Forbidden Uses

Reason codes and explanations must not create Career Knowledge, generate or strengthen Claim wording, generate View or Resume wording, or supply Portfolio or Interview Story wording. They must not be treated as Evidence, approval, or source of truth.

```text
Reason → Career Knowledge        forbidden
Reason → Claim / View wording   forbidden
Reason → Resume / Portfolio / Interview Story wording   forbidden
Reason exists → Evidence or approval   invalid
```

Reasons explain decisions; they are never expression material or generation input.

## Reason Safety

Store only the minimum information needed to explain the decision. A reason code such as `contains_confidential_content` is safe; copying the content that caused the risk is not.

A reason code or explanation must not contain raw Source content, source file excerpts, raw Slack, Teams, or GitHub text, private URLs, secret or credential values, confidential content or project names, public internal identifiers, or unreviewed personal information. Redaction is not permission to preserve unnecessary sensitive detail.

## Re-review Policy

Re-review requires an explicit trigger. Acceptable triggers include a new Evidence Reference, improved Evidence coverage or traceability, Human clarification, resolution of a safety or confidentiality risk, a policy change that resolves the former block, or a changed duplicate/subsumed relationship.

`needs_more_evidence` specifically requires new Evidence or improved traceability. `blocked_by_policy` specifically requires resolution of the blocking policy condition. Reopening any status creates an opportunity for a new Human Review; it does not approve the subject and must never cause automatic approval.

```text
Reopened != Approved
```

## Relationship to Review Decision Log

Review Decision Log preserves Human Review outcomes. Rejection / Defer Reason defines the categories and safety constraints that may explain those outcomes. Future `reason_codes` and `safe_explanation` fields remain audit metadata, must not change Career Knowledge, and must not generate View wording. This phase does not modify Review Decision Log runtime behavior or data.

## Relationship to Evidence Traceability

`needs_more_evidence`, `unsupported_by_evidence`, and `contradicted_by_evidence` describe review findings about support. They are not Evidence references, support edges, or coverage proof. Future Evidence Coverage, Evidence Finding, or Review Request work may connect these findings to safe traceability metadata without exposing raw Source.

## Future Connections

Possible future connections include safe reason fields on Review Decision Log, re-review requests, safety and semantic reviews, Evidence Traceability findings, and reason snapshots on a future PromotionDecisionRecord. Each connection must preserve the audit-only boundary.

## Non-Goals

This phase does not implement Review UI, CLI, reason schemas or records, automatic re-review, Review Decision Log runtime changes, Career Knowledge Store changes or data, Claim Candidates, Views, Resume output, generated output, or `source_sync` changes.
