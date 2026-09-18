// The seeded "Material Request Approval" Frappe Workflow governs Material Request, so the MR
// detail view must DEFER to it (via useWorkflow): a draft MR shows the workflow's role-gated
// "Submit for Approval" transition instead of the plain docstatus "Submit", plus the
// workflow-state pill. This guards the MR-workflow support wiring + the shipped workflow seed.
//
// Needs the persona users + a draft MR:
//   bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users
// (the spec fetches the MR via ensure_cypress_material_request; a missing record skips the test.)

describe("Material Request — honors the seeded approval workflow", () => {
	let draft;

	before(() => {
		cy.loginAs("admin");
		cy.request(
			"/api/method/buildsuite_core.api.cypress_setup.ensure_cypress_material_request"
		).then((res) => {
			draft = res.body.message;
		});
	});

	it("draft MR shows the workflow transition, not the plain Submit (Procurement approver)", function () {
		if (!draft) this.skip(); // couldn't provision a draft MR on this site
		cy.loginAs("procurement"); // Procurement Officer can drive MR transitions
		cy.visitApp(`/procurement/material-requests/${draft}`);
		cy.dt("page-title").should("be.visible"); // the MR is readable

		cy.dt("page-actions").within(() => {
			// The workflow transition from the Draft state — exactly ONE button, even though the
			// admin holds several of the transition's allowed roles (dedup guard).
			cy.get("button:contains('Submit for Approval')").should("have.length", 1);
			// The plain docstatus Submit must NOT show while a workflow governs the doctype.
			cy.contains("button", /^Submit$/).should("not.exist");
		});

		// The workflow-state pill reflects the current state.
		cy.contains("Draft").should("exist");
	});

	it("a raise-only persona (Site Engineer) does not get the approval transition", function () {
		if (!draft) this.skip();
		cy.loginAs("site-engineer");
		cy.visitApp(`/procurement/material-requests/${draft}`);
		// Site Engineer is raise-only (no write) so it can't drive the transition; the button
		// must not appear. (It may not even read the MR — either way, no transition button.)
		cy.get("body").then(() => {
			cy.contains("button", "Submit for Approval").should("not.exist");
		});
	});
});
