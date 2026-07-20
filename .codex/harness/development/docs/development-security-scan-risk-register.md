# Development Security Scan Risk Register

## Purpose

This document tracks concerns and residual risks discovered while defining and
implementing Development Security Scan for Artifact Persistence.

The canonical contract remains
`artifact-persistence-decision-contract.md`. This register does not change its
record shapes, enums, trust boundaries, or workflow rules. A contract change
requires the normal design decision process before implementation.

Last reviewed: 2026-07-20

## Priority

| Marker | Priority | Meaning |
| --- | --- | --- |
| 🔥 | P0 | Must be resolved before production Artifact Persistence is enabled. |
|  | P1 | Resolve before the named expansion trigger; it does not block committing the current interface-first WBS 4.4 implementation. |
|  | P2 | Hardening or maintainability work that may remain as an explicitly accepted residual risk. |

`Discovered in` records when the concern became visible. `Address in` records
the existing implementation phase or operational gate that owns its closure;
it does not create a new WBS item.

## Summary

| ID | Priority | Concern | Discovered in | Address in | Status |
| --- | --- | --- | --- | --- | --- |
| DSS-R001 | 🔥 P0 | Production scanner engine is not implemented | WBS 4.2 contract confirmation; reconfirmed in WBS 4.4 implementation | WBS 4.4 production enablement, before operations | Open |
| DSS-R002 | 🔥 P0 | Production scanner authority/adapter is intentionally uninstalled | WBS 4.4 implementation and authority review | WBS 4.4 production enablement, before operations | Open; fail closed |
| DSS-R003 | 🔥 P0 | Durable execution/evidence uniqueness and atomic conflict handling are not implemented | WBS 4.4 authority hardening and external review | Operational implementation before operations | Open |
| DSS-R004 | 🔥 P0 | Exact payload bytes are not yet bound through scan-to-write orchestration | WBS 4.4 integration review | WBS 4.5 Write Request and later Writer integration, before operations | Open |
| DSS-R005 | 🔥 P0 | `review_required` has no Human Review runtime | WBS 4.2 contract confirmation | Human Gate binding phase, before enabling that outcome operationally | Open; fail closed |
| DSS-R006 | 🔥 P0 | Write Request does not yet revalidate Security Binding and Evidence authority | WBS 4.4 integration review | WBS 4.5 Write Request | Open |
| DSS-R007 | 🔥 P0 | Security policies and artifact-type checks are provisional rather than production-approved | WBS 4.2 policy design and WBS 4.4 Registry implementation | WBS 4.4 production enablement, before operations | Open |
| DSS-R008 | 🔥 P0 | Timeout, retry, terminal `unknown`, and durable scan lifecycle behavior lack an operational backend | WBS 4.4 fail-closed implementation | Operational implementation before operations | Open |
| DSS-R009 | 🔥 P0 | Safe-location accuracy depends on the future scanner adapter | WBS 4.4 Registry-backed `field_path` review | Production scanner adapter implementation, before operations | Open |
| DSS-R010 | P1 | Production attestations are process-local capabilities, not cryptographically portable evidence | WBS 4.4 trusted-adapter hardening | Before multi-process, remote-scanner, or persisted-attestation use | Accepted for current threat model |
| DSS-R011 | P1 | Policy version compatibility and migration are single-version only | WBS 4.4 Registry implementation | Before registering a second policy version | Open |
| DSS-R012 | P1 | Registry `field_path` entries can drift from candidate schemas | WBS 4.4 Registry-backed `field_path` review | Before expanding artifact types or schema versions | Open |
| DSS-R013 | P1 | Canonical hashing interoperability is not verified across languages/processes | WBS 4.4 Evidence-hash review | Before a non-Python producer or verifier is introduced | Open |
| DSS-R014 | P1 | Timestamp authority and clock semantics are adapter-owned but not operationally specified | WBS 4.4 Evidence review | Before persisted production Evidence is enabled | Open |
| DSS-R015 | P2 | Production-like composition fixtures live close to trusted adapter code | WBS 4.3 source-binding hardening; observed again in WBS 4.4 tests | Test-boundary cleanup when composition infrastructure is consolidated | Open |
| DSS-R016 | P2 | Python privacy/opaque types do not resist arbitrary code already executing in-process | WBS 4.3 and WBS 4.4 authority reviews | Retain as documented threat-model exclusion unless isolation requirements change | Accepted residual risk |

## Detailed Risks

### DSS-R001 — Production scanner engine is not implemented 🔥

- Impact: the current interface-first implementation can validate and bind
  trusted evidence, but it cannot determine whether real candidate bytes contain
  secrets, private information, raw source, or other prohibited material.
- Current control: production remains fail closed when no scanner is installed.
- Closure criteria: select and version the scanner implementation; demonstrate
  all required checks against exact payload bytes; approve false-positive and
  false-negative policy; pass synthetic security fixtures without storing raw
  findings.

### DSS-R002 — Production scanner authority is uninstalled 🔥

- Impact: no production `automatic_pass` Security Binding can currently be
  minted. Installing an authority incorrectly would also weaken the provenance
  boundary.
- Current control: the production entry point owns authority selection and
  rejects an uninstalled authority, generic authority, test proof, or caller
  evidence.
- Closure criteria: the production composition root installs the registered
  adapter and scanner identity; opaque attestations are produced only from that
  path; positive and negative production-path tests remain green.

### DSS-R003 — Durable uniqueness and atomic conflict handling 🔥

- Impact: process-local indexes cannot prevent two processes from reusing one
  scan/evidence identity for different records, nor preserve idempotency across
  restarts.
- Current control: in-memory/test contracts reject conflicts within one process.
- Closure criteria: provide a durable authoritative store with atomic
  check-and-insert, complete-record equality for idempotency, conflict auditing,
  and restart/concurrency tests.

### DSS-R004 — Exact payload scan-to-write binding is incomplete 🔥

- Impact: without orchestration, code could scan one byte sequence and later
  request persistence of another even when metadata appears equivalent.
- Current control: Evidence binds the contract-defined `payload_hash` and
  `payload_format`; no Writer is enabled.
- Closure criteria: WBS 4.5 accepts exact bytes at its API boundary, recomputes
  hash and size without normalization, validates Evidence/Security Binding, and
  carries the same verified bytes forward to the Writer contract.

### DSS-R005 — Human Review runtime is absent 🔥

- Impact: `review_required` cannot be resolved into a valid
  `human_false_positive_confirmed` decision.
- Current control: WBS 4.4 never generates that decision and cannot derive an
  automatic-pass binding from `review_required`.
- Closure criteria: implement the canonical Human Review binding, reviewer
  authority, Evidence/payload binding, invalidation after changes, and an
  explicit rejection path. Until then, `review_required` stays non-persistable.

### DSS-R006 — Write Request revalidation is absent 🔥

- Impact: the future persistence boundary could trust a copied Security Binding
  without re-resolving its Evidence and authority.
- Current control: Write Request and Writer are not implemented.
- Closure criteria: WBS 4.5 validates the exact eight-field Security Binding,
  revalidates referenced Evidence integrity and authority, confirms policy and
  payload/source binding, and fails closed on missing or stale evidence.

### DSS-R007 — Production policy approval is incomplete 🔥

- Impact: a structurally closed Registry does not itself prove that required
  checks, blocking rules, size limits, artifact-type rules, and finding codes are
  operationally adequate.
- Current control: unknown policy versions and unregistered fields fail closed.
- Closure criteria: security and artifact owners approve the initial Registry;
  each required check has an implementation and fixture; artifact-type
  differences are explicit; policy release and rollback ownership are recorded.

### DSS-R008 — Operational scan lifecycle is incomplete 🔥

- Impact: timeout, retry, crash, and partial completion could otherwise create
  ambiguous or indefinitely pending persistence decisions.
- Current control: malformed, unavailable, unsupported, or unverifiable results
  become `unknown` or are rejected; neither permits automatic persistence.
- Closure criteria: define retry ownership and limits, terminal-state recording,
  duplicate execution handling, timeout classification, and durable recovery.

### DSS-R009 — Safe-location semantic accuracy is adapter-dependent 🔥

- Impact: Registry membership prevents arbitrary paths but does not prove the
  scanner reported the correct location for a finding. Incorrect locations can
  mislead reviewers or hide affected fields.
- Current control: Evidence stores only closed, artifact-type-specific safe field
  paths and never raw snippets or absolute paths.
- Closure criteria: production scanner mapping tests prove each emitted location
  corresponds to the registered structural field; ambiguous locations use a
  safe coarse classification rather than invented precision.

### DSS-R010 — Attestations are not portable cryptographic proofs

- Trigger: multi-process workers, remote scanners, queued evidence, or verification
  after process restart.
- Risk: an opaque in-process capability establishes composition provenance only
  inside the trusted Python process; it cannot authenticate serialized evidence
  across a service boundary.
- Closure direction: adopt authenticated service identity plus signed/MACed
  attestations or re-resolve evidence from an authoritative store. Do not serialize
  the current opaque capability as if it were a signature.

### DSS-R011 — Policy migration is single-version only

- Trigger: adding, deprecating, or concurrently accepting another security or
  artifact-type policy version.
- Risk: unclear rescanning, compatibility, and revocation rules can make old
  Evidence accidentally reusable.
- Closure direction: define accepted-version windows, rescan requirements,
  downgrade prevention, retirement behavior, and audit tests before version two.

### DSS-R012 — Registry and candidate-schema drift

- Trigger: changing artifact schemas, adding artifact types, or renaming fields.
- Risk: a stale allow-list may reject valid locations or continue accepting a
  location that no longer exists.
- Closure direction: add a consistency check that derives or validates registered
  field paths against the canonical artifact schema during CI.

### DSS-R013 — Cross-runtime canonical hash interoperability

- Trigger: a non-Python scanner, adapter, service, or verifier.
- Risk: differences in Unicode, number handling, or serialization can produce
  different Evidence hashes for the same intended record.
- Closure direction: publish canonical byte-level test vectors and require every
  implementation to reproduce them exactly.

### DSS-R014 — Timestamp authority and clock semantics

- Trigger: persisting and auditing production Scan Evidence.
- Risk: adapter-issued timestamps may be syntactically valid but unreliable for
  audit ordering, expiry, or incident reconstruction.
- Closure direction: define clock source, UTC format, skew tolerance, monotonic
  ordering expectations, and whether timestamps participate in freshness policy.

### DSS-R015 — Composition fixtures near production adapter code

- Risk: test-only composition helpers can be mistaken for supported production
  installation APIs, even if current production mint paths reject test proofs.
- Closure direction: keep test fixtures in test modules or an explicitly internal
  test-support module when composition infrastructure is consolidated.

### DSS-R016 — Same-process arbitrary-code threat model exclusion

- Risk: Python private names, exact-type checks, and opaque objects do not protect
  against an attacker already able to monkey-patch modules or mutate objects in
  the trusted process.
- Current decision: this is explicitly outside the WBS 4.4 threat model.
- Revisit trigger: untrusted plugins or third-party code are loaded into the
  authority process. At that point, use process isolation and authenticated IPC
  instead of strengthening Python naming conventions.

## Operational Gate

Production Artifact Persistence must remain disabled while any 🔥 P0 item is
open. A WBS 4.4 code commit may still be appropriate because the current
interface-first implementation is intentionally fail closed; commit readiness
does not imply operational readiness.

Before enabling production persistence, reviewers must record evidence that:

1. every 🔥 item is closed or the relevant outcome/path is technically disabled;
2. the production scanner and policy identities are registered and independently
   verified;
3. exact payload bytes remain bound from scan through Write Request and Writer;
4. `review_required`, `blocked`, and `unknown` cannot reach automatic persistence;
5. durable uniqueness, retry, and recovery behavior has passed concurrency and
   restart testing.
