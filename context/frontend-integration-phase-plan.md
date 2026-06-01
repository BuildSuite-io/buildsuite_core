# BuildSuite Core Frontend Integration Phase Plan

Created: 2026-06-01
Scope: Integrate the Vue prototype into the Frappe app before replacing local seed data.

## Architecture Decision

Use the CRM integration model as the primary blueprint (server-side permission gate, explicit dev boot hydration, route-level UI access control), and borrow LMS patterns only where useful (path flexibility / guest-oriented route behavior).

## Phase 0: Lock Route and Access Model

- Set canonical app route to /buildsuite_core.
- Define allowed roles now.
- Implement backend app-level permission function (check_app_permission equivalent).

Deliverable:
- Single source of truth for who can access BuildSuite UI and APIs.

## Phase 1: Wire Frappe Route to Frontend Shell

- Add website route rules in hooks for:
  - /buildsuite_core
  - /buildsuite_core/<path:app_path>
- Add app selector permission hook in add_to_apps_screen.

Deliverable:
- Deep links and refresh on nested frontend routes work through Frappe routing.

## Phase 2: Create Backend Boot Contract

- Add portal page backend and template files:
  - buildsuite_core/www/buildsuite_core.py
  - buildsuite_core/www/buildsuite_core.html
- Expose boot context keys at minimum:
  - csrf_token
  - site_name
  - read_only_mode
  - lang / text_direction
  - timezone
  - feature flags needed by frontend

Deliverable:
- Frontend gets server-derived runtime context in both prod and local builds.

## Phase 3: Replace Prototype Vite Setup with Frappe-Compatible Build

- Move prototype frontend into app-owned frontend workspace.
- Update Vite config to use frappe-ui vite plugin style:
  - frappeProxy: true
  - jinjaBootData: true
  - buildConfig.indexHtmlPath -> buildsuite_core/www/buildsuite_core.html

Deliverable:
- Build artifacts and HTML entry are generated for Frappe consumption.

## Phase 4: Add Dev Boot Parity

- In frontend main entry, in DEV mode call get_context_for_dev before app mount.
- Hydrate window with returned boot keys.
- Then mount app.

Deliverable:
- Dev and prod runtime behavior match (especially CSRF and boot data).

## Phase 5: Add Frontend Session and Access Guards

- Add session store based on user_id cookie.
- Add router guard logic:
  - if anonymous -> redirect to login with redirect-to
  - if logged in but unauthorized role -> not-permitted page
- Add server-side permission checks for APIs (never rely on UI-only checks).

Deliverable:
- Access is enforced consistently in UI and backend.

## Phase 6: Keep Seed Data, Add Data Adapter Seam

- Keep current local Pinia/localStorage behavior intact.
- Introduce an adapter layer with two modes:
  - local mode (existing behavior)
  - remote mode (Frappe API)

Deliverable:
- Incremental backend migration path without freezing product work.

## Phase 7: Migrate Data in Safe Vertical Slices

- Start with read-only APIs (dashboard cards, lookup lists).
- Migrate one bounded CRUD module next.
- Keep heavy mutation paths and uploads until CSRF/permission paths are fully stable.

Deliverable:
- Working hybrid system with low-risk rollout.

## Phase 8: CSRF and Upload Hardening

- For all manual upload/XHR/fetch mutation paths, send X-Frappe-CSRF-Token from window.csrf_token.
- Use frappeRequest as default resource fetcher for non-upload API interactions.

Deliverable:
- Reliable write/upload behavior in dev and prod.

## Phase 9: Validation Gate Before Seed Replacement

Validate all of the following before replacing seed data:

- Direct open of /buildsuite_core works.
- Browser refresh on deep route works.
- Login redirect and return path works.
- Unauthorized users are blocked by backend and UI.
- Upload succeeds with CSRF in dev and prod.
- Route guard behavior is deterministic for all supported roles.

Deliverable:
- Production-ready integration baseline.

## Suggested Execution Order

1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5
7. Phase 8
8. Phase 6
9. Phase 7
10. Phase 9

Rationale:
- Establish access + routing + runtime contract first.
- Stabilize CSRF/write paths before partial API migration.
- Replace seed data only after validation gate passes.
