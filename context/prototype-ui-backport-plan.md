# Prototype UI Backport Plan (Sessions 96 → 130)

Created: 2026-06-11
Goal: Bring the production Vue app (`frontend/`) up to the prototype's current UI (`context/buildsuite-core-demo/`, Session 130) **without** disturbing the deliberate Frappe-API plumbing that was added during integration.

---

## 1. Situation

- **Prototype** (`context/buildsuite-core-demo/`) is its own git repo, currently at **Session 130**. UI evolved heavily since production last aligned.
- **Production** (`frontend/`) was last aligned to roughly prototype **Session 95** (commit `ea5ccc0` "Sessions 72–95 backport"). Since then production added its own integration layer.
- The divergence is **two-directional**: the same view files differ on UI *and* on plumbing. A file copy is wrong; each file needs semantic reconciliation.

### Replay source material (important)
The prototype git history is **squashed** in the target range:
- Sessions **96–121** → one commit `ceee21b` ("Stage Planning workflow + Stage Review + user mgmt").
- Sessions **122–130** → clean, individual commits.

Therefore the replay **script** is the per-session narrative in `context/buildsuite-core-demo/CLAUDE.md §10`; the **diff source** is the prototype git tree (squashed where noted). Work proceeds in strict session order 96 → 130.

---

## 2. The invariant boundary (memorize this)

For every file touched, **preserve production's plumbing, port the prototype's UI.**

### KEEP (production — never overwrite from prototype)
- **Data layer**: `createDataAdapter(store)` + `adapter.list(...)` resources, `useDocTypeList`, `DocTypeListView`, `createResource` — anywhere production reads from Frappe instead of `store.<slice>`.
- **Route paths**: production dropped the `/app/` prefix (router base is `/client`). Prototype links like `/app/tasks/new` become `/tasks/new`.
- **Dark mode**: production has ~154 `dark:` classes; the prototype has ~1. Prototype "dark-mode fix" sessions (107, 115, 117) are **already solved differently** in production. Porting markup must **re-apply** production's `dark:` variants — never strip them.
- **Server-side pickers**: `DeskLinkPicker`, `DeskSortControl` (production-only, for Frappe server-side search/sort).
- **Frappe field names**: backend names (e.g. Task Update fields) per `context/implementation-progress.md` — do not revert to prototype aliases.
- **Integration utilities**: `FrappeUserBadge`, `useFormErrors`, `parseFrappeError`/`frappeError.js`, `appToast`, `session.js`, `stores/session.js`, adapters, auth guards.

### PORT (prototype — bring forward)
- Layout/markup structure, column sets, KPI strips, section ordering, cards.
- New screens & components (see scope below).
- Copy, labels, workflow step changes, field show/hide decisions.
- Styling refinements **expressed as light-mode classes**, then re-dressed with production's `dark:` variants.

### Gating (per user decision)
Production already has **persona-based backend gating**; personas map to the prototype's roles. Future intent: drive the frontend off user persona instead of the role switcher.
- **Preferred**: port the prototype's gating call-sites (`v-if="store.canCreateTask()"`, `v-if="store.canReadTasks"`, etc.) but back them with production's persona-aware permission source.
- **Acceptable fallback**: if wiring is awkward for a given screen, **defer** that screen's gating (port visual UI only) and leave a `// TODO(gating): wire to persona` marker. Do not wire the prototype's fake localStorage getters into production.

---

## 3. Scope (locked from user answers)

**In scope**
- All UI refinements to screens that already exist in production (Sessions 96–123 themes).
- **Stage Review dashboard + delay-reason gate** — net-new: `StageReviewView.vue`, `StageDelayReasonModal.vue`, delay-log section, route + nav wiring.
- **User management** — net-new: `NewUserView.vue` + create/edit/persona/email-stub flow on the Users settings page.
- Permission-gating parity (Sessions 124–130) wired to persona, or deferred per the fallback above.

**Out of scope (explicitly skip)**
- Home / ERPNext workspace **shell rework**: `ErpNextShell.vue`, `HomeWorkspaceView.vue`, `ErpNextWorkspaceView.vue`, `erpnextWorkspaces.js`, `WorkspaceIcon.vue`. Production keeps `AppHomeView` + `AccountingWorkspace`.
- Any prototype data-layer code (`store.*` localStorage behavior) — production uses adapters.

---

## 4. Per-session procedure (the loop)

For each session N from 96 to 130:

1. **Read the spec**: `CLAUDE.md §10 → "Session N"` narrative (what changed, which files, why).
2. **Get the diff**: for N ≥ 122, `git -C context/buildsuite-core-demo show <commit>`; for 96–121, diff the relevant file(s) against the squashed tree and use the narrative to isolate that session's slice.
3. **Classify each hunk** as UI (port) or plumbing (skip) using §2.
4. **Apply to production** the UI hunks, translated to production's idioms: `/app/`→`/`, `store.<slice>`→adapter resource, re-apply `dark:` variants, keep Frappe field names, route gating through persona.
5. **Build**: `cd frontend && npm run build` (catches template/JS errors). No test runner exists; build is the gate.
6. **Record**: tick the session in §6 with a one-line note on what was ported vs. skipped.
7. **Commit** per session (or per thematic slice) on a dedicated branch, mirroring the prototype's session-commit discipline.

Smoke-test in the dev environment (`build.local`) at the end of each thematic slice, not every session.

---

## 5. Thematic slices (strict order preserved within)

Sessions are replayed in numeric order; these clusters tell you where to build + smoke-test together and which sessions touch the same files.

| Slice | Sessions | Theme | Primary files |
|---|---|---|---|
| A | 96–101, 110, 113, 116, 122, 123 | Stage Planning workflow rework (task picker, Draft→Approval, field drops, inline planned-qty, default 100%, approver-only delete, header wrapping, +Add out of table chrome, Task-edit hierarchy) | `StagePlanningsView`, `StagePlanningDetailView`, `NewStagePlanningView`, `StageTaskPicker`, `TaskFormModal`, ProjectDetail Stage tab |
| B | 102, 104–109 | **Stage Review dashboard + delay-reason gate (NEW)** | `StageReviewView` (new), `StageDelayReasonModal` (new), router, nav |
| C | 103, 111, 112, 115, 117 | Stage Details restructure (KPI strip + cards) + dark-mode contrast (verify prod already covers) | `StagePlanningDetailView`, ProjectDetail tabs, dashboard tile |
| D | 114 | `window.confirm()` → `ConfirmDialog` rollout (prod already has `ConfirmDialog.vue` — audit call-sites) | app-wide confirm call-sites |
| E | 118, 120, 121 | Settings hub icon/tile styling; back-link removal; persona-pill unification | `SettingsHubView`, settings pages, `UsersView` |
| F | 119 | **User management create/edit (NEW)** | `NewUserView` (new), `UsersView` |
| G | 107, 115, 117 | Dark-mode fixes — **mostly verify/no-op** (prod is ahead) | Stage Review, project tabs, dashboard tile |
| H | 124–130 | Permission-matrix gating (PM/SiteEng/Foreman) — wire to persona or defer | gating call-sites across execution screens |

(Slices C/G overlap on dark-mode sessions; handle the dark-mode check once, in order.)

---

## 6. Session tracker

Status: ⬜ todo · 🔶 in progress · ✅ done · ⏭️ skipped (with reason)

| # | Session title (abbrev) | Status | Notes |
|---|---|---|---|
| 96 | Stage Planning rework: smart task picker + Draft→Approval | ✅ | Mostly pre-integrated. Backend uses **Frappe-native Workflow** (`workflow_state` Link + workflow.json fixture; states Draft/Pending Approval/Approved/Rejected/Cancelled; role-gated transitions). Done already: state-dispatched action buttons, 2-step New Stage wizard, StageTaskPicker, action-button gating. **Ported this session:** StagePlanningsView State column (`workflow_state` StatusBadge) + workflow-state filter (DeskSelect↔chip) + `?status=` deep-link honor. **Reject popup — IMPLEMENTED (follow-up):** added `reject_reason` field on the Stage Planning doctype + whitelisted `reject_stage_planning(name, reason)` (persists reason to DB before `apply_workflow`, since apply_workflow reloads from DB; `validate()` enforces a reason on Rejected). Frontend Reject button opens a required-reason popup; reason shown in a Rejected banner. **Workflow change:** removed the `Rejected → Revise` transition (in `permissions/setup.py _STAGE_TRANSITIONS`, the authoritative source, + the workflow fixture) — Rejected is now terminal. **Still deferred (no backend field):** activity feed (`stage.activity[]`) — would use Frappe's native document timeline. **Superseded (do not port):** `approval_required_role` on Project — production uses Frappe Workflow transition roles instead. **Deferred:** prototype's client-side "Pending approvals first" sort — doesn't map onto server pagination; revisit if needed. |
| 97 | New Stage wizard: trim step 1 + drop embedded picker footer | ⬜ | |
| 98 | Tasks-in-stage: inline planned-qty edit + drop Unit col | ⬜ | |
| 99 | Default planned quantity = 100% | ⬜ | |
| 100 | Approved stages: Delete is approver-only | ⬜ | |
| 101 | Stage view: drop planned-count/-completion; neutralize task-name colour | ⬜ | |
| 102 | Stage Review dashboard + delay-reason gate | ⬜ | NEW screen |
| 103 | Stage Planning tab: neutralize stage-title colour | ⬜ | |
| 104 | Stage Review: planned vs actual progress explicit | ⬜ | |
| 105 | Stage Review row: single overlaid bar + planned tick | ⬜ | |
| 106 | Stage Review list: full-width CSS-grid rows | ⬜ | |
| 107 | Dark-mode fixes on Stage Review | ⬜ | verify vs prod |
| 108 | Delay reason shape → ERPNext Delay Log | ⬜ | |
| 109 | Delay reasons → full-width section after Tasks | ⬜ | |
| 110 | Tasks-in-stage: Status pill two-line wrap | ⬜ | |
| 111 | Stage Details: KPI strip + carded layout | ⬜ | |
| 112 | Stage details card: drop redundant Stage-name row | ⬜ | |
| 113 | Post-Revise Draft: save-first, Submit optional | ⬜ | |
| 114 | window.confirm → ConfirmDialog app-wide | ⬜ | prod has component |
| 115 | Project tabs: dark-mode contrast | ⬜ | verify vs prod |
| 116 | Stage Planning tab: PLANNED START two-line header | ⬜ | |
| 117 | Project Dashboard tile: dark-mode title contrast | ⬜ | verify vs prod |
| 118 | Settings hub: icon + tile styling | ⬜ | |
| 119 | User management: create + edit + persona + email stubs | ⬜ | NEW screen |
| 120 | Settings: back-link removed; persona-pill gap fix | ⬜ | |
| 121 | Users list: persona chip unified neutral style | ⬜ | |
| 122 | +Add / +Upload lifted out of custom-table chrome | ⬜ | |
| 123 | Task edit modal: Hierarchy (Project RO + WP editable) | ⬜ | |
| 124 | M1 permission matrix wired into store + UI gating | ⬜ | persona/defer |
| 125 | TPE create unconditional for PM/SiteEng/Foreman | ⬜ | persona/defer |
| 126 | PM complete permission within their projects | ⬜ | persona/defer |
| 127 | PM unconditional CRUD on execution surface | ⬜ | persona/defer |
| 128 | PM unconditional Project edit + delete | ⬜ | persona/defer |
| 129 | Site Engineer: create + edit-own + submit-own | ⬜ | persona/defer |
| 130 | Foreman: same create + edit-own + submit-own | ⬜ | persona/defer |

---

## 7. Risks & guardrails

- **Dark-mode regression** — the top risk. After every ported template, grep the production file for lost `dark:` variants before building.
- **Route regression** — never let an `/app/`-prefixed link land in production.
- **Data-binding regression** — never let `store.tasks`-style direct localStorage reads replace an adapter resource.
- **Gating leakage** — a ported `v-if` backed by a fake getter that always returns true would expose actions to the wrong persona. Wire to persona or remove the `v-if` and defer with a TODO.
- **Field-name drift** — keep backend Frappe field names; do not reintroduce prototype aliases.

Build is the only automated gate (`npm run build`); pair it with a manual smoke test per slice on `build.local`.
