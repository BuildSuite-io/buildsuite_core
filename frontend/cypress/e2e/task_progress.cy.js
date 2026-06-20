// File a Task Progress Entry from the task detail page and confirm the parent
// Task updates via the real server hook. Opens an existing seeded task (read from
// the list) so we don't depend on the create form here.
//
// Uses 100% because progress is cumulative + monotonic — 100 is always >= the
// task's current progress, so the entry is valid regardless of which task is
// first in the list, and it drives the task to Completed (a clear success signal).

describe("Task progress entry updates the task", () => {
	it("filing 100% completes the task", () => {
		cy.login();
		cy.visitApp("/tasks");
		cy.dt("desk-list").find("[data-test-row]").first().click();
		cy.location("pathname").should("match", /\/tasks\/.+/);

		cy.dt("file-progress-entry").click();
		cy.dt("tpe-modal")
			.should("be.visible")
			.within(() => {
				cy.dt("field-progress").clear().type("100");
			});
		cy.dt("save-btn").click();

		// A successful save closes the modal; the server hook then drives the task to
		// 100% / Completed.
		cy.dt("tpe-modal").should("not.exist");
		cy.contains("Completed").should("be.visible");
	});
});
