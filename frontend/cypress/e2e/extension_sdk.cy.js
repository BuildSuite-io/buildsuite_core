// The extension SDK, end to end, against the demo extension (examples/buildsuite_demo_extension)
// installed on the site: a page, a slot component, a workspace tile — and a broken extension
// component that must not take the page down.

import { appUrl } from "../../src/utils/appRoute";

describe("Extension SDK — buildsuite_demo_extension", () => {
	beforeEach(() => {
		cy.login();
		cy.request("/api/method/buildsuite_core.api.company.company_context"); // session warm-up
	});

	it("a slot component from the installed app shows on the Settings page", () => {
		cy.visitApp("/settings");
		cy.get("[data-test=demo-extension-banner]").should("be.visible");
	});

	it("a page added by the app opens at /demo-extension", () => {
		cy.visitApp("/demo-extension");
		cy.get("[data-test=page-title]").should("contain", "Demo extension");
		cy.contains("Core was not rebuilt").should("be.visible");
	});

	it("a workspace tile added by the app links to that page", () => {
		cy.visitApp("/sales");
		cy.contains("a", "Demo extension").click();
		cy.location("pathname").should("include", "demo-extension");
	});

	it("a component that throws is contained: the rest of the page keeps working", () => {
		cy.visit(appUrl("/settings"), {
			onBeforeLoad: (win) => win.localStorage.setItem("buildsuite_demo_break", "1"),
		});
		cy.get("[data-test=demo-extension-banner]").should("be.visible");
		cy.get("[data-test=page-title]").should("exist");
		cy.window().then((win) => win.localStorage.removeItem("buildsuite_demo_break"));
	});

	it("a Core page can be wrapped: the extension adds to it and the Core view still renders", () => {
		cy.visitApp("/settings/data");
		cy.get("[data-test=demo-wrapped-notice]").should("be.visible");
		cy.get("[data-test=page-title]").should("exist");
	});

	it("a Core page can be replaced by the extension's own", () => {
		cy.visitApp("/settings/app-icon-diagnostics");
		cy.get("[data-test=demo-overridden]").should("be.visible");
	});

	it("DocType hooks run on the generic form: its slot shows and beforeSave can veto", () => {
		cy.visitApp("/records/Account%20Category/new");
		cy.get("[data-test=demo-form-notice]").should("be.visible");
		cy.get("input[type=text]").first().type("FORBIDDEN-DEMO value");
		cy.contains("button", "Create").click();
		cy.contains("The demo extension refuses this value.").should("be.visible");
	});

	it("every route has page slots, including a bespoke page that does not use DeskPage (Home)", () => {
		cy.visitApp("/home");
		cy.get("[data-test=demo-home-notice]").should("be.visible");
	});

	it("an installed app's settings page appears on the Settings page and opens as a form", () => {
		cy.visitApp("/settings");
		cy.contains("Demo extension settings").should("be.visible");
		cy.contains("Demo extension settings").click();
		cy.location("pathname").should("include", "/settings/doc/Demo%20Extension%20Settings");
		cy.contains("Default region").should("be.visible");
		cy.contains("button", "Delete").should("not.exist"); // a Single can't be deleted
	});

	it("a Custom Field control from the app shows on the bespoke Quotation form", () => {
		cy.visitApp("/quotations/new");
		cy.get("[data-test=demo-region] input").should("be.visible").type("East");
		cy.get("[data-test=demo-region] input").should("have.value", "East");
	});

	for (const [label, path] of [
		["Project", "/projects/new"],
		["Task", "/tasks/new"],
		["Work Package", "/work-packages/new"],
		["Subcontractor Work Order", "/subcontractor-work-orders/new"],
		["Subcontractor Bill", "/subcontractor-bills/new"],
		["Machinery", "/machinery/new"],
		["Machinery Usage", "/machinery-usage/new"],
		["Scope Change Order", "/sco/new"],
		["Stage Planning", "/stage-plannings/new"],
		["Task Progress Entry", "/progress-entries/new"],
		["Tender", "/tenders/new"],
		["Crew", "/crews/new"],
		["Field Attendance", "/field-attendance/new"],
		["Field Employee", "/field-employees/new"],
		["Subcontractor", "/subcontractors/new"],
		["Material Consumption", "/material-consumption/new"],
		["Measurement Book", "/measurement-books/new"],
		["Assembly", "/assembly/new"],
		["Estimate Template", "/estimate-template/new"],
	]) {
		it(`the same Custom Field control shows on the bespoke ${label} form`, () => {
			cy.visitApp(path);
			cy.get("[data-test=demo-region] input").should("be.visible").type("West");
			cy.get("[data-test=demo-region] input").should("have.value", "West");
		});
	}
	it("a Custom Field value entered in the extension control is saved on the record", () => {
		const stamp = Date.now();
		cy.visitApp("/projects/new");
		cy.dt("field-name").type(`Ext Region ${stamp}`);
		cy.dt("field-code").type(`EXT-${stamp}`);
		cy.fillLink("pick-project-category", "Commercial");
		cy.fillLink("pick-company");
		cy.get("[data-test=demo-region] input").type("North-East");
		cy.dt("save-btn").click();
		cy.location("pathname", { timeout: 30000 }).should("match", /\/projects\/(?!new)[^/]+$/);
		cy.location("pathname").then((path) => {
			const id = decodeURIComponent(path.split("/").pop());
			cy.request(`/api/resource/Project/${encodeURIComponent(id)}`).then((res) => {
				expect(res.body.data.demo_region).to.equal("North-East");
			});
		});
	});

	it("a Custom Field on the Subcontractor Work Order form is saved by the whitelisted save API", () => {
		cy.visitApp("/subcontractor-work-orders/new");
		cy.fillLink("pick-subcontractor", "Arrow");
		cy.fillLink("pick-project");
		cy.get("[data-test=demo-region] input").type("South");
		cy.get('input[placeholder^="Describe the work"]').type("Excavation");
		cy.get("tbody input[type=number]").eq(0).clear().type("10");
		cy.get("tbody input[type=number]").eq(1).clear().type("100");
		cy.dt("save-btn").click();
		cy.location("pathname", { timeout: 30000 }).should(
			"match",
			/\/subcontractor-work-orders\/(?!new)[^/]+$/
		);
		cy.location("pathname").then((path) => {
			const id = decodeURIComponent(path.split("/").pop());
			cy.request(`/api/resource/Subcontractor Work Order/${encodeURIComponent(id)}`).then(
				(res) => {
					expect(res.body.data.demo_region).to.equal("South");
				}
			);
		});
	});
	for (const [doctype, route] of [
		["Project", "projects"],
		["Task", "tasks"],
	]) {
		it(`a Custom Field is shown and saved from the ${doctype} edit modal`, () => {
			const value = `Edited-${Date.now()}`;
			cy.request(
				`/api/resource/${doctype}?limit_page_length=1&order_by=creation%20desc`
			).then((list) => {
				const id = list.body.data[0].name;
				cy.visitApp(`/${route}/${encodeURIComponent(id)}`);
				cy.contains("button", /^\s*Edit\s*$/).click();
				cy.get("[data-test=demo-region] input").should("be.visible").clear().type(value);
				cy.get("footer")
					.contains("button", /^\s*Save\s*$/)
					.click();
				cy.get("[data-test=demo-region]").should("not.exist");
				cy.request(`/api/resource/${doctype}/${encodeURIComponent(id)}`).then((res) => {
					expect(res.body.data.demo_region).to.equal(value);
				});
				// Re-open: the saved value is read back into the control.
				cy.contains("button", /^\s*Edit\s*$/).click();
				cy.get("[data-test=demo-region] input").should("have.value", value);
			});
		});
	}

	it("a list shows the column an installed app adds, filled from the record", () => {
		const stamp = Date.now();
		const name = `Ext List ${stamp}`;
		cy.visitApp("/projects/new");
		cy.dt("field-name").type(name);
		cy.dt("field-code").type(`EXL-${stamp}`);
		cy.fillLink("pick-project-category", "Commercial");
		cy.fillLink("pick-company", "XCorp (Demo)");
		cy.get("[data-test=demo-region] input").type(`Listed-${stamp}`);
		cy.dt("save-btn").click();
		cy.location("pathname", { timeout: 30000 }).should("match", /\/projects\/(?!new)[^/]+$/);
		cy.visitApp("/projects");
		cy.get('[data-test="desk-list"] input[placeholder*="earch"]').first().type(name);
		cy.get('[data-test="desk-list"] thead').contains("th", "Region");
		cy.contains("tr", name).should("contain", `Listed-${stamp}`);
	});

	it("a Custom Field on the Estimate Template form is saved by the generic create", () => {
		const stamp = Date.now();
		cy.visitApp("/estimate-template/new");
		cy.get('input[placeholder="ET-..."]').type(`ET-EXT-${stamp}`);
		cy.contains("label", /^\s*Name/)
			.parent()
			.find("input")
			.type(`Ext Template ${stamp}`);
		cy.get("[data-test=demo-region] input").type("Template-Region");
		cy.dt("save-btn").click();
		cy.location("pathname", { timeout: 30000 }).should(
			"match",
			/\/estimate-template\/(?!new)[^/]+$/
		);
		cy.location("pathname").then((path) => {
			const id = decodeURIComponent(path.split("/").pop());
			cy.request(`/api/resource/Estimate Template/${encodeURIComponent(id)}`).then((res) => {
				expect(res.body.data.demo_region).to.equal("Template-Region");
			});
		});
	});
});
