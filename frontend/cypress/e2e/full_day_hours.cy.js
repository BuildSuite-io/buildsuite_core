// Full day hours: a Labour costing section on the Company page (admin edits it, 0 < hours <= 24)
// and a Full day hours field on the project edit form whose hint names the company's value.

describe("Full day hours", () => {
	beforeEach(() => cy.login());

	it("Company page: Labour costing shows the value; an admin edits it and the rule is enforced", () => {
		cy.request({
			url: "/api/method/frappe.client.get_list",
			qs: { doctype: "Company", fields: JSON.stringify(["name"]), limit_page_length: 1 },
		})
			.its("body.message.0.name")
			.then((id) => {
				cy.visitApp(`/settings/companies/${encodeURIComponent(id)}`);
				cy.contains("Labour costing").should("be.visible");
				cy.get("[data-company-full-day]").should("contain", "8 h");

				cy.contains("button", "Edit").click();
				cy.get('input[aria-label="Full day hours"]').clear().type("25");
				cy.contains("Full day hours must be more than 0 and no more than 24.").should(
					"be.visible"
				);
				cy.get('input[aria-label="Full day hours"]').clear().type("9");
				cy.contains("Full day hours must be more than 0").should("not.exist");
				cy.contains("button", "Save").click();
				cy.get("[data-company-full-day]").should("contain", "9 h");

				// put it back so other specs see the shipped default
				cy.contains("button", "Edit").click();
				cy.get('input[aria-label="Full day hours"]').clear().type("8");
				cy.contains("button", "Save").click();
				cy.get("[data-company-full-day]").should("contain", "8 h");
			});
	});

	it("Project edit form: Full day hours hint names the company default", () => {
		cy.request({
			url: "/api/method/frappe.client.get_list",
			qs: { doctype: "Project", fields: JSON.stringify(["name"]), limit_page_length: 1 },
		})
			.its("body.message.0.name")
			.then((id) => {
				cy.visitApp(`/projects/${encodeURIComponent(id)}`);
				cy.contains("button", "Edit").first().click();
				cy.contains("Full day hours").should("be.visible");
				cy.contains("Uses company default: 8 h").should("be.visible");
			});
	});
});
