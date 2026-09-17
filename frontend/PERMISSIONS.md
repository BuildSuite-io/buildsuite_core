# Frontend Permissions & Gates

How access control works in the SPA, and how to add it when you build a page, list,
button, or picker. **Read this before adding any `v-if` that hides something for a role.**

---

## The one rule

**The backend is the only real gate. The frontend never decides access — it asks the
backend and hides the affordances the current user can't use.**

Every write (`create` / `update` / `remove`, submit, workflow action) goes through Frappe,
which enforces DocPerms + the `permissions/*.py` hooks server-side. If you forget a UI gate,
nothing leaks — the server refuses. UI gating exists only so a user doesn't see a button
that would then error.

So there is **no client-side permission matrix** anymore. Do **not** hardcode role name
lists in a component to decide what to show. Ask the backend-derived helpers below.

---

## Two kinds of gate

| Gate | Question it answers | Where it comes from |
|---|---|---|
| **Resource caps** | "Can this user create/read/edit/delete/submit *this doctype*?" | `usePermissions()` → backend `frappe.has_permission` |
| **Workspace / route visibility** | "Can this user open *this screen*?" | route `meta` + the backend workspace registry |

Both are computed once at boot (in `get_access_context`) and cached on the session store.
Everything reads from there — you never call Frappe permission APIs directly in a component.

---

## 1. Resource caps — `usePermissions()`

The workhorse. Import it, ask about a **resource key**.

```js
import { usePermissions } from "@/composables/usePermissions";
const { canCreate, canRead, canEdit, canDelete, canSubmit } = usePermissions();
```

```vue
<button v-if="canCreate('materialRequest')" @click="onNew">+ New</button>
<button v-if="canEdit('sco')" @click="startEdit">Edit</button>
<button v-if="canDelete('task')" @click="onDelete">Delete</button>
<button v-if="canSubmit('purchaseOrder')" @click="onSubmit">Submit</button>
```

- `canRead(key)` — user can list/open it.
- `canCreate(key)` — user can make a new one (unconditional).
- `canEdit(key)` / `canDelete(key)` — **coarse**: true for full-access *and* own-scope
  personas. Good for list-level buttons. On a **detail page where you hold the record**,
  prefer the record-aware pair so an "own-scope" user (e.g. a Site Engineer who may only edit
  their own records) sees the button only on records they created:

```js
const { canEditRecord, canDeleteRecord } = usePermissions();
```
```vue
<button v-if="canEditRecord('task', task)" @click="startEdit">Edit</button>
```
The record must carry Frappe's `owner` (the detail read transforms already keep it).

- `canSubmit(key)` — submit/cancel a submittable doctype (distinct from create).

### Resource keys

camelCase keys, defined once in **`buildsuite_core/permissions/resource_map.py`**
(`RESOURCE_DOCTYPES`). Current set:

```
project · workPackage · task · taskProgressEntry · stagePlanning · sco
materialRequest · purchaseOrder · purchaseReceipt · materialConsumption · item
boq · assembly · estimateTemplate · rateMaster
subcontractor · subcontractorWorkOrder · measurementBook · subcontractorBill
fieldEmployee · crew · fieldAttendance · machinery · machineryUsage
supplier · customer · supplierBill · salesInvoice · advance · pettyCash · expense
```

An unknown key resolves to **no access** (safe default), so a typo hides the button rather
than leaking it.

---

## 2. Screens — route guards

Route guards live in `src/router/index.js` (`router.beforeEach`). You gate a screen by
adding `meta` to its route — you don't write guard logic in the component.

| Put on the route | Effect |
|---|---|
| `meta: { workspace: "<slug>" }` | Only users who can see that workspace can open it. |
| `meta: { requiresAdmin: true }` | Admin (System Manager / BuildSuite Administrator) only. |
| `meta: { requiresBSA: true }` | BuildSuite Administrator only. |
| `meta: { cap: "<resourceKey>" }` | Gate on a resource cap (read, unless the action is inferred). |

**You usually don't even need `meta.cap`.** Resource routes are auto-gated by the
`ROUTE_CAPS` map in `router/index.js`, keyed by route **name**, with the action inferred:

- a `*-new` route needs **create**, a `*-edit` route needs **edit**, everything else **read**.

So when you add a new resource route, add one line to `ROUTE_CAPS`:

```js
// in ROUTE_CAPS
"material-requests": "materialRequest",
"material-request-new": "materialRequest",   // → needs canCreate
"material-request-edit": "materialRequest",   // → needs canEdit
```

The generic `/records/:doctype/*` browser is gated separately and **live** (the doctype is
dynamic) via `GENERIC_RECORD_CAPS` + `get_doctype_permissions`. You don't touch that for a
normal page.

A denied deep-link redirects home (or `/forbidden` for workspace/role denials). Guards
**fail open** while the session is still booting, so a legitimate user is never bounced
before their permissions are known.

---

## 3. Lists — `DocTypeListView`

The standard list stack already respects permissions end-to-end:

- The row data comes from `frappe.client.get_list`, which the backend filters by DocPerm +
  the `permission_query_conditions` hooks (team scoping, own-scope, etc.). A user simply
  won't see rows they can't read — you don't filter for security in the component.
- Gate the **"+ New"** button with `canCreate(key)`.

```vue
<DocTypeListView :doctype="'Task'" :field-order="[...]" @row-click="open">
  <template #actions>
    <button v-if="canCreate('task')" class="desk-save-btn" @click="onNew">+ New</button>
  </template>
</DocTypeListView>
```

For the **generic** `/records/:doctype` list (admin-curated doctypes), the view fetches
`get_doctype_permissions(doctype)` and gates its own New button — nothing to do.

---

## 4. Select / Link pickers — `DeskLinkPicker`

A picker resolves its options through `frappe.get_list`, so **read permission already gates
what a user can pick** — a persona who can't read Supplier gets an empty Supplier picker.
You don't add a permission check.

What you *do* pass is a **scope filter** (business rule, not security), e.g. company-scoping:

```vue
<DeskLinkPicker :doctype="'BOQ'" :filters="activeCompanyFilter()" v-model="form.boq" />
```

`:filters` is `[[field, op, value], …]` (or an object). Company-partitioned pickers use
`activeCompanyFilter()` from `@/composables/useActiveCompany`.

---

## 5. Workspace tiles & shortcuts

- **Shortcut tiles** (`<WorkspaceShortcut>`): pass `cap="<resourceKey>"` and the tile hides
  itself for personas who can't read that resource:

  ```vue
  <WorkspaceShortcut to="/tasks" icon="check-square" label="Tasks" cap="task" />
  ```

  The registry-driven shortcuts (from `get_workspace_shortcuts`) are **also gated
  server-side** by the target doctype's read permission — a shortcut to something the user
  can't read never reaches the client.

- **Records section** (`<WorkspaceRecordsSection>`): fully server-gated per doctype — just
  drop it in.

- **Which workspaces show** in the sidebar/launcher comes from the backend registry via the
  store; you don't gate the nav yourself.

---

## 6. Workflow-driven buttons — `useWorkflow`

When a doctype's lifecycle is a Frappe Workflow (e.g. Scope Change Order, finance bills),
don't hardcode which state-transition buttons to show. Ask the workflow:

```js
import { useWorkflow } from "@/composables/useWorkflow";
const { transitions, refresh } = useWorkflow("Scope Change Order");
const wfActions = computed(() => new Set((transitions.value || []).map((t) => t.action)));
// then in the detail view, after loading the doc: refresh(doc.name)
```
```vue
<button v-if="wfActions.has('Approve')" @click="onApprove">Approve</button>
```

`transitions` are already **role- and state-filtered by the backend** — the button appears
only when this user may take that action from the doc's current state.

---

## 7. Admin / role flags (use sparingly)

For coarse, non-resource gates (settings screens, a leadership-only tile), the store exposes
backend-derived flags — again, never a hardcoded role check:

```js
import { useDataStore } from "@/stores";
const store = useDataStore();
store.isAdmin          // System Manager or BuildSuite Administrator
store.isBSA            // BuildSuite Administrator
store.isLeadership     // Director / PM / Admin / BSA
store.hasRole("BuildSuite Accountant")   // explicit role check when unavoidable
```

Prefer a **resource cap** over a role flag whenever the thing you're gating is really
"can this user touch this doctype." Role flags are for screen-level / feature toggles.

---

## Adding a **new gated resource** (the whole loop)

You added a new doctype (say `Widget`) and want the SPA to gate it:

1. **Backend — make it a resource.** Add a key to `RESOURCE_DOCTYPES` in
   `buildsuite_core/permissions/resource_map.py`:
   ```python
   "widget": "Widget",
   ```
2. **Backend — give it DocPerms.** Add a `WIDGET_ROLE_PERMS` matrix + a `setup_widget_permissions()`
   in `permissions/setup.py`, and call it from `restore_role_permissions()`. (This is the
   authoritative grant. See `buildsuite_core/permissions/`.)
3. **Frontend — gate affordances** with `canCreate('widget')` etc. No client matrix to edit.
4. **Frontend — gate the route** by adding its route names to `ROUTE_CAPS` in `router/index.js`.

That's it — the cap flows automatically: `get_resource_permissions` picks up the new key from
the map and ships it in the boot payload.

> **Permissions changed on the site but the UI didn't update?** The access context is cached
> per session; a hard refresh re-fetches it. Backend DocPerm edits (in Desk, or via **Core
> Settings → Role permissions → Restore defaults**) take effect on the next boot.

---

## Golden rules

1. **Never hardcode a role-name list** in a component to decide visibility. Use a resource cap,
   or a store flag, or route `meta`.
2. **A missing UI gate is a UX bug, not a security hole** — the backend still refuses. But do
   add the gate so users aren't shown dead buttons.
3. **Don't filter lists/pickers "for security"** — the backend already scopes them. Filters you
   pass are business rules (e.g. company), not access control.
4. The dev **RoleSwitcher is cosmetic** — it changes the previewed persona label, *not* your
   actual permissions (those come from your logged-in user). To test a persona's real gates,
   log in as that persona's user.
5. When unsure, **omit the `v-if` and let the backend enforce** — better a button that errors
   than one that silently leaks.

---

## Where things live

| Piece | File |
|---|---|
| CRUD caps composable | `src/composables/usePermissions.js` |
| Resource key → doctype map | `buildsuite_core/permissions/resource_map.py` |
| Backend cap payload | `buildsuite_core/api/permission.py` (`get_resource_permissions`) |
| Route guards + `ROUTE_CAPS` | `src/router/index.js` |
| Workflow buttons | `src/composables/useWorkflow.js` |
| Store flags/getters | `src/stores/index.js`, `src/stores/session.js` (`access.*`) |
| Authoritative DocPerm matrices | `buildsuite_core/permissions/setup.py` |
| Row-level scoping (teams/own) | `buildsuite_core/permissions/{project,task,…}.py` |
