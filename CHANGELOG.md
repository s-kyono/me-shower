# Changelog

All notable changes to this project are documented in this file.

---

## [v0.4.0] - 2026-07-12

### Added

- Career Knowledge Store boundary
  - Defines the future storage boundary for reviewed Career Knowledge.
  - Adds the Career Knowledge Store rule contract and storage directory placeholder.
  - Clarifies that approved Review Decisions are not automatically persisted as Career Knowledge in v0.4.0.
  - Defines accepted meaning as the future input to Career Knowledge Store.

- Review Decision Log MVP
  - Adds an append-only Human Review decision log for Canonical Events.
  - Adds `approved`, `rejected`, `deferred`, and `needs_more_evidence` decision records.
  - Keeps Review Decision Log separate from Career Knowledge and Review Queue.
  - Requires reasons for all decisions and Evidence references for approved decisions.

- Review Queue derived worklist
  - Adds a generated review worklist for Canonical Events awaiting Human Review.
  - Defines readiness statuses separate from Promotion Decision statuses.
  - Prevents Review Queue from approving, rejecting, mutating `source_sync`, or creating Career Knowledge.
  - Adds review queue rules for traceability, confidence, confidentiality, and semantic risks.

- Promotion Criteria for Review & Promotion
  - Defines the boundary between Canonical Event and reviewed Career Knowledge.
  - Adds Promotion Decision statuses: `approved`, `rejected`, `deferred`, and `needs_more_evidence`.
  - Adds `.codex/review-promotion/rules/promotion_criteria.yaml` as the minimum rule contract for future Review Queue, Decision Log, and Career Knowledge Store work.
  - Clarifies that Source Confidence does not replace Human Review.
  - Clarifies that AI inference and claim candidates must not be persisted as observed facts.
  - Clarifies that Resume readiness must not override failed promotion checks.

## [v0.3.0] - 2026-07-12

### Added

- Source Intelligence pipeline from work traces to reviewable Canonical Events
  - Adds the common Source Adapter and `RawSource` model.
  - Adds GitHub, Slack, Teams, Daily Report, and file-based source ingestion.
  - Adds Evidence Guard and Noisy Input Normalization before persistence to `source_sync`.
  - Adds Source Confidence as an operational signal for evidence and extraction quality.
  - Adds Source Timeline as a derived inspection view rather than a source of truth.
  - Adds canonical concept, architecture, and operating-model documentation for Source Intelligence boundaries.

## [v0.2.0] - 2026-07-09

### Added

- Learning Loop framework
- Skill Review Proposal workflow
- Human Review workflow
- Evidence Guard
- Proposal Quality evaluation
- Agent Personality evaluation

### Improved

- Duplicate proposal detection
- Learning score validation
- Evidence redaction rules
- Resume generation workflow

### Deferred

- Noisy Input normalization (planned for v0.3.0)

### Notes

- First release where **me-shower** can continuously improve its own career knowledge through a human-in-the-loop workflow.

---

## [v0.1.0] - 2026-07-09

### Added

- Markdown resume generation
- PDF generation with WeasyPrint
- Forest theme
- Resume issue workflow
- Release archive under `generated/releases`
- Structured career data model

### Changed

- Switched output format from Excel to Markdown/PDF

### Notes

- First public MVP release of **me-shower** as a Personal Career Harness.
