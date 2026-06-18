# BuildSuite Core — Implementation Progress

> **Purpose**: AI session continuity artifact. Load this file at the start of each new session to avoid re-exploring the codebase. Update at every milestone.

---

## App Identity

- **Frappe app name**: `buildsuite_core`
- **App title**: BuildSuite Core
- **Publisher**: Infraholic Innovations Pvt. Ltd
- **Site**: `build.local` (bench at `/Users/yemikudaisi/frappe-bench-16`)
- **Active branch**: `vue`
- **App path**: `/Users/yemikudaisi/frappe-bench-16/apps/buildsuite_core`
- **Module**: `Buildsuite Core` (exact string used in all DocType JSONs and custom fields)
- **Frontend entry URL**: `/client` (was `/buildsuite_core` before 2026-06-05)
- **Vue Router base**: `/client` — all Vue routes are prefixed with this base automatically

---

## Context Files

| File | Purpose |
|---|---|
| `context/project-field-mapping.md` | Frappeline → ERPNext field mapping, lists exactly 3 custom fields needed + 1 property setter |
| `context/buildsuite-core-demo/` | Vue 3 prototype — ground truth for field shapes, UX flows, layout decisions. **Always check this before changing layout/UX** |
| `context/buildsuite-core-demo/src/data/seed.js` | Work Package + Stage Planning field shapes from demo |
| `context/implementation-progress.md` | **This file** — the single ongoing continuity doc |
| ~~`context/prototype-ui-backport-plan.md`~~ | **HISTORICAL** — prototype UI replay (Sessions 96→130). Backport complete; durable facts folded into this file (see "Prototype UI Backport" below). Safe to delete. |
| ~~`context/stage-review-scoping.md`~~ | **HISTORICAL** — Stage Review scoping; built (see Schema + Backport sections). Safe to delete. |
| ~~`context/user-management-scoping.md`~~ | **HISTORICAL** — User management scoping; built (see Backport section). Safe to delete. |

---

## URL and Routing Architecture

### Entry point
- Frappe serves the Vue app at `/client` (file: `buildsuite_core/www/client.py` + `client.html`)
- `website_route_rules` in `hooks.py` routes `/client` and `/client/<path>` to the `client` page
- `add_to_apps_screen` entry uses `"route": "/client"`

### Vue Router
- Base: `createWebHistory('/client')` — Vue Router prepends `/client` to all generated links and strips it when matching
- Route definitions use plain paths without any prefix (e.g. `path: 'projects'` not `path: 'app/projects'`)
- All route `<RouterLink>` and `router.push()` calls use paths WITHOUT `/client` prefix — the router handles it automatically
- The old `/app/` prefix was removed from every route in commit `28fd46b`
- Route guard protects all routes except `name: 'forbidden'`

### Backend boot
- `default_route` in boot payload: `/client`
- Dev boot URL: `/api/method/buildsuite_core.www.client.get_context_for_dev`
- `DEFAULT_ROUTE` constant in `session.js`: `/client`

---

## DocType Field Mappings (Backend ↔ Frontend)

### Task Update (progress entries)

The frontend prototype used different field names than the backend. All three views now use the correct backend names.

| Frontend alias (old prototype) | Backend field (Task Update) | Type |
|---|---|---|
| `progress_pct` | `cumulative_progress` | Float |
| `skilled_labour` | `skilled` | Int |
| `unskilled_labour` | `unskilled` | Int |
| `blocker_flag` | `blocker` | Check (0/1) |
| `blocker_note` | `blocker_detail` | Small Text |
| `entry_date` | `entry_date` | Date ✓ unchanged |
| `task` | `task` | Link→Task ✓ unchanged |
| `narrative` | `narrative` | Small Text ✓ unchanged |
| `weather` | `weather` | Select ✓ unchanged |
| `owner` | `owner` | Standard Frappe field ✓ unchanged |

**Transform convention**: All three Task Update views use a `transform()` in adapter calls that maps backend snake_case → camelCase for the view layer (`cumulative_progress` → `progressPct`, etc.). The backend mutation payloads (create/update) use the backend field names directly.

### Task (for reference)

| Frontend alias | Backend field |
|---|---|
| `id` | `name` |
| `name` | `subject` |
| `projectId` | `project` |
| `workPackageId` | `work_package` |
| `assignee` | `owner` |
| `startDate` | `exp_start_date` |
| `endDate` | `exp_end_date` |
| `task_type` | `type` |

---

## Utility Function Registry

> Rule for all future work: whenever a new reusable utility/helper is added, append it here with purpose and consumers.

| Utility | Location | Purpose | Used by |
|---|---|---|---|
| `getCookie(name)` | `frontend/src/utils/session.js` | Read cookie value by name for session bootstrap | `syncSessionFromCookie` |
| `syncSessionFromCookie()` | `frontend/src/utils/session.js` | Populate `window.session_user` from `user_id` cookie | `main.js`, `getSessionUser`, `applyBootToWindow` |
| `getSessionUser()` | `frontend/src/utils/session.js` | Canonical current session user getter | `isAuthenticated`, `getAccessContext` |
| `isAuthenticated()` | `frontend/src/utils/session.js` | Auth state check (`session_user != Guest`) | `router/index.js`, `getAccessContext` fallback |
| `getRouteBase()` | `frontend/src/utils/session.js` | Resolve app base route (`/client`) | `router/index.js`, `getLoginUrl` |
| `getFrappeHost()` | `frontend/src/utils/session.js` | Resolve dev frappe host for redirects/APIs | `getLoginUrl` |
| `getLoginUrl(path)` | `frontend/src/utils/session.js` | Build login URL with redirect-to anchored to app base | `router/index.js` |
| `applyBootToWindow(boot)` | `frontend/src/utils/session.js` | Hydrate boot payload into `window` and DOM lang/dir | `main.js` |
| `getAccessContext()` | `frontend/src/utils/session.js` | Fetch + cache backend access status (`allowed`, `reason`) | `router/index.js` |
| `isAccessContextFresh(maxAgeMs)` | `frontend/src/utils/session.js` | Validate whether cached backend access status is still usable | `getAccessContext` |
| `clearAccessContextCache()` | `frontend/src/utils/session.js` | Reset cached access-context promise | Reserved for future re-check flows |
| `toDateInputValue(value)` | `frontend/src/utils/dateInput.js` | Normalize date-like values to native date-input format (`YYYY-MM-DD`) | `ProjectDetailView.vue` edit modal, `TaskProgressEntryDetailView.vue` |
| `useProjectDetailListFilters({ ... })` | `frontend/src/views/project-detail/useProjectDetailListFilters.js` | Centralize Project Detail list-search state, per-tab filtering, and derived list stats | `ProjectDetailView.vue` |
| `PROJECT_REPORTS`, `*_COLS` constants | `frontend/src/views/project-detail/projectDetailConfig.js` | Canonical report tile metadata and DeskList column definitions for Project Detail tabs | `ProjectDetailView.vue` |
| `toArray(data)` | Inline helper in several views | Guard frappe-ui resource `.data` against `null` before calling array methods. Pattern: `if (Array.isArray(data)) return data; if (Array.isArray(data?.value)) return data.value; return []` | `TaskProgressEntriesView.vue`, `NewTaskProgressEntryView.vue`, `TaskProgressEntryDetailView.vue` |
| `hydrateFromRuntime()` | `frontend/src/stores/session.js` | Sync session user/authenticated state from runtime cookie globals | `refreshAccess`, `bootstrapSession` |
| `refreshAccess(options)` | `frontend/src/stores/session.js` | Pull backend access context and normalize auth/access store state | `bootstrapSession`, `ensureAccess` |
| `bootstrapSession()` | `frontend/src/stores/session.js` | One-time session/access initialization before route handling | `main.js`, `ensureAccess` |
| `ensureAccess(options)` | `frontend/src/stores/session.js` | Central guard entrypoint that initializes then revalidates access | `router/index.js` |
| `recheckAccess()` | `frontend/src/stores/session.js` | Force-clear access cache and re-evaluate backend authorization | `AccessDeniedView.vue` |
| `resetSession()` | `frontend/src/stores/session.js` | Clear auth/access state and cached access context | Reserved for logout/session-expiry flows |
| `createLocalDataAdapter(store)` | `frontend/src/data/adapters/localDataAdapter.js` | Adapter implementation over current Pinia local state for phased migration | `createDataAdapter` |
| `createRemoteDataAdapter()` | `frontend/src/data/adapters/remoteDataAdapter.js` | Generic remote DocType adapter contract (`list/read/create/update/remove/linkSearch`) over frappe-ui list + document resources. `read()` uses `frappe.client.get` so child tables (e.g. Stage Planning tasks/deps) are included. | `createDataAdapter`, filter/link/read slices |
| `createDataAdapter(store, mode)` | `frontend/src/data/adapters/index.js` | Adapter factory for local/remote mode switching during migration | All migrated views |
| `useDocTypeList(doctype, options)` | `frontend/src/composables/useDocTypeList.js` | Generic Frappe list-resource wrapper for read-only DocType list calls | `createRemoteDataAdapter`, `DocTypeListView.vue`, `ProjectsView.vue` |
| `DocTypeListView` | `frontend/src/components/doctype/DocTypeListView.vue` | Reusable meta-driven list shell (`doctype` + ordered `fieldOrder`) with default sort handling and reload-on-resolved-columns | `ProjectsView.vue`, `WorkPackagesView.vue`, `TasksView.vue` |
| `DeskLinkPicker` | `frontend/src/components/desk/DeskLinkPicker.vue` | Generic inline Link/autocomplete backed by `useDocTypeList` with server-side search. **Use for all Link-field inputs and list filters** (replaces DeskSelect for DocType-backed fields) | `ProjectsView.vue`, `TaskProgressEntriesView.vue`, `NewTaskProgressEntryView.vue`, form modals |
| `FileUploadHandler` | Via alias `frappe-ui-file-upload-handler` → `node_modules/frappe-ui/src/utils/fileUploadHandler.ts` | XHR-based file upload class from frappe-ui. Use this instead of `FileUploader` component (which requires unregistered `Button` global). Handles CSRF, progress, FormData. | `TaskProgressEntryDetailView.vue` |
| `stripHtml(html)` | `frontend/src/utils/frappeError.js` (internal) | Strip HTML tags and decode entities from Frappe server messages using DOM `createElement('div')`. Applied to all message paths in `parseFrappeError` — Frappe wraps field/doc names in `<strong><a href="/desk/...">` which point to ERPNext, not the Vue app. | `parseFrappeError` internals |
| `parseFrappeError(err)` | `frontend/src/utils/frappeError.js` | Parse any Frappe HTTP error response into `{ summary, fieldErrors }`. Checks `err.messages` (frappe-ui pre-parsed array) first, then falls back to `_server_messages`. Extracts field names from `MandatoryError` traceback. All message strings are HTML-stripped before returning. | `useFormErrors`, direct imports in detail views |
| `useFormErrors(backendToFormField)` | `frontend/src/composables/useFormErrors.js` | Form error state composable. Returns `{ errors, applyServerErrors(err), setErrors(e), clearError(key), reset() }`. Pass a `{ backendFieldName: formKey }` map once; use `applyServerErrors` in catch blocks and `setErrors` in `validate()`. Replaces `const errors = ref({})` + manual field mapping in every form view. | `NewProjectView`, `NewTaskView`, `NewWorkPackageView`, `WorkPackageDetailView`, `NewTaskProgressEntryView` |
| `_has_app_permission(log_denial)` | `buildsuite_core/api/permission.py` | Internal permission check with optional logging | `has_app_permission`, `get_access_context` |
| `get_access_context()` | `buildsuite_core/api/permission.py` | Whitelisted access-status API for frontend route guards | `frontend/src/utils/session.js#getAccessContext` |
| `setup_project_permissions()` | `buildsuite_core/permissions/setup.py` | Idempotent seed: ensures the 11 BuildSuite roles exist + writes the per-role Project Custom DocPerm matrix (permlevel 0). Source of truth = `PROJECT_ROLE_PERMS` dict | `install.after_migrate`, `install.after_install` |
| `PROJECT_ROLE_PERMS`, `BUILDSUITE_ROLES`, `PERSONA_TO_ROLE` | `buildsuite_core/permissions/setup.py` | Canonical role→CRUD matrix; tuple of all BuildSuite role names; persona-Select-value→role-name map (mirrors roles.js) | `setup`, `api/permission.py` (`ALLOWED_ROLES`), `utils/user.py` |
| `get_project_permission_query(user)` | `buildsuite_core/permissions/project.py` | `permission_query_conditions` hook for Project — returns SQL scoping list to teamed projects, or `""` when unscoped | `hooks.permission_query_conditions["Project"]` |
| `has_project_permission(doc, ptype, user)` | `buildsuite_core/permissions/project.py` | `has_permission` DENY-gate for a single Project — True unless scoped + not a team member | `hooks.has_permission["Project"]` |
| `_is_scoped(user)` / `_has_any_membership(user)` | `buildsuite_core/permissions/project.py` | Resolve whether a user's Project visibility is team-restricted (bucket logic); membership existence check on `Project Team` | `get_project_permission_query`, `has_project_permission` |
| `sync_persona_roles(doc, method)` | `buildsuite_core/utils/user.py` | `User` `validate` hook — keeps the user's BuildSuite role aligned with their `persona` field (grants mapped role, strips stale BuildSuite roles; never revokes System Manager) | `hooks.doc_events["User"]["validate"]` |
| `getDeskUrl()` | `frontend/src/utils/session.js` | URL of the real Frappe/ERPNext desk (`/app` in prod, dev frappe host in dev) | `DeskShell.vue` app dropdown "Go to Desktop" |
| `logout()` | `frontend/src/utils/session.js` | Best-effort POST to Frappe `/api/method/logout` then full-page redirect to `/login` | `DeskShell.vue` app dropdown "Logout" |

---

## Frontend Integration Execution Tracker

### Phase Status Board

- [x] **Phase 0 — Lock Route and Access Model** — Completed 2026-06-01
- [x] **Phase 1 — Wire Frappe Route to Frontend Shell** — Completed 2026-06-01
- [x] **Phase 2 — Create Backend Boot Contract** — Completed 2026-06-01 (`3d9b2c2`)
- [x] **Phase 3 — Replace Prototype Vite Setup with Frappe-Compatible Build** — Completed 2026-06-01 (`42cbcff`)
- [x] **Phase 4 — Add Dev Boot Parity** — Completed 2026-06-01 (`b2f750e`)
- [x] **Phase 5 — Add Frontend Session and Access Guards** — Completed 2026-06-01
- [x] **Phase 6 — Keep Seed Data, Add Data Adapter Seam** — Completed 2026-06-02

- [ ] **Phase 7 — Migrate Data in Safe Vertical Slices**
  - Status: In progress
  - **Migrated views** (adapter-backed, working against real backend):
    - `ProjectsView` — generic list shell + DeskLinkPicker company filter
    - `WorkPackagesView` — generic list shell + DeskLinkPicker project filter
    - `TasksView` — generic list shell with DeskLinkPicker filters
    - `ProjectDetailView` — adapter.read + adapter.list for all tabs; adapter.update/remove for CRUD
    - `TaskDetailView` — adapter.read/update/remove; Task Update entries via adapter.list
    - `TaskProgressEntriesView` — adapter.list('Task Update') with transform
    - `TaskProgressEntryDetailView` — adapter.read/update/remove('Task Update') + adapter.list('File') for attachments
    - `NewTaskProgressEntryView` — adapter.create('Task Update') + DeskLinkPicker task picker
    - `StagePlanningsView` — DocTypeListView shell + DeskLinkPicker project filter + date-range baseFilters
    - `StagePlanningDetailView` — adapter read/update/remove + StageTaskPicker modal + edit modal
  - **Remaining to close Phase 7**: NewTaskView, NewProjectView
  - Reference: `6e188f7`, `5d95fcc`, `062c5e5`, `c50f8c8`, `37d27e9`, `c8b6224`, `845f567`, `cccc79e`, `28fd46b`, `70cfcb6`

- [ ] **Phase 8 — CSRF and Upload Hardening**
  - Status: In progress
  - File upload via `FileUploadHandler` XHR is live for Task Update attachments (uses `window.csrf_token`)
  - Standard adapter mutations (create/update/remove) go through frappe-ui resources which handle CSRF
  - Remaining: validate PROD upload flow end-to-end

- [ ] **Phase 9 — Validation Gate Before Seed Replacement**
  - Status: Not started

### Current Position Snapshot (2026-06-05)

- Phases 0–6: complete
- Phase 7: in progress — 8 views fully migrated to adapter, ~6 remaining
- Phase 8: in progress — file upload working, full PROD validation pending
- Phase 9: not started

**What works against the real Frappe backend today:**
- Projects list, create, read, update, delete
- Work Packages list, create, read, update, delete
- Tasks list, read, update, delete (create via TaskDetailView progress modal)
- Project detail page — all tabs loading from backend
- Task detail page — full CRUD + progress entry filing
- Task Progress Entry list, detail, create (all against Task Update doctype)
- Task Update file attachments (upload, list, delete via Frappe File doctype)

---

## CRUD Patterns and Lessons Learned

### Stable patterns (copy from these)

**adapter.read() with transform:**
```js
const taskResource = ref(null)
function loadTaskResource(id) {
  if (!id) { taskResource.value = null; return }
  taskResource.value = adapter.read('Task', id, {
    nameField: 'name',
    fields: ['name', 'subject', 'project', ...],
    cache: `buildsuite-task-detail:${id}`,
    transform(rows) {
      return rows.map(row => ({
        id: row?.name || '',
        name: row?.subject || row?.name || '',
        projectId: row?.project || '',
        // ... map every backend field to frontend alias
      }))
    },
  })
}
watch(() => props.id, loadTaskResource, { immediate: true })
const task = computed(() => {
  const backendTask = firstResourceRow(taskResource.value)
  if (backendTask) return backendTask
  return store.taskById(props.id) || null  // local fallback
})
```

**toArray() guard — ALWAYS use when accessing resource.data for array operations:**
```js
// frappe-ui initializes resource.data to null, not []. Without this, .filter()/.length throws.
function toArray(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.value)) return data.value
  return []
}
const items = computed(() => toArray(someResource.data))
```

**File upload (use FileUploadHandler, NOT frappe-ui FileUploader component):**
```js
import FileUploadHandler from 'frappe-ui-file-upload-handler'
// FileUploader component requires <Button> globally registered — don't use it.
const handler = new FileUploadHandler()
await handler.upload(file, { doctype: 'Task Update', docname: props.id, private: true })
```

**Fetching attachments from Frappe File doctype:**
```js
attachmentsResource.value = adapter.list('File', {
  filters: [['attached_to_doctype', '=', 'Task Update'], ['attached_to_name', '=', entryId]],
  fields: ['name', 'file_name', 'file_url', 'file_size', 'is_private', 'creation', 'owner'],
  orderBy: 'creation desc',
})
```

**DeskLinkPicker for Link/filter fields (NOT DeskSelect):**
```html
<DeskLinkPicker
  v-model="form.taskId"
  doctype="Task"
  label-field="subject"
  value-field="name"
  :search-fields="['subject', 'name']"
  :page-length="20"
  placeholder="— Select task —"
/>
```

### Repeated failure patterns

1. **Resource data is null on first render** — frappe-ui inits `.data` to `null`. Never call `.filter()`, `.length`, or `.find()` directly on `resource.data`. Always use `toArray()` or check `Array.isArray()` first.

2. **Field-name drift** — prototype uses camelCase aliases; backend uses snake_case. Add a `transform()` to every adapter call. Failing to do this causes silent write no-ops or read errors.

3. **DeskSelect for backend Link fields** — DeskSelect with a locally-fetched list breaks in remote mode because the list may not contain the current value. Use DeskLinkPicker for any field that links to a Frappe DocType.

4. **frappe-ui FileUploader component needs global Button** — the component's fallback slot uses `<Button>` which must be globally registered. Use `FileUploadHandler` class directly instead.

5. **Sub-path imports of frappe-ui blocked in production build** — e.g. `import X from 'frappe-ui/src/utils/X'` fails in Rollup (not in exports map). Add an alias in `vite.config.js` following the existing `frappe-ui-*` pattern.

6. **Modal z-index below sidebar** — DeskShell sidebar is `z-50`. All modal backdrops must be `z-[60]` or higher.

7. **Date inputs need YYYY-MM-DD** — use `toDateInputValue()` from `frontend/src/utils/dateInput.js` before binding to `<input type="date">`.

### Acceptance checks per CRUD slice

1. Create: record persists and route navigation resolves the created record id
2. Read: detail form binds all fields including dates and linked values
3. Update: changed values persist in remote mode
4. Delete: confirms (ConfirmDialog), removes, routes back to parent list with toast
5. List: sort/filter controls work; count shown in table footer

---

## Vite Config Notes (`frontend/vite.config.js`)

Key non-obvious settings:

- `optimizeDeps.exclude: ['frappe-ui']` — frappe-ui is excluded from esbuild pre-bundling so Vite's plugin pipeline handles its lucide virtual modules
- `optimizeDeps.include: ['debug']` — `debug` is a CJS-only package pulled transitively by frappe-ui's TextEditor (tiptap). Must be pre-bundled explicitly or it crashes the dev server with a missing default export
- `frappe-ui-file-upload-handler` alias — points to `node_modules/frappe-ui/src/utils/fileUploadHandler.ts` so it can be imported across the exports-map restriction
- `feather-icons` alias — routes through a shim at `src/shims/feather-icons-default.js` because frappe-ui imports feather-icons as a default export but modern ESM only exposes named exports

---

## ProjectDetailView Tab Architecture

`ProjectDetailView.vue` has been split — tabs with substantial content are extracted into components under `frontend/src/views/project-detail/`:

| File | Responsibility |
|---|---|
| `tabs/OverviewTab.vue` | Summary strip (4 KPI cards) + About/Reports/PM/Details sidebar layout |
| `tabs/AttachmentsTab.vue` | File list + upload via `<input>` + delete (uses local store blob URLs) |
| `tabs/TeamTab.vue` | Team member list with PM badge and remove buttons |
| `tabs/ActivityTab.vue` | Project created entry (stub feed) |
| `ProjectEditModal.vue` | Edit project form (DeskLinkPicker fields for customer/type/company/PM) |
| `ProjectTeamMemberModal.vue` | Add team member picker modal |
| `projectDetailConfig.js` | `BOQ_COLS`, `TASK_COLS`, `WP_COLS`, `SCO_COLS`, `TEAM_COLS`, `SUB_COLS`, `PROJECT_REPORTS` column/tile definitions |
| `useProjectDetailListFilters.js` | All filter state, computed filtered lists, task stats for the inline tabs |

Inline tabs (still in `ProjectDetailView.vue`): Subprojects, Work Packages, Tasks, Stage Planning, BOQ, SCOs.

---

## Dark Mode Implementation Notes

Dark mode is driven by `html.dark` class (set by `store.theme` → `App.vue`). Key rules in `frontend/src/style.css`:

- `html.dark .bg-white` → `#242424` (card/modal surface)
- `html.dark body` → `#1A1A1A` (page canvas)
- `html.dark .desk-input` → `background: #242424; border: #333333; color: #F5F5F5`
- `html.dark .text-ink-900` → `#F5F5F5`

**Known dark-mode pitfalls:**
- `html.dark .desk-input` is in `@layer components`. If it doesn't apply, add `dark:bg-[#242424]` etc. directly as Tailwind utility classes on the element (lands in `@layer utilities` which has higher priority).
- DeskLinkPicker dropdown header had a hardcoded `!important` white background — overridden in `DeskLinkPicker.vue` `<style>` with a matching `html.dark ... !important` rule.
- `from-success-50` and similar gradient-from classes have no dark override in the default palette — add them to `style.css` if used in gradient headers.

---

## Development Workflow

### Run the frontend dev server
```bash
cd /Users/yemikudaisi/frappe-bench-16/apps/buildsuite_core/frontend
npm run dev
# Opens at http://localhost:5173
# Proxies /api/* to http://localhost:8001 (Frappe dev server)
```

### Build
```bash
npm run build
# Outputs to buildsuite_core/public/frontend/
```

### Test against Frappe site
Access via `http://build.local/client` after `bench start`.

### Key env
- `VITE_FRAPPE_HOST` — override Frappe host for the dev proxy (default `http://localhost:8001`)
- `VITE_DATA_MODE` — `remote` (default) or `local` to switch adapter mode

---

## Schema Reference

### Task Update DocType

Custom DocType in `buildsuite_core` module.

| Fieldname | Fieldtype | Required | Notes |
|---|---|---|---|
| `task` | Link→Task | Yes | |
| `entry_date` | Date | Yes | |
| `cumulative_progress` | Float | Yes | precision: 0 |
| `narrative` | Small Text | No | |
| `skilled` | Int | No | Skilled labour count |
| `unskilled` | Int | No | Unskilled labour count |
| `weather` | Select | No | Clear/Rainy/Hot/Cold/Storm |
| `blocker` | Check | No | default: 0 |
| `blocker_detail` | Small Text | No | mandatory_depends_on: `eval:doc.blocker==1` |

Standard Frappe fields also available: `name`, `owner`, `creation`, `modified`.

### Work Package DocType

| Fieldname | Type | Notes |
|---|---|---|
| `project` | Link→Project | reqd, in_list_view |
| `code` | Data | in_list_view |
| `work_package_name` | Data | reqd, in_list_view |
| `status` | Select | Planned/In Progress/On Hold/Completed |
| `progress` | Percent | default: 0 |
| `budget` | Currency | |
| `start_date` | Date | |
| `end_date` | Date | |
| ~~`owner_user`~~ | ~~Link→User~~ | **Do not request this field.** Causes `DataError: Field not permitted in query`. Use the Frappe built-in `owner` field (tracks creator) for read surfaces instead. |
| `description` | Text | |

### Stage Planning DocType (approval workflow fields)

Approval lifecycle runs on the Frappe-native **Stage Planning Approval** workflow (`workflow_state` Link; states Draft → Pending Approval → Approved / Rejected / Cancelled). Transition roles + own-submit conditions are rewired to BuildSuite roles by `setup_stage_planning_workflow()` (see Backend Permissions Architecture). Notable custom fields:

| Fieldname | Type | Notes |
|---|---|---|
| `workflow_state` | Link→Workflow State | Draft default; drives the action bar in `StagePlanningDetailView` |
| `reject_reason` | Small Text | reqd on Rejected; persisted by `reject_stage_planning(name, reason)` **before** `apply_workflow` (apply_workflow reloads from DB, so an unsaved value is lost). `Rejected → Revise` removed — Rejected is terminal. |
| `stage_planning_tasks` | Table→Stage Planning Task | child rows: `task`, `planned_start`, `planned_end`, `planned_qty` (default 100), `qty_unit` (`%`) |
| `delay_reasons` | Table→Stage Delay Reason | append-only Delay Log (below) |

> Superseded vs prototype: `approval_required_role` on Project is **not** used (production drives approver gating via Frappe Workflow transition roles). The prototype's `stage.activity[]` feed is **deferred** (would use Frappe's native document timeline).

### Stage Delay Reason DocType (child, `istable: 1`)

ERPNext-style Delay Log row, embedded on Stage Planning via `delay_reasons`. Appended by the whitelisted `add_stage_delay_reason(stage, reason, responsible_party, days_delayed=None, note=None)` (gated on read/project-membership — logging a delay is NOT a stage edit, so it works on Approved stages without revising; saved with `ignore_permissions`).

| Fieldname | Type | Notes |
|---|---|---|
| `reason` | Data | reqd; frontend offers presets + free text (stored as text) |
| `responsible_party` | Select | Own / Subcontractor / Client / External / Consultant |
| `days_delayed` | Int | optional (blank = TBD / ongoing) |
| `note` | Small Text | optional |
| `logged_by` | Link→User | read-only, stamped on insert |
| `logged_on` | Datetime | read-only, stamped on insert |

`StageReviewView.vue` (Vue-styled dashboard, route `/stage-plannings/:id/review`) renders KPI strip + Task-progress (overlaid bar + planned tick) + Delay-reasons + Labour-movement. **Materials** section omitted (no BOQ doctypes until M2). `isStageDelayed` is frontend-computed. **Labour movement** sums every Task Update for the stage's tasks (the planned-window filter was dropped — real windows rarely bracket entry dates; see 2026-06-12 log).

### Custom Fields on Project (fixtures)

| Fieldname | Type | Notes |
|---|---|---|
| `custom_project_id` | Data | reqd, unique, in_list_view |
| `is_group` | Check | default 0 |
| `parent_project` | Link→Project | depends_on: eval:doc.is_group==0 |
| `custom_team_members` | Table→Project Team | Team membership grid (drives record-level permissions) |

> Custom fields are NOT JSON fixtures — they are created on every `bench migrate` via `after_migrate` → `create_custom_fields(CUSTOM_FIELD)`. Source: `buildsuite_core/custom_property_list/custom_field.py`.

### Project Team DocType (child table)

`istable: 1`, name `Project Team`, used by `Project.custom_team_members`.

| Fieldname | Fieldtype | Notes |
|---|---|---|
| `user` | Link→User | The team member |
| `full_name` | Data | `fetch_from: user.full_name` |

### Custom Field on User (fixture)

| Fieldname | Type | Notes |
|---|---|---|
| `persona` | Select | 12 options matching `roles.js` `name` fields (Director / Owner … BuildSuite Administrator). Drives auto role assignment via `sync_persona_roles`. Option strings MUST match `PERSONA_TO_ROLE` keys. |

---

## Backend Permissions Architecture (record-level access)

Team-membership scoping layered on top of Frappe role DocPerms. Covers **Project, Task, Work Package, Task Progress Entry, Stage Planning** (all 5 done 2026-06-11).

### The model (locked decisions)
- **Base CRUD = role DocPerms.** Each BuildSuite role gets a Custom DocPerm at permlevel 0 on each doctype per its spec matrix. Seeded idempotently by `setup_record_permissions()` on every migrate (one `setup_*_permissions` per doctype + `_apply_role_perms` generic).
- **Record set = team membership.** Per-doctype `permission_query_conditions` (lists/reports) + `has_permission` (single-doc DENY gate). Project keys off membership in `Project.custom_team_members` (the `Project Team` child table). **Everything else inherits Project scoping** — visible iff the parent project is teamed. Project link path per doctype: Task/WP/Stage Planning have `project`; Task Progress Entry indirects via `task` → `Task.project`.
- **Membership is binary presence** — a user is on a project's team or not. No per-project `team_role`.
- **Own-scope rules (enforced in `has_*_permission`, since DocPerm grants blanket write):**
  - **Task** — Site Engineer edit/delete own-**created** (`owner`); Foreman own-created **OR assigned** (`_assign`).
  - **Task Progress Entry** — SE & Foreman edit own-created any time; **delete own only within 24h** of `creation`. Procurement Officer + Store Keeper have **no DocPerm (hidden)**.
  - **Stage Planning** — SE & Foreman edit/delete own-created, **only while `workflow_state` ∈ {Draft, Rejected}** (locked once submitted). Procurement + Store Keeper hidden.
  - Full-write roles (Director, PM, BS-Admin, System Manager) bypass all own-scope checks.
- **Stage Planning workflow** — the Submit/Approve/Reject/Revise/Cancel actions live on the **Stage Planning Approval** workflow, rewired to BuildSuite roles by `setup_stage_planning_workflow()`: SE/Foreman can **Submit their own** draft (transition condition `doc.owner == frappe.session.user`); full roles do everything. State `allow_edit` is set to the no-DocPerm marker role **`BuildSuite Project User`** (mandatory field) so the workflow never blocks editing — DocPerm + `has_permission` is the real gate.
- **Persona → role is automatic.** A `User.validate` hook (`sync_persona_roles`) grants the BuildSuite role mapped from the `persona` Select field, plus the `BuildSuite Project User` marker role.

### Scoping buckets (most-permissive wins: EXEMPT > FLIP > TEAM-ONLY)
- **EXEMPT (never scoped):** `BuildSuite Director`, `BuildSuite HR Manager`, and the `Administrator` user. HR's read-only is enforced by DocPerm, not scoping.
- **FLIP (unrestricted-until-teamed):** `BuildSuite PM`, `System Manager`, `BuildSuite Administrator` — see all projects when on **zero** teams; scoped to teamed projects once a member of any team.
- **TEAM-ONLY (always scoped):** Estimator, QS, Site Engineer, Foreman, Procurement Officer, Store Keeper, Accountant. Zero memberships = zero projects.

### Key Frappe mechanics (verified against framework source)
- `permission_query_conditions(user)` returns an SQL `WHERE` string (ANDed with others; `""` = no filter). Filters list/report/count.
- `has_permission(doc, ptype, user)` is a **DENY gate** — returning `True` never grants beyond DocPerm; returning `False` denies. So base rights come from DocPerm; the hook only narrows.
- Universal admin check is `user == "Administrator"`. **System Manager is NOT a bypass** here (it follows the FLIP rule per spec).
- DocPerms on ERPNext/custom doctypes are stored as **Custom DocPerm** rows — they live in the DB, re-applied each migrate; they do NOT travel as code fixtures. "Hidden" roles (Procurement/Store Keeper on TPE & Stage) simply get no row.

### Files
| File | Role |
|---|---|
| `buildsuite_core/permissions/setup.py` | 5 role-perm matrices (`PROJECT_/TASK_/WORK_PACKAGE_/TASK_PROGRESS_ENTRY_/STAGE_PLANNING_ROLE_PERMS`), `BUILDSUITE_ROLES`, `PERSONA_TO_ROLE`, `WORKFLOW_EDITOR_ROLE`, `setup_record_permissions()` (per-doctype `setup_*` + `_apply_role_perms`), `setup_stage_planning_workflow()` |
| `buildsuite_core/permissions/project.py` | scoping buckets (`_is_scoped`/`_has_any_membership`/`_is_project_member` shared) + `get_project_permission_query` / `has_project_permission` |
| `buildsuite_core/permissions/task.py` | `get_task_permission_query` / `has_task_permission` + `_can_modify_task` (SE created-by, Foreman assignee/creator) |
| `buildsuite_core/permissions/work_package.py` | scoping only (read-only roles, no own-scope) |
| `buildsuite_core/permissions/task_progress_entry.py` | scoping via `task→project`; own-edit + delete-within-24h (`_within_delete_window`) |
| `buildsuite_core/permissions/stage_planning.py` | scoping + own-scope with `workflow_state ∈ {Draft,Rejected}` guard |
| `buildsuite_core/utils/user.py` | `sync_persona_roles` (persona→role + `BuildSuite Project User` marker, on `User.validate`) |
| `buildsuite_core/api/permission.py` | `ALLOWED_ROLES` = `{System Manager} ∪ BUILDSUITE_ROLES` (app-entry gate) |
| `buildsuite_core/hooks.py` | wires `permission_query_conditions` + `has_permission` for all 5 doctypes, and `User.validate` |

### Persona → role sync rules (`sync_persona_roles`)
- Runs on `validate` (covers create + edit; mutates `doc.roles` in place — atomic, no recursive save). Delete needs no handler (Has Role rows cascade).
- Grants the persona's mapped role **+ the `BuildSuite Project User` marker role**; strips other managed roles so persona stays the single source of truth.
- **System Manager is grant-only — never auto-revoked** (so changing persona can't strip platform-admin access). `Administrator`/`Guest` skipped.
- `persona = "System Manager (Admin)"` → grants native `System Manager` (not a BuildSuite role).

### Verification (done, against live `build.local`)
- Migrate seeds all 5 DocPerm matrices (Project/Task 11 rows; WP 11; TPE 9 — Procurement/Store hidden; Stage 9 — same) — all match spec exactly. Stage workflow rewired (allow_edit=marker role; SE/Foreman submit-own condition).
- Project/Task E2E: scoping buckets, SE created-by, Foreman assignee/creator, PM flip, HR read-all, Administrator unaffected — all pass.
- WP/TPE/Stage E2E: read-only scoping; SE TPE delete own <24h ✓ / >24h denied ✓; Procurement hidden on TPE & Stage; HR read-all on TPE; SE Stage edit in Draft ✓ but locked once Approved ✓; SE can Submit own draft via workflow condition ✓.
- Confirmed Frappe forces `owner = session.user` on insert — so `owner` is reliably the creator (the frontend's `owner: form.assignee` is silently a no-op, matching the chosen owner=creator / `_assign`=assignee model).
- Persona sync confirmed incl. `BuildSuite Project User` granted alongside the persona role.

---

## Known Constraints / Future Work

- **Record-level perms cover the 5 core doctypes** (Project, Task, Work Package, Task Progress Entry, Stage Planning). Other doctypes (BOQ, SCO, Subcontract, Workforce…) still use default perms — out of scope until those modules land.
- **HR labour-fields-only on TPE deferred**: spec wants HR to read only labour fields (permlevel 1 hiding narrative/weather/blocker/attachments). Shipped as plain read-all on TPE for now; field-level permlevel perms are a future pass.
- **Stage Planning workflow uses a marker role for `allow_edit`**: `BuildSuite Project User` (no DocPerms) is granted to every persona purely so the workflow's mandatory single-role `allow_edit` doesn't block editing. If you re-export the workflow fixture, note `setup_stage_planning_workflow()` re-applies BuildSuite roles in `after_migrate` (runs after the fixture import, so it wins).
- **Task assignee = Frappe-native `_assign`** (ToDo assignment), NOT a custom field. The frontend's `owner: form.assignee` is a no-op (Frappe overwrites owner with the creator). Foreman's "assigned" rule reads `_assign`; the frontend should be rewired to use Frappe assignment so assignees are actually recorded.
- **Persona field is the single source of truth for BuildSuite roles** — manual edits to a user's BuildSuite roles in Desk get overwritten on next save if they don't match the persona. (System Manager is exempt — never auto-revoked.)
- **NewTaskView / NewProjectView**: Still use store-based task/project creation. Not yet migrated to adapter.
- **WorkPackageDetailView**: Partially migrated (read via adapter, mutations still store-based).
- **Task Update attachments in NewTaskProgressEntryView**: The `+ New Entry` form doesn't yet support attachments — those are only available in the detail view post-creation.
- **Entered by filter in TaskProgressEntriesView**: Shows `store.team` members in the dropdown but the backend `owner` field is a Frappe User email/ID. The filter works correctly in local mode; in remote mode it won't match unless the Frappe User IDs happen to match the team member IDs.
- **`custom_scope_changes` tab**: Content not yet implemented.
- **`custom_work_package` on Task**: ERPNext's standard Task has no `work_package` link field. A custom field is needed for full WP→Task traceability in the Frappe Desk view.

---

## Prototype UI Backport (Sessions 96–130) — COMPLETE

Replay of the prototype's UI from prototype-Session 95 → 130 into the production Vue app, preserving the Frappe-API plumbing. All sessions ported (only prototype-S113 deferred — low-value button-priority refinement). The three planning/scoping docs are now historical; durable facts captured here.

**Net-new artifacts built during the backport:**
- **Stage Planning workflow** — Frappe-native Workflow (not the prototype's hand-rolled state machine). Reject popup + `reject_reason`; Rejected is terminal. See Schema + Backend Permissions sections.
- **Stage Review** — `StageReviewView.vue` + `StageDelayReasonModal.vue` + `Stage Delay Reason` child doctype + `add_stage_delay_reason`. See Schema Reference.
- **User management** — real Frappe Users, not the prototype's localStorage team. Backend `buildsuite_core/api/users.py` (whitelisted, admin-gated: list / create / update / send_user_welcome / send_user_password_reset). Persona = the `User.persona` Select; the `sync_persona_roles` hook maps it to a BuildSuite role (frontend only sets persona). Frontend: `NewUserView.vue`, rebuilt `UsersView.vue`, `data/usersApi.js`. Emails are real Frappe sends (sit in Email Queue if no SMTP). Map: `admin`→System Manager, `bsa`→BuildSuite Administrator.
- **Permission-matrix UI gating** — `PERSONA_CAPS` (roles.js) + `usePermissions()` composable, keyed to `store.role`, which is auto-set from the logged-in `User.persona` on load. Advisory only — **backend is authoritative** (confirmed 2026-06-12: frappe-ui `resource` → `frappe.client.insert` enforces perms; the persona switcher is cosmetic).

**Known deferred follow-up:** the app's people pickers (Task assignee / Project PM) still read the legacy `store.team`; rewiring them to Frappe Users is a separate pass.

---

## Session Log

| Date | What |
|---|---|
| 2026-05-28 | M1-A: Site Execution workspace HTML block + sidebar |
| 2026-05-29 | M1-B: Custom fields, Work Package DocType, Stage Planning DocType, Project form JS |
| 2026-05-29 | M1-C: Standard Frappe UI: add buttons, quick entry dialogs, Bootstrap progress bars |
| 2026-06-01 | Phases 0–5: Route/access model, boot contract, Frappe-compatible Vite build, session + guard |
| 2026-06-02 | Phase 6: Data adapter seam, ProjectsView + WorkPackagesView migrated, DeskLinkPicker introduced |
| 2026-06-03 | Phase 7 start: DocTypeListView shell, generic sort/pagination, Projects fully migrated |
| 2026-06-04 | Phase 7: Task CRUD alignment, sort standardization, date normalization utility |
| 2026-06-04 | Refactor: ProjectDetailView tabs extracted into `project-detail/tabs/` components; debug logs removed |
| 2026-06-04 | Feat: Task Progress Entry views wired to Task Update backend doctype (field name corrections, transforms) |
| 2026-06-04 | Fix: `toArray()` null guard for frappe-ui resource.data in progress entry list + new entry form |
| 2026-06-04 | Refactor: Task filter in progress entries list replaced with DeskLinkPicker |
| 2026-06-04 | Feat: File attachment support on Task Progress Entry detail (FileUploadHandler + Frappe File doctype) |
| 2026-06-04 | Fix: DeskLinkPicker dropdown sticky search bar stayed white in dark mode (hardcoded `!important`) |
| 2026-06-05 | Refactor: App entry URL changed from `/buildsuite_core` to `/client`; www files renamed; hooks.py updated |
| 2026-06-05 | Refactor: `/app/` route prefix removed from all 51 Vue files; router base set to `/client`; HomeView replaced by AppHomeView as landing |
| 2026-06-05 | Fix: Workspace shortcuts localStorage migration strips stale `/app/` route_path values on hydrate |
| 2026-06-05 | Fix: NewTaskProgressEntryView null crash — tasksResource.data null on first render |
| 2026-06-05 | Refactor: Task select in NewTaskProgressEntryView replaced with DeskLinkPicker |
| 2026-06-05 | Fix: `debug` CJS package added to Vite `optimizeDeps.include` to fix dev server crash |
| 2026-06-05 | Fix: `frappe-ui-file-upload-handler` alias added to vite.config.js for production build |
| 2026-06-05 | Fix: DeskList search input dark mode via Tailwind `dark:` utility classes |
| 2026-06-05 | Fix: Task name column in TasksView changed from DeskLink (green) to neutral ink-900 span |
| 2026-06-05 | Refactor: TaskDetailView aligned with prototype — progress block inside grid, chart-bar icon, status enum updated (Yet To Start/In Delay/Blocked), quick-status check fixed, Entered by locked, modal z-indexes fixed |
| 2026-06-05 | Feat: Project Detail Attachments tab migrated to real Frappe File doctype (FileUploadHandler upload, adapter.remove delete, DocTypeListView list with mime-type SVG icon column via new `icon` preset) |
| 2026-06-05 | Feat: DocTypeListView `icon` preset — renders SVG icon from `column.iconFn(row)`; `defineExpose({ reload })`; `defaultColumnLabel` respects explicit empty string |
| 2026-06-06 | Feat: Frappe error parsing — `parseFrappeError` utility + `useFormErrors` composable; checks `err.messages` (frappe-ui pre-parsed) then falls back to `_server_messages`; `DeskLinkPicker` gains `error` prop (red border); wired into all create/update form views |
| 2026-06-06 | Feat: ProjectEditModal wired for field-level server errors — `errors` prop + `clear-error` emit; ProjectDetailView uses `useFormErrors` for edit path |
| 2026-06-06 | Feat: TaskFormModal and TaskDetailView inline modals (edit + progress entry) wired for field-level server errors via `useFormErrors` |
| 2026-06-08 | Fix: `owner_user` field purged from all Work Package views (NewWorkPackageView, WorkPackageDetailView, ProjectDetailView, WorkPackagesView) — Frappe built-in `owner` tracks creator; `owner_user` is not a DocType field and caused `DataError: Field not permitted in query` |
| 2026-06-08 | Fix: TaskFormModal `work_package: null` — wpsResource was fetching only `['name']` (adapter default); added explicit `fields: ['name', 'work_package_name', 'project']`; fixed cascade watch `wp.id` → `wp.name` with `wpLocked` guard; added `selectedWP` computed; fixed WP dropdown label `package_name` → `work_package_name`; fixed assignee default to `''` |
| 2026-06-08 | Fix: WorkPackageDetailView task list not updating after modal task creation — wired `@created="tasksResource?.reload?.()"` on TaskFormModal |
| 2026-06-08 | Fix: Frappe server error messages containing HTML (`<strong><a href="/desk/...">`) now stripped to plain text in `parseFrappeError` — `stripHtml()` helper applied to both `err.messages` (frappe-ui pre-parsed path) and `parseServerMessages` internal path |
| 2026-06-08 | Feat: Work Package field added to TaskDetailView edit modal — DeskLinkPicker filtered by task's project, wired into `saveEdit` payload and `useFormErrors` mapping |
| 2026-06-08 | Fix: TasksView WP column showed `—` for all tasks — `package_name` (non-existent field) was causing backend DataError, silently emptying the WP map; fixed fields to `['name', 'work_package_name']`, cache key bumped to `buildsuite-task-wp-map-v2`, WP sub-line now hidden via `v-if` when task has no WP |
| 2026-06-11 | Feat: Project Team child doctype + `custom_team_members` table field on Project + `persona` Select on User |
| 2026-06-11 | Feat: Team-based record-level permissions for Project — `permissions/setup.py` (11 BuildSuite roles + Project Custom DocPerm matrix, idempotent seed on migrate), `permissions/project.py` (EXEMPT/FLIP/TEAM-ONLY scoping via `permission_query_conditions` + `has_permission`). `ALLOWED_ROLES` app gate expanded. Task permission hooks removed (deferred). Admin-only bypass; System Manager follows FLIP. Verified e2e on `build.local`. Commit `b7c24ee` |
| 2026-06-11 | Feat: Persona→role auto-assignment — `utils/user.py:sync_persona_roles` on `User.validate` grants the BuildSuite role mapped from `persona` (`PERSONA_TO_ROLE`), strips stale BuildSuite roles, keeps System Manager. Fixed persona Select options to match roles.js (added Quantity Surveyor, removed duplicate Accountant). Verified e2e |
| 2026-06-11 | Feat: Task record-level permissions — `permissions/task.py` (project-inherited scoping via `get_task_permission_query`/`has_task_permission`) + `TASK_ROLE_PERMS` matrix seeded by `setup_task_permissions` (install now calls `setup_record_permissions`). Site Engineer edit/delete own-created (owner); Foreman own-created OR assigned (`_assign`); full-write roles bypass. Task hooks re-wired in hooks.py. Verified e2e on `build.local` |
| 2026-06-11 | Feat: Work Package + Task Progress Entry + Stage Planning record-level permissions — 3 new `permissions/*.py` modules + matrices in setup.py; all inherit project scoping. WP read-only (no own-scope). TPE: SE/Foreman edit own + delete own within 24h; Procurement/Store hidden; HR read-all. Stage: SE/Foreman create+edit/delete own while Draft/Rejected; Stage Planning Approval workflow rewired to BuildSuite roles (`setup_stage_planning_workflow`, SE/Foreman submit-own condition); new no-DocPerm marker role `BuildSuite Project User` for workflow `allow_edit`, granted via persona sync. All 5 doctypes verified e2e on `build.local` |
| 2026-06-12 | Backport closeout: prototype UI replay 96→130 complete (see "Prototype UI Backport"). Retired the 3 planning/scoping docs (folded durable facts here). |
| 2026-06-12 | Fix (Stage Review): restored the **conditional** delay-reason gate to match prototype S102 — `onStageReview` opens the dialog only when the stage is delayed AND has zero delay reasons; otherwise opens the review directly. (Reverted an earlier unconditional gate removal.) |
| 2026-06-12 | Fix (dark mode): added missing `-950` palette shades (brand/success/warning/danger/info) in `tailwind.config.js` + a global `html.dark .from-success-50` override in `style.css`. The Labour-movement gradient header was the only one on `from-success-50`, which had no dark override (brand/info/warning/ink did) → light wash in dark mode. |
| 2026-06-12 | Fix (Stage Review Labour movement): layout re-aligned to prototype (2-col Skilled/Unskilled grid, `users-2` icon added to `workspaceIcons.js`, descriptive footer; dropped the Total-man-days row). **Dropped the date-window filter** — labour now sums every Task Update for the stage's tasks (planned windows rarely bracket entry dates, which made it read 0). |
| 2026-06-12 | Verified: project create from the frontend (frappe-ui `resource` → `frappe.client.insert`) **respects** Frappe permissions — an estimator is correctly denied. The persona switcher is cosmetic; backend is authoritative. (Confirmed with a temporary on-load probe, since removed.) |
| 2026-06-16 | **M1 UAT remediation** (branch `fix/m1-uat`, see `context/M1-UAT.csv`). Status pipeline: removed the invalid `project.status="Working"` write in Task Progress Entry `before_save` (it threw — root cause of TPE-006/007 "Shows error"); wired the dormant `update_task_status`/`update_task_status_insert` into Task `validate`/`before_insert` so `task_status`↔native `status` sync (TSK-006/007). New custom `project_status` Select on Project (New/Ongoing/Delayed/Completed, default New) + `sync_project_status` (→ native Open/Completed) on Project `validate` + idempotent `backfill_project_status` in `after_migrate`; frontend create/edit/list now read+write `project_status` (PRJ-008/009, unblocks PRJ-019/STG-012). Company: `set_company_on_insert` (default/inherit) + `enforce_company_rules` (inherit on subproject, lock on edit) (PRJ-005/012/013). Progress: wired `update_project_progress` into Task `on_update`/`on_trash` (PRJ-010). TPE delete revert: `on_trash` rebuilds `task_progress_details` from the **remaining** TPEs and clears native `status` off Completed so erpnext `validate_progress` doesn't re-clamp progress to 100 (TPE-009/010 — this clamp was the subtle bug). Blocker note now validated server-side in TPE `validate` (TPE-011). Guarded cascade delete: `cascade_delete_project`/`cascade_delete_task` on `on_trash`, blocked if GL/JE/Invoice/Stock entries reference the tree (PRJ-014/TSK-013/STG-011). `parent_project` `depends_on` flipped to `eval:doc.parent_project` (PRJ-006). Stage Rejected→Draft on edit in `stage_planning.validate` (SAW-006). "Entered by" (native `owner`) now rendered as text in TPE list + detail (TPE-005). task_type default Activity confirmed already present in create forms (TSK-004). WP create/edit have no editable owner field (already removed); list keeps Frappe-native creator column (WP-007 note). New test module `buildsuite_core/tests/test_uat_fixes.py` (13 `UnitTestCase` tests, all green). **Flagged for discussion, not fixed:** PRJ-015 (default-seed Commercial stages), TPE-014 (TPE company derivation), PRJ-016 (not run). |
| 2026-06-17 | **Project team add/remove in Vue.** The Team tab was wired only to the local Pinia store (never persisted). Added whitelisted `buildsuite_core.api.project_team` helpers (`add_/remove_/get_project_team`) that mutate the `custom_team_members` child table via `doc.append`/`save` with `doc.check_permission("write")` — child-table edits can't go through `frappe.client.set_value`. Frontend: `data/projectTeamApi.js` wrapper; `ProjectDetailView` reads `custom_team_members` off the project doc (frappe.client.get includes child tables), renders avatars (derived initials/color), and calls the API on add/remove with a project reload + toast. `ProjectTeamMemberModal` now uses **DeskLinkPicker** (doctype User, excludes existing members + PM, enabled-only) instead of a local DeskSelect. Test `test_project_team_add_and_remove`. |
| 2026-06-17 | **Company-from-user model** (PRJ-012/013). Added custom `company` Link field to **User**; `utils.user.sync_persona_roles` now throws if a persona'd user has no company (server-side only), with `backfill_user_company` (default company) wired into `after_migrate`. `api/users.create_buildsuite_user` stamps the **creator's company** onto new users (Vue user form never shows company). `set_company_on_insert` now infers a project's company from the creating user's company (Frappe also auto-fills the field from the global default on `new_doc`, so single-company sites just work). Project create/edit forms (`NewProjectView`, `ProjectEditModal`) **no longer show or send company** — it's inferred + locked server-side; `ProjectDetailView` still displays it read-only (OverviewTab). Also: new-project form drops the manual parent-project picker (subprojects only via `?parentId=`), and the weighted parent-progress rollup (parent % = direct tasks + each subproject weighted by its task count) landed in `utils.task.update_project_progress`. Tests: `test_uat_fixes.py` now 17 `UnitTestCase` tests (added company-infer, persona-requires-company, weighted-rollup), all green. |

| 2026-06-18 | **App-branding dropdown + footer profile (prototype S149/S153 adaptation).** The sidebar BuildSuite header is now a dropdown (`DeskShell.vue`): **Go to Desktop** → the real ERPNext desk via new `getDeskUrl()` (`/app`), **Logout** → new `logout()` (POST `/api/method/logout` then `/login`) — both in `utils/session.js` (the prototype's versions were a Vue-landing route + an `alert()` stub). The "Core" badge moved into the dropdown sub-line; the footer Settings link became a **profile** entry (avatar + name + role; Settings still on the topbar gear). Dropped the Project Detail **Activity** tab (import + tab def + render block; `tabs/ActivityTab.vue` deleted). Frontend build clean. Out of scope (prototype-only): Rate Master tweaks (S154–158, M3) and the Procurement workspace dashboard (S159, M4). |

#todo

One thing worth flagging for later (not blocking)
I noticed the production frontend store still runs the prototype's company model — store.companies is seeded from a @/data/companies fixture (3 fake "Acme" companies), and isMultiCompany/activeCompany derive from that, not from the backend Company doctype. Meanwhile the actual picker and Project.company use the real backend companies (NG Build...). They're two disconnected sources:

isMultiCompany is true purely because the fixture has 3 entries — so the Company field always shows, even though the real site's company count could differ.
The "default to active company" comment can't be honored, because activeCompany is a fixture id (ACME-COM) that isn't a valid backend Company.
That's a real piece of tech debt in the prototype→backend transition, but it's out of scope for getting the suite green and would change app behavior — so I left it. Worth a dedicated pass later to make the company model backend-driven (count companies from the Company doctype, default the form to Frappe's default company). Want me to note that somewhere, or take it on as a separate task?
