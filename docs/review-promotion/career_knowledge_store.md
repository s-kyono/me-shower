# Career Knowledge Store

## Purpose

Career Knowledge Store is the future durable source of truth for Career Knowledge accepted through Human Review. v0.4.0 defines its storage boundary, rules, and draft entry contract, but does not persist any entries.

## What It Is

The Store will hold accepted meaning supported by safe, traceable Evidence. That knowledge can later support Resume, Portfolio, Interview Story, and Skills views without making any generated view authoritative.

The storage location is `app/data/career_knowledge/`. In v0.4.0 the directory contains only `.gitkeep`.

## What It Is Not

Career Knowledge Store is not Source, `source_sync`, Review Queue, Review Decision Log, Resume, PDF, or generated output. It does not store a Canonical Event wholesale, and an `approved` decision record is not itself Career Knowledge.

## Entry Schema Draft

```yaml
career_knowledge_entry:
  schema_version: career_knowledge_v0_4
  knowledge_id:
  source_decision_ref:
    decision_id:
    reviewed_at:
  canonical_event_ref:
    source_sync_file:
    source_id:
    event_index:
    event_date:
  accepted_meaning:
    summary:
    actions: []
    decisions: []
    improvements: []
    tags: []
  evidence_refs: []
  knowledge_type:
  confidence:
  created_at:
  updated_at:
  status:
```

- `schema_version` identifies the v0.4 draft contract.
- `knowledge_id` provides stable identity for future updates and supersession.
- `source_decision_ref` traces the entry to a decision by `decision_id` and `reviewed_at`.
- `canonical_event_ref` identifies the originating Canonical Event without copying it.
- `accepted_meaning` contains only the summary, actions, decisions, improvements, and tags explicitly accepted by Human Review.
- `evidence_refs` contains safe, traceable references, never raw source content.
- `knowledge_type` may later classify entries as `implementation`, `decision`, `improvement`, `learning`, or `strength`.
- `confidence` measures confidence in reviewed Career Knowledge and is distinct from Source Confidence.
- `created_at` and `updated_at` are Store management timestamps.
- `status` may later be `active`, `superseded`, or `archived`.

## Forbidden Content

The Store must not contain raw source content, secrets, private URLs, confidential content, non-generalized internal names, AI inference, claim candidates, Resume overstatement, generated Resume or PDF output, Review Queue items, Review Decision Log records treated as knowledge, or unprocessed copies of complete Canonical Events.

## Relationship to Review Decision Log

Review Decision Log is the append-only history of Human Review decisions. Career Knowledge Store is the future durable record of accepted meaning. A future Career Knowledge Entry references its originating `decision_id`; it does not copy the decision record or replace the log.

In v0.4.0, `approved` means only that a decision may be considered a future Career Knowledge candidate. It is not complete persistence input and must not trigger automatic storage.

## v0.5.0 Dependency

Career Knowledge Store accepts future `accepted_meaning`, not an entire Canonical Event. The current Review Decision Log does not yet record `accepted_meaning`, `event_fingerprint`, structured reviewed Evidence references, semantic review, safety review, or supersession. PromotionDecisionRecord hardening in v0.5.0 must introduce those inputs before persistence behavior is designed.
