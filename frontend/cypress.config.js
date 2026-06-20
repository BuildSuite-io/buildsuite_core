import { defineConfig } from "cypress";

// Real-backend e2e (LMS-style). Like LMS (baseUrl http://pertest:8000), the
// baseUrl is the FRAPPE SERVER itself — the one origin that serves BOTH the
// built Vue bundle (/core, see frontend/src/utils/appRoute.js) AND the API
// (/api/...). cy.login posts a relative /api/method/login that resolves against
// baseUrl, so it hits Frappe directly and the session cookie is same-origin with
// the app cy.visitApp() loads. No Vite dev server, no /api proxy in the loop.
//
// Prereq: the frontend must be BUILT so Frappe serves it — run `bench build`
// (or `cd frontend && npm run build`) before the suite, then `bench start`.
//
//  - Default:  http://localhost:8001  (the running Frappe web server / site)
//  - Override: CYPRESS_BASE_URL=http://<host>:<port> for CI / another site.
//
// NOTE: the Vite dev server (:5173, `npm run dev`) is for live-reload dev only.
// Its /api proxy rewrites the Host header (changeOrigin), which is a different
// path than Frappe's own serving — point Cypress at the Frappe port instead.
// Specs use cy.visitApp('/projects') so they track `bench change-app-route`.
export default defineConfig({
  // cy.login() with no args logs in as the provisioned cypress-admin persona user
  // (full BuildSuite Administrator access) — so the suite never needs the real
  // Administrator password. Provision via buildsuite_core.api.cypress_setup.
  adminPassword: process.env.CYPRESS_ADMIN_PWD || "Cypress-Suite-2026!",

  testUser: process.env.CYPRESS_ADMIN_USER || "cypress-admin@buildsuite.test",

  // Frappe is slow
  defaultCommandTimeout: 20000,

  pageLoadTimeout: 30000,
  retries: { runMode: 2, openMode: 0 },
  video: true,
  viewportWidth: 1280,
  viewportHeight: 800,

  e2e: {
    baseUrl: process.env.CYPRESS_BASE_URL || "http://localhost:8001",
    specPattern: "cypress/e2e/**/*.cy.js",
    supportFile: "cypress/support/e2e.js",
  },

  component: {
    devServer: {
      framework: "vue",
      bundler: "vite",
    },
  },
});
