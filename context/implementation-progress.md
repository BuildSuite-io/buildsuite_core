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
| `context/implementation-progress.md` | **This file** |

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
| `createRemoteDataAdapter()` | `frontend/src/data/adapters/remoteDataAdapter.js` | Generic remote DocType adapter contract (`list/read/create/update/remove/linkSearch`) over frappe-ui list resources | `createDataAdapter`, filter/link/read slices |
| `createDataAdapter(store, mode)` | `frontend/src/data/adapters/index.js` | Adapter factory for local/remote mode switching during migration | All migrated views |
| `useDocTypeList(doctype, options)` | `frontend/src/composables/useDocTypeList.js` | Generic Frappe list-resource wrapper for read-only DocType list calls | `createRemoteDataAdapter`, `DocTypeListView.vue`, `ProjectsView.vue` |
| `DocTypeListView` | `frontend/src/components/doctype/DocTypeListView.vue` | Reusable meta-driven list shell (`doctype` + ordered `fieldOrder`) with default sort handling and reload-on-resolved-columns | `ProjectsView.vue`, `WorkPackagesView.vue`, `TasksView.vue` |
| `DeskLinkPicker` | `frontend/src/components/desk/DeskLinkPicker.vue` | Generic inline Link/autocomplete backed by `useDocTypeList` with server-side search. **Use for all Link-field inputs and list filters** (replaces DeskSelect for DocType-backed fields) | `ProjectsView.vue`, `TaskProgressEntriesView.vue`, `NewTaskProgressEntryView.vue`, form modals |
| `FileUploadHandler` | Via alias `frappe-ui-file-upload-handler` → `node_modules/frappe-ui/src/utils/fileUploadHandler.ts` | XHR-based file upload class from frappe-ui. Use this instead of `FileUploader` component (which requires unregistered `Button` global). Handles CSRF, progress, FormData. | `TaskProgressEntryDetailView.vue` |
| `_has_app_permission(log_denial)` | `buildsuite_core/api/permission.py` | Internal permission check with optional logging | `has_app_permission`, `get_access_context` |
| `get_access_context()` | `buildsuite_core/api/permission.py` | Whitelisted access-status API for frontend route guards | `frontend/src/utils/session.js#getAccessContext` |

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
  - **Remaining to close Phase 7**: WorkPackageDetailView, StagePlanningsView full CRUD, NewTaskView, NewProjectView
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
| `owner_user` | Link→User | Named `owner_user` to avoid conflict with Frappe built-in `owner` |
| `description` | Text | |

### Custom Fields on Project (fixtures)

| Fieldname | Type | Notes |
|---|---|---|
| `custom_project_id` | Data | reqd, unique, in_list_view |
| `is_group` | Check | default 0 |
| `parent_project` | Link→Project | depends_on: eval:doc.is_group==0 |

---

## Known Constraints / Future Work

- **NewTaskView / NewProjectView**: Still use store-based task/project creation. Not yet migrated to adapter.
- **StagePlanningsView / StagePlanningDetailView**: Not yet migrated to adapter (reads from store).
- **WorkPackageDetailView**: Partially migrated (read via adapter, mutations still store-based).
- **Task Update attachments in NewTaskProgressEntryView**: The `+ New Entry` form doesn't yet support attachments — those are only available in the detail view post-creation.
- **Entered by filter in TaskProgressEntriesView**: Shows `store.team` members in the dropdown but the backend `owner` field is a Frappe User email/ID. The filter works correctly in local mode; in remote mode it won't match unless the Frappe User IDs happen to match the team member IDs.
- **`custom_scope_changes` tab**: Content not yet implemented.
- **`custom_work_package` on Task**: ERPNext's standard Task has no `work_package` link field. A custom field is needed for full WP→Task traceability in the Frappe Desk view.

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
