# BuildSuite Core — Implementation Progress

> **Purpose**: AI session continuity artifact. Load this file at the start of each new session to avoid re-exploring the codebase. Update at every milestone.

---

## App Identity

- **Frappe app name**: `buildsuite_core`
- **App title**: BuildSuite Core
- **Publisher**: Infraholic Innovations Pvt. Ltd
- **Site**: `build.local` (bench at `/Users/yemikudaisi/frappe-bench-16`)
- **Active branch**: `agents/project-view-custom-fields-implementation`
- **App path**: `/Users/yemikudaisi/frappe-bench-16/apps/buildsuite_core.worktrees/agents-project-view-custom-fields-implementation`
- **Module**: `Buildsuite Core` (exact string used in all DocType JSONs and custom fields)

---

## Context Files

| File | Purpose |
|---|---|
| `context/project-field-mapping.md` | Frappeline → ERPNext field mapping, lists exactly 3 custom fields needed + 1 property setter |
| `context/buildsuite-core-demo/` | Vue 3 prototype — ground truth for field shapes, UX flows, seed data |
| `context/buildsuite-core-demo/src/data/seed.js` | Work Package + Stage Planning field shapes from demo |
| `context/implementation-progress.md` | **This file** |

---

## Frontend Integration Execution Tracker

> Source plan: `context/frontend-integration-phase-plan.md`
>
> How to use:
> - Mark each phase checkbox when complete.
> - Fill actual dates and PR/commit references.
> - Do not start seed-data replacement until Phase 9 passes.

### Phase Status Board

- [x] **Phase 0 — Lock Route and Access Model**
  - Status: Completed
  - Target route fixed: `/buildsuite_core`
  - Backend app permission function implemented
  - Date completed: 2026-06-01
  - Reference (PR/commit): commit pending capture

- [x] **Phase 1 — Wire Frappe Route to Frontend Shell**
  - Status: Completed
  - `website_route_rules` added for `/buildsuite_core` + deep path
  - App selector permission hook added in `add_to_apps_screen`
  - Frontend portal shell target created
  - Date completed: 2026-06-01
  - Reference (PR/commit): commit pending capture

- [x] **Phase 2 — Create Backend Boot Contract**
  - Status: Completed
  - `buildsuite_core/www/buildsuite_core.py` created
  - `buildsuite_core/www/buildsuite_core.html` created
  - Boot keys include csrf/site/read-only/lang/direction/timezone
  - `get_context_for_dev` whitelisted and permission-gated
  - HTML now exposes a real `#app` mount target
  - Date completed: 2026-06-01
  - Reference (PR/commit): `3d9b2c2`

- [x] **Phase 3 — Replace Prototype Vite Setup with Frappe-Compatible Build**
  - Status: Completed
  - Frontend moved to app-owned frontend workspace
  - Vite now builds into `buildsuite_core/public/frontend` and emits a manifest
  - Website shell loads built frontend assets from the Vite manifest
  - `frappe-ui` plugin and dev boot parity still pending
  - Date completed: 2026-06-01
  - Reference (PR/commit): `42cbcff`

- [ ] **Phase 4 — Add Dev Boot Parity**
  - Status: In progress
  - DEV calls `get_context_for_dev` before app mount
  - Boot values assigned to `window` in DEV
  - Frontend route guard now checks session via boot/cookie and redirects guests to login for `/app` routes
  - Session handling is centralized in `frontend/src/utils/session.js` and reused by bootstrap + router guard
  - Date completed:
  - Reference (PR/commit):

- [ ] **Phase 5 — Add Frontend Session and Access Guards**
  - Status: Not started
  - Session store based on `user_id` cookie
  - Router guards for anonymous/unauthorized users
  - Backend APIs enforce permission (no UI-only security)
  - Date completed:
  - Reference (PR/commit):

- [ ] **Phase 6 — Keep Seed Data, Add Data Adapter Seam**
  - Status: Not started
  - Data adapter supports local + remote modes
  - Existing local Pinia/localStorage mode still works
  - Date completed:
  - Reference (PR/commit):

- [ ] **Phase 7 — Migrate Data in Safe Vertical Slices**
  - Status: Not started
  - Read-only slice migrated first
  - One bounded CRUD slice migrated second
  - High-risk mutation/upload paths deferred until stable
  - Date completed:
  - Reference (PR/commit):

- [ ] **Phase 8 — CSRF and Upload Hardening**
  - Status: Not started
  - Manual upload/mutation paths send `X-Frappe-CSRF-Token`
  - `frappeRequest` set as default fetcher where applicable
  - Date completed:
  - Reference (PR/commit):

- [ ] **Phase 9 — Validation Gate Before Seed Replacement**
  - Status: Not started
  - Deep-link refresh works
  - Login redirect + return works
  - Unauthorized users blocked in backend and UI
  - Upload works in DEV and PROD with CSRF
  - Date completed:
  - Reference (PR/commit):

### Final Go/No-Go Checklist (Seed Data Replacement)

- [ ] All phases 0–9 completed
- [ ] Validation gate passed and signed off
- [ ] Rollback path documented
- [ ] Team approval to switch from local seed mode to API-backed mode

### Execution Notes Log

| Date | Phase | Change summary | Owner | Link |
|---|---|---|---|---|
| 2026-06-01 | Phase 0-2 | Added `website_route_rules`, app permission hook, initial website boot shell, and whitelisted dev boot endpoint | Copilot | `873d985`, `3d9b2c2` |
| 2026-06-01 | Phase 3 | Copied the Vue prototype into an app-owned `frontend/` workspace, pointed Vite output at app public assets, and wired the website shell to the built asset manifest | Copilot | working tree |
| 2026-06-01 | Phase 4 | Added Vite dev proxy and frontend pre-mount DEV boot hydration from `get_context_for_dev` | Copilot | working tree |

---

## Milestones Completed

### M1-A: Site Execution Workspace (done before this session)
- Custom HTML Block fixture at `buildsuite_core/fixtures/custom_html_block.json`
- Workspace sidebar at `buildsuite_core/buildsuite_core/workspace/buildsuite/buildsuite.json`
- `hooks.py` wires the Custom HTML Block fixture

### M1-B: Project View Custom Fields (this session — 2026-05-29)

**Branch**: `agents/project-view-custom-fields-implementation`

#### Files created / modified

| Path | What |
|---|---|
| `buildsuite_core/fixtures/custom_field.json` | 12 Custom Field records for Project |
| `buildsuite_core/fixtures/property_setter.json` | Extends Project.status with Working + On Hold |
| `buildsuite_core/buildsuite_core/doctype/work_package/` | New Work Package DocType |
| `buildsuite_core/buildsuite_core/doctype/stage_planning/` | New Stage Planning DocType |
| `buildsuite_core/buildsuite_core/doctype/stage_planning_task/` | Child table: Stage Planning Task |
| `buildsuite_core/buildsuite_core/doctype/stage_planning_dependency/` | Child table: Stage Planning Dependency |
| `buildsuite_core/public/js/project.js` | Project form JS — renders related records in tabs |
| `buildsuite_core/hooks.py` | Added Custom Field + Property Setter fixtures; added `doctype_js` |

---

## Schema Reference

### Custom Fields on Project (fixtures)

All use `"module": "Buildsuite Core"`.

| Fieldname | Type | Notes |
|---|---|---|
| `custom_project_id` | Data | reqd, unique, in_list_view, insert_after: project_name |
| `is_group` | Check | default 0, insert_after: company |
| `parent_project` | Link→Project | depends_on: eval:doc.is_group==0, insert_after: is_group |
| `custom_subprojects` | Tab Break | insert_after: actual_end_date |
| `custom_subprojects_html` | HTML | mount point for JS, insert_after: custom_subprojects |
| `custom_work_packages` | Tab Break | insert_after: custom_subprojects_html |
| `custom_work_packages_html` | HTML | mount point for JS |
| `custom_tasks` | Tab Break | insert_after: custom_work_packages_html |
| `custom_tasks_html` | HTML | mount point for JS |
| `custom_stage_planning` | Tab Break | insert_after: custom_tasks_html |
| `custom_stage_planning_html` | HTML | mount point for JS |
| `custom_scope_changes` | Tab Break | insert_after: custom_stage_planning_html |

> **Note**: The 5 Tab Break fields (`custom_subprojects`, `custom_work_packages`, `custom_tasks`, `custom_stage_planning`, `custom_scope_changes`) were created directly in the DB in the previous session and already exist on `build.local`. After `bench migrate` they will be managed by the fixture. The HTML fields are new.

### Property Setter on Project

| Field | Property | New Value |
|---|---|---|
| `Project.status` | options | `Open\nWorking\nCompleted\nOn Hold\nCancelled` |

### Work Package DocType

- **Naming**: `WP-.YYYY.-.###`
- **Module**: `Buildsuite Core`
- **Permissions**: System Manager (full), Projects User (no delete)

| Fieldname | Type | Notes |
|---|---|---|
| `project` | Link→Project | reqd, in_list_view, in_standard_filter |
| `code` | Data | in_list_view |
| `work_package_name` | Data | reqd, in_list_view |
| `status` | Select | Planned/In Progress/On Hold/Completed, default: Planned |
| `progress` | Percent | default: 0 |
| `budget` | Currency | |
| `start_date` | Date | |
| `end_date` | Date | Expected End Date |
| `owner_user` | Link→User | Named `owner_user` to avoid conflict with Frappe built-in `owner` |
| `description` | Text | |

### Stage Planning DocType

- **Naming**: `STG-.YYYY.-.###`
- **Module**: `Buildsuite Core`

| Fieldname | Type | Notes |
|---|---|---|
| `stage_name` | Data | reqd, in_list_view |
| `project` | Link→Project | reqd, in_list_view, in_standard_filter |
| `planned_start` | Date | |
| `planned_end` | Date | |
| `planned_task_count` | Int | default 0 |
| `planned_completion_pct` | Percent | default 0 |
| `description` | Text | |
| `dependencies` | Table→Stage Planning Dependency | |
| `stage_planning_tasks` | Table→Stage Planning Task | |

### Stage Planning Task (Child Table, `istable: 1`)

| Fieldname | Type |
|---|---|
| `task` | Link→Task |
| `planned_start` | Date |
| `planned_end` | Date |
| `planned_qty` | Float |
| `qty_unit` | Data |

### Stage Planning Dependency (Child Table, `istable: 1`)

| Fieldname | Type |
|---|---|
| `stage` | Link→Stage Planning |

---

## Project Form JS (`public/js/project.js`)

Registered in `hooks.py` as `doctype_js = {"Project": "public/js/project.js"}`.

On `refresh` (existing docs only), fetches related records using `frappe.db.get_list()` and injects HTML tables into the HTML mount-point fields:

| Tab field | HTML field | Fetches from |
|---|---|---|
| `custom_subprojects` | `custom_subprojects_html` | `Project` where `parent_project == frm.doc.name` |
| `custom_work_packages` | `custom_work_packages_html` | `Work Package` where `project == frm.doc.name` |
| `custom_tasks` | `custom_tasks_html` | `Task` where `project == frm.doc.name` |
| `custom_stage_planning` | `custom_stage_planning_html` | `Stage Planning` where `project == frm.doc.name` |

Each tab has a **+ Add** button using Frappe's standard `btn btn-primary btn-sm` class with `frappe.utils.icon("add", "xs")` icon. Clicking it opens a **Quick Entry dialog** via `frappe.ui.form.make_quick_entry()` with the parent `project` (or `parent_project` for sub-projects) pre-filled. After saving, the tab list refreshes automatically — no full-page redirect.

### Quick Entry per DocType

| DocType | quick_entry | Fields shown in dialog |
|---|---|---|
| Work Package | `1` (enabled) | project, code, work_package_name, status |
| Stage Planning | `1` (enabled) | stage_name, project, planned_start, planned_end |
| Task | n/a (ERPNext built-in — uses mandatory fields fallback) | subject, project, status |
| Project (sub-project) | n/a (force=true passed) | project_name + mandatory fields |

---

## Development Workflow

### Recommended: symlink worktree as the installed app (zero-merge dev loop)
```bash
cd /Users/yemikudaisi/frappe-bench-16
mv apps/buildsuite_core apps/buildsuite_core.bak   # first time only
ln -s apps/buildsuite_core.worktrees/agents-project-view-custom-fields-implementation apps/buildsuite_core
bench --site build.local migrate
bench build --app buildsuite_core
```
Undo when done: `rm apps/buildsuite_core && mv apps/buildsuite_core.bak apps/buildsuite_core`

### Alternative: rsync (no symlink)
```bash
rsync -av \
  apps/buildsuite_core.worktrees/agents-project-view-custom-fields-implementation/buildsuite_core/ \
  apps/buildsuite_core/buildsuite_core/
bench --site build.local migrate && bench build --app buildsuite_core
```

---

> **Important**: The site `build.local` is installed from the **main** app path at `/apps/buildsuite_core` (on branch `version-16`), NOT from the worktree. The worktree at `/apps/buildsuite_core.worktrees/agents-project-view-custom-fields-implementation` is the development branch.

### To test changes on `build.local`

**Option A — Merge/PR workflow (recommended)**
1. Commit all changes in the worktree branch
2. Create a PR and merge into the target branch
3. In the main app path, `git pull` then run migrate

**Option B — Quick local test (override the installed path)**
```bash
# Temporarily install the worktree version
cd /Users/yemikudaisi/frappe-bench-16
bench --site build.local uninstall-app buildsuite_core
bench install-app buildsuite_core --app-path apps/buildsuite_core.worktrees/agents-project-view-custom-fields-implementation
bench --site build.local migrate
bench build --app buildsuite_core
```

**Option C — Copy only changed files to main app**
```bash
cp -r apps/buildsuite_core.worktrees/agents-project-view-custom-fields-implementation/buildsuite_core/* \
      apps/buildsuite_core/buildsuite_core/
cp apps/buildsuite_core.worktrees/agents-project-view-custom-fields-implementation/buildsuite_core/fixtures/*.json \
   apps/buildsuite_core/buildsuite_core/fixtures/
bench --site build.local migrate
bench build --app buildsuite_core
```

After `bench migrate`:
1. Creates `Work Package`, `Stage Planning`, `Stage Planning Task`, `Stage Planning Dependency` tables
2. Applies Custom Field records from `custom_field.json` (adds `custom_project_id`, `is_group`, `parent_project`, HTML fields)
3. Applies Property Setter — `Project.status` gains **Working** and **On Hold** options

After `bench build`: `public/js/project.js` is included in the Frappe asset bundle.

---

## Known Issues / Migration Notes

- **`KeyError: 'name'` on `bench migrate`** (reported during session): Caused by a Custom Field or Property Setter fixture record missing a `name` field. Fixed in commit `acfe733` — both `custom_field.json` and `property_setter.json` now include explicit `name` values. Migration should succeed after that commit.

---

## Known Constraints / Future Work

- **`custom_scope_changes` tab**: Content not yet implemented — reserved for scope change management (future milestone)
- **Tab ordering conflict**: The 5 Tab Break fields already exist in the DB with different `insert_after` values. After `bench migrate` with fixtures, Frappe will reconcile them to the fixture values. Verify ordering in Customize Form after migration.
- **Work Package → Tasks relationship**: The demo uses a `workPackageId` field on Task. ERPNext's standard Task has no such field. A future custom field `custom_work_package` (Link→Work Package) on Task would be needed for full fidelity. Not in scope for M1-B.
- **Stage Planning Dependency**: The `stage` link currently points to any Stage Planning. A filter to restrict to same-project stages should be added via a `get_query` in a future `stage_planning.js` file.

---

## Next Milestone Candidates (M2)

| Priority | Task |
|---|---|
| High | Implement `custom_scope_changes` tab — define Scope Change DocType and render in tab |
| High | Add `custom_work_package` (Link→Work Package) custom field on Task for full WP→Task traceability |
| Medium | `stage_planning.js` — add `get_query` on dependency `stage` field to restrict to same project |
| Medium | Sub-project guard: prevent more than 1 level of nesting (validate `parent_project` depth in Python) |
| Low | Gantt / timeline view for Stage Planning |

---

## Session Log

| Date | Session | What |
|---|---|---|
| 2026-05-28 | M1-A | Site Execution workspace HTML block + sidebar created |
| 2026-05-29 | M1-B | Custom fields, Work Package DocType, Stage Planning DocType, Project form JS |
| 2026-05-29 | M1-C | Standard Frappe UI: `btn btn-primary btn-sm` add buttons, quick entry dialogs (no redirect), Bootstrap progress bars, `table table-hover` |
