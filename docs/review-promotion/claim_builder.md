# Claim Builder

## Purpose

Claim Builder is the future transformation layer that turns reviewed Career Knowledge into presentation candidates for downstream Views. v0.4.0 defines its responsibility boundary, constraints, and draft contract. It does not generate or persist candidates.

## Responsibilities and Boundaries

Claim Builder reshapes accepted Career Knowledge into audience-aware expression candidates. Its future inputs are Career Knowledge Entries, `accepted_meaning`, safe Evidence references, and validated PromotionDecisionRecords.

It is not a knowledge promotion or persistence mechanism. It does not create or modify Career Knowledge Store, Source, Evidence, Review Decisions, Resume, PDF, or another View.

## Claim Candidate

A Claim Candidate is a generated expression that may later be selected for a Resume, Portfolio, Interview Story, casual meeting, or general profile. It remains a candidate until Human Review or View Selection approves its use.

It is not truth, Career Knowledge, Source, Evidence, a Review Decision, Resume output, generated final output, or a source of truth. `approved_for_view` is permission for a View context only; it is not Career Knowledge approval, Promotion approval, or persistence.

## Input and Output Constraints

Claim Builder may eventually use only reviewed Career Knowledge Entries, their `accepted_meaning`, safe Evidence references, and validated PromotionDecisionRecords. `source_decision_refs` exists only for traceability.

It must not directly consume raw source, `source_sync`, Canonical Events, Review Queue items, Review Decision Log rows, an `approved` decision alone, Daily Reports, raw Slack, Teams, or GitHub text, generated Resume, or generated PDF. Its only future output is a Claim Candidate; v0.4.0 produces no actual output.

## Claim Candidate Schema Draft

```yaml
claim_candidate:
  schema_version: claim_candidate_v0_4
  claim_id:
  source_knowledge_refs: []
  source_decision_refs: []
  claim_type:
  audience:
  text:
  supported_by: []
  risk_flags: []
  status:
  created_at:
```

- `schema_version` is fixed to `claim_candidate_v0_4` for this draft.
- `claim_id` provides the candidate's unique identity.
- `source_knowledge_refs` identifies the Career Knowledge Entries used; it is a future-only field in v0.4.0.
- `source_decision_refs` is supplementary traceability, not direct generation input.
- `claim_type` candidates are `achievement`, `strength`, `responsibility`, `technical_depth`, `decision_making`, `improvement`, and `learning`.
- `audience` candidates are `resume`, `portfolio`, `interview`, `casual_meeting`, and `general_profile`.
- `text` is pre-review candidate wording, not final Resume wording.
- `supported_by` contains safe references to Career Knowledge, Evidence, or `accepted_meaning`, never raw content.
- `risk_flags` exposes overstatement, inference, evidence, confidentiality, scope, and audience risks for review.
- `status` candidates are `draft`, `needs_review`, `approved_for_view`, and `rejected`.
- `created_at` records when the candidate was created.

## Risk Flags

Draft flags are `unsupported_claim`, `evidence_missing`, `ai_inference_risk`, `resume_overstatement_risk`, `confidentiality_risk`, `private_url_risk`, `raw_source_risk`, `too_broad`, `too_specific`, and `audience_mismatch`. They prevent unsupported or unsafe wording from flowing unchanged into a View.

## Downstream Relationships

Career Knowledge Store remains the source of truth. Claim Builder is read-only with respect to it, and candidates must never be written back as Career Knowledge. View Generation follows Human Review or View Selection and remains non-authoritative.

## v0.5.0 Dependency

Actual generation depends on PromotionDecisionRecord hardening that supplies `accepted_meaning`, structured reviewed Evidence references, and a validated promotion-ready record. Until those inputs and actual Career Knowledge Entries exist, Claim Builder remains a contract only.
