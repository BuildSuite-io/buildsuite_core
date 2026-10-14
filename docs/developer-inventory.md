# BuildSuite Core — Developer Inventory

A catalog of the app's features, systems, utilities, and conventions, meant as a **review checklist**: skim it and mark what deserves real documentation. Each entry is a one-liner with key files where useful.

Legend: **[undoc]** = no dedicated doc yet · **[has doc]** = some doc exists (see §K) · **[footgun]** = non-obvious, high-value to write down.

---

## A. Cross-cutting architecture & "seams"

- **Single-company seam** — app runs single-company; the working company resolves via `utils/project.default_company()` / `useActiveCompany()`, never hardcoded. Multi-company is a master switch on **BuildSuite Core Settings** (`multi_company_enabled`) that scopes lists/pickers/new-record defaults. `docs/multi-company-implementation-plan.md`. **[has doc]**
- **Single-currency by construction** — no multicurrency in use; everything posts in the default company currency. ERPNext-native MC fields exist but are unused. **[undoc]**
- **Company-stamping on insert** — org-wide ERPNext masters (e.g. Item) get a BuildSuite `company` custom field stamped on insert (`utils/project.stamp_company_on_insert`, `doc_events`). Supplier/Customer are intentionally global (no company field — see `patches.drop_party_company_field`). **[undoc]**
- **Custom fields & property setters are code, not fixtures** — `custom_property_list/custom_field.py` (`CUSTOM_FIELD` map) synced via `after_migrate`/`before_migrate` (`install.py`), NOT JSON fixtures. Explains why `bench migrate` applies field changes. **[undoc · footgun]**
- **Permission setup is install-only** — `permissions/setup.py:setup_record_permissions()` runs on `after_install`, not `after_migrate`; role/perm changes reach existing sites only via a **patch**. **[undoc · footgun]**
- **`_apply_role_perms` drops unlisted BuildSuite roles** — a doctype's full perm set must be applied in **one** call (full + select together), or the second call wipes the first's roles. **[undoc · footgun]**
- **Duplicate Custom DocPerm rows break scope resolution** — a role with a stale extra read row (`if_owner=0`) reports read-all; a clean setup yields one row per role/permlevel. Worth a note + optional dedup patch. **[undoc · footgun]**
- **In-request admin elevation** — `utils/session.as_administrator()`; never raw `frappe.set_user` (clobbers sid → logout). **[undoc · footgun]**
- **Print architecture** — SPA prints via server-rendered default Frappe Print Formats; customize by seeding a Print Format + `default_print_format` (no frontend change); dark mode via `.print-document`. `api/printing.py`, `components/ServerPrintDocument.vue`. **[undoc]**
- **i18n** — SPA reuses Frappe's `__()` (`utils/translate.js`); app CSV `translations/fr.csv`; `bench clear-cache` required after CSV changes. **[undoc]**

## B. Permissions & access control

- **Two-layer model** — authoritative DocPerms (`permissions/setup.py`, tested by `TestPersonaCrudMatrix`) + cosmetic Vue gates (`data/roles.js`, `usePermissions`). `frontend/PERMISSIONS.md`. **[has doc]**
- **Persona → role sync** — `Persona` / `Persona Role` doctypes; `utils/user.sync_persona_roles` (User.validate hook) keeps a user's BuildSuite roles in sync with their persona; every persona also carries the workflow-editor marker role (`BuildSuite Project User`, `setup.WORKFLOW_EDITOR_ROLE`). **[undoc]**
- **SPA permission payload** — `api/permission.py:get_resource_permissions` + `permissions/resource_map.py`. Maps DocPerms to the frontend, including **scope** (`readScope`/`writeScope`/`deleteScope` = `all`|`own`|`none`) resolved from the `if_owner` map (because doc-less `has_permission` can't tell "own" from "all"). Consumed by `usePermissions` (`canReadAll`, `canEdit`, `canEditRecord`, `ownsRecord`). **[undoc · subtle]**
- **Row-level scoping hooks** — `permission_query_conditions` + `has_permission` for Project, Task, Work Package, Task Progress Entry, Stage Planning, Scope Change Order (`permissions/*.py`). **[undoc]**
- **Beneficiary-owner model (Petty Cash + Expense)** — `owner` = the beneficiary, `raised_by` = the creator, native `if_owner` (no permission hook); `utils/beneficiary_owner.py` `doc_events`. See-all = Admin/Director/Accountant/SysMgr; everyone else own-scoped. The finance panels gate org-wide tabs on `readScope`. **[undoc]**
- **Report access matrix** — `report_access.py` (which roles see which reports; constrained by workspace visibility). **[undoc]**
- **Mobile permission layer** — `setup_mobile_permissions()` layers extra DocPerms for the companion mobile app (upgrade-only). **[undoc]**
- **Caveat: ERPNext User Permissions** — self-service User Permissions can silently narrow access and break the matrix. **[undoc]**

## C. Backend feature modules (`buildsuite_core/api/*.py`)

**Estimation & BOQ:** `boq` (assembly explosion, revisions, clone, template import, actuals recompute), `boq_actuals` (cost-code actuals log), `cost_report` (Cost vs Budget by cost code), `estimation_seed`, `rate_master` (+ construction rate history), `insights` (ask-a-question reporting). `docs/boq-implementation.md`, `docs/jv-cost-code-actuals.md`.

**BOQ cost accounting (worth its own page):** **Actuals** (Material Consumption / Subcontractor Bill / Expense Entry, by cost code) vs **Committed** (submitted Subcontractor Work Order **+ Purchase Order** lines, by cost-code group) + the Committed/Actual **drill-down modals**. The **cost-code pattern**: four fields (`cost_code_type/group/item/label`, `custom_*` on ERPNext doctypes) + the shared `CostCodePicker.vue`.

**Procurement:** `procurement`, `procurement_docs` (Material Request / Purchase Order / Purchase Receipt, with per-line cost codes), `procurement_report`.

**Subcontract:** `subcontract` (subcontractors, Work Orders, committed-by-cost-code, SOV read/save), `subcontractor_bill`, `supplier_bill`, `suppliers`. `docs/subcontractor-bill-implementation-plan.md`.

**Project Finance:** `finance_account`, `finance_payment` (advances / receipts / payments), `finance_report` (P&L, aged, financial position), `invoice` (Sales Invoice wrapper), `petty_cash`, `expense_entry`. `docs/site-execution-reports.md`.

**Site execution / schedule:** `material_consumption`, `progress_report`, `project_dashboard`, `project_team`, `schedule`, `schedule_engine`, `schedule_snapshot` (baselines), `delay_analysis`, `task_assignment`. `docs/schedule-implementation.md`.

**Workforce / Equipment:** `field_employee`, `field_attendance`, `crew`, `equipment` (machinery + usage).

**Scope changes:** `sco` (Scope Change Order + BOQ-revision tie-in).

**Platform:** `workflow` (dynamic workflow bridge), `terms` (T&C library), `notification`, `todo`, `search` (command palette + global search), `report` (in-app report runner), `users`, `persona`, `role_permissions`, `permission`, `core_settings`, `project_settings`, `project_template`, `company`, `home`, `customers`, `printing`.

## D. Platform mechanisms worth their own page

- **Dynamic Workflow bridge** — `api/workflow.py` + `composables/useWorkflow.js`: reuse a Frappe Workflow on any doctype; `apply_workflow` is monkeypatched to take a JSON string; SPA detail views route to the workflow transitions when one is active. Shipped workflows: Material Request / Scope Change Order / Stage Planning Approval. **[undoc]**
- **Generic DocType browser/form** — `records/` routes → `DocTypeRecordsListView`, `DocTypeRecordFormView` → `DocTypeForm` + `DocTypeFieldControl` (meta-driven controls, incl. `RichTextEditor` for Text Editor fields) + `DocTypeChildTable`. Lets admins CRUD any curated doctype in-app. **[undoc]**
- **Workspace registry** — `BuildSuite Workspace` / `Workspace Role` / `Workspace Shortcut` + `Workspace Setting` doctypes: sidebar visibility, order, per-role shortcut tiles; read by `DeskShell`; seeded via `seed_workspaces` + `seed_workspace_reports` and a patch. **[undoc]**
- **Schedule engine** — `api/schedule_engine.py` + `composables/useScheduleEngine.js` + snapshots. `docs/schedule-implementation.md`. **[has doc]**
- **Search / command palette** — `api/search.py`, `data/search.js` (places + records; permission-safe global search). **[undoc]**
- **Insights** — leadership ask-a-question reporting. `docs/insights-feature-options.md`. **[has doc]**
- **Rich text** — `components/RichTextEditor.vue` (frappe-ui TextEditor / TipTap, table support), used by the generic form + Terms settings; isolated async chunk. **[undoc]**

## E. Backend utilities (`buildsuite_core/utils/*.py`)

`beneficiary_owner` · `branding` (letter-head rebuild) · `date_bounds` · `employee_permissions` · `material_request` · `party` (contact upsert/join) · `payment` · `petty_cash` · `project` (**default_company, company scoping, stamp_company_on_insert**) · `purchase_order` · `purchase_receipt` · `quotation` · `session` (**as_administrator, getSessionUser**) · `stock_entry` · `subcontract_billing` · `task` / `task_type` · `user` (**sync_persona_roles**).

## F. Frontend architecture

- **Composables (21)** — `useActiveCompany`, `usePermissions`, `useWorkflow`, `useDocTypeList`, `useDoctypeMeta`, `useAutosave`, `useConfirm`, `usePagination`, `usePageTitle`, `useFormErrors`, `useScheduleEngine`, `useInsightsData`, `useAttendanceSheet`, `useHiddenUsers`, and the `use*Options` / `use*Names` option loaders.
- **Stores** — `stores/index.js` (data store: coreSettings, companies, workspaces, `isAdmin` / `isBSA` / `hasRole`, todo counts…) + `stores/session.js` (access / roles payload).
- **Layout shells** — `layouts/DeskShell` (sidebar app), `layouts/TodoShell` (thin full-width). Desk component library (`components/desk/*`: DeskPage, DeskForm, DeskField, DeskSelect, DeskLinkPicker, DeskTextarea, DeskActionBar…).
- **Theme system** — design tokens + `desk-save-btn` primary (near-black light / green dark), `ink` / `danger` / `brand` scales, dark mode via `html.dark`. `frontend/DEVELOPER_GUIDE.md`. **[has doc]**
- **Data layer** — `data/*Api.js` thin `frappeRequest` wrappers per domain; `utils/frappeError.js` parsing.
- **Views (~86 top-level + feature dirs `finance/`, `procurement/`, `project-detail/`, `records/`, `settings/`, `workforce/`, `workspaces/`, `landings/`).**

## G. Custom doctypes (~80, BuildSuite-owned — by domain)

- **Estimation:** BOQ (+ Group / Item / Sub Item / WP Summary), Assembly (+ Component / Category), Estimate Template (+ Group / Row), Construction Rate Master (+ Rate History), Construction Trade, BuildSuite Tenders (+ Section / Items).
- **Site / PM:** Work Package, Stage Planning (+ Task / Dependency), Task Progress Entry (+ Details), Schedule Snapshot, Scope Change Order (+ Activity), Project Category, Project Settings, Project Tab Visibility, Project Team, Project Assigned, Stage Delay Reason.
- **Subcontract:** Subcontractor, Subcontractor Work Order (+ Line), Subcontractor Bill (+ Line / Tax), Measurement Book (+ Entry), Subcontract Delivery Type.
- **Workforce / Equipment:** Field Employee, Field Attendance (+ Employee), Crew (+ Member), Labour Trade, Labour / Overtime Attendance Register, Machinery (+ Usage / Type).
- **Finance:** Petty Cash Request, Expense Entry (+ Table).
- **Platform:** Persona (+ Role), BuildSuite Workspace (+ Role / Shortcut), Workspace Setting (+ Doctype / Report), BuildSuite Core Settings.

## H. Reports (Query / Script)

`cost_code_variance` · `client_bill_register` · `billing_and_collection` · `receivables_and_payables` · `financial_position` · `subcontractor_position` · `subcontractor_ledger` · `subcontractor_work_order_register` · `subcontractor_bill_register` · `measurement_book_register` · `material_status`.

## I. Workflows & lifecycle

- **Shipped workflows:** Stage Planning Approval, Scope Change Order Approval, Material Request Approval (`fixtures/workflow.json`; states Draft → Pending Approval → Approved/Rejected + Cancel). **Gotcha:** a workflow state's `allow_edit` is a CLIENT-only Desk lock (not server-enforced), and a doc stuck in a state the active workflow doesn't define is locked for everyone. **[undoc · footgun]**
- **Submittable doctypes** carry submit/cancel/amend ptypes (`_SUBMIT_PTYPES`); the generic form renders the Draft → Save/Submit → Cancel/Amend lifecycle.

## J. Dev / ops / testing

- **Install & migrate** — `install.py` (`after_install` / `after_migrate` / `before_migrate`: custom fields, property setters, seeds, letter heads).
- **Patches** — `patches.txt` + `patches/*.py` — the mechanism to reach existing sites (many worked examples).
- **Seeders** — `seed_personas`, `seed_workspaces`, `seed_workspace_reports`, `install.seed_master_data`.
- **Testing** — `tests/base.py` (`BuildSuiteTestCase`); the permission matrix (`TestPersonaCrudMatrix`, `TestResourcePermissionDerivation`); `docs/buildsuite_core_unit_tests.csv`. **Caveats:** `bench run-tests` exit 0 ≠ pass; permission tests can deadlock if run concurrently (they commit `Custom DocPerm`); ~19 known baseline failures (HSN/env).
- **Semgrep** — `.frappe-semgrep-rules/` (keep changes semgrep-clean).
- **e2e** — Cypress broken on this OS (SIGILL) → persona HTTP login + Playwright fallback; `api/cypress_setup.py` provisions persona test users + fixtures.
- **Conventions** — no AI attribution in commits; backticks in `git commit -m` trigger shell substitution (use heredoc); `gh pr edit --base` fails on a Projects GraphQL deprecation (use `gh api -X PATCH`).

## K. Existing docs (don't duplicate)

`README.md` · `DASHBOARD_GAPS.md` · `frontend/DEVELOPER_GUIDE.md` · `frontend/PERMISSIONS.md` · `docs/{boq-implementation, jv-cost-code-actuals, schedule-implementation, multi-company-implementation-plan, subcontractor-bill-implementation-plan, site-execution-reports, insights-feature-options}.md`.

---

## Suggested first documentation targets (mostly [undoc] + non-obvious)

1. **Permissions end-to-end** — persona→role sync, the DocPerm matrix, the SPA payload + `if_owner`→scope (`readScope`/`writeScope`), beneficiary-owner model.
2. **The seams** — `default_company`/multi-company, single-currency policy, custom-fields-as-code, permission-setup-is-install-only + the patch pattern, `as_administrator`, duplicate-DocPerm hygiene.
3. **Dynamic Workflow bridge** (+ the `allow_edit` client-lock footgun).
4. **Generic DocType browser/form** (meta-driven controls + RichTextEditor).
5. **BOQ cost accounting** — Actuals vs Committed, the cost-code pattern.
6. **Print architecture** and **i18n**.
