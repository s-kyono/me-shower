---
epic_id: "{{ epic_id }}"
status: "{{ passed | failed | blocked }}"
checked_at: "{{ checked_at }}"
design_lock_revision: {{ design_lock_revision }}
review_result: "{{ review_result }}"
---

# Release Gate

## 1. Gate Summary

{{ gate_summary }}

## 2. Preconditions

- [ ] Latest implementation review is accepted
- [ ] Design Lock is valid and aligned
- [ ] Required artifacts exist
- [ ] Working tree and staged scope are understood

## 3. Test Results

### Focused Tests

{{ focused_test_results }}

### Full Test Suite

{{ full_test_results }}

### Smoke Tests

{{ smoke_test_results }}

## 4. Static Validation

- [ ] Lint passed
- [ ] Formatter check passed
- [ ] Schema validation passed
- [ ] `git diff --check` passed

{{ static_validation_details }}

## 5. Security, Secrets, and Privacy Checks

### Secret Detection

- [ ] API keys are not present
- [ ] Access tokens are not present
- [ ] Passwords and credentials are not present
- [ ] Private keys and certificates are not present
- [ ] `.env` values are not present
- [ ] Logs and fixtures contain no real secrets

### Personal Information Detection

- [ ] Real names are not present
- [ ] Email addresses are not present
- [ ] Phone numbers are not present
- [ ] Addresses and location data are not present
- [ ] Birth dates and personal identifiers are not present
- [ ] Private work history or conversation content is not present

### Raw Source and Derived Data

- [ ] Raw source content is not persisted
- [ ] Real raw source is not reused as a fixture
- [ ] Rejection logs do not contain source content
- [ ] Exceptions and stack traces do not expose input content
- [ ] Generated artifacts do not contain unreviewed information

### Scan Evidence

- Detection Method: {{ detection_method }}
- Scanned Paths: {{ scanned_paths }}
- Excluded Paths: {{ excluded_paths }}
- Findings: {{ findings }}
- False-positive Handling: {{ false_positive_handling }}

## 6. Safety and Data Boundary Checks

{{ safety_and_data_boundary_checks }}

## 7. Design Lock Alignment

{{ design_lock_alignment }}

## 8. Git Diff and Publish Scope

- Current Branch: {{ current_branch }}
- Base Branch: {{ base_branch }}
- Staged Files: {{ staged_files }}
- Unrelated Changes: {{ unrelated_changes }}
- Forbidden Paths Changed: {{ forbidden_paths_changed }}

## 9. Known Failures

{{ known_failures }}

## 10. Remaining Risks

{{ remaining_risks }}

## 11. Final Decision

- Result: {{ passed | failed | blocked }}
- Secret Scan: {{ secret_scan_result }}
- Privacy Scan: {{ privacy_scan_result }}
- Raw Source Scan: {{ raw_source_scan_result }}
- Publish Allowed: {{ true | false }}
- Next Action: {{ next_action }}
