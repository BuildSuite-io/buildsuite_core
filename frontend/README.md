# BuildSuite Core — Frontend

The Vue 3 single-page app for the `buildsuite_core` Frappe app. In production it is
built and served by Frappe at the app route (`/core`); it talks to Frappe over the
standard REST/`frappe.client` API using the logged-in session.

## Stack

Vue 3 (`<script setup>`) · Vite · Pinia · Vue Router · Tailwind · frappe-ui

## Develop

Requires a running bench with `buildsuite_core` installed (Node ≥ 24).

```bash
yarn install
yarn dev      # Vite dev server on :5173, /api proxied to the bench backend
```

The dev server proxies `/api` to the local Frappe backend (port read from the
bench's `sites/common_site_config.json`; override with `VITE_FRAPPE_HOST`). Log
in through the app — auth, permissions and data all come from Frappe.

## Build

```bash
yarn build    # → ../buildsuite_core/public/frontend  (served by Frappe at /core)
```

`bench build` runs this automatically. After a manual build, `bench --site <site>
clear-cache` so Frappe serves the new bundle.

## Test (Cypress, real backend)

```bash
yarn test         # headless    (needs `bench start` + the built bundle)
yarn test:open    # interactive runner
```

Provision the persona test users once before the suite:

```bash
bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users
```

`baseUrl` defaults to `http://localhost:8001`; override with `CYPRESS_BASE_URL`.

## Layout

```
src/
  router/        routes (history base = the app route, e.g. /core)
  stores/        Pinia store + the data adapter over frappe-ui resources
  layouts/       DeskShell (sidebar + topbar)
  components/    desk/ primitives (DeskPage, DeskList, DeskForm, …) + shared UI
  views/         one file per page
  composables/   usePermissions, useFormErrors, …
  utils/         session, appRoute, formatting helpers
cypress/         real-backend e2e specs
```

## Architecture & patterns

See [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) — the data-adapter seam, the Desk
primitives (`DeskPage` / `DeskList` / `DeskForm` …), `usePermissions`, forms &
server errors, routing, file uploads, and dark mode, each with copy-paste examples.

See the repo-root `README.md` for the full app, the local dev gate (`make check`),
and contribution guidelines.
