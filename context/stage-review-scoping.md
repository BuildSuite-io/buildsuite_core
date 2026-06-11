# Stage Review — backport scoping (Slice B: Sessions 102, 104–109)

Created: 2026-06-11
Goal: port the prototype's per-stage **Stage Review dashboard** + **delay-reason gate** into production, backed by real Frappe data where it exists, with explicit scope cuts where the backend isn't there yet.

## 1. Data-availability matrix (prototype dashboard sections → production)

| Dashboard section | Prototype data source | Backend status | Decision |
|---|---|---|---|
| KPI: Tasks / Task progress (actual vs planned) | `stage.stagePlanningTasks[].plannedQty` + `task.progress/status` | ✅ `stage_planning_task.planned_qty` + Task | **Build** |
| KPI + section: Task progress (overlaid bar + planned tick, S104–106) | same | ✅ available | **Build** |
| KPI + card: Labour deployed/movement | `taskProgressEntries` over stage window (`skilledLabour`/`unskilledLabour`) | ✅ `Task Progress Entry` has `task`, `entry_date`, `skilled`, `unskilled` | **Build** |
| Section: Materials — planned vs actual | `activeBoqForProject` + `boqItemsByBoq` | ❌ **No BOQ doctypes** (BOQ is Milestone 2) | **OMIT** until M2 |
| Section: Delay reasons (S108/109) | `stage.delayReasons[]` | ❌ no field/table yet | **Build (new child table)** |
| Section: Stage activity feed | `stage.activity[]` | ❌ no backend activity log | **OMIT** in v1 (Frappe native timeline later) |
| "Delayed" pill + gate | `store.isStageDelayed(id)` | derive in frontend | **Frontend computed** (no backend field) |

**Net production v1 = KPI strip + Task-progress section + Delay-reasons section + Labour-movement card.** Materials and Activity are cut (no backing data).

## 2. Backend changes

### 2a. New child-table doctype: `Stage Delay Reason` (`istable: 1`)
Mirrors an ERPNext-style Delay Log row (S108 shape).

| field | type | notes |
|---|---|---|
| `reason` | Data | reqd. Frontend offers preset suggestions + free text (stored as text, like the prototype). |
| `responsible_party` | Select | `Own / Subcontractor / Client / External / Consultant` |
| `days_delayed` | Int | optional (0/blank = "TBD / ongoing") |
| `note` | Small Text | optional |
| `logged_by` | Link → User | read-only, stamped on insert |
| `logged_on` | Datetime | read-only, stamped on insert |

`in_list_view`: reason, responsible_party, days_delayed.

### 2b. Stage Planning gets a child table field
- `delay_reasons` — Table, options `Stage Delay Reason`, under a new "Delay Log" section. (Append-only in practice.)

### 2c. Whitelisted append method
`add_stage_delay_reason(stage, reason, responsible_party, days_delayed=None, note=None)`:
- permission-gate to project members / approvers,
- append a child row, stamp `logged_by` = session user + `logged_on` = now,
- save, return the new row.

> **⚠ Permission wrinkle to resolve in build:** delays are logged *during execution*, including on **Approved** stages — but the workflow sets `allow_edit = System Manager` for Approved, and `has_stage_planning_permission` restricts write. Logging a delay must NOT require unlocking/revising the stage. Plan: the method treats a delay-log append as a non-edit action — gate it on project-membership (read access) and append the child row without routing through the stage's full workflow edit-lock. (Exact mechanism — child-row insert vs `ignore_permissions`-scoped save — decided in build; flagged so it isn't a surprise.)

### 2d. `is_stage_delayed` — **no backend.** Frontend computes it:
`(planned_end < today AND mean task progress < 100) OR (calendar-expected % − actual % > 15 pts within the window)`.

## 3. Frontend composition

### 3a. New `StageReviewView.vue` (Vue-styled dashboard, route `/stage-plannings/:id/review`)
Inside DeskShell, **not** a Desk record page (matches Project Dashboard's Vue style). Data via adapters:
- `adapter.read('Stage Planning', id)` (+ its `stage_planning_tasks`, `delay_reasons`)
- `adapter.read('Project', stage.project)`
- `adapter.list('Task', filter to the stage's task ids)` — for progress/status
- `adapter.list('Task Progress Entry', filter task ∈ stage tasks AND entry_date in window)` — labour rollup

Sections (top → bottom):
1. **Header** — breadcrumb, stage title, `workflow_state` badge, "Delayed" pill if `isStageDelayed`, project + window, "← Back to stage".
2. **KPI strip (4)** — Tasks (count + done/in-progress) · Task progress (actual% / planned%, +pts vs plan, +calendar-expected sub) · Labour deployed (skilled+unskilled man-days) · Schedule (days overrun / on-window).
3. **Task progress (full width)** — CSS-grid rows (S106): Task · single overlaid bar with planned-% tick (S105) · `actual% / planned%` · variance pill · status. + inline legend.
4. **Delay reasons (full width, S109)** — grid table: # · Reason · Responsible (party pill) · Days (`Nd`/TBD) · Notes · Logged (avatar+name+date). Header shows totals (`N days · M TBD`). "+ Add" opens the modal (non-gate mode).
5. **Labour movement (card)** — skilled + unskilled man-days from progress entries in the window + entry count.

Dark-mode classes throughout (production has dark mode; prototype's S107 dark fixes are re-expressed via production's existing dark utilities — `stage-progress-tick` style class for the planned tick).

### 3b. New `StageDelayReasonModal.vue`
Teleport popup. Fields: Reason (preset `<select>` + "Custom…" → free text), Responsible Party (`<select>` enum), No. of days delayed (optional number), Notes (optional). Calls `add_stage_delay_reason`, emits `saved`. `isGate` prop tweaks copy for the gate flow.

### 3c. Wiring
- Route `stage-planning-review` at `/stage-plannings/:id/review` (props:true).
- **"Stage Review" button** in `StagePlanningDetailView` `#actions` (all states).
- **Delay gate:** on click, if `isStageDelayed` && zero `delay_reasons` → open modal in gate mode; on `saved` → navigate. Else navigate directly.

## 4. Decisions to confirm before building
1. **Delay log = child table on Stage Planning** (`Stage Delay Reason`, §2a/2b) — vs a separate linked doctype. Recommend child table (matches the embedded prototype shape + ERPNext Delay Log convention).
2. **Materials section OMITTED** until BOQ (M2) exists — confirm OK (it's the biggest cut vs the prototype).
3. **Activity feed OMITTED** in v1 (no backend activity log) — confirm OK; could later surface Frappe's native document timeline.
4. **Delay reasons addable on Approved stages** without revising (the §2c permission wrinkle) — confirm that's the intended behavior (it matches the prototype: logging a delay ≠ editing the stage).

## 5. Build order (once confirmed)
1. Backend: `Stage Delay Reason` doctype + `delay_reasons` field on Stage Planning + `add_stage_delay_reason` method → migrate.
2. Frontend: `StageDelayReasonModal.vue` → `StageReviewView.vue` → route + Stage Review button + gate.
3. Build + verify on `build.local` (seed a delayed stage, log a reason, open review).
