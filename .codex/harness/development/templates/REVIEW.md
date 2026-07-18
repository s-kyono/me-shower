---
epic_id: "{{ epic_id }}"
status: "{{ accepted | changes_required | blocked }}"
reviewed_at: "{{ reviewed_at }}"
reviewer: "{{ reviewer }}"
design_lock_revision: {{ design_lock_revision }}
implementation_revision: {{ implementation_revision }}
reviewed_snapshot_hash: "{{ reviewed_snapshot_hash }}"
---

# Implementation Review

## 1. Summary

{{ summary }}

## 2. Review Priorities

1. Security
2. Reproducibility and Operational Stability
3. Maintainability and Boundary Clarity
4. Performance
5. Delivery Speed

## 3. Design Lock Alignment

{{ design_lock_alignment }}

## 4. Verified Boundaries

{{ verified_boundaries }}

## 5. Findings

### Blocking

{{ blocking_findings }}

### Must Fix

{{ must_fix_findings }}

### Deferred

{{ deferred_findings }}

## 6. Validation Performed

{{ validation_performed }}

## 7. Trade-off Assessment

### Accepted Trade-offs

{{ accepted_trade_offs }}

### Rejected Trade-offs

{{ rejected_trade_offs }}

### Revisit Triggers

{{ revisit_triggers }}

## 8. Remaining Risks

{{ remaining_risks }}

## 9. Decision

- Result: {{ accepted | changes_required | blocked }}
- Next Action: {{ next_action }}
