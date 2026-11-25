# AGENTS.md: building on BuildSuite Core

This is the checklist for any AI agent (or harness) adding a feature, page, report or fix to
**BuildSuite Core**, or building a **custom app on top of it**. Work through it in order. Each item
points to where the rule or the pattern to copy lives. When something here and the code disagree,
the code is right; flag the difference in your PR.

BuildSuite Core is a Frappe/ERPNext v16 app with a Vue SPA served at `/core`
(`frontend/`). Production may run an **older** Frappe/ERPNext than your local bench.

---

## 1. Before you write code

- [ ] **Branch** off the latest `develop` (`git fetch upstream && git checkout -b <type>/<area> upstream/develop`). One branch per area; never stack new work on a merged branch.
- [ ] **Find the prototype screen** for what you're building and read it before designing. Match it exactly: labels, columns, filters, buttons, colours, inline text vs cards. Don't add extras without saying so in the PR.
- [ ] **Find the closest existing feature** in this repo and copy its pattern rather than inventing one (e.g. a new list → `frontend/src/views/procurement/PurchaseReceiptsListView.vue`).
- [ ] **Reproduce the bug first** (for fixes): find the cause, not just the symptom; check whether it was fixed before (`git log -S`).
- [ ] **Decide what "done" looks like** and which persona(s) will use it.

## 2. Data model

- [ ] **ERPNext doctypes:** extend with custom fields in `buildsuite_core/custom_property_list/custom_field.py` (`custom_` prefix, `"module": "BuildSuite Core"`) and property setters in `property_field.py`. Never edit Frappe/ERPNext files.
- [ ] **New doctypes** live under `buildsuite_core/buildsuite_core/doctype/`, module `BuildSuite Core`.
- [ ] **Seeds** (`install.py`, `seed_*`) are **create-if-missing**: never overwrite what an admin has edited.
- [ ] **Existing sites** get data changes through a patch in `patches.txt`. Patches only **add** what's missing; they never reset or remove.
- [ ] **ERPNext gaps:** don't assume ERPNext has a field or status. Check the doctype JSON and the database; derive what's missing from source documents.

## 3. Permissions (two layers: update both)

- [ ] **Server (authoritative):** the DocPerm matrix in `buildsuite_core/permissions/setup.py`. It runs on install only, so add a patch that grants only what's missing on live sites (`_grant_missing_role_perms`), never re-applying the matrix (`_apply_role_perms`).
- [ ] **Screen gates:** add the doctype to `buildsuite_core/permissions/resource_map.py` and the route to `ROUTE_CAPS` in `frontend/src/router/index.js`; gate buttons with `usePermissions()` (`canRead/canCreate/...`).
- [ ] **Reports:** a bespoke report gets a Report anchor in `buildsuite_core/report_access.py` (roles) and its route in `GATED_REPORT_ROUTES`. Links to it check `useReportAccess().canOpenReport(route)`.
- [ ] **Every whitelisted endpoint checks permission first** (`doc.check_permission(...)`), before any business rule or message.
- [ ] **Read lists with `frappe.get_list`** (record-level permissions apply), not `frappe.get_all`, when the data goes back to a user.
- [ ] **Elevate only via** `utils/session.as_administrator()`; never `frappe.set_user` in a request.
- [ ] **Update the persona matrix tests** (`tests/test_permission_matrix.py`) and `frontend/PERMISSIONS.md`.

## 4. Company and project scoping

- [ ] A document's company **follows its project** (`_company_for(project)`), not the user's default.
- [ ] Lists use `company_scope()` server-side / `activeCompanyFilter()` client-side (all companies while multi-company is off, the working company while on). Defaults use `default_company()`. Don't hard-code a company.
- [ ] Project-team scoping follows the persona's **Project visibility**.

## 5. Backend API

- [ ] `@frappe.whitelist()` with **type hints on every argument** (semgrep requires it).
- [ ] User-facing strings in `_()`.
- [ ] **Guard ERPNext/Frappe internal imports** with `try/except ImportError` and a fallback; production is older.
- [ ] Change submitted documents through a proper save (allow-on-submit fields), not `frappe.db.set_value`, so changes are validated and versioned.
- [ ] Don't load unbounded lists: page server-side, or fetch details only for the rows on screen.

## 6. Frontend page

- [ ] Wrap the page in `DeskPage`; lists use `DocTypeListView`.
- [ ] **Columns fetch what they name:** a column needing extra fields lists them (`fields: [...]`); non-field columns get their own key (never reuse a real field's key).
- [ ] **Data derived per row** (e.g. a PO read off lines) is fetched on `@rows-change` for the visible rows only.
- [ ] **Filters:** match the prototype's set; a value that can be `0` goes in `baseFilters`, not `filterValues`.
- [ ] **Deep links** (`?status=`, `?tab=`, `?filters=`) open the list already filtered, and the number on the link equals the list.
- [ ] **People by name, never email:** `useUserNames().userName(id)` / `UserAvatar`. **Projects by name:** `useProjectNames()`.
- [ ] **Every string** through `__()` (`frontend/src/utils/translate.js`); add translations to `buildsuite_core/translations/<lang>.csv`.
- [ ] **Errors** through `parseFrappeError` / `serverErrorMessage` (`frontend/src/utils/frappeError.js`).
- [ ] **Dark mode:** colour tokens (`ink-*`, `brand-*`, …), no hard-coded colours.
- [ ] Add the page to search (`frontend/src/data/search.js`) and its workspace tile.

## 7. Prints

- [ ] Prints are **server-rendered Print Formats** shown through `ServerPrintDocument.vue`; seed them create-if-missing (`print_formats.py`). Customise a layout by seeding a format, not by drawing it in Vue.
- [ ] Company branding comes from the company Letter Head (logo and subtext set in Settings › Company).

## 8. Workflows and notifications

- [ ] Reuse the workflow bridge (`api/workflow.py` + `useWorkflow`); don't build a parallel approval flow.
- [ ] Notifications use Notification Log. Team-scoping is the Workflow "Team-scoped Notifications" checkbox plus the persona setting; don't add per-feature notification logic.

## 9. Tests

- [ ] Tests extend `BuildSuiteTestCase` (`buildsuite_core/tests/base.py`); every test rolls back.
- [ ] Test **as the personas who use it**, not only as Administrator, including one who must be refused.
- [ ] A fix's test **fails without the fix**; check by running it with the fix stashed.
- [ ] Run the module plus the suites your change touches (permissions, the feature's neighbours).

## 10. Quality gates (all must pass)

- [ ] `pre-commit` (ruff, ruff-format, prettier, eslint). No ambiguous Unicode in Python comments or docstrings (`›`, `−`, `×`).
- [ ] `semgrep` clean on what the branch adds (Frappe rules; baseline against `develop`).
- [ ] `cd frontend && yarn build` succeeds.
- [ ] **Check it in the browser** as a real persona: the page, its filters, its numbers and its links.
- [ ] **A fresh site works:** anything seeded or permission-related must also work on a new install, not only after migrate.

## 11. Git and PR

- [ ] Small, focused commits; the message says what changed and why.
- [ ] **No AI attribution** in commits or PRs (no `Co-Authored-By`, no "Generated with").
- [ ] The PR description states the problem, cause, fix, and tests. **No local details** (site names, local record counts, dev-machine issues); reviewers run their own sites.
- [ ] Note anything you didn't do, didn't verify, or that differs from the prototype.

---

## 12. Custom apps on top of BuildSuite Core

- [ ] **Don't fork or edit Core.** Extend through the Extension SDK (`docs/extension-sdk-guide.md`, quickstart `docs/extension-sdk-quickstart.html`): list columns, form fields, views and hooks registered from your app.
- [ ] Server-side, use your own app's `hooks.py` (`doc_events`, `override_whitelisted_methods` only when unavoidable) and your own custom fields (your app's module, its own prefix).
- [ ] **Permissions are additive:** grant your roles what they need; never reduce Core's grants.
- [ ] Follow sections 1–11 for your own code (prototype, permissions, i18n, tests, gates, PR rules).
- [ ] If you need a hook Core doesn't offer, add it to Core in a separate, generic PR rather than working around it.

## Definition of done

The feature matches the prototype; every persona sees and can do exactly what the matrix says; numbers agree with the lists they open; it works on a fresh site and after migrate; tests (including persona tests) and all quality gates pass; the PR is on its own branch with a clean description.
