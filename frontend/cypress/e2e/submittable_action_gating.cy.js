// A detail page's own lifecycle buttons (Edit / Submit / Delete / Cancel) must be gated on the
// persona's CAPABILITY, not just the document's docstatus. The bug this guards against: a
// read-only Director opens a draft Subcontractor Bill and sees Edit/Submit/Delete — all of which
// the backend then 403s — because the view gated them on `isDraft` alone. It also covers the
// subtler case: PM + Procurement may RAISE and edit a bill (create + write) but NOT delete or
// submit it (backend _CRW vs the QS/Accountant _FULL_SUB), so they see Edit but not Submit/Delete.
//
// Data-driven from PERSONA_CAPS (the same table usePermissions() reads), so it stays correct as the
// caps change. This is the surface the existing specs miss: module_entity_crud covers the LIST
// "+ New" (create) affordance, and cross_entity_create_buttons covers cross-entity CREATE buttons —
// neither opens a record to check its own edit/submit/delete/cancel buttons.
//
// Requires the persona test users + at least one draft and one submitted Subcontractor Bill:
//   bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users
// (the spec fetches the bill names via ensure_cypress_bills; a missing slot skips that half.)
//
// NOTE: assumes the plain docstatus lifecycle (no active workflow on the bill) — the app's default.

import { PERSONA_CAPS } from "../../src/data/roles";

const ENTITY = "subcontractorBill";

// Personas that can READ a Subcontractor Bill (so the detail renders). Non-readers (estimator,
// foreman, store-keeper, hr-manager) can't reach it and are covered by the CRUD specs.
const BILL_READERS = [
	"director",
	"pm",
	"qs",
	"site-engineer",
	"procurement",
	"accountant",
	"admin",
	"bsa",
];

// Lifecycle buttons on the bill detail → the PERSONA_CAPS key each must be gated on.
const DRAFT_BUTTONS = [
	{ text: "Edit", cap: "e" }, // canEdit
	{ text: "Submit", cap: "x" }, // canSubmit
	{ text: "Delete", cap: "d" }, // canDelete
];
const SUBMITTED_BUTTONS = [
	{ text: "Cancel", cap: "x" }, // canSubmit (cancel is part of the submit right)
];

// subcontractorBill caps are plain booleans (no own-scope), so `=== true` mirrors usePermissions.
const capable = (persona, key) => PERSONA_CAPS[persona]?.[ENTITY]?.[key] === true;

function assertButtons(persona, buttons) {
	buttons.forEach(({ text, cap }) => {
		cy.dt("page-actions").within(() => {
			if (capable(persona, cap)) {
				cy.contains("button", text).should("exist");
			} else {
				// The lapse: a persona without the right must NOT see the button.
				cy.contains("button", text).should("not.exist");
			}
		});
	});
}

describe("Subcontractor Bill detail — lifecycle buttons follow the persona's capability", () => {
	let draft;
	let submitted;

	before(() => {
		cy.loginAs("admin");
		cy.request("/api/method/buildsuite_core.api.cypress_setup.ensure_cypress_bills").then((res) => {
			draft = res.body.message.draft;
			submitted = res.body.message.submitted;
		});
	});

	BILL_READERS.forEach((persona) => {
		it(`${persona}: draft bill shows Edit/Submit/Delete only where capable`, function () {
			if (!draft) this.skip(); // no draft bill on this site
			cy.loginAs(persona);
			cy.visitApp(`/subcontractor-bills/${draft}`);
			cy.dt("page-title").should("be.visible"); // the bill is readable
			assertButtons(persona, DRAFT_BUTTONS);
		});

		it(`${persona}: submitted bill shows Cancel only if it can submit/cancel`, function () {
			if (!submitted) this.skip();
			cy.loginAs(persona);
			cy.visitApp(`/subcontractor-bills/${submitted}`);
			cy.dt("page-title").should("be.visible");
			assertButtons(persona, SUBMITTED_BUTTONS);
		});
	});
});
