---
plan_id: "{{ plan_id }}"
title: "{{ title }}"
status: "{{ draft | under_review | accepted | superseded }}"
revision: {{ revision }}
created_at: "{{ created_at }}"
updated_at: "{{ updated_at }}"
base_branch: "{{ base_branch }}"
related_adrs: {{ related_adrs }}
related_issues: {{ related_issues }}
supersedes: {{ supersedes }}
---

# {{ title }}

## 1. Executive Summary

{{ executive_summary }}

## 2. Background

{{ background }}

## 3. Problem Statement

{{ problem_statement }}

## 4. Goal

{{ goal }}

## 5. Success Definition

{{ success_definition }}

## 6. Scope

### 6.1 In Scope

{{ in_scope }}

### 6.2 Out of Scope

{{ out_of_scope }}

## 7. Users and Use Cases

{{ users_and_use_cases }}

## 8. Principles and Invariants

{{ principles_and_invariants }}

## 9. Accepted Decisions

{{ accepted_decisions }}

## 10. Source of Truth and Data Boundaries

{{ source_of_truth_and_data_boundaries }}

## 11. Human Review Boundaries

{{ human_review_boundaries }}

## 12. Evidence Requirements

{{ evidence_requirements }}

## 13. Failure and Safety Model

{{ failure_and_safety_model }}

## 14. Acceptance Criteria

{{ acceptance_criteria }}

## 15. Risks and Accepted Trade-offs

### Accepted Risks

{{ accepted_risks }}

### Trade-offs

{{ trade_offs }}

### Revisit Triggers

{{ revisit_triggers }}

## 16. Dependencies and Constraints

{{ dependencies_and_constraints }}

## 17. Open Items

{{ open_items }}

## 18. ADR Candidates

{{ adr_candidates }}

## 19. Implementation Design Handoff

{{ implementation_design_handoff }}

## 20. Approval

- Plan Status: {{ approval_status }}
- Submitted By: {{ submitted_by }}
- Submitted At: {{ submitted_at }}
- Plan State Revision: {{ plan_state_revision }}
