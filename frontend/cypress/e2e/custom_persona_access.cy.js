// A persona an admin builds from a role BuildSuite does not ship gets exactly what it is configured
// for — the same way a built-in persona does — and nothing else.
//
// The persona "Cypress Plant Coordinator" carries one custom role (no BuildSuite role at all),
// configured by hand as a site admin would:
//   - Workspace Structure: may see Equipment and Procurement
//   - Role Permission Manager: Machinery (create / read / write), Machinery Type (read),
//     Purchase Order (read)
//   - The "BuildSuite Purchase Register" report's roles
// The spec checks each grant works, and that what was NOT granted stays shut.
//
// Requires the user + configuration (idempotent):
//   bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_custom_persona

import { appUrl } from "../../src/utils/appRoute";

const USER = "cypress-plant-coordinator@buildsuite.test";
const PERSONA = "Cypress Plant Coordinator";
const CUSTOM_ROLE = "Cypress Plant Coordinator";
const MACHINE_TYPE = "Cypress Excavator";

const api = (method) => `/api/method/${method}`;

// The router sends a denied deep link to the app's root ("/"), which opens Home — not to an
// error page.
function expectBouncedHome() {
	cy.location("pathname").should("match", new RegExp(`^${appUrl("")}(/home)?/?$`));
}

describe("A custom persona gets what its roles are configured for", () => {
	beforeEach(() => {
		cy.login(USER, Cypress.config("adminPassword"));
	});

	it("has no BuildSuite role, yet is let into the app under its own persona", () => {
		cy.request(api("buildsuite_core.api.permission.get_access_context")).then(({ body }) => {
			const access = body.message;
			expect(access.allowed, "allowed into the SPA").to.equal(true);
			expect(access.persona).to.equal(PERSONA);
			expect(access.persona_slug).to.be.a("string").and.not.be.empty;
			expect(access.roles).to.include(CUSTOM_ROLE);
			const buildSuiteRoles = access.roles.filter(
				(r) => r.startsWith("BuildSuite") && r !== "BuildSuite Project User"
			);
			expect(buildSuiteRoles, "no BuildSuite persona role").to.be.empty;
			expect(access.roles).not.to.include("System Manager");
		});

		cy.visitApp("/");
		cy.location("pathname").should("not.include", "forbidden");
		// Shown under its own name, not as a built-in persona or "System Manager (Admin)".
		cy.contains(PERSONA).should("be.visible");
		cy.contains("System Manager (Admin)").should("not.exist");
	});

	it("sees exactly the workspaces its role was given", () => {
		cy.request(api("buildsuite_core.api.workspace_setting.get_visible_workspaces")).then(
			({ body }) => {
				const slugs = body.message.map((w) => w.slug).sort();
				expect(slugs).to.deep.equal(["equipment", "procurement"]);
			}
		);

		cy.visitApp("/equipment");
		cy.location("pathname").should("eq", appUrl("/equipment"));

		// A workspace it was not given: the deep link is refused.
		cy.visitApp("/workforce");
		expectBouncedHome();
	});

	it("can do on a doctype what its DocPerms allow, and no more", () => {
		cy.request(api("buildsuite_core.api.permission.get_resource_permissions")).then(
			({ body }) => {
				const caps = body.message;
				expect(caps.machinery, "Machinery caps").to.include({
					c: true,
					r: true,
					e: true,
					d: false,
				});
				expect(caps.machineryUsage.r, "Machinery Usage read").to.equal(false);
				expect(caps.project.r, "Project read").to.equal(false);
			}
		);

		// The list opens with its create affordance, and the new-record form is reachable.
		cy.visitApp("/machinery");
		cy.dt("page-title").should("contain", "Machinery Register");
		cy.dt("page-actions").contains("New").should("be.visible");
		cy.visitApp("/machinery/new");
		cy.location("pathname").should("eq", appUrl("/machinery/new"));

		// The backend accepts the write — not just the UI showing the button.
		cy.request("/api/method/frappe.client.get_value?doctype=Company&fieldname=name").then(
			({ body }) => {
				const company = body.message?.name;
				expect(company, "a company to own the machine").to.be.a("string");
				cy.request({
					method: "POST",
					url: api("frappe.client.insert"),
					body: {
						doc: {
							doctype: "Machinery",
							machinery_name: `Cypress custom-persona machine ${Date.now()}`,
							machinery_type: MACHINE_TYPE,
							company,
						},
					},
				}).then(({ body: created }) => {
					expect(created.message.owner).to.equal(USER);
					cy.visitApp(`/machinery/${encodeURIComponent(created.message.name)}`);
					cy.dt("page-title").should("contain", created.message.machinery_name);
				});
			}
		);

		// Doctypes it was not given: their routes are refused, and the backend refuses too.
		cy.visitApp("/machinery-usage");
		expectBouncedHome();
		cy.request({
			url: api("frappe.client.get_list"),
			qs: { doctype: "Machinery Usage", limit_page_length: 1 },
			failOnStatusCode: false,
		})
			.its("status")
			.should("eq", 403);
	});

	it("opens the report its role was granted, and not the others", () => {
		cy.request(api("buildsuite_core.api.permission.get_access_context")).then(({ body }) => {
			expect(body.message.report_routes).to.deep.equal([
				"/procurement/report/purchase-register",
			]);
		});

		cy.visitApp("/procurement/report/purchase-register");
		cy.location("pathname").should("eq", appUrl("/procurement/report/purchase-register"));
		cy.dt("page-title").should("contain", "Purchase register");

		cy.visitApp("/procurement/report/delivery-followup");
		expectBouncedHome();
	});
});
