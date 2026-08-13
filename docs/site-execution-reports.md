# Site Execution Reports — Data Sources

The Site Execution workspace links four reports, reworked to match the prototype's Overview
set. Each is a **Frappe Query Report** (SQL) that renders **in-app** through the generic
report renderer at `/reports/view/<Report Name>` (`FrappeReport.vue`) — the same renderer used
for ERPNext's financial statements, so it gets the filter bar, number formatting, and (where
applicable) tree/cards/chart automatically.

Definitions live in
`buildsuite_core/buildsuite_core/doctype/workspace_setting/seed_workspace_reports.py`
(the `REPORTS` tuple); the workspace tiles are seeded/repointed by the same module and the
`reseed_site_execution_reports` patch. Every report takes an optional **Project** filter (and
Billing also takes **From/To Date**); an empty filter means "all".

Only **submitted** documents count as real (docstatus = 1) — drafts and cancelled are excluded,
consistent with the rest of the app (a draft WO/bill/invoice isn't a commitment/receivable yet).

---

## 1. Delay Analysis
*Stages slipping, by how much, and current progress.* — **Roles:** all site roles (Director,
PM, QS, Site Engineer, Foreman, Admin).

| Column | Source | Notes |
|---|---|---|
| Stage / Stage Name / Project | `Stage Planning` (`name`, `stage_name`, `project`) | |
| Planned End | `Stage Planning.planned_end` | the stage's planned finish |
| Progress | `Stage Planning.mean_progress` | mean % across the stage's tasks |
| Days Late | `DATEDIFF(today, planned_end)` | how far past the planned end |

**A stage is "slipping"** when `planned_end < today` **and** `mean_progress < 100`. Sorted by
most days late first.
**Caveat:** shows *how late* and *how far along*; the "what sits downstream" dependency chain
is not yet surfaced (a possible enhancement using `Stage Planning Dependency`).

---

## 2. Billing and Collection
*Invoiced, received, overdue and retention held, per project.* — **Roles:** finance
(Director, PM, QS, Accountant, Admin). **Filters:** Project, From/To Date (on `posting_date`).

Grouped by **Project**, over submitted **Sales Invoice** rows (`grand_total`,
`outstanding_amount`, `due_date`, `posting_date`, `project`):

| Column | Formula |
|---|---|
| Invoiced | `SUM(grand_total)` |
| Received | `SUM(grand_total − outstanding_amount)` |
| Outstanding | `SUM(outstanding_amount)` |
| Overdue | `SUM(outstanding_amount)` where `due_date < today` |
| Retention Held | `SUM(Subcontractor Bill.retention_amount)` for that project (submitted bills) |

Retention comes from the payable side (**Subcontractor Bill**), everything else from the
receivable side (**Sales Invoice**).

---

## 3. Subcontractor Position
*WO value, measured, billed, paid, retention and outstanding, per subcontractor.* —
**Roles:** finance. Grouped by **Subcontractor** (Supplier).

| Column | Source | Formula |
|---|---|---|
| WO Value | `Subcontractor Work Order.total_value` (submitted) | total committed to the subcontractor |
| Measured Qty | `Measurement Book.measured_total` (status = Certified, via `work_order → WO.subcontractor`) | certified measured quantity |
| Billed | `Subcontractor Bill.gross` (submitted) | gross billed |
| Retention | `Subcontractor Bill.retention_amount` (submitted) | held back |
| Paid | linked `Purchase Invoice.grand_total − outstanding_amount` (`Subcontractor Bill.purchase_invoice`) | actually paid |
| Outstanding | `Billed − Paid` | still owed |

The three sources (WOs, Measurement Books, Bills) are unioned and rolled up per subcontractor.
**Caveat:** "Measured Qty" is a quantity total (from certified MBs), not a currency value.

---

## 4. Material Status
*Ordered → received → consumed → at site, by item.* — **Roles:** all site roles. Grouped by
**Item**.

| Column | Source | Formula |
|---|---|---|
| Ordered | `Purchase Order Item.qty` (parent PO submitted) | quantity ordered |
| Received | `Purchase Receipt Item.received_qty` (parent PR submitted) | quantity received |
| Consumed | `Stock Entry Detail.qty` where parent `Stock Entry.stock_entry_type = 'Material Issue'` (submitted) | issued to site |
| At Site | `Received − Consumed` | on-hand derived from the project's own movements |

Project scoping uses the `project` field that Purchase Order Item, Purchase Receipt Item and
Stock Entry all carry.
**Caveat:** "At Site" is computed as *received − consumed* (project-accurate) rather than from
`Bin.actual_qty`, because `Bin` is keyed by warehouse and has no project field. This is a close
proxy for current on-site stock per project.

---

## Roles & visibility
A report's roles are set on the **Report** doc itself (`REPORTS` → `_ensure_report`). The
workspace tile is **hidden** for any user who can't run the report
(`api/workspace_setting._resolve` checks `Report.is_permitted()`), so a Site Engineer sees only
Delay Analysis and Material Status, while Billing and Subcontractor Position appear for finance
roles. No per-tile role config is needed — the Report's own permissions drive both execution and
tile visibility.

## Adding or changing a report
Edit the `REPORTS` tuple (name, ref doctype, icon, description, SQL, filters, roles).
`_ensure_report` reconciles the query, filters and roles on every migrate, so changes reach
existing sites; new workspace links are added by `seed_workspace_reports()` (fresh installs) or
a small patch (existing installs).
