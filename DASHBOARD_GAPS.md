# Dashboard Live-Data Gaps Report

_Not committed — working notes for the "wire all dashboards to live data (M1–M3)" pass._
_Generated 2026-08-05._

## 1. Executive summary

Every **reachable** dashboard in the app is now backed by live Frappe/ERPNext data.
The remaining mock-backed views (the 11 role "landings") are **dead code** — not wired to
the router, reachable by no navigation path — so they were left untouched by design.

| # | Dashboard | Route | Reachable | Data backing | Status |
|---|-----------|-------|-----------|--------------|--------|
| 1 | **App Home** | `/home` (`AppHomeView`) | ✅ (app index) | `api.home.get_home_dashboard` | **LIVE — this pass (PR #141)** |
| 2 | **Desk Overview** | `/dashboard` (`DashboardView`) | ✅ | `api.home.get_home_dashboard` | **LIVE — this pass (PR #141)** |
| 3 | **Project Dashboard** | `/project-dashboard` | ✅ | `api.project_dashboard.get_project_dashboard` | LIVE (PR #140, not yet merged to `develop`) |
| 4 | **Procurement Dashboard** | `/procurement-dashboard` | ✅ | `api.procurement.get_dashboard` | LIVE (pre-existing) |
| 5 | **Equipment Dashboard** | `/equipment-dashboard` | ✅ | `api.equipment.get_dashboard` | LIVE (pre-existing) |
| 6 | **Subcontractor Dashboard** | `/subcontract-dashboard` | ✅ | `useDocTypeList` (live doctype reads) | LIVE (pre-existing) |
| 7 | `HomeView` (launcher grid) | — | ✅ | workspace config only (no data metrics) | N/A (nav only) |
| — | 11 role landings | _none_ | ❌ unreachable | mock store / hardcoded | **Out of scope (dead code)** |

**Net result of M1–M3:** 6 of 6 reachable dashboards are live. Home + Desk overview were
the only reachable ones still on the mock store; both are converted in PR #141.

## 2. What PR #141 delivered

New whitelisted aggregator `buildsuite_core/api/home.py::get_home_dashboard()` — one
company-scoped read, computed server-side (scales to the ~1,400-project dataset on
`bs.local`), returning:

- **KPIs:** `active_projects`, `open_tasks`, `overdue_tasks`, `pending_scos`,
  `progress_today`, `users`, `total_order_book`.
- **`projects`** — active root projects: id, name, client, status, progress, budget (BOQ
  contract value → `estimated_costing` fallback), PM, and a schedule **tone**
  (danger/warning/success) computed from planned window vs. progress.
- **`pending_scos`** — Scope Change Orders in "Pending Approval" (title + cost impact).
- **`tasks_in_progress`** — `Working` tasks with progress + assignee (from `_assign`).

Both `AppHomeView` and `DashboardView` are now thin renderers. The home greeting reads the
**live session user** (`useSessionStore` → resolved to full name via `useUserNames`),
replacing the mock `store.user`.

## 3. Data gaps — metrics with NO live source yet

These are surfaced honestly (shown as pending / "no source", never faked). They need new
backend doctypes or fields before they can go live — same gaps the Project Dashboard hit.

| Gap | Where it appears | Why it can't be live yet |
|-----|------------------|--------------------------|
| **Labour / Material / Overhead** cost heads | Project Dashboard `cost.heads` | No cost-type classification on postings; only Subcontractor (bills) and Machinery (usage) have a live source. |
| **Man-days on site** | Project Dashboard `activity.man_days` | No attendance / site-labour doctype exists. |
| **Goods Receipt Notes (GRN)** | (Store Keeper landing — dead) | ERPNext "Goods Receipt Note" doctype doesn't exist here; `Purchase Receipt` is the nearest live proxy (used by Project Dashboard deliveries). |
| **HR headcount / labour-vs-office** | (HR Manager landing — dead) | No Frappe HR (Employee/Attendance) data seeded. |
| **RA bills to pay / variance flags / petty-cash balance tiles** | (Accountant landing — dead) | Hardcoded illustrative literals in the prototype; real values live in Finance doctypes but were never wired. |
| **Tenders due / win-rate** | (Estimator landing — dead) | No tender/opportunity pipeline doctype. |

None of these block the reachable dashboards — they are either already shown as "pending"
(Project Dashboard) or live only on the dead landing views.

## 4. The 11 role landings — recommendation

`frontend/src/views/landings/*` (Accountant, Admin, Director, Estimator, Foreman,
HRManager, PM, Procurement, QS, SiteEngineer, StoreKeeper) are **imported nowhere** — no
route, no role→landing map, no component reference. A whole-`src` search for "Landing"
finds only `style.css` and a comment. They are legacy prototype views left over from an
earlier role-first navigation concept that was replaced by the workspace launcher + the
Desk overview.

Wiring them to live data now would be wasted effort: there is no navigation path to reach
them, and several (Accountant/HR/StoreKeeper) are almost entirely hardcoded literals that
would need new backend doctypes (§3) rather than simple wiring.

**Recommended decision (pick one):**

1. **Delete them** — cleanest; the workspace launcher + Desk overview already cover the
   "landing" role. _(Recommended.)_
2. **Revive intentionally** — first design a role→landing route/selection mechanism, then
   wire each to live data. This is a feature project, not a data-wiring pass, and depends
   on the §3 backends for the finance/HR/stock roles.

Until that decision is made, they should be treated as inert — they render for no one.

## 5. Verification

- `bench --site bs.local execute buildsuite_core.api.home.get_home_dashboard` → returns
  live KPIs + lists (active_projects 1398, open_tasks 1443, users 5, order book ₹1.01Cr on
  the current `bs.local` dataset).
- `vite build` → clean; `AppHomeView` and `DashboardView` compile.
- `pre-commit` → ruff + prettier + eslint pass.
