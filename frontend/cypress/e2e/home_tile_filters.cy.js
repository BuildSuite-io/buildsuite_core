// Clicking a Home snapshot tile opens its list with the tile's filter applied AND visible: the
// filter shows as a removable chip (labelled with the field's label, not its raw fieldname), so the
// list the user lands on is plainly the one the number counts.

describe("Home tiles — the drilled-into list shows the tile's filter", () => {
	beforeEach(() => {
		cy.loginAs("admin");
		cy.visitApp("/");
	});

	it("Open tasks → Tasks list with a visible, removable status filter", () => {
		cy.contains("Open tasks").first().click({ force: true });
		cy.location("search").should("contain", "filters=");
		cy.contains("Task Status").should("be.visible");
		cy.contains("task_status").should("not.exist");
		cy.contains("Completed, Cancelled, Template").should("be.visible");
		cy.contains("button", "Clear").click();
		cy.contains("Completed, Cancelled, Template").should("not.exist");
	});

	it("Pending stage approvals → Stage Planning list showing the State chip", () => {
		cy.contains("Pending stage approvals").first().click({ force: true });
		cy.location("search").should("contain", "status=");
		cy.contains("State").should("be.visible");
		cy.contains("Pending Approval").should("be.visible");
	});
});
