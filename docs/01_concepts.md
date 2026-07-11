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
Views
```

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

## Canonical Event

Canonical Event is a reviewable event extracted from Source.

It is an intermediate representation that allows humans to inspect what happened and what it may mean. It is not yet Career Knowledge, but it is a candidate for it.

Canonical Events accumulate in `source_sync`.

## source_sync

`source_sync` is the Canonical Event Store.

In v0.3.0, it is closer to source-of-truth than downstream outputs such as Resume or PDF, but it is still not identical to reviewed Career Knowledge.

It is the layer where normalized, reviewable fact candidates are accumulated before long-term knowledge promotion.

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

View is a purpose-specific output generated from Career Knowledge.

Examples include:

- Resume
- PDF
- Portfolio
- Interview Story
- Proposal Draft
- Skill Inventory
- Weekly Career Review

Views vary by audience and purpose. Durable knowledge should remain upstream in Career Knowledge, while views are generated as needed.

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
