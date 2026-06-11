# User Management — backport scoping (Session 119)

Created: 2026-06-11
Goal: port the prototype's User management (create / edit / persona / welcome + reset emails) into production, backed by **real Frappe Users** + the existing BuildSuite roles.

## 1. The model (what production already has)

- **People = Frappe `User`.** Task `owner`, `FrappeUserBadge`, `logged_by`, the session user — all real Frappe Users. There is no Employee doctype in `buildsuite_core`.
- **Persona = a BuildSuite role.** The backend already defines **12 BuildSuite roles** (Director, PM, Estimator, QS, Site Engineer, Foreman, Procurement Officer, Store Keeper, Accountant, HR Manager, Administrator, Project User) in `permissions/setup.py`. These ARE the personas the gating reads (`frappe.get_roles`). Every persona also carries the baseline marker role **`BuildSuite Project User`** (setup.py).
- **The current `UsersView` is NOT real** — it lists the localStorage **seed team** (`store.team`, USR-001..007), with a note that real user CRUD "is part of the Frappe auth layer and is out of prototype scope." This is the gap S119 closes.
- Frappe-native APIs confirmed present: `User.add_roles()/remove_roles()`, `User.send_welcome_mail_to_user()`, `reset_password(user)`, and the `send_welcome_email` check field.

## 2. The fork in the road (decision 1)

**Path A — Real Frappe User management (recommended).** UsersView lists real Users; create makes a real `User` + assigns the persona's BuildSuite role; edit changes persona / enable-disable; welcome + reset use Frappe's native email flows. This matches the prototype's stated intent ("backend auto-assigns Frappe Roles based on persona") and the production direction (use Frappe-native plumbing).

**Path B — localStorage parity.** Rebuild create/edit on `store.team` (fake), exactly mirroring the prototype. Rejected unless you want it: it adds fake user CRUD to a production app whose auth is real.

This doc scopes **Path A.**

## 3. Backend (new whitelisted methods, admin-gated)

All gated to `System Manager` / `BuildSuite Administrator`.

| Method | Does |
|---|---|
| `list_buildsuite_users()` | Returns enabled non-system Users that hold a BuildSuite role, each with derived `persona` (from their BuildSuite role), `full_name`, `email`, `enabled`, last welcome/reset timestamps if tracked. |
| `create_buildsuite_user(full_name, email, persona, enabled=1, send_welcome=1)` | Creates a Frappe `User` (split name → first/last), sets `enabled`, assigns persona role + `BuildSuite Project User`, optionally fires the welcome email. Returns the user. Dedupes on email. |
| `update_buildsuite_user(email, full_name?, persona?, enabled?)` | Edits; on persona change, removes the old BuildSuite persona-role(s) and adds the new one (keeps `BuildSuite Project User`). |
| `send_user_welcome(email)` | `send_welcome_mail_to_user()` (resend). |
| `send_user_password_reset(email)` | `reset_password(email)` — emails a reset link. |

**Persona ↔ role map** (decision 2 — confirm, esp. the last two):

| Persona (frontend id) | BuildSuite role |
|---|---|
| director | BuildSuite Director |
| pm | BuildSuite PM |
| estimator | BuildSuite Estimator |
| qs | BuildSuite QS |
| site-engineer | BuildSuite Site Engineer |
| foreman | BuildSuite Foreman |
| procurement | BuildSuite Procurement Officer |
| store-keeper | BuildSuite Store Keeper |
| accountant | BuildSuite Accountant |
| hr-manager | BuildSuite HR Manager |
| admin | BuildSuite Administrator |
| bsa | System Manager (+ BuildSuite Administrator) |

One persona per user (switching swaps the role). The `BuildSuite Project User` baseline is always present.

## 4. Frontend

- **`UsersView.vue` rebuilt** — lists real Users from `list_buildsuite_users()` (replaces the `store.team` source). Columns: Name · Email · Persona (neutral pill, per S121) · Status (enabled/disabled). Row click → edit modal. `+ New User` in actions (admin-only).
- **`NewUserView.vue` (new)** — create form: Full name (req) · Email (req, format + uniqueness) · Persona select (the 12) · Account status (enabled/disabled) · "Send welcome email" + "Send password-reset link" checkboxes. On save → `create_buildsuite_user` (+ optional email triggers) → route back with a confirmation banner.
- **Edit modal** — change persona / enable-disable / resend welcome / send reset; toasts for queued emails.
- Route `settings-user-new` at `/settings/users/new`; `+ New User` from the hub/list.

## 5. Decisions to confirm
1. **Path A (real Frappe Users)** vs Path B (localStorage parity). Recommend A.
2. **Persona = single BuildSuite role** per the §3 map (confirm `admin` → BuildSuite Administrator, `bsa` → System Manager).
3. **Emails are real Frappe sends** (welcome + reset). Requires SMTP on the site; if not configured they sit in the Email Queue (Frappe handles gracefully, no crash). OK?
4. **List filter**: show only enabled Users holding a BuildSuite role; hide system accounts (Administrator, Guest). OK?
5. **⚠ Known divergence (important):** the REST of the app still resolves people from the legacy localStorage seed team (`store.team` / `teamMember()` / the Task-assignee + Project-PM dropdowns). So a user created here is a **real Frappe User** but will **not** appear in those legacy dropdowns until a separate "migrate people pickers to Frappe Users" pass. S119 = real user administration; rewiring assignee/PM pickers to Frappe Users is a follow-up. Confirm this incremental step is acceptable (vs. doing the bigger people-migration now).

## 6. Build order (once confirmed)
1. Backend: the 5 whitelisted methods + persona↔role map → migrate not needed (no schema; roles already exist).
2. Frontend: `NewUserView.vue` → rebuild `UsersView.vue` (real list + edit modal) → route + hub link.
3. Build + verify on `build.local` (create a user, assign persona, confirm role lands, trigger reset → Email Queue entry).
