# Scheduler + Gantt port — sliced implementation plan

Porting the prototype's Task Dependencies + schedule engine + interactive Gantt
(prototype Sessions **135–148**) into the production Vue + Frappe frontend.

**Branch:** `feat/scheduler-gantt` (off `vue`). Merge back to `vue`, then `vue → develop` PR.

> Work ONE slice per session. Each slice is scoped to keep context small so
> auto-compaction doesn't trigger mid-task. Read only the prototype reference
> named in that slice — never the whole 1,751-line `ScheduleView.vue` at once.

---

## Locked decisions (from planning)

1. **Dependency storage** — a **custom child table on Task**: `predecessor` (Link
   Task) + `dependency_type` (Select FS/SS/FF) + `lag_days` (Int, may be
   negative). One edge row per dependency. **Successors are inferred** (reverse
   query), never stored. This realizes the prototype's `taskDependencies` edge
   contract (§13.4) in the "predecessors stored on the successor" form.
2. **Schedule engine runs on the BACKEND (Frappe Python).** Cascade + conflict
   flagging are server-authoritative. The frontend calls whitelisted methods and
   renders results; it does not own the cascade math.
3. **Scope** — dependencies + scheduler + Gantt only. The non-Gantt prototype
   catch-up (Estimation S131, Estimate Templates / BOQ cost-head S134, Tasks-list
   typeahead S148, TPE list ink S135) is **deferred** to a separate effort.

---

## Data contract (target backend shape)

**Reuse ERPNext's native `Task.depends_on`** child table (child doctype `Task
Depends On`, whose `task` field IS the predecessor) — strictly less surface area
than a new doctype, and a free Desk UI. Add two custom fields to it:

| field | type | notes |
|---|---|---|
| `task` | Link → Task | (native) the predecessor — must come first |
| `dependency_type` | Select | `FS` (default) / `SS` / `FF` |
| `lag_days` | Int | default 0; negative = lead / allowed overlap |

- **Successor** of X = any Task whose `custom_predecessors` contains X (reverse
  query). Never stored.
- **task_type** (Activity / Milestone / Inspection) already drives rendering;
  **Milestone = zero-duration** (start == end), engine treats span as 0.

### Engine rules (mirror the prototype, enforce in Python)
- `FS`: `successor.start ≥ predecessor.end + lag`
- `SS`: `successor.start ≥ predecessor.start + lag`
- `FF`: `successor.end   ≥ predecessor.end + lag`
- Multi-predecessor → **most binding** (MAX earliest-allowed-start across edges).
- Milestone successor → duration forced 0 (move the single date).
- **Calendar days** (working-days/holidays is a later enhancement, not in scope).
- **Cycle guard**: reject an edge that would create a loop (A→B→…→A).
- Two modes (from prototype): **flag-only** (recompute `schedule_conflict` per
  task, move nothing) on indirect edits; **cascade** (`reschedule_downstream`)
  only on an explicit trigger (Gantt drag, "Reschedule downstream" action).

---

## Prototype reference map (read per slice, not all at once)

Reference clone: `context/buildsuite-core-demo/` (pulled to S148). Read the named
file/commit for the slice you're on.

| Concern | Prototype file(s) | Commit |
|---|---|---|
| Dependency slice + engine | `src/stores/index.js` (dep getters ~386, engine ~3178+) | `944d301` (S135 A) |
| Engine rules / self-checks | `src/utils/scheduleSelfChecks.js` | `944d301`, `f8ae8e5` |
| Deps section on Task Detail | `src/views/TaskDetailView.vue` | `aa6fcda` (S135) |
| task_type-aware scheduling | `src/stores/index.js`, forms | `f8ae8e5` (S136 A) |
| Gantt component (1,751 ln) | `src/views/ScheduleView.vue` | `3a58d11` (S135 B), `3949d1d` (S136 B) |
| Gantt polish tail | `ScheduleView.vue` | S137–148 (`44ea5d4`…`eb2c190`) |

To read a session's intent: `git -C context/buildsuite-core-demo show <commit>`.

---

## Slices

Status legend: ☐ not started · ◐ in progress · ☑ done

### Track 1 — Dependencies (foundation)

**◐ Slice 1.1 — Backend: dependency fields + read API**
- ☑ **Bit 1** — add `dependency_type` (FS/SS/FF) + `lag_days` custom fields to the
  native `Task Depends On` child table via `custom_field.py` (idempotent on
  migrate). `task` is the predecessor; successors inferred by reverse query.
- ☐ **Bit 2** — whitelisted `get_project_schedule(project)` → tasks (id, subject,
  task_type, dates, progress, work_package) + each task's predecessor edges
  (predecessor/type/lag); inferred successors derivable from the edge set. Plus a
  **cycle-guard** validation (reject A→B→…→A on Task save).
- **Files:** `custom_property_list/custom_field.py` (done), new
  `buildsuite_core/api/schedule.py`, `hooks.py` (Task validate for cycle guard).
- **Accept:** `get_project_schedule` returns edges; a cyclic edge is rejected.
- **Ref:** `944d301` store dep slice for field shape.

**☐ Slice 1.2 — Frontend: Dependencies section on TaskDetailView**
- Read-only list of predecessors (subject + type + lag) and inferred successors;
  add/remove a predecessor (Task link picker + type + lag inputs). Writes
  `custom_predecessors` via the adapter.
- **Files:** `frontend/src/views/TaskDetailView.vue`, maybe a small
  `DependencyEditor.vue`. **Accept:** add/remove predecessor persists; successors
  list updates. **Context:** one view. **Ref:** `aa6fcda`.

**☐ Slice 1.3 — Frontend: predecessor picker on NewTaskView (optional)**
- Allow setting predecessors at create time. **Files:** `NewTaskView.vue`.
  **Accept:** new task with a predecessor persists the edge.

### Track 2 — task_type / Milestone alignment

**☐ Slice 2.1 — Backend + forms: confirm task_type + Milestone semantics**
- Verify the backend `task_type` field has Activity/Milestone/Inspection; ensure
  Milestone forces start==end (zero-duration) on save. Align create/detail forms.
- **Files:** `custom_field.py` (if field missing), `utils/task.py`,
  `NewTaskView.vue` / `TaskFormModal.vue` / `TaskDetailView.vue`.
- **Accept:** a Milestone task stores a single date; engine sees span 0.
- **Ref:** `f8ae8e5` (S136 A).

### Track 3 — Schedule engine (backend)

**☐ Slice 3.1 — Backend engine core (pure functions)**
- `buildsuite_core/scheduling/engine.py`: earliest-allowed-start per edge
  (FS/SS/FF + lag), most-binding across predecessors, milestone duration 0,
  cycle-safe topological walk. Unit-test against the prototype's
  `scheduleSelfChecks.js` cases.
- **Accept:** engine functions pass ported self-check cases. **Context:** isolated
  module + tests. **Ref:** `scheduleSelfChecks.js`.

**☐ Slice 3.2 — Backend: conflict flagging (flag-only mode)**
- On Task save (date/dep change), recompute `schedule_conflict` (custom Check) for
  the task + immediate neighbours. No movement. Expose flag in
  `get_project_schedule`. **Accept:** a task starting before its predecessor
  allows is flagged.

**☐ Slice 3.3 — Backend: cascade (reschedule_downstream)**
- Whitelisted `reschedule_downstream(task, new_start, new_end)` shifting successors
  duration-preserving (milestones move their single date). Returns the changed
  set. **Accept:** moving a predecessor shifts the chain; no cycles; returns diff.

### Track 4 — Gantt (slice heavily — never port 1,751 lines at once)

**☐ Slice 4.1 — Read-only Gantt skeleton** — timeline axis + one bar/row from
start/end + searchable project picker. Replaces the 149-line stub. Reads
`get_project_schedule`. **Ref:** `3a58d11` (structure only).

**☐ Slice 4.2 — task_type rendering** — Activity bar (progress fill), Milestone
diamond (zero-duration), Inspection gate. **Ref:** `3949d1d`.

**☐ Slice 4.3 — Dependency arrows (read-only)** — draw FS/SS/FF arrows from edges,
plus `schedule_conflict` styling. **Ref:** `3a58d11`, `0dcd808` (subproject deps).

**☐ Slice 4.4 — Drag-move + resize** — update dates via adapter; offer
"Reschedule downstream" calling Slice 3.3. **Ref:** `3a58d11`, `44ea5d4` (inline
date inputs), `db54e7b` (hit-test).

**☐ Slice 4.5 — Draw-dependency by drag** — create a predecessor edge from the
Gantt. **Ref:** `db54e7b`, `4edee65`, `db54e7b`.

**☐ Slice 4.6 — Grouping + summary rows** — opt-in group by Stage/WP, summary bars
+ slip badge, expand/collapse all. **Ref:** `5a94d9f`, `d47a0f5`, `61aa423`.

**☐ Slice 4.7 — Polish tail** — dark-mode colors, label contrast halo, undated
ghosts, slimmer summary bars. **Ref:** S141/147 (`920ff70`, `eb2c190`).

### Track 5 — Non-Gantt catch-up (DEFERRED — out of scope here)
Estimation S131, Estimate Templates/BOQ S134, Tasks typeahead S148, TPE ink S135.
Track separately; several may not exist in production yet.

---

## Working method (keep context small)
- One slice → one commit/PR. Update the ☐/☑ status above as you go.
- At slice start, read ONLY that slice's prototype ref (`git show <commit>` or the
  one named file). Don't open `ScheduleView.vue` whole unless on a 4.x slice, and
  even then read by section.
- Backend slices: apply via `bench --site build.local execute …` and verify with a
  curl/login probe, like the task_status work.
- Frontend slices: rebuild (`cd frontend && npm run build`) before testing against
  `:8001` (bundle is gitignored).
