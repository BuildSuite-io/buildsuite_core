// Timesheets: the Workforce tile, the list, a draft's detail and edit form (header Cost code, the
// hourly-rate line), and the import page (template link, an old Task column flagged, an unknown
// cost code left out with its reason).

const api = (path, qs) => cy.request({ url: `/api/method/${path}`, qs }).its("body.message");

describe("Timesheets", () => {
	let employee;
	let project;
	let draft;

	before(() => {
		cy.login();
		api("frappe.client.get_list", {
			doctype: "Employee",
			fields: JSON.stringify(["name"]),
			filters: JSON.stringify([
				["is_labour", "=", 1],
				["status", "=", "Active"],
			]),
			limit_page_length: 1,
		}).then((r) => (employee = r[0].name));
		api("frappe.client.get_list", {
			doctype: "Project",
			fields: JSON.stringify(["name"]),
			limit_page_length: 1,
		}).then((r) => (project = r[0].name));
		// A draft on a quiet old day, made through the same API the form uses.
		cy.visitApp("/timesheets");
		cy.window().then((win) =>
			cy
				.request({
					method: "POST",
					url: "/api/method/buildsuite_core.api.timesheet.save_timesheet",
					headers: { "X-Frappe-CSRF-Token": win.csrf_token },
					body: {
						employee,
						date: `2019-0${1 + Math.floor(Math.random() * 8)}-${
							10 + Math.floor(Math.random() * 15)
						}`,
						time_logs: JSON.stringify([{ project, hours: 6 }]),
					},
					failOnStatusCode: false,
				})
				.then((res) => {
					draft = res.body.message?.name;
				})
		);
	});

	beforeEach(() => cy.login());

	it("the Workforce landing offers Timesheets, which opens the list with New and Import", () => {
		cy.visitApp("/workforce");
		cy.contains("Timesheets").click();
		cy.location("pathname").should("match", /\/timesheets$/);
		cy.contains("h1, [class*=text-xl]", "Timesheets").should("be.visible");
		cy.contains("a", "Import").should("be.visible");
		cy.contains("a", "+ New").should("be.visible");
	});

	it("a draft's detail shows its rows uncoded; Edit shows the header Cost code and the rate line", function () {
		if (!draft) this.skip();
		cy.visitApp(`/timesheets/${draft}`);
		cy.contains("Not coded").should("be.visible");
		cy.contains("button", "Edit").click();
		cy.location("pathname").should("contain", "/edit");
		cy.contains("label", "Cost code").should("be.visible");
		cy.get("[data-costing-line]").should("contain", "an hour").and("contain", "daily rate");
	});

	it("Import: template link, an old Task column is flagged and an unknown cost code is left out", () => {
		cy.visitApp("/timesheets/import");
		cy.contains("a", "Download template")
			.should("have.attr", "href")
			.and("contain", "timesheet_template");

		const csv = `Date,Employee code,Project code,Task,Hours\n2019-02-11,${employee},${project},Paint,3\n`;
		cy.get("[data-timesheet-file]").selectFile(
			{ contents: Cypress.Buffer.from(csv), fileName: "old.csv", mimeType: "text/csv" },
			{ force: true }
		);
		cy.get("[data-legacy-task]").should("be.visible");
		cy.contains("1 timesheets ready").should("be.visible");

		const csv2 = `Date,Employee code,Project code,Cost code,Hours\n2019-02-12,${employee},${project},Z.99,3\n`;
		cy.get("[data-timesheet-file]").selectFile(
			{ contents: Cypress.Buffer.from(csv2), fileName: "bad.csv", mimeType: "text/csv" },
			{ force: true }
		);
		cy.contains('Cost code "Z.99" is not on the estimate of').should("be.visible");
	});

	after(() => {
		if (!draft) return;
		cy.login();
		cy.visitApp("/timesheets");
		cy.window().then((win) =>
			cy.request({
				method: "DELETE",
				url: `/api/resource/Timesheet/${draft}`,
				headers: { "X-Frappe-CSRF-Token": win.csrf_token },
				failOnStatusCode: false,
			})
		);
	});
});
