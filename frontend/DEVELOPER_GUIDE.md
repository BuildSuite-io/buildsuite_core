# Frontend Developer Guide

The BuildSuite Core frontend is a **Vue 3 + frappe-ui** SPA served by Frappe at
`/client` and built into `buildsuite_core/public/frontend/`. It talks to the live
Frappe/ERPNext backend through a thin **data-adapter seam** and renders DocType
data with a reusable list/form stack.

> For backend field mappings, the permission model, and project history, see
> [`../context/implementation-progress.md`](../context/implementation-progress.md) — the
> canonical continuity doc. This guide is the **frontend pattern reference**: how to
> build a feature with the established building blocks.

---

## 0. Architecture at a glance

| Concern | Mechanism |
|---|---|
| Entry / routing | Vue Router base `/client` (see §9). Never hand-write the `/client` prefix. |
| Data access | `createDataAdapter(store)` → `adapter.list/read/create/update/remove/linkSearch` (§1) |
| Data mode | `VITE_DATA_MODE` = `remote` (default, real Frappe) or `local` (seed/localStorage) |
| Lists | `DocTypeListView` (DocType-aware) over `DeskList` (presentational) (§3–§4) |
| Link fields & filters | `DeskLinkPicker` — server-side search (§2) |
| Forms / server errors | `useFormErrors` + `parseFrappeError` (§5) |
| Confirmations | `useConfirm()` + global `<ConfirmDialog>` (§6) |
| Permission gating (UI) | `usePermissions()` keyed to the logged-in persona; **backend is authoritative** (§7) |
| File uploads | `FileUploadHandler` (XHR) → Frappe `File` doctype (§8) |
| Dark mode | `html.dark` class + `style.css` overrides + `dark:` utilities (§10) |

**Golden rules**
- Reads/writes go through the **adapter**, never direct `store.<slice>` localStorage access in remote mode.
- Every adapter call that feeds the view layer uses a `transform()` to map backend
  snake_case → the view's camelCase aliases.
- `resource.data` is **`null` until loaded** — guard with `toArray()` before `.filter/.map/.length`.
- The backend enforces permissions; UI gating only hides buttons that would fail.

---

## 1. Data layer — the adapter

`createDataAdapter(store)` returns an object with a uniform contract. The remote
implementation wraps frappe-ui resources; the local one runs over Pinia seed state.

```js
import { createDataAdapter } from '@/data/adapters'
const adapter = createDataAdapter(store)
```

| Method | Backend call | Notes |
|---|---|---|
| `list(doctype, opts)` | `frappe.client.get_list` | Returns a frappe-ui list resource (`.data`, `.loading`, `.reload()`). Omits Table fields. |
| `read(doctype, name, opts)` | `frappe.client.get` | Returns the **full document incl. child tables** (e.g. Stage Planning tasks/deps). |
| `create(doctype, values)` | `frappe.client.insert` | **Enforces permissions.** Returns the created doc. |
| `update(doctype, name, values)` | `frappe.client.set_value` | Enforces permissions. |
| `remove(doctype, name)` | `frappe.client.delete` | Enforces permissions. |
| `linkSearch(doctype, opts)` | search resource | Backs `DeskLinkPicker`. |

> **Permissions are real.** `create/update/remove` route through `frappe.client.*`,
> which run `doc.insert()/save()/delete()` **without** `ignore_permissions`. A
> wrong-role user is denied server-side. The persona switcher is a cosmetic UI
> affordance — it does **not** change backend authorization.

### 1.1 `read()` with transform (the canonical detail pattern)

```js
const taskResource = ref(null)
function loadTask(id) {
  if (!id) { taskResource.value = null; return }
  taskResource.value = adapter.read('Task', id, {
    fields: ['name', 'subject', 'project', 'work_package', 'status', 'exp_end_date'],
    cache: `buildsuite-task-detail:${id}`,
    transform(rows) {
      return rows.map(row => ({
        id: row?.name || '',
        name: row?.subject || row?.name || '',
        projectId: row?.project || '',
        workPackageId: row?.work_package || '',
        // map EVERY backend field you read to a view alias
      }))
    },
  })
}
watch(() => props.id, loadTask, { immediate: true })

// firstResourceRow() unwraps doc/array/value shapes; fall back to local store.
const task = computed(() => firstResourceRow(taskResource.value) || store.taskById(props.id) || null)
```

### 1.2 The `toArray()` guard (use everywhere you touch `resource.data`)

```js
// frappe-ui inits resource.data to null, not []. Without this, .filter()/.length throws.
function toArray(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.value)) return data.value
  return []
}
const items = computed(() => toArray(someResource.value?.data))
```

### 1.3 Mutations

```js
const created = await adapter.create('Project', { project_name: 'X', is_group: 1, status: 'New' })
await adapter.update('Task', id, { status: 'Completed' })
await adapter.remove('Work Package', id)
// reload the list/detail resource afterwards: resource.value?.reload?.()
```

---

## 2. Link fields & filters — `DeskLinkPicker`

**Always use `DeskLinkPicker` for any field that links to a Frappe DocType** (and for
list filters over a DocType). Do **not** use `DeskSelect` with a locally-fetched list —
in remote mode it breaks when the list doesn't contain the current value.

```vue
<DeskLinkPicker
  v-model="form.workPackageId"
  doctype="Work Package"
  label-field="work_package_name"
  value-field="name"
  :search-fields="['work_package_name', 'name']"
  :filters="form.projectId ? [['project', '=', form.projectId]] : []"
  :page-length="20"
  placeholder="— Select work package —"
  :error="errors.workPackageId"
  @change="clearError('workPackageId')"
/>
```

It searches server-side via the adapter, supports a red `error` border, and composes
with `useFormErrors` (§5).

---

## 3. List views — Quick Start

Use `DocTypeListView` for DocType-backed screens; use `DeskList` directly when data
does **not** come from a DocType resource (already-prepared rows).

```vue
<DocTypeListView
  doctype="Project"
  :field-order="[
    'custom_project_id', 'project_name', 'customer', 'project_type', 'status',
    'estimated_costing', 'percent_complete', 'expected_start_date', 'expected_end_date',
    'owner', 'company',
  ]"
  :columns="[
    { key: 'custom_project_id', label: 'Project ID' },
    { key: 'project_name', label: 'Project Name' },
    { key: 'customer', label: 'Client' },
    { key: 'project_type', label: 'Project Type' },
    { key: 'status', label: 'Status', preset: 'status' },
    { key: 'estimated_costing', label: 'Budget' },
    { key: 'percent_complete', label: 'Progress', preset: 'progress' },
    { key: 'timeline', label: 'Timeline', preset: 'timeline', fields: ['expected_start_date', 'expected_end_date'] },
    { key: 'owner', label: 'Owner' },
    { key: 'company', label: 'Company' },
  ]"
  :search-fields="['project_name', 'custom_project_id', 'customer', 'name']"
  :base-filters="[['is_group', '=', 1]]"
  :filter-values="filterValues"
  :filter-field-map="{ status: 'status', type: 'project_type', company: 'company' }"
  cache-key="buildsuite-project-list-generic"
  row-key="name"
  search-placeholder="Search by name, code, client..."
  :paginated="true"
  :page-size="20"
  :page-size-options="[10, 20, 50, 100]"
  @row-click="onRowClick"
/>
```

`DocTypeListView` does **not** take a `rows` prop — it fetches from Frappe and feeds
`DeskList` internally.

### 3.1 `DeskList` (presentational shell)

```vue
<DeskList :rows="rows" :columns="columns" row-key="id" @row-click="onRowClick" />
```

**Props:** `rows*`, `columns*`, `rowKey` (`'id'`), `modelValue` (search), `searchPlaceholder`,
`bulkSelect` (`false`), `selected`, `showSort` (`true`), `showColumns` (`true`),
`showAddFilter` (`true`), `sortOptions` / `sortBy` (config-driven sort dropdown),
`paginated` (`true`), `pageSize` (`10` for `DeskList`, `20` for most screens), `pageSizeOptions`.

**Column shape:** `key*`, `label*`, `align?`, `render?(row)→string`, `class?`.

**Emits:** `update:modelValue`, `update:selected`, `update:sortBy`, `row-click`, `add-filter`,
`sort`, `toggle-columns`.

**Slots:** `filter-chips`, `pre-columns-controls`, `actions`, `cell-<columnKey>` (`{ row, value }`), `empty`.

> Action buttons (`+ New`, `+ Add …`) belong **above the table** (right-aligned), not
> inside the filter bar — use the `#actions` slot or a sibling flex row.

---

## 4. `DocTypeListView` API

### 4.1 Core props

`doctype*`, `fieldOrder*` (`String[]`), `columns?` (renderer config, §4.3),
`searchFields?` (`['name']`), `baseFilters?` (`[]`), `filterValues?`, `filterFieldMap?`,
`pageLength?` (server fetch size, `100`), `cacheKey?`, `initialOrderBy?` (`'creation desc'`),
`rowKey?` (`'name'`), `searchPlaceholder?`, `emptyMessage?`.

### 4.2 Pagination props (forwarded to `DeskList`)

`paginated?` (`true`), `pageSize?` (`10`), `pageSizeOptions?` (`[10,20,50,100]`).
Pagination is **client-side over fetched rows** today; `pageLength` caps the server fetch.

**Emits:** `row-click`. **Slots:** `filter-chips` (scope `{ resource, meta, metaLoading, fields }`),
`cell-<columnKey>`, `empty`. A provided `cell-` slot overrides any preset/renderer/default.

### 4.3 Column renderer API (`columns`, optional)

`ColumnConfig`: `key*`, `label?`, `align?`, `preset?` (`'status' | 'progress' | 'timeline'`),
`fields?` (composite backing, e.g. timeline), `renderer?` (Component | string), `rendererProps?`.

**Built-in presets:** `status` (→ `StatusBadge`), `progress` (bar + clamped %),
`timeline` (one column from two date fields; default `expected_start_date`/`expected_end_date`).

A custom `renderer` component receives `row`, `column`, `value` (single value or `fields[]`
tuple), `meta`, and `...rendererProps`.

### 4.4 Sorting & filtering

- Sort: grouped control in the action cluster (asc/desc toggle + field select); sortable
  fields derived from resolved fields + metadata + `meta.sort_field` + `modified` fallback.
- Filter: `baseFilters` first, then truthy `filterValues` mapped via `filterFieldMap`.

---

## 5. Forms & server errors — `useFormErrors`

Pair a `{ backendFieldName: formFieldKey }` map with `parseFrappeError` so Frappe
mandatory/validation errors land on the right field, and the summary toasts.

```js
import { useFormErrors } from '@/composables/useFormErrors'
const { errors, applyServerErrors, setErrors, clearError, reset } = useFormErrors({
  project_name: 'name',
  company:      'company',
})

function validate() {                      // client-side
  const e = {}
  if (!form.name) e.name = 'Required'
  setErrors(e)
  return Object.keys(e).length === 0
}

async function save() {
  if (!validate()) return
  try {
    const res = await adapter.create('Project', payload)
    router.push(`/projects/${res.name}`)
  } catch (err) {
    showToast(applyServerErrors(err) ?? 'Failed to save', 'error')   // maps fields + returns summary
  }
}
```

In the template, clear a field error the moment the user fixes it: `@change="clearError('company')"`.
`parseFrappeError` strips Frappe's HTML (`<strong><a href="/desk/…">`) to plain text and reads
`err.messages` (frappe-ui pre-parsed) before falling back to `_server_messages`.

---

## 6. Confirmations — `useConfirm`

A single `<ConfirmDialog>` is mounted in `App.vue`; call `useConfirm()` anywhere for a
promise-based confirm. **Never use `window.confirm()`.**

```js
import { useConfirm } from '@/composables/useConfirm'
const confirmDialog = useConfirm()

async function deleteThing() {
  const ok = await confirmDialog({
    title: 'Delete project',
    message: 'This removes the project and all its work packages and tasks.',
    confirmLabel: 'Delete',
    destructive: true,          // red confirm button
  })
  if (!ok) return
  await adapter.remove('Project', id)
}
```

Options: `title`, `message`, `confirmLabel`, `destructive`. Returns `Promise<boolean>`
(Esc / backdrop / Cancel → `false`). Opening a new dialog settles any pending one as `false`.

---

## 7. Permission gating (UI) — `usePermissions`

Hides create/edit/delete affordances for the active persona. The persona is auto-set
from the **logged-in user** (`User.persona` via `get_access_context`) on load; the
switcher previews others within the session. The **backend (`permissions/*.py`) is the
real gate** — this only hides buttons that would fail.

```js
import { usePermissions } from '@/composables/usePermissions'
const { canCreate, canRead, canEdit, canDelete } = usePermissions()
```

```vue
<button v-if="canCreate('task')" class="desk-save-btn">+ New Task</button>
<button v-if="canEdit('stagePlanning')" @click="openEdit">Edit</button>
```

Doctype keys: `'project' | 'workPackage' | 'task' | 'taskProgressEntry' | 'stagePlanning'`.
`canCreate` is `true` only for full-create personas; `canEdit/canDelete` show for full **and**
own-scope personas (the backend enforces the precise own-record rule); read-only personas get
a restricted-access notice. Capabilities live in `PERSONA_CAPS` (`src/data/roles.js`).

> Do **not** wire a `v-if` to a getter that always returns true — that leaks actions to
> the wrong persona. Gate via `usePermissions`, or omit the `v-if` and rely on the backend.

---

## 8. File uploads — `FileUploadHandler`

Use the XHR `FileUploadHandler` class, **not** frappe-ui's `FileUploader` component
(its fallback slot needs a globally-registered `<Button>`).

```js
import FileUploadHandler from 'frappe-ui-file-upload-handler'   // vite alias
const handler = new FileUploadHandler()
await handler.upload(file, { doctype: 'Task Update', docname: id, private: true })
```

List attachments from the Frappe `File` doctype, delete with `adapter.remove('File', name)`:

```js
adapter.list('File', {
  filters: [['attached_to_doctype', '=', 'Task Update'], ['attached_to_name', '=', id]],
  fields: ['name', 'file_name', 'file_url', 'file_size', 'is_private', 'creation', 'owner'],
  orderBy: 'creation desc',
})
```

---

## 9. Routing

- Router base is `createWebHistory('/client')`. Route definitions use **bare paths**
  (`path: 'projects'`), and `<RouterLink>` / `router.push()` use paths **without** the
  `/client` prefix — the router adds/strips it automatically.
- The legacy `/app/` prefix is gone. Never let an `/app/…` link into production.
- A route guard protects all routes except `name: 'forbidden'`; access is resolved via
  `session.js` / `stores/session.js` against the backend.

---

## 10. Dark mode

Driven by an `html.dark` class (set by `store.theme` in `App.vue`). Most contrast is
handled by global overrides in `src/style.css`, so plain palette classes usually "just work":

- `html.dark .bg-white` → `#242424` (card/modal surface), `html.dark body` → `#1A1A1A`
- `html.dark .text-ink-900` → `#F5F5F5`, `html.dark .desk-input` → dark field styling

**Gotchas (learned the hard way):**
- **`from-<color>-50` gradient headers** have no automatic dark override — each color used in
  a gradient needs an explicit `html.dark .from-<color>-50 { … }` rule in `style.css`
  (brand/info/warning/success/ink are covered; add others before using them). A missing one
  shows the **light gradient in dark mode**.
- Don't use inline hex (`style="color:#475569"`) — it bypasses the `html.dark` overrides.
  Use palette classes (`text-ink-600`) so dark mode applies.
- Don't use shades that don't exist in the palette (e.g. `dark:from-success-950` only works
  because `-950` shades were added to `tailwind.config.js`). Unknown classes are silently dropped.
- **Modal backdrops must be `z-[60]`+** — the DeskShell sidebar is `z-50`.

---

## 11. Build & dev

```bash
cd frontend
npm run dev      # http://localhost:5173, proxies /api/* to the Frappe dev server
npm run build    # → buildsuite_core/public/frontend/  (the only automated gate — keep it green)
```

- Test against the site at `http://build.local/client` after `bench start`.
- Built assets are **not committed** — they're produced by `npm run build` / `bench build`
  at deploy time.
- Env: `VITE_FRAPPE_HOST` (dev proxy target), `VITE_DATA_MODE` (`remote` default / `local`).
- Vite gotchas live in `vite.config.js` (the `frappe-ui` excludes, `debug` include, the
  `frappe-ui-file-upload-handler` / `feather-icons` aliases) — see
  [`../context/implementation-progress.md`](../context/implementation-progress.md) "Vite Config Notes".

---

## 12. Key file reference

| Area | File(s) |
|---|---|
| Adapter seam | `src/data/adapters/{index,remoteDataAdapter,localDataAdapter}.js` |
| List stack | `src/components/doctype/DocTypeListView.vue`, `src/components/desk/DeskList.vue` |
| Link picker | `src/components/desk/DeskLinkPicker.vue` |
| Composables | `src/composables/{useDocTypeList,useFormErrors,useConfirm,usePermissions}.js` |
| Errors | `src/utils/frappeError.js` (`parseFrappeError`) |
| Confirm host | `src/components/ConfirmDialog.vue` (mounted in `App.vue`) |
| Permissions | `src/data/roles.js` (`PERSONA_CAPS`) |
| Session/auth | `src/utils/session.js`, `src/stores/session.js` |
| Reference screens | `ProjectsView` (generic list), `StagePlanningDetailView` (workflow), `StageReviewView` (Vue dashboard), `settings/UsersView` + `NewUserView` (user mgmt) |
