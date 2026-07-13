# View Generation From Career Knowledge

## Purpose

View Generation defines the future projection boundary for projecting Career Knowledge and reviewed Claim Candidates into purpose-specific Views. v0.4.0 defines only its responsibility boundary, input and output constraints, View types, and safety rules. It does not generate a View.

## What View Generation Is

View Generation selects content that has been reviewed for a particular use and presents it in an audience-appropriate form. It is downstream of Career Knowledge Store, Claim Builder, and Human Review or View Selection.

```text
Career Knowledge Store
  ↓
Claim Builder
  ↓
Claim Candidates
  ↓
Human Review / View Selection
  ↓
View Generation
  ↓
Purpose-specific View
```

## What View Generation Is Not

View Generation is not promotion, review, evidence collection, or knowledge persistence. It does not create or modify Career Knowledge, Source, Evidence, Review Decisions, Claim Candidates, or PromotionDecisionRecords. It cannot make a candidate authoritative by including it in output.

## What a View Is

A View is a generated, purpose-specific projection of Career Knowledge and reviewed Claim Candidates. It may change selection, ordering, level of detail, and wording for an audience without changing the accepted meaning.

A View is not truth, Career Knowledge, Source, Evidence, a Review Decision, or a Claim Candidate. Resume, Portfolio, Interview Story, and every other View remain regenerable downstream artifacts rather than sources of truth.

## Input Constraints

Future View Generation may use only Career Knowledge Entries, reviewed Claim Candidates, and purpose-specific View Selection or View Approval results to generate View text. `accepted_meaning` is used only as meaning contained within a Career Knowledge Entry. It is not sufficient as a standalone input and must not be accepted directly as a way to bypass Career Knowledge Store.

Safe Evidence references support auditability and traceability only. They must not be resolved into raw source content or used to generate View text, a new Claim, or new wording. A PromotionDecisionRecord is also validation or traceability context, not View-text generation material.

It must not directly use raw source, `source_sync`, Canonical Events, Review Queue items, Review Decision Log rows, an `approved` decision alone, a PromotionDecisionRecord alone, Daily Reports, raw Slack, Teams, or GitHub text, unreviewed Claim Candidates, generated Resume, or generated PDF.

Approval is purpose-specific. Permission to use a Claim Candidate in a Resume does not imply permission to use it in a Portfolio or Interview Story.

Every generation request requires a target View type, at least one Career Knowledge Entry reference, and purpose-specific View permission. Career Knowledge Entries may directly supply structural facts such as periods, affiliations, roles, technologies, and chronology. Generated claim-like wording additionally requires a reviewed Claim Candidate. View Generation must not infer claim-like wording from structural fields alone.

These are conditional input requirements, not an assertion that every allowed input is always required. Safe Evidence references and PromotionDecisionRecords remain traceability or validation context rather than generation inputs.

## Transformation Constraints

View Generation may select, reorder, summarize without changing meaning, and adjust tone without changing meaning. It must not create a new fact or causal relationship, expand the person's contribution scope, or merge multiple Claims into a meaning that none of the reviewed inputs contains.

For example:

```text
Claim A: Designed the system.
Claim B: Processing time was reduced.

Not allowed: The system design reduced processing time.
```

Unless the causal relationship is present in reviewed Career Knowledge or a reviewed Claim Candidate, the combined sentence is a new Claim. If new meaning is needed, it must become a new Claim Candidate and pass through review before View use.

Attribution, individual versus team contribution, contribution scope, numbers and units, time scope, conditions, qualifiers, uncertainty, the presence or absence of causality, and semantic categories such as `observed_fact` and `human_interpretation` must survive selection and rewriting. Omitting a qualifier must never strengthen a Claim.

```text
Original:    The person handled part of the design within the team.
Allowed:     The person was responsible for part of the team's design.
Not allowed: The person handled the design.
Not allowed: The person led the design.
```

Removing “within the team” or “part of” expands the contribution scope and therefore changes meaning.

## Approval and Safety

Approval permits purpose-specific use; it does not waive safety constraints. View Approval cannot authorize raw source disclosure, confidential content, unresolved overstatement, or a personal-information policy violation. Approval with an unresolved confidentiality, raw-source, overstatement, or personal-information risk is not valid for generation.

## Output Constraints

The only future outputs are Views. View Generation must not output Career Knowledge Entries, Source, Evidence, Review Decisions, Claim Candidates, or PromotionDecisionRecords. v0.4.0 creates no Resume, PDF, Portfolio, Interview Story, other View, or generated output.

## View Types

- `resume`: an application-oriented summary; optimization must not distort Career Knowledge or overstate scope or results.
- `portfolio`: a public or semi-public achievement presentation; it must exclude private URLs, confidential content, internal proper nouns, and raw source.
- `interview_story`: a spoken narrative for interviews; narrative clarity must not exaggerate causality or contribution.
- `casual_meeting_profile`: a lightweight introduction; natural language must preserve accepted meaning.
- `skill_summary`: a skills-and-strengths presentation; every skill expression must be supported by Career Knowledge, and a skill list must not replace experience.
- `timeline_view`: a chronological projection of reviewed Career Knowledge and non-resolvable traceability metadata. It does not read `source_sync` directly and must not resolve or render Source content.

`timeline_view` is distinct from Source Timeline. Source Timeline is an operational View used to inspect `source_sync`; `timeline_view` is a purpose-specific chronological View of reviewed Career Knowledge.

## View and Render Format

PDF is not a View type. View Generation outputs a structured View or View Document that contains the approved meaning and presentation structure. A separate Renderer may produce Markdown, HTML, or PDF and must not alter accepted meaning.

```text
View Generation → Structured View → Renderer → Markdown / HTML / PDF
```

View Generation does not render PDF, and v0.4.0 implements neither View Generation nor Renderer.

## Traceability and View Content

View content is not audit metadata. Source IDs, Decision IDs, Evidence IDs, and other internal identifiers must not be rendered in View content or exposed in public or semi-public Views. Traceability metadata remains separate for audit and validation.

Non-resolvable traceability metadata contains no raw-source path, private URL, secret or authentication data, or internal proper noun. It must not allow a View user to retrieve Source content.

## Personal Information

Personal information is excluded by default and requires a separate explicit policy for any View that needs it. View Generation must not add or infer names, addresses, telephone numbers, email addresses, birth dates, photographs, education, qualifications, or similar information; it must not obtain such information from unreviewed Source. Personal information must never be introduced merely by projection.

## Failure Policy

View Generation fails closed. Missing purpose-specific permission or a missing Career Knowledge reference rejects generation. Conflicting Claims or unresolved risks return to Human Review. Unknown facts are omitted or routed to review, and AI must never fill missing information by inference.

## View Backflow Prohibition

The flow is one-way:

```text
Career Knowledge → Claim Candidate → View
View -X-> Career Knowledge
```

Resume wording must not be stored as Career Knowledge, Portfolio wording must not replace `accepted_meaning`, Interview Story phrasing must not become Source, generated PDF must not become authoritative, and View wording must not be used as Evidence for another Claim.

If a View exposes an error or missing detail, its wording must not flow back into Career Knowledge. The issue must be routed as an upstream review request for Human Review and, if needed, a new Review Decision or Career Knowledge revision. The View itself is never promoted back into knowledge. Detailed View Feedback and Upstream Review Request schemas are deferred beyond v0.4.0.

## Relationship to Claim Builder

The Claim Builder boundary defines future derivation of presentation candidates from Career Knowledge. A future View Generation implementation may run only after Human Review or View Selection has approved a candidate for the specific View context. An unreviewed candidate and a generic `approved_for_view` status without purpose-specific authorization are insufficient.

## Relationship to Resume Regeneration Policy

Resume is one View, not the primary asset. Resume Regeneration Policy defines when regeneration is allowed, which reviewed inputs may be used, and how generated output is reviewed. It preserves the same truth, approval, safety, and no-backflow boundaries while adding Resume-specific trigger and draft-before-delivery rules.

## v0.5.0 Dependency

Actual View generation depends on hardened PromotionDecisionRecords, persisted Career Knowledge Entries with `accepted_meaning`, actual Claim Candidates, and purpose-specific View Selection or View Approval. Until those exist, View Generation remains a contract only.
