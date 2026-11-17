// Settings, trimmed to what the product needs (the prototype's cleanup): the hub carries only real
// pages (no "Soon" stubs), Core Settings lost the dead "Default project type", and the Company page
// has no Linked projects list and a brand-colour selector that actually saves.

const REAL_TILES = [
	"Company",
	"Users",
	"Personas",
	"BuildSuite Core Settings",
	"Project Settings",
	"Bank & Cash Accounts",
	"Terms & Conditions",
	"Workspace Setting",
	"Project Categories",
	"Data Tools",
	"App Icon Diagnostics",
];
const GONE_STUBS = [
	"Roles & Permissions",
	"Naming Series",
	"General Settings",
	"Email & Notifications",
	"Workflows",
	"Custom Fields",
	"Print Templates",
	"Integrations",
	"Audit Log",
];

describe("Settings cleanup", () => {
	beforeEach(() => cy.login());

	it("the hub lists only real settings pages — no stubs, no 'Soon'", () => {
		cy.visitApp("/settings");
		REAL_TILES.forEach((t) => cy.contains(".group", t).should("be.visible"));
		GONE_STUBS.forEach((t) => cy.contains(".group", t).should("not.exist"));
		cy.contains("Soon").should("not.exist");
		cy.contains("managed in Frappe Desk").should("be.visible");
	});

	it("every tile opens a page", () => {
		cy.visitApp("/settings");
		cy.contains(".group", "Company").click();
		cy.location("pathname").should("match", /\/settings\/companies$/);
		cy.visitApp("/settings");
		cy.contains(".group", "BuildSuite Core Settings").click();
		cy.location("pathname").should("match", /\/settings\/core$/);
		cy.visitApp("/settings");
		cy.contains(".group", "Bank & Cash Accounts").click();
		cy.location("pathname").should("match", /\/settings\/finance-accounts$/);
	});

	it("Core Settings no longer offers the dead 'Default project type'", () => {
		cy.visitApp("/settings/core");
		cy.contains("Project naming").should("be.visible");
		cy.contains("Default project type").should("not.exist");
	});

	describe("Company page", () => {
		let id;
		beforeEach(() => {
			cy.request({
				url: "/api/method/frappe.client.get_list",
				qs: { doctype: "Company", fields: JSON.stringify(["name"]), limit_page_length: 1 },
			})
				.its("body.message.0.name")
				.then((name) => {
					id = name;
					cy.visitApp(`/settings/companies/${encodeURIComponent(id)}`);
					cy.contains("Pill colour").should("be.visible");
				});
		});

		it("has no Linked projects list", () => {
			cy.contains("Linked projects").should("not.exist");
			// the one-line count beside Delete stays — it's what explains a refused delete
			cy.contains(
				/project(s)? reference this company|No projects reference this company/
			).should("be.visible");
		});

		it("the brand colour is a selector whose choice is saved on the Company", () => {
			cy.contains("button", "Edit").click();
			cy.contains("select option", "Rose").parent().as("colour");
			// pick a colour different from the current (possibly derived) one, so there is a change
			cy.get("@colour").then(($s) => {
				const target = $s.val() === "Rose" ? "Blue" : "Rose";
				cy.wrap(target).as("target");
				cy.get("@colour").select(target);
			});
			cy.contains("button", "Save").click();
			cy.contains("button", "Edit").should("be.visible");

			// persisted on the doctype, and still there after a reload
			cy.get("@target").then((target) => {
				cy.request({
					url: "/api/method/buildsuite_core.api.company.company_branding",
					qs: { company: id },
				})
					.its("body.message.brand_colour")
					.should("eq", target);
				cy.reload();
				cy.contains("Pill colour").parent().should("contain.text", target);

				// put the company back to "derive from the ID"
				cy.window()
					.its("csrf_token")
					.then((token) =>
						cy.request({
							method: "POST",
							url: "/api/method/buildsuite_core.api.company.update_company_branding",
							headers: { "X-Frappe-CSRF-Token": token },
							body: { company: id, brand_colour: "" },
						})
					)
					.its("body.message.brand_colour")
					.should("not.eq", target);
			});
		});
	});
});
