# Scheduler / Gantt — Developer Documentation

> Ground-truth for the scheduling subsystem: the task-graph data model, the dependency
> math, conflict flagging, the cascade engine, the undo/revision snapshot layer, and the
> Vue Gantt. Derived from `buildsuite_core/api/schedule.py`, `schedule_engine.py`,
> `schedule_snapshot.py`, `permissions/`, `hooks.py`, and
> `frontend/src/views/ScheduleView.vue` + `frontend/src/composables/useScheduleEngine.js`.
> When this doc and the code disagree, **the code wins** — update this file.

---

## 1. What it is

The scheduler is a **dependency-aware Gantt** over a project's **native ERPNext Tasks**.
Tasks carry start/end dates and predecessor edges; moving a task **cascades** a
duration-preserving forward shift to everything downstream, conflicts are **flagged**
(never silently "fixed"), and every cascade is **undoable** (plus named **revisions**).

There is no custom "schedule" doctype — the schedule *is* the set of Tasks in a project
plus their `depends_on` edges. The engine is a pure graph computation layered on top.

---

## 2. Data model

### 2.1 Task — scheduling fields
- **`exp_start_date` / `exp_end_date`** (native) — the working start/finish. These are the
  authoritative schedule dates the Gantt reads and writes.
- **`task_status`** (custom) — BuildSuite status (`Yet To Start / In Progress / In Delay /
  Completed / Blocked`); the native `status` is hidden. (See main CLAUDE.md §5.)
- **`type`** (native Task Type link) — `Milestone` is special: a **zero-duration** point in
  time held on `exp_end_date` only (start collapses to end — see `normalize_milestone_task`).
- **`progress`** (native) — server-derived; drives actuals and status.
- **`project`, `work_package`** — the task's project + optional Work Package tag (used for
  the By-WP grouping).

### 2.2 Predecessors — `depends_on` (child table "Task Depends On")
Each edge row on a Task:
- **`task`** — the predecessor task.
- **`dependency_type`** (custom field) — `FS` / `SS` / `FF` (finish-to-start, start-to-start,
  finish-to-finish). Anything else imposes no timing constraint.
- **`lag_days`** (custom field) — days of lag (positive) or **lead** (negative → overlap).

The custom fields are added to `Task Depends On` in
`custom_property_list/custom_field.py`.

### 2.3 Grouping inputs
`get_project_schedule` also returns the project's **Work Packages** and **Stage Plannings**
(with their task membership + `planned_start`/`planned_end`) so the Gantt can group By Stage /
By WP and roll up progress per group.

---

## 3. The dependency model

`_earliest_start_for_edge(pred, succ, dep)` in `schedule_engine.py` computes the earliest
allowed start for a successor from **one** edge; `_compute_earliest_start` takes the **MAX**
(most binding) across all of a task's predecessor edges.

| Type | Earliest successor start |
|---|---|
| **FS** (finish→start) | `pred.end + lag` |
| **SS** (start→start) | `pred.start + lag` (a milestone predecessor uses its single date) |
| **FF** (finish→finish) | `pred.end + lag − succ_duration` (so the *finish* aligns) |
| other (e.g. SF) | unconstrained (`None`) |

- **Lag vs lead:** `lag_days > 0` pushes later; `< 0` is a lead (overlap allowed).
- **Milestones:** a milestone predecessor collapses every type to "milestone date + lag" (no
  span); a milestone successor has duration 0.
- **Cycle guard:** `validate_task_dependencies` (Task `validate` hook) rejects any edge that
  would create a cycle (`_creates_cycle`); the engine's topological routines also return
  `None`/abort if a cycle is somehow present.

---

## 4. Backend API

### 4.1 `api/schedule.py` (the graph + edges)
| Function | Kind | Purpose |
|---|---|---|
| `get_project_schedule(project)` | @whitelist | The full schedule graph: tasks (+ dates, status, progress, WP, predecessors), work_packages, stages, project bounds |
| `get_task_dependencies(task)` | @whitelist | This task's predecessors + inferred successors |
| `add_task_predecessor(task, predecessor, dependency_type, lag_days)` | @whitelist | Add/update an edge (saves the Task → re-flags conflicts) |
| `remove_task_predecessor(task, predecessor)` | @whitelist | Remove an edge |
| `incomplete_fs_predecessor(task_name, depends_on_rows=None)` | — | Name of an FS predecessor that isn't `Completed` (drives the FS gate) |
| `validate_task_dependencies` / `normalize_milestone_task` | hooks | Cycle guard; milestone single-date normalization |

### 4.2 `api/schedule_engine.py` (the compute)
Pure functions over an in-memory graph (`_load_graph(project)` → `tasks_by_id`, `edges`):

- **`compute_conflicts(root_id, …)`** — **FLAG-ONLY**: `{task_id: (conflict, reason)}` for the
  downstream subgraph. A task conflicts when its dates violate a predecessor constraint. It
  **does not move anything**.
- **`compute_cascade(root_id, …, root_override)`** — **CASCADE**: duration-preserving forward
  shifts in topological order. **Never pulls a task earlier** (slack is preserved); returns
  `moves[]` (downstream only — the root is excluded) or `None` on a cycle.
- **`recompute_schedule_conflicts(root_task)`** — recompute + **persist**
  `schedule_conflict` / `conflict_reason` for the root + its downstream subgraph.
- **`reschedule_downstream(task, new_start, new_end, dry_run)`** — @whitelist. The commit path
  for a move:
  - `dry_run=1` → return `{moves}` as a **preview** (the client also computes this instantly).
  - `dry_run=0` → **capture an undo snapshot** (if anything downstream moves — see §6), then
    save the root + each move under `frappe.flags.in_schedule_cascade` (per-Task write perms +
    progress/stage hooks still run; per-save conflict re-flag suppressed), and
    `recompute_schedule_conflicts` once at the end.

---

## 5. Conflict flagging (flag, don't fix)

Philosophy: moving a task **shifts** its downstream dependents (cascade), but out-of-order
dates that the user creates directly are **flagged**, not auto-corrected.

- Each Task carries `schedule_conflict` (bool) + `conflict_reason` (text).
- **`recompute_conflicts_on_update`** (Task `on_update` hook) re-flags the task's downstream
  subgraph whenever its dates/deps change — **skipped** while `frappe.flags.in_schedule_cascade`
  is set (so a cascade/restore doesn't re-flag per save; it flags once at the end).
- The Gantt renders conflicted bars distinctly and offers "reschedule" to resolve.

---

## 6. Undo + Revisions — `Schedule Snapshot`

A shared snapshot layer (see also `docs/`-adjacent code in
`api/schedule_snapshot.py`). A **`Schedule Snapshot`** doctype (per project) stores a
serialized copy of the project's task dates (`exp_start_date`/`exp_end_date`) with a `kind`:

- **Undo** — captured automatically **right before a group action** (a cascade where
  `reschedule_downstream` moves ≥1 downstream task; a single-task move captures nothing).
  Bounded stack: last `UNDO_LIMIT` (10) per project; older ones auto-prune.
- **Revision** — a named, user-saved restore point.

| Endpoint | Purpose |
|---|---|
| `undo_last(project)` | Pop the newest Undo snapshot, restore it, delete it → repeated calls walk the stack back |
| `save_revision(project, label)` | Save a named Revision of the current schedule |
| `list_snapshots(project, kind?)` | List snapshots for the UI |
| `restore_snapshot(name, capture_undo=1)` | Restore a snapshot; captures an Undo first so the restore is itself undoable |
| `delete_snapshot(name)` | Delete a snapshot |

**Restore** uses the same machinery as the cascade: write dates back via `doc.save()` (per-Task
write perms enforced) under `in_schedule_cascade`, then `recompute_schedule_conflicts` for the
changed tasks. Capture runs with `ignore_permissions` (the user is already permitted to make
the change that triggered it). Permissions on the doctype follow **Task-edit rights**
(`setup_schedule_snapshot_permissions` → `TASK_ROLE_PERMS`).

Scope note: snapshots capture **dates only**, not predecessor edges — matching the
cascade-undo need. Extending revisions to the dependency graph means serializing/restoring
`edges` in the same payload.

---

## 7. Hooks (`hooks.py` → `doc_events["Task"]`)

- **`validate`** (in order): `validate_task_dependencies` (cycle guard) → `normalize_milestone_task`
  → `validate_task_dates` (parent/child bounds) → `update_task_status` → **`enforce_predecessor_gate`**
  (last).
- **`on_update`**: WP/project progress rollups, stage sync/aggregates, and
  `recompute_conflicts_on_update` (downstream re-flag).
- **Daily scheduler**: `utils.task.update_delayed_tasks`.

### The FS gate (`enforce_predecessor_gate`)
A task **can't start** (leave `Yet To Start`/`Blocked`, or log progress) while a
**Finish-to-Start** predecessor isn't `Completed`. Enforced on Task `validate`
(`utils/task.py::enforce_predecessor_gate`) and on Task Progress Entry
(`task_progress_entry.py`), both via `incomplete_fs_predecessor`. A negative lag (lead) does
**not** gate; `SS`/`FF` edges don't gate.

---

## 8. Frontend — `frontend/src/`

### 8.1 `views/ScheduleView.vue` — the Gantt
- **Loads** the graph via `getProjectSchedule`; view-models each task to
  `{id, startDate, endDate, progress, task_type, workPackageId, schedule_conflict, …}`.
- **Move / resize** a bar → optimistic client move → **client-side cascade preview**
  (`computeCascade`) → persist the root → if anything downstream shifts, open the cascade
  modal → **"Apply cascade"** calls `rescheduleDownstream(dry_run=0)` (the authoritative commit
  that also captures the undo snapshot).
- **Zoom** (day/week/month/quarter), **group by** none/Stage/WP with per-group progress
  roll-ups + summary bars, task **search**, dependency **draw/delete** by drag, conflict
  highlighting.
- **Undo** button (depth-badged; `undoLast`) + **Revisions** dropdown (save / list / restore /
  delete) — the §6 snapshot layer.

### 8.2 `composables/useScheduleEngine.js` — client mirror of the engine
Pure JS twins of the Python engine so previews are instant and offline-consistent:
`computeEarliestStart`, `computeConflicts`, `computeAllConflicts`, `hasCycle`,
`computeCascade` (+ `addDays` / `diffDays` / `iso`). The server remains authoritative on
commit; the client version only drives the live preview + conflict tinting.

### 8.3 `utils/scheduleApi.js` — thin fetch wrappers
Over `buildsuite_core.api.schedule.*`, `schedule_engine.*`, and `schedule_snapshot.*`
(GET reads, POST mutations with CSRF; throws `Error(<server message>)`).

---

## 9. Invariants & gotchas

- **`exp_start_date` / `exp_end_date` are the authoritative dates.** `task_status` and
  `progress` are decoupled/derived — never write progress from a form.
- **Cascade only pushes later** — it preserves slack and never pulls a task earlier. To move
  something earlier, move it directly.
- **`moves` excludes the root** — a "group action" is `len(moves) >= 1`; that's the exact
  condition an undo snapshot is captured on.
- **`frappe.flags.in_schedule_cascade`** suppresses per-save conflict re-flagging during a
  cascade/restore; the caller re-flags once at the end. Mirror this in any new bulk mutation.
- **Milestones are single-date** (`exp_end_date`); `normalize_milestone_task` collapses start
  to end on save. Cascade/engine treat them as zero-duration.
- **Cycles are rejected** at edge-add (`validate_task_dependencies`) and abort the cascade
  (`compute_cascade` → `None`).
- **Snapshots are dates-only** and bounded (last 10 Undo/project). Undo is a **pop** (destroys
  the snapshot); a Revision restore is non-destructive and captures its own Undo first.
- **Backend touching whitelisted methods / hooks / permissions → `bench migrate`** + a real
  browser pass before "done" (main CLAUDE.md §3).
