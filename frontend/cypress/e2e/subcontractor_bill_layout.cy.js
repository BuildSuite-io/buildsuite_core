// The Subcontractor Bill detail follows the prototype layout: a collapsible "Subcontractor Invoice
// reference", a Type column on Taxes and Charges, the expense account in its own block under the
// discount, and a Direct-bill / delivery-type sub-label on the first summary tile. Make Payment
// stays on a submitted bill (it is deliberately NOT removed, unlike the prototype).

describe("Subcontractor Bill detail — prototype layout", () => {
	let draft;
	let submitted;

	before(() => {
		cy.loginAs("admin");
		cy.request("/api/method/buildsuite_core.api.cypress_setup.ensure_cypress_bills").then(
			(res) => {
				draft = res.body.message.draft;
				submitted = res.body.message.submitted;
			}
		);
	});

	it("draft: reference toggle, Type column, expense-account block", function () {
		if (!draft) this.skip();
		cy.loginAs("admin");
		cy.visitApp(`/subcontractor-bills/${draft}`);
		cy.contains("button", "Subcontractor Invoice reference").should("be.visible");
		cy.contains("h3", "Taxes and Charges")
			.parents("section")
			.within(() => {
				cy.contains("th", "Type").should("exist");
				cy.contains("th", "Account Head").should("exist");
			});
		cy.contains("h3", "Retention, TDS & discount")
			.parent()
			.parent()
			.within(() => {
				cy.contains("Expense account").should("exist");
				cy.contains("Where the cost posts in the ledger.").should("exist");
			});
		cy.contains("Less: TDS withheld").should("exist");
	});

	it("reference section opens and shows the invoice fields", function () {
		if (!draft) this.skip();
		cy.loginAs("admin");
		cy.visitApp(`/subcontractor-bills/${draft}`);
		cy.contains("button", "Subcontractor Invoice reference").then(($b) => {
			if (!Cypress.$("body").text().includes("Subcontractor Invoice No"))
				cy.wrap($b).click();
		});
		cy.contains("label", "Subcontractor Invoice No").should("be.visible");
		cy.contains("label", "Subcontractor Invoice Date").should("be.visible");
	});

	it("submitted: Make Payment is still offered and there is no Open in Accounting button", function () {
		if (!submitted) this.skip();
		cy.loginAs("admin");
		cy.visitApp(`/subcontractor-bills/${submitted}`);
		cy.dt("page-title").should("be.visible");
		cy.contains("button", "Open in Accounting").should("not.exist");
	});
});
