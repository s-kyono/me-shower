# Architecture

This document defines the structural boundaries and responsibilities behind me-shower.

Its purpose is to make clear where truth lives, what each layer is responsible for, and how Source Intelligence should be understood as a knowledge-shaping layer rather than a bundle of convenience importers.

## End-to-End Flow

```text
Raw Source
    ↓
Source Adapter
    ↓
RawSource
    ↓
Evidence Guard
    ↓
Noisy Input Normalization
    ↓
Canonical Event
    ↓
source_sync
    ↓
Review / Promotion Boundary
    ↓
Career Knowledge
    ↓
Views
```

The key rule in this flow is that views such as Resume or PDF must not come first. Source is structured into reviewable Canonical Events, stored as candidates in `source_sync`, and passed through the Review / Promotion Boundary before Career Knowledge is grown. Only then are downstream views generated.

## v0.3.0 Source Intelligence Flow

```text
GitHub / Slack / Teams / Daily Report / File
    ↓
Source Adapter
    ↓
RawSource
    ↓
Source Normalizer
    ↓
Evidence Guard
    ↓
Noisy Input Normalization
    ↓
Canonical Event
    ↓
source_sync
    ↓
Source Confidence
    ↓
Source Timeline
```

This flow should not be interpreted as a list of import features. It is the current architecture for converting work traces into reviewable Career Knowledge candidates.

## Responsibility Boundaries

### Source Adapter

Receives source-specific inputs such as GitHub, Slack, Teams, Daily Reports, or files and converts them into a common `RawSource` shape.

### RawSource

Transient adapter output. It is a transport format for ingestion, not durable knowledge.

### Source Normalizer

Applies source-aware cleanup and interpretation so heterogeneous traces can be handled consistently downstream.

### Evidence Guard

Prevents unsafe raw text, secrets, private URLs, and sensitive internal information from flowing into long-term storage or generated outputs. This boundary must not be bypassed.

### Noisy Input Normalization

Converts messy, fragmentary, or ambiguous text into more usable candidate actions and events. Without this layer, downstream timeline and view quality becomes unstable.

### Canonical Event

A reviewable event produced after normalization. It is the main unit that allows Source to be inspected as a structured event rather than preserved as raw text.

### source_sync

`source_sync` is the Canonical Event Store.

In v0.3.0, it is the most source-of-truth-like internal layer, but it is still not identical to reviewed Career Knowledge. It stores normalized fact candidates, not final long-term knowledge.

### Source Confidence

An operational signal attached to Canonical Events that reflects source strength, evidence quality, and extraction stability. It supports review prioritization, not value judgment.

### Source Timeline

A derived operational view generated from `source_sync`. It is useful for inspecting the flow of events over time, but it must not replace the event store.

### Review Queue

A generated worklist derived directly from Canonical Events in `source_sync`. It displays review readiness, safe Evidence references, and semantic risks so a human can begin review. It is neither Career Knowledge nor a Promotion Decision Log, creates no decision status, and never mutates `source_sync`.

### Review / Promotion Boundary

The persistence gate between `source_sync` and Career Knowledge. It applies Promotion Criteria and requires Human Review before a Canonical Event can become durable knowledge. Source Confidence can prioritize and inform this review, but even `high` confidence cannot bypass it.

The boundary records one of `approved`, `rejected`, `deferred`, or `needs_more_evidence`. Only `approved` may flow into Career Knowledge. The other statuses retain the review outcome without treating the candidate as truth.

### Career Knowledge

Reviewed long-term knowledge built from Canonical Events and supporting evidence. This is the durable core the system is trying to grow.

### View Generator

Generates downstream outputs such as Resume, PDF, Portfolio summaries, or Interview Stories from Career Knowledge.

## Truth Boundary

This section defines what each layer is and is not. If these boundaries blur, downstream convenience tends to become upstream truth.

### Raw Source

External or local original material. It is input material, not long-term truth inside me-shower.

### RawSource

Transient adapter output. It is not durable knowledge.

### source_sync

The Canonical Event Store in v0.3.0. It accumulates Career Knowledge candidates, but it is not identical to reviewed Career Knowledge.

### Career Knowledge

Human-reviewed long-term knowledge. This is the main asset me-shower is meant to grow.

### Source Timeline

A derived operational view generated from `source_sync`. It is not history itself.

### Resume / PDF / Portfolio

Views generated from Career Knowledge. They are not sources of truth.

### Skills

Operational knowledge for agents. Skills are not Career Knowledge itself.

## Mermaid View

```mermaid
flowchart TD
    A[Raw Source] --> B[Source Adapter]
    B --> C[RawSource]
    C --> D[Evidence Guard]
    D --> E[Noisy Input Normalization]
    E --> F[Canonical Event]
    F --> G[source_sync]
    G --> H[Source Confidence]
    G --> I[Source Timeline]
    G --> P[Review Queue]
    P --> J[Human Review / Promotion Boundary]
    J -->|approved| K[Career Knowledge]
    J -->|rejected / deferred / needs more evidence| N[Non-promoted decision]
    K --> L[Resume View]
    K --> M[Portfolio View]
    K --> O[Interview Story View]
```

## Source of Truth Layers

```text
Raw Source: external / local original
RawSource: transient adapter output
source_sync: canonical event store
Review / Promotion Boundary: human-reviewed persistence gate
Career Knowledge: reviewed long-term knowledge
Source Timeline: derived view
Resume: audience-specific view
PDF: rendered artifact
```

The key architectural rule is simple:

> Downstream views must not silently become upstream truth.

Resume and PDF are outputs. They are not where durable career knowledge should originate.

## v1.0.0 Consolidation Targets

v0.x prioritizes concept validation, so some implementation density is acceptable. v1.0.0 should reorganize the system around validated responsibility boundaries.

Candidate modules:

- `commands/`
- `services/`
- `domain/`
- `source_intelligence/`
- `career_knowledge/`
- `evidence/`
- `timeline/`
- `views/`

Expected consolidation topics:

- split `main.py`
- separate domain models
- isolate the Source Intelligence module
- isolate the Career Knowledge module
- isolate the view generation module
- introduce a review queue
- define a clearer persistence model
