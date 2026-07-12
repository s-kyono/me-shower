# Review Queue

Review Queue is a regenerable Human Review worklist derived from Canonical Events in `source_sync`. It helps reviewers find candidates, see whether safe and traceable Evidence is available, and focus on semantic or policy risks.

It is not a source of truth, Career Knowledge, or a Promotion Decision Log. Building or inspecting the Queue does not mutate a Canonical Event, store raw source content, create an approval outcome, or promote knowledge.

## Readiness

- `ready_for_review`: stable Canonical Event reference, `high` or `medium` confidence, traceable safe Evidence, and no blocking policy or structural issue
- `needs_evidence_before_review`: safe Evidence traceability is missing, or low confidence requires stronger Evidence and reassessment
- `blocked_by_policy`: confidential, raw sensitive, private, or otherwise unsafe content is detected
- `needs_cleanup`: the event cannot be stably traced or its structure and semantic kinds need cleanup

These values only describe whether Human Review can begin. The Promotion Decision statuses `approved`, `rejected`, `deferred`, and `needs_more_evidence` are forbidden in Review Queue and remain the responsibility of the future Promotion Decision Log.

## Outputs

`build-review-queue` writes `app/generated/review_queue.md` and `app/generated/review_queue.jsonl` by default. Both are disposable derived outputs, excluded from normal PR scope, and must not be hand-edited or treated as durable state.
