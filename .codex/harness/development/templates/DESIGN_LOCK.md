---
design_lock_id: "{{ design_lock_id }}"
epic_id: "{{ epic_id }}"
status: "{{ draft | locked | invalidated | superseded }}"
revision: {{ revision }}
plan_revision: {{ plan_revision }}
created_at: "{{ created_at }}"
submitted_by: "{{ submitted_by }}"
submitted_at: "{{ submitted_at }}"
---

# Design Lock: {{ title }}

## 1. Execution Contract

- Plan: {{ plan_path }}
- Related ADRs: {{ related_adrs }}
- Repository Root: {{ repository_root }}
- Base Branch: {{ base_branch }}
- Working Branch: {{ working_branch }}

## 2. Locked Scope

### In Scope

{{ in_scope }}

### Out of Scope

{{ out_of_scope }}

### Completion Conditions

{{ completion_conditions }}

## 3. Architecture

### Module Structure

{{ module_structure }}

### Dependency Direction

{{ dependency_direction }}

### Public Boundaries

{{ public_boundaries }}

### Forbidden Dependencies

{{ forbidden_dependencies }}

## 4. Components and Responsibilities

{{ components_and_responsibilities }}

## 5. Data and Type Boundaries

### Input Types

{{ input_types }}

### Candidate Types

{{ candidate_types }}

### Accepted Types

{{ accepted_types }}

### Persistence Rules

{{ persistence_rules }}

### Raw Data Rules

{{ raw_data_rules }}

## 6. Integration Points

{{ integration_points }}

## 7. Change Boundaries

### Allowed Changes

{{ allowed_changes }}

### Conditional Changes

{{ conditional_changes }}

### Forbidden Changes

{{ forbidden_changes }}

## 8. Verification Strategy

### Required Tests

{{ required_tests }}

### Negative Cases

{{ negative_cases }}

### Smoke Tests

{{ smoke_tests }}

### Release Checks

{{ release_checks }}

## 9. Acceptance Mapping

{{ acceptance_mapping }}

## 10. Autonomous Decisions

Execute may decide the following without returning to Plan:

{{ autonomous_decisions }}

## 11. Recorded Deviations

Execute may apply the following only when the deviation is recorded:

{{ recorded_deviations }}

## 12. Blocking Deviations

Execute must stop and return to Plan when any of the following is required:

{{ blocking_deviations }}

## 13. Known Constraints

{{ known_constraints }}

## 14. Invariants

{{ invariants }}

## 15. Approval

- Design Status: {{ approval_status }}
- Submitted By: {{ submitted_by }}
- Submitted At: {{ submitted_at }}
- Plan Revision: {{ plan_revision }}
- Design Lock Revision: {{ revision }}
