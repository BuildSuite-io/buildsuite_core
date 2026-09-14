# Multi-company support — implementation plan

## Why

BuildSuite is single-company in practice today. The Settings → Companies page is a
localStorage mock (Acme demo data), the topbar switcher only sets a prototype `activeCompany`,
and `company` is anchored to the project on only a few finance doctypes. We are adding real
multi-company support so that:

- Each company owns its own brand and catalog (assemblies, rate masters, templates, etc.).
- The topbar switcher selects the **working company** and re-scopes the whole app — lists,
  pickers, and new-record defaults.
- Cross-company mixing is blocked. The driving example: **one company's BOQ must not be
  attachable to another company's project or scope-change order.**

Decisions taken up front: catalog masters are **per-company**; the switcher **sets the working
company**; this pass delivers the **foundation + validations** (cost-code `Data`→`Link`
conversion is deferred).

## What already exists (reused, not rebuilt)

- `default_company()` (`utils/project.py`) — the single company resolver; `active_company()`
  (`api/company.py`) exposes it to the SPA.
- `activeCompanyFilter()` (`frontend/src/composables/useActiveCompany.js`) — the company-scope
  filter seam, already used by the finance views; `DeskLinkPicker` re-queries when its filters change.
- The "anchor company to project" pattern — `subcontractor_work_order.py` `_set_company()` always
  re-derives `company` from the project and throws on drift; `subcontractor_bill.py`
  `_sync_from_work_order` does the same.
- `expense_entry.py` `validate_single_company()` and `machinery_usage.py` ("… does not belong to …")
  — the templates for company-mismatch guards.
- A real Company data path — `useDocTypeList("Company")` / `remoteDataAdapter.getCompanies()`,
  already used by `ProjectsView.vue`.

## Scope of company fields

- **Have `company` already:** BOQ, Subcontractor WO/Bill, Measurement Book, Scope Change Order,
  Expense Entry, Petty Cash Request, Crew, Machinery, Labour/Overtime Attendance Register.
- **Need `company` added (project-scoped):** Work Package, Stage Planning, Field Attendance,
  Machinery Usage, Schedule Snapshot, Task Progress Entry (via task → project).
- **Need `company` added (masters, now per-company):** Assembly, Assembly Category, Construction
  Rate Master, Rate Master Category, Estimate Template, Estimate Template Group, Project Category,
  Machinery Type, Subcontract Delivery Type, Construction Trade, Labour Trade.

## Stages (one PR, independently reviewable)

1. **Backend foundation.** Shared helpers in `utils/project.py`:
   `anchor_company_to_project(doc, project_field)` (always re-derive from the project, throw on
   drift) and `assert_same_company(doc, link_field, link_doctype, label)` (the linked record's
   company must equal the document's). Add `company` to the six project-scoped doctypes that lack
   it; wire the cascade into each `validate()`; convert the weak "only-if-blank" derivations (BOQ,
   Measurement Book, Scope Change Order) to always-re-derive.

2. **Per-company masters.** Add `company` (default = working company, read-only after insert) to
   the catalog masters; update the seeders to stamp `company`; existing rows backfilled by the
   Stage 7 patch.

3. **Cross-company validations (core).** Guard the real gaps with `assert_same_company`:
   `SCO.boq_revision`, `BOQ.base_revision`, `MB.work_order`, and BOQ-item
   `assembly`/`rate_master`/`work_package`/`task` — all must share the project's company. Mirror the
   guards in the API creators. Cost-code `Data` fields are flagged as deferred (no FK).

4. **Working-company seam.** `set_active_company(company)` in `api/company.py` sets the user default
   company server-side (so `default_company()` follows the switcher); `useActiveCompany.js` becomes
   the single source and `store.setActiveCompany()` drives it so pickers/lists re-query.

5. **Real-company conversion (frontend).** Repoint the store's `companies` slice to the real Company
   doctype via an async `loadCompanies()` mapping real rows into the existing view shape; real
   create/update/delete; list/detail/switcher backed by real data.

6. **Company-aware pickers + lists.** Bind the active-company (or the doc's project-company) filter
   on company-partitioned pickers and lists across the create flows, using the finance-view pattern.

7. **Migration + tests.** A patch backfills `company` on existing project-scoped rows (from their
   project) and stamps existing masters with the default company. New tests (mirroring
   `tests/test_subcontractor_bill.py`) assert cross-company attachment is blocked and the cascade
   anchors company correctly.

## Verification

1. `bench --site bs.local migrate` — new `company` fields created; backfill patch stamps existing
   rows and masters; no errors.
2. `bench --site bs.local run-tests --app buildsuite_core --module buildsuite_core.tests.test_company_scope`
   plus existing `test_subcontractor_bill` / `test_boq` green.
3. Create a second Company; switch via the topbar → lists/pickers re-scope; a new project defaults
   to the selected company.
4. Attempt to attach a company-A BOQ to a company-B project's SCO → blocked with a clear
   "does not belong to company" error (the driving example).
5. `yarn build` passes; brand / letter head resolve per company.

## Out of scope

- Cost-code `Data`→`Link` conversion (WO/Bill/MB) — FK-level cross-company enforcement on cost
  codes deferred to a later pass.
- Inter-company transactions and financial consolidation.
