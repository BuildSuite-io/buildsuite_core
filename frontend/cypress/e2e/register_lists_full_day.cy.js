// The two attendance register lists: no Task column, a "Captured as" column linking to the source
// document, and (Labour only) Hours shown as regular hours over the full day.

describe("Attendance register lists", () => {
	beforeEach(() => cy.login());

	it("Labour Attendance Register: Captured as + Hours, no Task", () => {
		cy.visitApp("/labour-attendance");
		cy.contains("th, [role=columnheader]", "Captured as").should("be.visible");
		cy.contains("th, [role=columnheader]", "Hours").should("be.visible");
		cy.contains("th, [role=columnheader]", "Task").should("not.exist");
		// rows made by a sheet link back to it, and show "regular / full-day h"
		cy.contains("a", "Attendance")
			.should("have.attr", "href")
			.and("contain", "/field-attendance/");
		cy.contains(/\d+(\.\d+)?\s*\/\s*\d+(\.\d+)? h/).should("be.visible");
	});

	it("Overtime Attendance Register: Captured as, no Task", () => {
		cy.visitApp("/overtime-attendance");
		cy.contains("th, [role=columnheader]", "Captured as").should("be.visible");
		cy.contains("th, [role=columnheader]", "Task").should("not.exist");
		cy.contains("a", "Attendance")
			.should("have.attr", "href")
			.and("contain", "/field-attendance/");
	});
});
