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
	]) {
		it(`the same Custom Field control shows on the bespoke ${label} form`, () => {
			cy.visitApp(path);
			cy.get("[data-test=demo-region] input").should("be.visible").type("West");
			cy.get("[data-test=demo-region] input").should("have.value", "West");
		});
	}
});
