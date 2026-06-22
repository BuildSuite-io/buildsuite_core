// Custom commands. Mirrors the Frappe LMS pattern (apps/lms/cypress/support/commands.js):
// programmatic login via /api/method/login, plus a few selector helpers. The Vue app
// is served under the app route (see frontend/src/utils/appRoute.js) — use
// cy.visitApp('/projects') so specs stay route-agnostic (track `bench change-app-route`).
import { appUrl } from "../../src/utils/appRoute";

// Persona id -> { user, password }. Provisioned idempotently by
// buildsuite_core.api.cypress_setup.ensure_cypress_users (see the plan / README).
// Password defaults to the Cypress adminPassword config.
const PERSONA_USERS = {
	admin: "cypress-admin@buildsuite.test",
	pm: "cypress-pm@buildsuite.test",
	estimator: "cypress-estimator@buildsuite.test",
	procurement: "cypress-procurement@buildsuite.test",
};

// --- auth --------------------------------------------------------------------

Cypress.Commands.add("login", (email, password) => {
	if (!email) email = Cypress.config("testUser") || "Administrator";
	if (!password) password = Cypress.config("adminPassword");
	cy.request({
		url: "/api/method/login",
		method: "POST",
		body: { usr: email, pwd: password },
		timeout: 60000,
		retryOnStatusCodeFailure: true,
		retryOnNetworkFailure: true,
	});
});

// Log in as a provisioned persona test user (used by the permission specs).
Cypress.Commands.add("loginAs", (persona) => {
	const user = PERSONA_USERS[persona];
	if (!user)
		throw new Error(
			`Unknown persona '${persona}'. Known: ${Object.keys(PERSONA_USERS).join(", ")}`
		);
	cy.login(user, Cypress.config("adminPassword"));
});

// --- selector helpers --------------------------------------------------------

// data-test hook on the BuildSuite Desk primitives (our equivalent of frappe-ui's
// structural [data-slot]/[role] attributes).
Cypress.Commands.add("dt", (name) => cy.get(`[data-test="${name}"]`));

// Visit an in-app path with the current app route base prepended (single-sourced
// from frontend/src/utils/appRoute.js). e.g. cy.visitApp('/projects').
Cypress.Commands.add("visitApp", (path = "") => cy.visit(appUrl(path)));

Cypress.Commands.add("button", (text) => cy.get(`button:contains("${text}")`));
Cypress.Commands.add("link", (text) => cy.get(`a:contains("${text}")`));

// ConfirmDialog (components/ConfirmDialog.vue) — accept / cancel the global confirm.
Cypress.Commands.add("confirmAccept", () => cy.dt("confirm-accept").click());
Cypress.Commands.add("confirmCancel", () => cy.dt("confirm-cancel").click());

// Fill a DeskLinkPicker field: click its trigger (data-test = the picker's
// dataTest prop), optionally type a query into the portalled search popover, then
// pick the first option. Omit `query` to just select the first available option
// (e.g. picking any valid Company when the test doesn't care which).
Cypress.Commands.add("fillLink", (dataTest, query) => {
	cy.get(`[data-test="${dataTest}"]`).click();
	cy.get(".desk-link-picker-popover")
		.should("be.visible")
		.within(() => {
			if (query) cy.get("input").first().clear().type(query);
		});
	// options render inside the same portalled popover (frappe-ui Autocomplete)
	cy.get(".desk-link-picker-popover")
		.find('[role="option"], [data-slot="item"], li')
		.first()
		.click();
});
