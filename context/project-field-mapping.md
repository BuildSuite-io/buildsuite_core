# ERPNext Project Mapping Baseline (Frappeline -> ERPNext)

## Source and intent
- Source requirements: [mapping.txt](mapping.txt)
- ERPNext reference schema: [project.json](project.json)
- Purpose: provide a reliable context artifact for follow-up AI runs to generate Custom Field and Property Setter fixtures.

## Executive summary
- Frappeline rows evaluated: 23
- Required new custom fields on Project: 3
- Required schema behavior changes via Property Setter: 1 (Status options)
- Optional UX label alignments via Property Setter: 4
- Existing Project fields that can be reused as-is: majority of core timeline/costing fields

## 1) Field-by-field mapping (Frappeline -> ERPNext)

| Frappeline field | Frappeline type | ERPNext fieldname | ERPNext label | Match type | Action |
|---|---|---|---|---|---|
| details_sec | Section Break | n/a | n/a | Layout only | Optional: recreate section via Customize Form if desired |
| project_code | Data | custom_project_id (new) | Project ID | Missing | Create Custom Field |
| project_name | Data | project_name | Project Name | Exact | Reuse |
| project_type | Link | project_type | Project Type | Exact | Reuse |
| status | Select | status | Status | Partial | Update options via Property Setter |
| priority | Select | priority | Priority | Exact (same values) | Reuse |
| col_1 | Column Break | n/a | n/a | Layout only | Optional layout customization |
| company | Link | company | Company | Exact | Reuse |
| is_group | Check | is_group (new) | Is Group | Missing | Create Custom Field |
| parent_project | Link(Project) | parent_project (new) | Parent Project | Missing | Create Custom Field |
| customer | Link | customer | Customer | Exact | Reuse |
| schedule_sec | Section Break | section_break_18 (Timeline) | Timeline | Conceptual | Reuse or relabel section |
| expected_start_date | Date | expected_start_date | Expected Start Date | Exact | Reuse |
| expected_end_date | Date | expected_end_date | Expected End Date | Exact | Reuse |
| col_2 | Column Break | column_break_20 | (Column Break) | Conceptual | Reuse |
| actual_start_date | Date | actual_start_date | Actual Start Date (via Timesheet) | Near match | Optional label setter only |
| actual_end_date | Date | actual_end_date | Actual End Date (via Timesheet) | Near match | Optional label setter only |
| costing_sec | Section Break | project_details | Costing and Billing | Conceptual | Reuse or relabel section |
| estimated_cost | Currency | estimated_costing | Estimated Cost | Near match | Optional label/alias decision |
| col_3 | Column Break | column_break_28 | (Column Break) | Conceptual | Reuse |
| total_costing_amount | Currency | total_costing_amount | Total Costing Amount (via Timesheet) | Near match | Reuse (optional label trim) |
| notes_sec | Section Break | section_break0 | Notes | Exact | Reuse |
| notes | Text Editor | notes | Notes | Exact | Reuse |

## 2) Required custom fields to create

These are the only fields that are functionally missing from ERPNext Project and should be generated as Custom Field fixtures.

### CF-1: custom_project_id
- Target DocType: Project
- Fieldtype: Data
- Label: Project ID
- Fieldname: custom_project_id
- Required: 1
- Unique: 1
- In List View: 1
- Suggested insert_after: project_name
- Rationale: Frappeline project_code requires a human-readable unique identifier separate from naming series.

### CF-2: is_group
- Target DocType: Project
- Fieldtype: Check
- Label: Is Group
- Fieldname: is_group
- Default: 0
- Suggested insert_after: company
- Rationale: Needed for tree/parent-child project grouping behavior.

### CF-3: parent_project
- Target DocType: Project
- Fieldtype: Link
- Options: Project
- Label: Parent Project
- Fieldname: parent_project
- Depends On: eval:!doc.__islocal
- Suggested insert_after: is_group
- Rationale: Self-referential parent link required for sub-project hierarchy.

## 3) Required property setter changes

### PS-1 (required): extend Project.status options
- Target: DocType Field (Project.status)
- Property: options
- Current ERPNext values: Open, Completed, Cancelled
- Required values for Frappeline parity:
  - Open
  - Working
  - Completed
  - On Hold
  - Cancelled
- Rationale: Frappeline workflow explicitly uses Working and On Hold.

## 4) Optional property setters (UX alignment only)

Apply only if you need exact label parity with Frappeline/UI docs.

- Project.actual_start_date label -> Actual Start Date (via Time Sheet)
- Project.actual_end_date label -> Actual End Date (via Time Sheet)
- Project.project_details label -> Costing
- Project.status label -> Project Status

## 5) Fields present in ERPNext Project but not required for Frappeline baseline

No custom field creation needed for these unless your process requires them:
- naming_series
- is_active
- percent_complete_method
- percent_complete
- project_template
- department
- sales_order
- users (child table)
- collect_progress and related scheduler fields
- totals for billing/sales/purchase/material and margin fields

## 6) Fixture generation checklist for next AI run

Use this document to generate fixtures in this order:
1. Custom Field fixtures for CF-1, CF-2, CF-3.
2. Property Setter fixture for PS-1 (status options).
3. Optional Property Setters from section 4, only if strict label parity is required.
4. Export fixtures and validate by opening Project form and creating a test Project.

## 7) Suggested acceptance criteria

- Project form shows Project ID, Is Group, Parent Project.
- Project ID enforces uniqueness.
- Parent Project allows linking to existing Project docs.
- Status dropdown includes Working and On Hold.
- Existing ERPNext Project behavior (timesheets/costing) remains intact.
