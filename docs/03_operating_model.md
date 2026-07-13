# Operating Model

This document describes how me-shower should be operated day to day.

The goal is not to produce Resume output after every change. The goal is to continuously grow inspectable Career Knowledge from work traces while preserving evidence boundaries and Human Review.

## Daily Inputs

- GitHub: implementation, Pull Requests, change history
- Slack / Teams: discussion, review, and decision traces
- Daily Report: context, judgment, blockers, learning, and intent
- local memo: lightweight supporting notes

Freestyle inputs are first-class sources.

GitHub often shows what changed. Slack and Teams often show what was discussed. Daily Reports often show what the human understood, why they made a decision, and where they were blocked. Career Knowledge needs all of these.

## Operating Flow

```text
1. Work happens
2. Sources are collected
3. Source Intelligence normalizes them
4. Canonical Events are stored in source_sync
5. Timeline may be generated for chronological inspection
6. Review Queue is generated as the Human Review worklist
7. Human reviews candidate events against the Promotion Criteria
8. Review Decision Log records the outcome
9. A future persistence step writes accepted meaning to Career Knowledge Store
10. A future Claim Builder derives presentation candidates from Career Knowledge
11. Human Review or View Selection approves candidates for a specific use
12. A purpose-specific View policy determines whether regeneration is permitted
13. Views are generated as drafts when needed and reviewed before delivery
```

This sequence matters. me-shower should not jump directly from noisy inputs to Resume claims.

## How to Read Confidence

- `high`: strong source and extraction
- `medium`: usable, but review is helpful
- `low`: review first

Source Confidence is not a judgment of achievement value. It is an operational measure of source quality and extraction reliability.

## The Role of Human Review

Human Review exists so AI proposals do not become Career Knowledge automatically.

Its main roles are:

- stop exaggeration
- stop confidential leakage
- stop incorrect extraction
- decide whether an event should become long-term knowledge

The operating rule is:

```text
AI proposes.
Human reviews.
Career Knowledge persists.
```

The review and promotion path is:

```text
source_sync
  ↓
Review Queue
  ↓
Human Review
  ↓
Review Decision Log
  ↓
Future Career Knowledge Store
```

Review Queue only organizes candidates and exposes missing Evidence, traceability, policy risks, and semantic concerns. Its readiness statuses are `ready_for_review`, `needs_evidence_before_review`, `blocked_by_policy`, and `needs_cleanup`. They are preparation states, never promotion outcomes. The Queue cannot create `approved`, `rejected`, `deferred`, or `needs_more_evidence`; those belong to the Review Decision Log.

Review Decision Log is the append-only history of Human Review decisions about Canonical Events. It is not Source, Review Queue, Career Knowledge, or `CHANGELOG.md`. Even `approved` only records that the event may be treated as a future Career Knowledge candidate; it does not persist Career Knowledge in v0.4.0. Existing decisions are never overwritten or deleted. A changed judgment is recorded as a new decision; formal supersession belongs to PromotionDecisionRecord v0.5.0.

## Operating Career Knowledge Store

- An `approved` decision alone is not sufficient to write Career Knowledge in v0.4.0.
- The Store accepts future `accepted_meaning` only, never an unprocessed copy of the complete Canonical Event.
- Raw source, secrets, private URLs, confidential content, non-generalized internal names, AI inference, claim candidates, and generated output must not be stored.
- Career Knowledge Entries reference the originating Review Decision instead of replacing or duplicating the Decision Log.
- The Store must not be edited casually by hand. Persistence behavior will be designed after v0.5.0 PromotionDecisionRecord hardening introduces accepted meaning and the required review metadata.

## Operating Claim Builder

- Claim Builder must use reviewed Career Knowledge and `accepted_meaning`; it must not read `source_sync` directly.
- Claim Builder must not read Review Decision Log rows directly or treat an `approved` decision alone as sufficient input.
- Review Decision and Evidence references on a Claim Candidate provide traceability; they do not replace Career Knowledge as the input boundary.
- A Claim Candidate requires Human Review or View Selection before it can be used.
- A Claim Candidate must never become a source of truth, Career Knowledge, or Resume output by status change or convenience.
- `approved_for_view` authorizes only a specific downstream use. It does not mean Career Knowledge approval, Promotion approval, or persistence.
- Claim Builder must not expose raw source, secrets, private URLs, confidential content, AI inference presented as fact, or Resume overstatement.
- v0.4.0 creates no Claim Candidate data, persistence, CLI, or View output.

## Operating View Generation

- View Generation may generate text only from Career Knowledge Entries and reviewed Claim Candidates under purpose-specific View Selection or View Approval.
- Every request requires a target View type, a Career Knowledge Entry reference, and purpose-specific View permission. These are conditional rules, not a requirement that every allowed input always be present.
- Career Knowledge may directly supply structural facts such as periods, affiliations, roles, technologies, and chronology. Claim-like wording requires a reviewed Claim Candidate and must not be inferred from structural fields alone.
- `accepted_meaning` must be accessed through its Career Knowledge Entry. It is not sufficient alone and must not bypass Career Knowledge Store.
- Safe Evidence references and PromotionDecisionRecords are traceability or validation context only. They must not resolve raw content, generate View text, or create a new Claim.
- View Generation must not read `source_sync`, raw source, Canonical Events, Review Queue items, or Review Decision Log rows directly.
- An `approved` decision alone or a PromotionDecisionRecord alone is not sufficient input.
- An unreviewed Claim Candidate must not be used. View permission is purpose-specific: Resume approval does not imply Portfolio or Interview Story approval.
- View Generation may select, reorder, summarize, and adjust tone only without meaning change. It must not create facts or causality, expand contribution scope, or merge Claims into new meaning. New meaning requires a new Claim Candidate and review.
- Attribution, team versus individual contribution, contribution scope, numbers and units, time scope, qualifiers, uncertainty, causality presence or absence, and semantic category must be preserved. Omitting a qualifier must not strengthen a Claim.
- Approval permits use but never overrides safety. Unresolved confidentiality, raw-source, overstatement, or personal-information risk invalidates generation permission.
- Audit and traceability metadata must remain separate from View content. Internal Source, Decision, and Evidence identifiers must not be rendered or exposed to public or semi-public Views.
- Personal information is excluded by default. It must not be inferred, obtained from unreviewed Source, or added by projection; a View that needs it requires a separate explicit policy.
- `timeline_view` chronologically projects reviewed Career Knowledge and non-resolvable traceability metadata. It is not Source Timeline, does not read `source_sync`, and does not render Source content.
- PDF is a render format, not a View type. Resume is a View that may be rendered as Markdown, HTML, or PDF.
- View Generation produces a future structured View. A separate Renderer produces Markdown, HTML, or PDF and must not change accepted meaning. Neither component is implemented in v0.4.0.
- Missing permission or Career Knowledge references rejects generation. Conflicting Claims and unresolved risks return to review; unknown facts are omitted or reviewed, never filled by AI.
- A View must never become a source of truth, Career Knowledge, or a Claim Candidate. Resume is a View, not an authoritative record.
- View output and wording must never flow back into Career Knowledge, `accepted_meaning`, Source, Evidence, or Claim support. A discovered issue must be routed to an upstream review request for Human Review and any necessary new Review Decision or Career Knowledge revision.
- View Generation must not expose raw source, secrets, private URLs, confidential content, AI inference presented as fact, or Resume overstatement.
- v0.4.0 defines only the boundary, constraints, and View types. It implements no CLI and creates no Resume, PDF, Portfolio, Interview Story, or other View output.

## Operating Resume Regeneration

- Resume is a View, not Career Knowledge or source of truth.
- Resume regeneration requires Career Knowledge, reviewed Claim Candidates for generated Claim text, and purpose-specific Resume View Permission. Resume policy and template also constrain the future output.
- Resume must not be regenerated from raw source, `source_sync`, Canonical Events, Review Queue items, Review Decision Log rows, approved decisions alone, PromotionDecisionRecords alone, unreviewed Claim Candidates, previous Resume output, generated PDFs, or Views from another purpose.
- Changes only to forbidden upstream or generated artifacts are not regeneration triggers. Eligible changes include Career Knowledge, reviewed Claim Candidates, Resume permission, Resume policy, Resume template, and render format.
- Regeneration permission is not delivery permission. Every regenerated Resume is draft output and requires review before delivery, submission, or publication.
- Resume optimization may select, reorder, summarize, or adjust tone only while preserving accepted meaning. It must not invent facts or causality, expand contribution scope, or strengthen a Claim by dropping qualifiers.
- Unresolved blocking or confidentiality risk rejects regeneration. Unresolved overstatement returns to review, and personal information requires a separate explicit policy.
- Resume output and wording must never update Career Knowledge, become `accepted_meaning`, or serve as future generation input. Findings return upstream for Human Review and any necessary new Review Decision or Career Knowledge revision.
- v0.4.0 defines only the policy boundary. It implements no CLI, Resume generation, Structured Resume View, Renderer, lifecycle, manifest, diff, Markdown, PDF, or other generated output.

## Career Knowledge Promotion Criteria

A Canonical Event is not Career Knowledge. When it is stored in `source_sync`, it is only a reviewable candidate. Promotion Criteria are not a score of how impressive the work is; they are the persistence gate for deciding whether the candidate is safe and useful as reviewed, long-term Career Knowledge.

Promotion requires all of the following:

1. Supporting Evidence exists.
2. Source Confidence is `high` or `medium`; confidence never replaces Human Review, and `low` cannot be approved without stronger evidence and reassessment.
3. A human has reviewed the candidate and accepted the meaning of its summary, actions, decisions, and improvements.
4. Secrets, private URLs, confidential information, and sensitive internal names have been removed.
5. `observed_fact`, `human_interpretation`, `ai_inference`, and `claim_candidate` remain distinguishable; AI inference is not stored as fact.
6. The meaning has not been exaggerated or reshaped merely to improve a Resume or another View.
7. The reviewer confirms career relevance: the event contributes to long-term understanding of the person's work, judgment, learning, improvement, or repeatable strengths.

Career relevance is a retention decision, not a judgment that the work is prestigious or high-value. A routine event may be relevant, while an impressive-sounding but unsupported claim is not promotable.

Promotion review produces exactly one status:

- `approved`: all required checks pass; the accepted meaning may become Career Knowledge
- `rejected`: the candidate must not become Career Knowledge, including unsupported or misleading claims
- `deferred`: no current decision is appropriate, but the candidate may be reviewed later
- `needs_more_evidence`: the candidate has potential relevance but lacks sufficient support for approval

Only `approved` permits promotion. A failed required check must never be converted into approval because the wording is Resume-ready. `rejected`, `deferred`, and `needs_more_evidence` are valid outcomes, not errors to hide or auto-upgrade.

The minimum decision model is defined in `.codex/review-promotion/rules/promotion_criteria.yaml`. It is a contract for future Review Queue, Decision Log, and Career Knowledge Store work, not a runtime validation engine in v0.4.0.

## Log Responsibilities

- `CHANGELOG.md`: project-level release and change history
- `LOG.md`: design rationale, strict review results, and notes that connect to future improvements
- `app/data/daily_reports/*.md`: daily work, interests, learning, and technology-stack summaries treated as Source input
- `app/data/review_decisions/YYYY-MM-DD.jsonl`: append-only `approved`, `rejected`, `deferred`, and `needs_more_evidence` Human Review decisions for Canonical Events

These records are not interchangeable. A Daily Report or Daily Digest is Source, not Career Knowledge. It must pass through Source Intelligence, Promotion Criteria, and Human Review before any accepted meaning can become Career Knowledge. `CHANGELOG.md` records project changes, not individual promotion decisions, and `.codex/steering_sheets/change_log.md` is not an official project log.

## Handling Generated Output

- `generated/` should generally stay out of normal PR scope
- Timeline, PDF, and Resume previews are regenerable artifacts
- generated output must not become source of truth

Outputs are disposable compared with the underlying knowledge structure.

## Handling Raw Source

- raw source must not become long-term truth
- secrets, tokens, private URLs, and sensitive internal information must not be stored
- Evidence Guard must not be bypassed

Raw traces are useful as input material, but they are too unsafe and unstable to serve directly as long-term knowledge.

## Handling Skills

- Skills are not the authoritative career record
- Skills are agent operational knowledge
- Skills are used to improve source reading quality, review quality, and view generation quality

Even when Skills improve, the thing being grown is still Career Knowledge.

## Failure Modes

This section makes likely failure patterns explicit. Even if a change seems useful, it should be treated carefully if it pushes the system toward one of these failure modes.

### Resume Optimization Drift

If Resume wording is optimized too aggressively, Career Knowledge becomes subordinate to Resume presentation. This must be avoided.

### source_sync Over-Trust

`source_sync` is a Canonical Event Store, not reviewed Career Knowledge itself. Unreviewed extracted results must not be treated as final truth.

### Skills Expansion Drift

If Skills improvement becomes too central, the project drifts toward agent optimization. Skills are support infrastructure. Career Knowledge is the asset being grown.

### Timeline Canonization

Timeline is a derived view for inspecting flow. Appearing on the Timeline does not make something reviewed Career Knowledge.

### Daily Report Vacuum

Daily Reports are important freestyle inputs, but they are not meant to absorb an entire life log. They should focus on context, judgment, learning, and blockers relevant to Career Knowledge.

### AI Plausibility Trap

AI can produce plausible language. Plausibility is not evidence. AI inference must not be preserved as if it were the person’s actual experience.

### Convenience Drift

Convenience alone must not justify collapsing source-of-truth boundaries. Convenience matters, but it is not more important than Career Knowledge integrity.

## v0.x Operating Policy

- prioritize feature validation and operational learning
- do not collapse Concept or Boundary
- tolerate implementation density temporarily and reorganize at v1.0.0
- leave important decisions in logs and changelog where appropriate
