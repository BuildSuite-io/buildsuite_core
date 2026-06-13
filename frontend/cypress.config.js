import { defineConfig } from "cypress";

// Real-backend e2e (LMS-style). The suite drives a live Frappe site:
//  - Local iteration: run `npm run dev` (REMOTE data mode) on :5173, whose /api
//    proxy forwards login + data calls to the backend. baseUrl = localhost:5173.
//  - CI / served bundle: `bench build`, then point CYPRESS_BASE_URL at the
//    Frappe-served /client (e.g. http://build.local:8001).
// The Vue app is served under the app route (frontend/src/utils/appRoute.js).
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
  video: false,
  viewportWidth: 1280,
  viewportHeight: 800,

  e2e: {
    baseUrl: process.env.CYPRESS_BASE_URL || "http://localhost:5173",
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
