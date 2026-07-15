# Real Data Ingestion Safety Gate

## Role

The gate decides whether a real work Source may cross a persistence boundary. Inspection happens in memory before Canonical Event extraction and before any persistent or temporary output.

```text
Raw Source
  ↓
in-memory inspection
  ↓
pass / pass_with_sanitization / blocked
  ↓
Safe Normalized Source Candidate
  ↓
future Source Ingestion POC
```

The rule contract is `.codex/source-intelligence/rules/real_data_ingestion_safety.yaml`. Runtime startup validates the complete protected-category set, actions, and placeholders against the detector contract; an unknown or conflicting detector finding fails closed. Credentials, raw-persistence requests, and unknown high-risk candidates block. Supported categories are sanitized. Personal and internal identifiers remain heuristic candidates; this MVP does not claim complete automatic identification.

Findings contain only category, action, safe field path, rule ID, and confidence. Audit metadata adds versions and category counts. It contains no raw, hashed, matched, or reversible value.

Private URLs and their placeholders are never retained as Evidence or Source IDs. When a private reference has no existing safe local target, the Canonical Event omits both `source_reference` and the redacted Source ID; only category-level audit counts remain. Existing safe local Source references may be retained for traceability.

All Source Adapter normalization routes converge on the gate before event extraction. Source inspection commands also inspect the complete RawSource but print only ordinal and category-level metadata. The `source_sync` writer reinspects serialized output immediately before atomic replacement.

The public persistence handoff is `persist_text_safely`. It snapshots the current candidate value, reruns the complete gate, and writes only the resulting immutable local string through a private atomic helper. Wrappers improve API clarity but are not trusted as a security boundary: mutation or construction-token misuse is still stopped by the final reinspection. `blocked` results contain no sanitized wrapper. The next Source Ingestion POC must use this public persistence API rather than a low-level writer.

Adapter failures cross a separate safe-error boundary. Inspection and normalization commands emit only a fixed operation, adapter kind, and `adapter_access_failed` code; repository names, channel/team identifiers, paths, API response bodies, and original exception messages are not CLI output.

## Trust boundary

This POC protects untrusted Source input when the repository's application code is used as distributed. Production Source writes must use `persist_text_safely`; an architecture test fixes the private atomic helper's only call site to that public safety boundary. Adapter errors discard the original exception context before a safe error crosses the boundary.

Code and repository integrity are outside this gate's threat model. The project does not claim to protect against a person who modifies the Python source, imports and deliberately calls private internals, monkeypatches the gate, rewrites Git history, or already controls the host or process. A user must review the code and revision they choose to run. Protecting against malicious in-process code would require a separate process or service and is not part of this POC.
