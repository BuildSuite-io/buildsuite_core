# BOQ (Bill of Quantities) — Developer Documentation

> Ground-truth for the BOQ subsystem: the data model, the amount roll-up chain, the
> approval workflow, the whitelisted API, permissions, and the frontend. Derived from
> the code under `buildsuite_core/buildsuite_core/doctype/boq*`, `buildsuite_core/api/boq.py`,
> `buildsuite_core/permissions/setup.py`, and `frontend/src/views/Boq*.vue`.
> When this doc and the code disagree, **the code wins** — update this file.

---

## 1. What it is

A **BOQ** is a costed, revisable estimate for a **Project**, structured as a three-level tree:

```
BOQ                         (the estimate — one per revision, one Approved per project)
 └─ BOQ Group               (a section: "Civil Works", "MEP", …)
     └─ BOQ Item            (a line of work: qty × rate = amount; optionally an Assembly)
         └─ BOQ Sub Item    (rate-analysis component: resource + coefficient + rate)
```

BOQ Items can be **manual** (rate typed in) or **assembly-driven** (rate derived from
sub-items exploded out of an `Assembly`). Items optionally tag a **Work Package** and a
**Task**; task progress drives actuals. A BOQ carries **margin** + **tax** rates and rolls
everything up to a `total`, with a per-Work-Package breakdown.

---

## 2. Data model

Four doctypes. **None are child tables** — the tree is an adjacency list of standalone
doctypes wired by parent-pointer `Link` fields. (The *only* child table in the model is
`wp_summaries` on the BOQ, holding the per-WP roll-up buckets.)

### 2.1 `BOQ` — `autoname: BOQ-.#####`, `title_field: title`

| Field | Type | Notes |
|---|---|---|
| `project` | Link → Project | required |
| `company` | Link → Company | defaulted from the project (`before_insert`/`validate`) |
| `title` | Data | |
| `revision` | Int | 1-based; `create_revision` sets `max+1` |
| `base_revision` | Link → BOQ | the revision this was cloned from |
| `status` | Select | **Draft / Submitted / Approved / Superseded** |
| `source_sco` | Link | set when a revision is raised from a Scope Change Order |
| `prepared_by` / `prepared_date` | Link User / Date | stamped `before_insert` |
| `approved_by` / `approved_date` | Link User / Date | stamped on approve |
| `margin_rate` / `tax_rate` | Percent | inputs to the roll-up |
| `planned_amount` / `actual_amount` / `margin_amount` / `tax_amount` / `total` | Currency | **server-derived** (see §3) |
| `wp_summaries` | Table → BOQ WP Summary | per-WP buckets: planned / margin / tax / total |

### 2.2 `BOQ Group` — `boq → BOQ`, `code`, `group_name`, `idx_order`

The section header. `code` (e.g. `A`, `B`) is a display/business code, **not** the relational
key. Ordered by `idx_order`.

### 2.3 `BOQ Item` — the costed line

`boq → BOQ`, `boq_group → BOQ Group`, `code`, `description`, `unit → UOM`,
`planned_qty`, `rate`, `planned_amount`, `actual_qty`, `actual_amount`,
`task → Task`, `work_package → Work Package`, `cost_head` (Select),
`quantity_source` (Manual / Assembly / Template / Takeoff), `assembly → Assembly`, `driving_qty`.

### 2.4 `BOQ Sub Item` — rate-analysis component

`boq → BOQ`, `boq_item → BOQ Item`, `rate_master → Construction Rate Master`,
`resource_name`, `description`, `qty_per_unit`, `uom → UOM`, `coefficient`, `rate`, `amount`,
`qty`, `work_package`, `cost_head`, `source_assembly → Assembly`.

### 2.5 How the levels link

Each child stores the **docname** of its parent; every level *also* carries a **direct
`boq`** link to the root (denormalized) so "all items in this BOQ" / "all sub-items in this
BOQ" is one flat query without walking the tree:

```
BOQ ◄── BOQ Group.boq
BOQ ◄── BOQ Item.boq          BOQ Group ◄── BOQ Item.boq_group
BOQ ◄── BOQ Sub Item.boq      BOQ Item  ◄── BOQ Sub Item.boq_item
```

Nothing *outside* the BOQ tree Links to a Group/Item/Sub Item — the only inbound references
are these internal parent pointers. The denormalized `boq` link must be kept consistent by
the code that creates rows (clone / explode / import all set it). There are **no DB-level
foreign keys**; cascade delete is enforced in controllers (§4).

---

## 3. The amount roll-up chain (server-authoritative)

Amounts and the assembly-item rate are **derived on the server**. Forms must never write
`planned_amount`, `actual_amount`, `total`, or an assembly item's `rate`.

```
BOQ Sub Item.validate         amount = qty_per_unit × rate          (rate snapshotted from Rate Master)
        │  after_insert / on_update / after_delete
        ▼
roll_up_item_rate(item)       item.rate = Σ sub_item.amount
        │                     item.planned_amount = planned_qty × rate
        │                     item.actual_amount  = actual_qty  × rate
        ▼
recompute_boq(boq)  ──►  BOQ.validate ──► compute_boq_totals(doc):
        planned = Σ item.planned_amount
        margin  = planned × margin_rate%
        tax     = (planned + margin) × tax_rate%
        total   = planned + margin + tax
        actual  = Σ item.actual_amount
        wp_summaries = buckets by work_package, margin+tax split proportionally to each WP's planned share
```

Key points:

- **Manual item:** `rate` is typed; `BOQ Item.validate` computes `planned_amount = planned_qty × rate`.
- **Assembly item:** `rate` is **derived** — `roll_up_item_rate` sums the sub-items' `amount`.
  Editing/adding/removing a sub-item re-rolls the item, then the BOQ.
- **Rate Master snapshot:** a sub-item linked to a `Construction Rate Master` snapshots
  `rate` + `uom` from it at validate-time — it is a *snapshot*, not a live link. Each component
  keeps its own unit (bag / litre / day…), distinct from the parent item's UOM.
- **`recompute_boq(name)`** simply re-saves the BOQ so its `validate` re-rolls. Batch
  operations set **`frappe.flags.boq_skip_rollup = True`** to suppress the per-row re-save and
  call `recompute_boq` **once** at the end (see explode / recalc / clone).

Relevant code: `doctype/boq/boq_rollup.py` (`compute_boq_totals`, `recompute_boq`),
`doctype/boq_item/boq_item.py` (`roll_up_item_rate`), `doctype/boq_sub_item/boq_sub_item.py`.

---

## 4. Controllers

| Doctype | Hook | Behavior |
|---|---|---|
| **BOQ** | `before_insert` | default company from project; stamp `prepared_by/date`; default `status=Draft`, `revision=1` |
| | `validate` | default company; `compute_boq_totals(self)` |
| | `on_trash` | cascade-delete the tree — **Sub Items → Items → Groups** |
| **BOQ Item** | `validate` | `planned_amount = planned_qty × rate`; `actual_amount = actual_qty × rate`; default `driving_qty = planned_qty`; normalize `quantity_source`; **project-scope check** |
| | `on_update` | push `work_package` + `cost_head` down to its sub-items (denormalized join keys); `recompute_boq` |
| | `on_trash` | delete its sub-items under the `boq_item_deleting` flag; `recompute_boq` once |
| **BOQ Sub Item** | `validate` | snapshot `rate`+`uom` from Rate Master; `coefficient = qty_per_unit`; `amount = qty_per_unit × rate`; inherit parent's WP/cost-head when unset |
| | `after_insert` / `on_update` / `after_delete` | `roll_up_item_rate(boq_item)` (skipped if the parent item is mid-delete) |
| **BOQ Group** | `on_trash` | (group-level cleanup) |

**Project-scope validation** (`BOQ Item._validate_project_scope`): an item's `task` and
`work_package` must belong to the **BOQ's own project** — you can't cost another project's
work into this BOQ; otherwise it `frappe.throw`s.

---

## 5. Workflow

```
Draft ──submit_boq──► Submitted ──approve_boq──► Approved
  ▲                                                 │
  └──────── create_revision (new Draft) ◄───────────┘   approving a revision
                                                         SUPERSEDES the prior Approved
Approved (prior) ──────────────────────────────► Superseded
```

- **`submit_boq`** — `Draft → Submitted`. Requires write.
- **`approve_boq`** — `Draft/Submitted → Approved`; **supersedes any other `Approved` BOQ of
  the same project** (→ `Superseded`), so a project has at most **one Approved BOQ**. Stamps
  `approved_by/date`. Gated server-side to **`BOQ_APPROVE_ROLES`**.
- **No un-approve.** To change an Approved BOQ you raise a **revision** (a fresh Draft via
  `create_revision`); approving it supersedes the old one.
- **Draft-only edits:** `explode_item` and `import_template` enforce `_require_draft`; the
  frontend also gates the edit UI on `status === "Draft"`.

---

## 6. Whitelisted API — `buildsuite_core/api/boq.py`

Reads and plain CRUD on the tree go through the generic data adapter
(`frappe.client.*`). Only the operations below need the API. Frontend wrappers live in
`frontend/src/utils/boqApi.js`.

| Endpoint | Signature | Purpose |
|---|---|---|
| `submit_boq` | `(boq)` | Draft → Submitted |
| `approve_boq` | `(boq)` | Approve; supersede sibling Approved; role-gated |
| `explode_item` | `(boq_item)` | Rebuild an item's sub-items from its Assembly (Draft only, idempotent) |
| `recalculate_actuals` | `(boq)` | For task-linked items: `actual_qty = planned_qty × task.progress%` |
| `create_revision` | `(boq, source_sco=None, title=None)` | Clone into a new Draft revision (`revision = max+1`, `base_revision = src`) |
| `clone_boq` | `(from_project, to_project, from_work_package=None, to_work_package=None, title=None)` | project→project copy, or WP→WP retag within a project |
| `import_template` | `(boq, estimate_template)` | Seed groups+items from an Estimate Template into a Draft BOQ |

### 6.1 Assembly explosion — `explode_item`
Draft only. Deletes the item's existing sub-items, then inserts one `BOQ Sub Item` per
assembly component (`qty = coefficient × driving_qty`), stamping the item's WP/cost-head and
`source_assembly`. Sets `item.quantity_source = "Assembly"`, `item.rate = assembly.rate_per_unit`,
and `planned_qty = driving_qty = driving`. Wrapped in `boq_skip_rollup`, with a single
`recompute_boq` at the end. Idempotent (re-exploding replaces the sub-items).

### 6.2 Actuals — `recalculate_actuals`
For every item with a `task`, sets `actual_qty = planned_qty × task.progress / 100` and
`actual_amount = actual_qty × rate`. Batch-flagged; one `recompute_boq` at the end. (Task
progress is itself server-derived — see the main CLAUDE.md progress rules.)

### 6.3 Revisions & clones — `_clone_tree`
`_clone_tree(src_boq, dst_boq, reset_actuals=True, src_wp=None, wp_override=None, drop_wp=False)`
copies groups → items → sub-items from one BOQ into another.
- **`create_revision`** — same project, `revision = max+1`, `base_revision = src`, copies
  `margin_rate`/`tax_rate`. Used by the **SCO → BOQ revision** tie-in (`source_sco` set;
  see `api/sco.py::create_boq_revision`).
- **`clone_boq`** — two modes:
  - *project → project*: a new Draft BOQ on the target, WP tags dropped (`drop_wp`).
  - *WP → WP (same project)*: retag the source WP's lines onto the target WP on the project's
    latest BOQ (`src_wp` + `wp_override`).

### 6.4 Template import — `import_template`
Seeds groups + items from an `Estimate Template` into a Draft BOQ (reusing existing groups by
name). Assembly rows auto-explode; Resource rows get a single rate-analysis sub-item.

---

## 7. Permissions

`buildsuite_core/permissions/setup.py` → `setup_boq_permissions()` applies `BOQ_ROLE_PERMS`
across `BOQ_DOCTYPES = (BOQ, BOQ Group, BOQ Item, BOQ Sub Item)`.

- **Full CRUD** — the estimation roles `_ESTIMATION_ROLES`:
  **BuildSuite Administrator, Director, PM, Estimator, QS** (`_BOQ_FULL`).
  *System Manager* is omitted here but keeps native full perms on custom doctypes.
- **Everyone else: no access** (the Estimation workspace is hidden from them). *M2 tightened
  this from the earlier "read for Site Engineer / Foreman / Accountant / HR".*
- **Approve is separately gated** (server-authoritative, in `approve_boq`) to
  **`BOQ_APPROVE_ROLES` = Director, PM, Administrator, System Manager**.
- The tree's link pickers resolve `BOQ_LINKED_MASTER_DOCTYPES` (UOM, Construction Rate Master,
  Assembly, Estimate Template), so BOQ-readable roles get read on those.

The backend is always authoritative; the SPA's `usePermissions()` only hides buttons that
would fail.

---

## 8. Frontend — `frontend/src/views/`

- **`BoqView.vue`** — the BOQ list (search across id/title; a project picker to create a new BOQ).
- **`BoqDetailView.vue`** — the three-level tree editor + roll-up summary.
  - **Loads** the BOQ via `adapter.read("BOQ", id)`, and the tree as **three separate lists**
    via `adapter.list` filtered by `boq` (`childList("BOQ Group")`, `"BOQ Item"`,
    `"BOQ Sub Item"`), grouped client-side (`boqItemsByGroup`, `boqSubItemsByItem`).
  - **CRUD** on groups/items/sub-items via `adapter.create/update/remove`.
  - **Workflow / explode / revision / clone / import / recalc** via the whitelisted
    `boqApi.*` wrappers.
  - **Group/Item codes are optional** — blank auto-generates (`nextGroupCode` → `A, B, C…`;
    `nextItemCode` → `{group}.NN`), computed client-side so the backend always receives a code.
  - **Tree search** filters the tree to matching paths (code / description / unit / rate-master),
    auto-expands them, and highlights matches.

Data seam: `createDataAdapter(store)` → `remoteDataAdapter` (real Frappe via `frappe.client.*`)
by default; `VITE_DATA_MODE=local` uses the Pinia seed. See `frontend/DEVELOPER_GUIDE.md`.

---

## 9. Invariants & gotchas

- **Amounts + assembly-item rates are server-derived.** Never POST `planned_amount`,
  `actual_amount`, `total`, or an assembly item's `rate` from a form.
- **`code` is display, docname is the key.** Renaming a code never breaks the tree.
- **The `boq` link is denormalized** on every level for flat queries — keep it consistent when
  writing rows (clone/explode/import already do).
- **Batch ops set `frappe.flags.boq_skip_rollup`** to avoid O(n) re-saves; they call
  `recompute_boq` exactly once at the end. If you add a bulk mutation, follow the same pattern.
- **Cascade delete is in code** (`BOQ.on_trash`, `BOQ Item.on_trash`), not the DB. The
  `boq_item_deleting` flag stops a sub-item's delete-rollup from re-saving a parent that is
  itself being deleted.
- **One Approved BOQ per project** — `approve_boq` supersedes the rest.
- **Draft-only structural edits** — enforced by `_require_draft` in the API; mirror this in any
  new mutating endpoint.
- **Backend touching whitelisted methods / workflow / permissions → `bench migrate`** and a
  real browser pass before calling it done (see main CLAUDE.md §3).
