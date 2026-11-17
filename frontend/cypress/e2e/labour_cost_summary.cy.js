// Labour Cost Summary: opens from the Workforce landing, groups three ways, and the old
// "Labour cost from timesheets" link lands on it.

describe("Labour Cost Summary", () => {
	beforeEach(() => {
		cy.loginAs("admin");
	});

	it("opens from the Workforce landing with its header, filters and groupings", () => {
		cy.visitApp("/workforce");
		cy.contains("Labour Cost Summary").click();
		cy.location("pathname").should("contain", "/workforce/labour-cost-summary");
		cy.contains("h1", "Labour Cost Summary").should("be.visible");
		cy.contains(
			"Hours, man-days and what labour cost each project, from submitted attendance and timesheets."
		).should("be.visible");
		["Project", "Worker", "Period", "Captured as"].forEach((l) =>
			cy.contains("label", l).should("be.visible")
		);
		["By project", "By cost code", "By worker"].forEach((g) =>
			cy.contains("button", g).should("be.visible")
		);
	});

	it("shows the tiles, the footer note, and switches the columns with the grouping", () => {
		cy.visitApp("/workforce/labour-cost-summary");
		["Workers", "Hours", "Man-days", "Overtime (hrs)", "Labour cost"].forEach((t) =>
			cy.contains(t).should("be.visible")
		);
		cy.get("[data-report-footer]").should(
			"contain",
			"Man-days = hours ÷ the full day on each sheet"
		);
		cy.contains("button", "By worker").click();
		cy.contains("th", "Days worked").should("be.visible");
		cy.contains("button", "By cost code").click();
		cy.contains("th", "Cost code").should("be.visible");
	});

	it("the old Labour cost from timesheets link lands on it", () => {
		cy.visitApp("/workforce/timesheet-cost");
		cy.location("pathname").should("contain", "/workforce/labour-cost-summary");
	});
});
