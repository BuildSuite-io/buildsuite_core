// A detail page that creates OTHER entities via "link" buttons must gate each button on the
// TARGET entity's create right — not the host's. A Director/Owner is full on the Work Order but
// read-only on Measurement Book + Subcontractor Bill, so on a (submitted) WO they must NOT see
// "+ Record measurement" or "+ Bill progress". Same rule for every such cross-entity button:
// if you can't CREATE the target, you don't see the button.
//
// Data-driven from PERSONA_CAPS (the same table usePermissions() reads), so it stays correct as
// caps change. A persona that CAN create the target must see the button; one that can't must not.
//
// Requires the persona test users + a submitted WO:
//   bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users
// (the spec itself provisions the WO via ensure_cypress_work_order.)

import { PERSONA_CAPS } from "../../src/data/roles";

// Cross-entity link buttons on the Work Order detail → the PERSONA_CAPS key each gates on.
const WO_LINK_BUTTONS = [
	{ text: "Record measurement", cap: "measurementBook" },
	{ text: "Bill progress", cap: "subcontractorBill" },
];

// Personas that can READ a Work Order (so the detail page renders). No-WO-read personas
// (foreman, store-keeper, hr-manager) can't reach it and are covered by permissions.cy.js.
const WO_READERS = [
	"director",
	"pm",
	"qs",
	"estimator",
	"site-engineer",
	"procurement",
	"accountant",
	"admin",
	"bsa",
];

describe("Cross-entity create buttons follow the target entity's create right", () => {
	let woName;

	before(() => {
		cy.loginAs("admin");
		cy.request("/api/method/buildsuite_core.api.cypress_setup.ensure_cypress_work_order").then((res) => {
			woName = res.body.message;
		});
	});

	WO_READERS.forEach((persona) => {
		it(`${persona}: WO detail shows each link button only if it can create the target`, function () {
			if (!woName) this.skip(); // no submitted WO to test against on this site
			cy.loginAs(persona);
			cy.visitApp(`/subcontractor-work-orders/${woName}`);
			cy.dt("page-title").should("be.visible"); // the WO detail is readable

			WO_LINK_BUTTONS.forEach(({ text, cap }) => {
				const canCreateTarget = PERSONA_CAPS[persona]?.[cap]?.c === true;
				if (canCreateTarget) {
					cy.contains("button", text).should("exist");
				} else {
					// The Director/Owner case: full on the WO, read-only on the target → no button.
					cy.contains("button", text).should("not.exist");
				}
			});
		});
	});
});
