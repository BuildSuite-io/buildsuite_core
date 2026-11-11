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
});
