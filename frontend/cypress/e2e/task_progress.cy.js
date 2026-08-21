// File a Task Progress Entry from the task detail page and confirm the parent Task updates
// via the real server hook.
//
// The global Tasks list is scoped to the active company, which may hold no tasks, so this
// self-seeds: it creates a Commercial-category project (its template imports tasks under the
// project's company), then opens one of those tasks from the project's Tasks tab.
//
// Uses 100% because progress is cumulative + monotonic — 100 is always >= a seeded task's
// current progress, so the entry is valid and drives the task to Completed (a clear signal).

describe("Task progress entry updates the task", () => {
	it("filing 100% completes the task", () => {
		const stamp = Date.now();
		cy.login();

		// --- seed tasks via a Commercial project (template imports tasks by default) ---
		cy.visitApp("/projects");
		cy.dt("page-actions").contains("New").click();
		cy.location("pathname").should("include", "/projects/new");
		cy.dt("field-name").type(`Cypress TaskProj ${stamp}`);
		cy.dt("field-code").type(`CYTP-${stamp}`);
		cy.fillLink("pick-project-category", "Commercial"); // category drives the template
		cy.fillLink("pick-company");
		cy.contains("Import default tasks").should("be.visible"); // template loaded → tasks will import
		cy.dt("save-btn").click();
		cy.location("pathname", { timeout: 30000 }).should("match", /\/projects\/.+/);

		// --- open a seeded task from the project's Tasks tab ---
		cy.contains("button", "Tasks").click();
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
