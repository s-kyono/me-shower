---
adr_id: "{{ adr_id }}"
title: "{{ title }}"
status: "{{ proposed | accepted | rejected | superseded | deprecated }}"
date: "{{ date }}"
epic: "{{ epic_id }}"
supersedes: {{ supersedes }}
related_adrs: {{ related_adrs }}
related_issues: {{ related_issues }}
---

# {{ title }}

## Context

{{ context }}

## Decision

{{ decision }}

## Decision Drivers

{{ decision_drivers }}

## Considered Options

{{ considered_options }}

## Selected Option

{{ selected_option }}

## Rationale

{{ rationale }}

## Trade-offs

{{ trade_offs }}

## Consequences

### Positive Consequences

{{ positive_consequences }}

### Negative Consequences

{{ negative_consequences }}

### Constraints Introduced

{{ constraints_introduced }}

## Rejected Alternatives

{{ rejected_alternatives }}

## Accepted Risks

{{ accepted_risks }}

## Revisit Triggers

{{ revisit_triggers }}

## References

{{ references }}
