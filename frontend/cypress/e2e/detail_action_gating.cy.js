// Comprehensive companion to submittable_action_gating.cy.js.
//
// Every entity's DETAIL page renders its action buttons (Edit / Submit / Cancel / Delete, plus
// cross-entity "+ Create X" buttons) behind a persona CAPABILITY — not just the document's
// docstatus. The bug this guards against: a read-only persona opens a record and sees Edit /
// Submit / Delete that the backend then 403s, because the view gated them on the record's state
// alone. Each detail view (now fixed) imports usePermissions() and ANDs a cap into every button's
// v-if; this spec asserts, per persona, that each button appears iff that cap is true.
//
// This is the surface the other specs miss: module_entity_crud covers the LIST "+ New" (create)
// affordance and cross_entity_create_buttons covers cross-entity CREATE buttons from a fixed
// record — neither opens EVERY entity's detail to check its own edit/submit/delete/cancel
// buttons. submittable_action_gating.cy.js stays as the dedicated Subcontractor Bill lifecycle
// spec; this file is the broad, data-driven sweep over the rest.
//
// Data-driven from PERSONA_CAPS (the same table usePermissions() reads) + a MANIFEST describing
// each entity's detail route, fixture slot, and buttons — so it stays correct as the caps change.
// Fixture record names come from ensure_cypress_records (reuses demo data); a null slot skips.
//
// Modelling notes / known caveats:
//   * Buttons are matched with `cy.contains("button", text)` inside [data-test="page-actions"]
//     (the DeskPage #actions slot). Buttons rendered ELSEWHERE are intentionally NOT modelled:
//       - BOQ's actions live in a DeskActionBar menu (inside DeskForm), not page-actions — so BOQ
//         carries no buttons here and only gets a readability check.
//       - RateMaster's Edit/Delete live in the record drawer; only its page-actions "+ New rate"
//         (canCreate) is modelled.
//       - Machinery's "+ Log usage" is a RouterLink (<a>), not a <button>, so it is omitted.
//   * A cross-entity "+ Create X" button gates on the TARGET entity's create cap — modelled as
//     { capEntity: '<target>', cap: 'c' }. Its `when` opens the record in the state that also
//     satisfies the button's non-cap condition (e.g. a submitted PO not yet fully received, a
//     submitted invoice with outstanding > 0). A freshly-submitted demo record satisfies these;
//     if demo data is fully received/paid the positive assertion may under-fire — negatives
//     (a non-capable persona never sees the button) are always exact.
//   * Assumes the plain docstatus lifecycle (no active Frappe Workflow on Stock Entry / Field
//     Attendance / Sales Invoice / Purchase Invoice) — the app's default. An active workflow
//     replaces Submit/Cancel with its transitions and these assertions would need revisiting.
//
// Requires the persona test users + demo records:
//   bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users

import { PERSONA_CAPS } from "../../src/data/roles";

// Per entity: `base` (detail route is `${base}/${name}`), the fixture key (defaults to `entity`),
// and the page-actions buttons. Each button: { text, cap: 'e'|'d'|'x'|'c', when, capEntity? }.
//   cap  — the PERSONA_CAPS key the button's v-if ANDs in: e(dit)/d(elete)/x(submit·cancel)/c(reate)
//   when — 'draft' | 'submitted' (which fixture slot renders the button) | 'any' (master; uses 'one')
//   capEntity — for cross-entity create buttons, the TARGET entity the cap lives under (else = entity)
const MANIFEST = [
	// ---- Subcontract ----
	{
		entity: "subcontractorWorkOrder",
		base: "/subcontractor-work-orders",
		buttons: [
			{ text: "Edit", cap: "e", when: "draft" },
			{ text: "Submit", cap: "x", when: "draft" },
			{ text: "Delete", cap: "d", when: "draft" },
			// cross-entity: raise a Measurement Book / Subcontractor Bill from a submitted WO
			{ text: "+ Record measurement", capEntity: "measurementBook", cap: "c", when: "submitted" },
			{ text: "+ Bill progress", capEntity: "subcontractorBill", cap: "c", when: "submitted" },
			{ text: "Cancel", cap: "x", when: "submitted" },
		],
	},
	{
		entity: "measurementBook",
		base: "/measurement-books",
		// Non-submittable (status field). Fixture is a Draft book, so Edit + Certify render;
		// Delete has no status gate. Revert / "+ Create bill" need a certified book — out of scope.
		buttons: [
			{ text: "Edit", cap: "e", when: "any" },
			{ text: "Certify", cap: "x", when: "any" },
			{ text: "Delete", cap: "d", when: "any" },
		],
	},
	{
		entity: "subcontractor",
		base: "/subcontractors",
		buttons: [
			{ text: "Edit", cap: "e", when: "any" },
			{ text: "Delete", cap: "d", when: "any" },
		],
	},
	// ---- Procurement ----
	{
		entity: "materialRequest",
		base: "/procurement/material-requests",
		buttons: [
			{ text: "Edit", cap: "e", when: "draft" },
			{ text: "Submit", cap: "x", when: "draft" },
			{ text: "Delete", cap: "d", when: "draft" },
			{ text: "+ Create Purchase Order", capEntity: "purchaseOrder", cap: "c", when: "submitted" },
			{ text: "Cancel", cap: "x", when: "submitted" },
		],
	},
	{
		entity: "purchaseOrder",
		base: "/procurement/purchase-orders",
		buttons: [
			{ text: "Edit", cap: "e", when: "draft" },
			{ text: "Submit", cap: "x", when: "draft" },
			{ text: "Delete", cap: "d", when: "draft" },
			{ text: "+ Create Receipt", capEntity: "purchaseReceipt", cap: "c", when: "submitted" },
			{ text: "Cancel", cap: "x", when: "submitted" },
		],
	},
	{
		entity: "purchaseReceipt",
		base: "/procurement/receipts",
		buttons: [
			{ text: "Edit", cap: "e", when: "draft" },
			{ text: "Submit", cap: "x", when: "draft" },
			{ text: "Delete", cap: "d", when: "draft" },
			{ text: "Cancel", cap: "x", when: "submitted" },
		],
	},
	{
		entity: "materialConsumption",
		base: "/material-consumption",
		buttons: [
			{ text: "Edit", cap: "e", when: "draft" },
			{ text: "Submit", cap: "x", when: "draft" },
			{ text: "Delete", cap: "d", when: "draft" },
			{ text: "Cancel", cap: "x", when: "submitted" },
		],
	},
	// ---- Equipment ----
	{
		entity: "machinery",
		base: "/machinery",
		// "+ Log usage" is a RouterLink, not a <button> — omitted (see header caveats).
		buttons: [
			{ text: "Edit", cap: "e", when: "any" },
			{ text: "Delete", cap: "d", when: "any" },
		],
	},
	{
		entity: "machineryUsage",
		base: "/machinery-usage",
		buttons: [
			{ text: "Edit", cap: "e", when: "any" },
			{ text: "Delete", cap: "d", when: "any" },
		],
	},
	// ---- Estimation ----
	{
		entity: "boq",
		base: "/boq",
		// Actions live in the DeskActionBar menu, not page-actions — readability check only.
		buttons: [],
	},
	{
		entity: "assembly",
		base: "/assembly",
		buttons: [
			{ text: "Edit", cap: "e", when: "any" },
			{ text: "Delete", cap: "d", when: "any" },
		],
	},
	{
		entity: "estimateTemplate",
		base: "/estimate-template",
		buttons: [
			{ text: "Edit", cap: "e", when: "any" },
			{ text: "Delete", cap: "d", when: "any" },
		],
	},
	{
		entity: "rateMaster",
		base: "/rate-master",
		// Edit/Delete live in the record drawer; only the page-actions create button is here.
		buttons: [{ text: "+ New rate", cap: "c", when: "any" }],
	},
	// ---- Workforce ----
	{
		entity: "fieldEmployee",
		base: "/field-employees",
		buttons: [
			{ text: "Edit", cap: "e", when: "any" },
			{ text: "Delete", cap: "d", when: "any" },
		],
	},
	{
		entity: "crew",
		base: "/crews",
		buttons: [
			{ text: "Edit", cap: "e", when: "any" },
			{ text: "Delete", cap: "d", when: "any" },
		],
	},
	{
		entity: "fieldAttendance",
		base: "/field-attendance",
		buttons: [
			{ text: "Edit", cap: "e", when: "draft" },
			{ text: "Delete", cap: "d", when: "draft" },
			{ text: "Submit", cap: "x", when: "draft" },
			{ text: "Cancel", cap: "x", when: "submitted" },
		],
	},
	// ---- Project Finance ----
	{
		entity: "salesInvoice",
		base: "/project-finance/invoices",
		buttons: [
			{ text: "Edit", cap: "e", when: "draft" },
			{ text: "Delete", cap: "d", when: "draft" },
			{ text: "Submit", cap: "x", when: "draft" },
			// "Receive payment" posts a Payment Entry (advance) — gates on advance create.
			{ text: "Receive payment", capEntity: "advance", cap: "c", when: "submitted" },
			{ text: "Cancel", cap: "x", when: "submitted" },
		],
	},
	{
		entity: "supplierBill",
		base: "/project-finance/supplier-bills",
		buttons: [
			{ text: "Edit", cap: "e", when: "draft" },
			{ text: "Delete", cap: "d", when: "draft" },
			{ text: "Submit", cap: "x", when: "draft" },
			// "Pay" posts a Payment Entry (advance) — gates on advance create.
			{ text: "Pay", capEntity: "advance", cap: "c", when: "submitted" },
			{ text: "Cancel", cap: "x", when: "submitted" },
		],
	},
];

const ALL_PERSONAS = Object.keys(PERSONA_CAPS);

// Caps are plain booleans (module entities carry no own-scope), so `=== true` mirrors usePermissions.
const has = (persona, entity, key) => PERSONA_CAPS[persona]?.[entity]?.[key] === true;
const canRead = (persona, entity) => PERSONA_CAPS[persona]?.[entity]?.r === true;

// which fixture slot renders a button of this `when`.
const slotOf = (when) => (when === "draft" ? "draft" : when === "submitted" ? "submitted" : "one");
// pick the id for a slot, tolerating a master's single "one" slot for readability checks.
const idForSlot = (rec, slot) =>
	slot === "__any__" ? rec.one || rec.draft || rec.submitted : rec[slot];

MANIFEST.forEach((row) => {
	const fixtureKey = row.fixture || row.entity;
	// Personas that can READ the record (so its detail renders). Non-readers land on the
	// forbidden route and are covered by the CRUD specs.
	const readers = ALL_PERSONAS.filter((p) => canRead(p, row.entity));
	// Distinct fixture slots this entity exercises; entities with no buttons still get one
	// readability pass so a reader is proven able to open the detail at all.
	const slots = [...new Set(row.buttons.map((b) => slotOf(b.when)))];
	const slotList = slots.length ? slots : ["__any__"];

	describe(`${row.entity} detail — action buttons follow the persona's capability`, () => {
		let records;

		before(() => {
			cy.loginAs("admin");
			cy.request(
				"/api/method/buildsuite_core.api.cypress_setup.ensure_cypress_records"
			).then((res) => {
				records = res.body.message;
			});
		});

		readers.forEach((persona) => {
			slotList.forEach((slot) => {
				const buttons = row.buttons.filter((b) => slotOf(b.when) === slot);
				const label = slot === "__any__" ? "detail opens" : `${slot} buttons`;

				it(`${persona}: ${row.entity} — ${label} match the caps`, function () {
					const rec = records[fixtureKey] || {};
					const id = idForSlot(rec, slot);
					if (!id) this.skip(); // no fixture for this slot on this site

					cy.loginAs(persona);
					cy.visitApp(`${row.base}/${id}`);
					cy.dt("page-title").should("be.visible"); // the record is readable

					buttons.forEach((b) => {
						const capEntity = b.capEntity || row.entity;
						cy.dt("page-actions").within(() => {
							if (has(persona, capEntity, b.cap)) {
								cy.contains("button", b.text).should("exist");
							} else {
								// The lapse: a persona without the right must NOT see the button.
								cy.contains("button", b.text).should("not.exist");
							}
						});
					});
				});
			});
		});
	});
});
