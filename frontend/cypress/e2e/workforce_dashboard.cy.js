// The Workforce workspace offers a Dashboard tile that opens the KPI strip + recent panels.

describe("Workforce dashboard", () => {
	beforeEach(() => {
		cy.loginAs("admin");
	});

	it("opens from the Workforce workspace tile and shows the KPIs and both panels", () => {
		cy.visitApp("/workforce");
		cy.contains("Workforce Dashboard").click();
		cy.location("pathname").should("contain", "/workforce-dashboard");
		cy.contains("h1", "Workforce Dashboard").should("be.visible");
		["Active workers", "Active crews", "Man-days logged", "Labour cost"].forEach((k) =>
			cy.contains(k).should("be.visible")
		);
		cy.contains("Recent attendance").should("be.visible");
		cy.contains("Recent labour cost").should("be.visible");
	});

	it("the Workforce landing offers Timesheets and the three reports", () => {
		cy.visitApp("/workforce");
		cy.contains("Timesheets").should("be.visible");
		[
			"Labour Attendance Register",
			"Overtime Attendance Register",
			"Site Attendance Summary",
		].forEach((r) => cy.contains(r).should("be.visible"));
		cy.contains("Timesheets").click();
		cy.location("pathname").should("contain", "/records/Timesheet");
	});

	it("Recent attendance → View all opens the Field Attendance list", () => {
		cy.visitApp("/workforce-dashboard");
		cy.contains("Recent attendance").should("be.visible");
		cy.contains("a", "View all").first().click();
		cy.location("pathname").should("contain", "/field-attendance");
	});
});
