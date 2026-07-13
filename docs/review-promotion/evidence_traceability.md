# Evidence Traceability

## Purpose

Evidence Traceability defines how Career Knowledge, Claim Candidates, Views, and Resume outputs may remain auditably connected to supporting Evidence without turning Evidence into wording input or exposing raw source. v0.4.0 defines this policy boundary only.

> Evidence supports meaning. Evidence does not generate wording.

## What Evidence Traceability Is

Evidence Traceability is cross-cutting audit infrastructure. It preserves inspectable support relationships for audit, Human Review support, future evidence coverage checks, unsupported-claim detection, contradiction detection, and stale-evidence detection.

It answers questions such as:

- Which Evidence references support this Career Knowledge Entry?
- Which Career Knowledge Entries support this Claim Candidate?
- Which reviewed Claim Candidates or Career Knowledge Entries does this View or Resume derive from?
- Is the downstream meaning fully supported, partially supported, unsupported, contradicted, or awaiting review?

## What Evidence Traceability Is Not

Evidence Traceability is not generation infrastructure, a source of truth, Career Knowledge, a Claim Candidate, a View, Human Review, or approval. It does not collect Evidence, resolve sources, persist Evidence data, produce wording, or render output.

The following implications are invalid:

```text
Evidence Reference exists != Human Review completed
Traceability exists != Career Knowledge approved
Traceability exists != Claim approved
Traceability exists != View approved
Traceability exists != Resume delivery approved
```

## Evidence Reference Role

An Evidence Reference is a safe reference used only to preserve auditability. It is not raw source content. It may identify a support relationship without copying source text, exposing a retrievable private location, or granting downstream generation access to the source.

Evidence references may support traceability, audit, review, future coverage checks, unsupported-claim detection, contradiction detection, and stale-evidence detection. They must not generate Claim, View, Resume, Portfolio, or Interview Story wording; replace Career Knowledge; replace Human Review; or imply approval.

## Correct Traceability Chains

Career Knowledge keeps the primary relationship to Evidence:

```text
Career Knowledge Entry
  ↓ traceable_to
Evidence Reference
```

A Claim Candidate derives meaning from Career Knowledge and may retain an additional audit trace:

```text
Claim Candidate
  ↓ supported_by
Career Knowledge Entry
  ↓ traceable_to
Evidence Reference
```

```text
Claim Candidate
  ↓ audit_trace
Evidence Reference
```

A View or Resume derives from reviewed downstream inputs while Evidence remains audit metadata:

```text
View / Resume
  ↓ derived_from
Claim Candidate / Career Knowledge Entry
  ↓ traceable_to
Evidence Reference
```

None of these chains permits Evidence to produce wording directly.

## Forbidden Shortcuts

The following paths are forbidden:

```text
Evidence Reference → Claim text
Evidence Reference → View text
Evidence Reference → Resume text
raw source → View / Resume
Traceability exists → Approved
Evidence Reference exists → Human Review completed
```

Evidence must not be treated as Career Knowledge, and an audit link must not be converted into generation permission.

## Traceability Safety

Traceability metadata must remain separate from public or semi-public View and Resume content. It must not render or expose:

- raw source content or source file paths
- private URLs or source-resolution handles
- secrets, tokens, credentials, or authentication data
- confidential content or non-generalized project names
- raw Slack, Teams, or GitHub text
- internal identifiers intended only for private audit
- unreviewed personal information

Traceability must not resolve raw source for a View, Resume, Renderer, or public Manifest. Safe references preserve verification capability within a controlled future audit boundary; they do not make raw content available downstream.

## Relationship to Career Knowledge

A future Career Knowledge Entry may be `traceable_to` one or more safe Evidence references. The reviewed `accepted_meaning` remains Career Knowledge; the Evidence Reference only records support. An Evidence Reference cannot create Career Knowledge, and its existence does not prove that promotion review or persistence approval is complete.

## Relationship to Claim Builder

Claim Builder derives Claim Candidate meaning from reviewed Career Knowledge. A Claim Candidate may identify its supporting Career Knowledge references and may carry direct Evidence references for audit, but Evidence references cannot generate Claim wording or bypass Career Knowledge and Human Review.

## Relationship to View Generation

Views derive from Career Knowledge and reviewed Claim Candidates under purpose-specific permission. Evidence references may accompany a future View as separate audit metadata, but View Generation cannot resolve them, read raw source through them, or use them to generate or strengthen wording.

## Relationship to Resume Regeneration Policy

Resume regeneration follows the same boundary as other Views. A future Resume may retain an audit trail to Career Knowledge, reviewed Claims, and safe Evidence references, but Evidence references cannot trigger regeneration, generate Resume wording, establish delivery approval, or flow into rendered public content.

## Future Coverage Statuses

A future coverage checker may classify support as:

- `supported`
- `partially_supported`
- `unsupported`
- `contradicted`
- `requires_review`

Coverage describes the support relationship; it does not decide promotion or approval. A coverage status alone must not promote a Claim, approve a View, or create Career Knowledge. `unsupported` and `contradicted` must return to Human Review.

## Future Manifest Relationship

A future View Manifest or Resume Manifest may include Career Knowledge references, Claim references, permission references, Evidence references, a policy version, and a content hash. Evidence references in a Manifest remain audit metadata. They must not generate text, resolve raw source for public output, expose private or confidential data, or make the Manifest a source of truth.

No Manifest is implemented in v0.4.0.

## Non-Goals

This phase does not implement:

- an Evidence DB or Evidence data
- an Evidence resolver or raw source resolver
- an evidence coverage or unsupported-claim checker
- a View Manifest or Resume Manifest
- a CLI
- Source Intelligence or `source_sync` changes
- Career Knowledge Store or Claim Candidate data changes
- View, Resume, PDF, or other generated output
