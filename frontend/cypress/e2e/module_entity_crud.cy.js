// Basic CRUD permission ENABLEMENT for every live-module entity outside the 6 core
// ones (procurement / subcontract / estimation / workforce / equipment). For each entity this
// verifies the personas who SHOULD be able to create it can actually reach the list (read
// enablement) and see its "+ New" affordance (create enablement), and that read-only personas
// can still open the list.
//
// The expected create/read sets are DERIVED from the backend-derived oracle (support/personaCaps.js,
// generated from api.permission.get_resource_permissions) — the same source usePermissions now reads
// — so they can never drift from the backend. (The persona_caps_fresh spec guards the oracle itself.)
// The two derived attendance registers aren't resource-mapped entities, so they keep an explicit
// read-only set.
//
// These list views are gated through usePermissions().canCreate, so the spec asserts BOTH directions:
// create-capable personas see "+ New", and read-only personas do NOT (while still being able to open
// the list).
//
// Requires the persona test users:
//   bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users

import { PERSONA_CAPS } from "../support/personaCaps";

const PERSONAS = Object.keys(PERSONA_CAPS);
const creators = (cap) => PERSONAS.filter((p) => PERSONA_CAPS[p][cap]?.c === true);
const readers = (cap) => PERSONAS.filter((p) => PERSONA_CAPS[p][cap]?.r === true);

// entity -> route, "+ New" affordance label (null = read-only register, no create button), and the
// oracle resource key (`cap`) its create/read are derived from. The two derived attendance registers
// have no resource key, so they carry an explicit read-only set instead.
const ENTITIES_RAW = [
	// --- Procurement ---
	{ key: "Material Request", route: "/procurement/material-requests", newText: "New Request", cap: "materialRequest" },
	{ key: "Purchase Order", route: "/procurement/purchase-orders", newText: "New PO", cap: "purchaseOrder" },
	{ key: "Purchase Receipt", route: "/procurement/receipts", newText: "New Receipt", cap: "purchaseReceipt" },
	{ key: "Material Consumption", route: "/material-consumption", newText: "Record consumption", cap: "materialConsumption" },
	{ key: "Item", route: "/items", newText: "New Item", cap: "item" },

	// --- Estimation ---
	{ key: "BOQ", route: "/boq", newText: "New BOQ", cap: "boq" },
	{ key: "Assembly", route: "/assembly", newText: "New", cap: "assembly" },
	{ key: "Estimate Template", route: "/estimate-template", newText: "New", cap: "estimateTemplate" },
	{ key: "Rate Master", route: "/rate-master", newText: "New rate", cap: "rateMaster" },

	// --- Subcontract ---
	{ key: "Subcontractor", route: "/subcontractors", newText: "New", cap: "subcontractor" },
	{ key: "Subcontractor Work Order", route: "/subcontractor-work-orders", newText: "New", cap: "subcontractorWorkOrder" },
	{ key: "Measurement Book", route: "/measurement-books", newText: "New", cap: "measurementBook" },
	{ key: "Subcontractor Bill", route: "/subcontractor-bills", newText: "New", cap: "subcontractorBill" },

	// --- Workforce ---
	{ key: "Field Employee", route: "/field-employees", newText: "New", cap: "fieldEmployee" },
	{ key: "Crew", route: "/crews", newText: "New", cap: "crew" },
	{ key: "Field Attendance", route: "/field-attendance", newText: "New", cap: "fieldAttendance" },
	// Derived registers — read-only, not resource-mapped; explicit read set (DERIVED_ATTENDANCE_ROLE_PERMS).
	{
		key: "Labour Attendance Register", route: "/labour-attendance", newText: null, cap: null, create: [],
		read: ["director", "pm", "qs", "site-engineer", "foreman", "accountant", "hr-manager", "admin", "bsa"],
	},
	{
		key: "Overtime Attendance Register", route: "/overtime-attendance", newText: null, cap: null, create: [],
		read: ["director", "pm", "qs", "site-engineer", "foreman", "accountant", "hr-manager", "admin", "bsa"],
	},

	// --- Equipment ---
	{ key: "Machinery", route: "/machinery", newText: "New", cap: "machinery" },
	{ key: "Machinery Usage", route: "/machinery-usage", newText: "Log usage", cap: "machineryUsage" },
];

// Fill create/read from the oracle for resource-mapped entities; keep explicit sets for the registers.
const ENTITIES = ENTITIES_RAW.map((e) =>
	e.cap ? { ...e, create: creators(e.cap), read: readers(e.cap) } : e
);

describe("Create enablement — authorised personas reach each entity's + New", () => {
	PERSONAS.forEach((persona) => {
		const mine = ENTITIES.filter((e) => e.newText && e.create.includes(persona));
		if (!mine.length) return;
		it(`${persona}: can create its ${mine.length} authorised entities`, () => {
			cy.loginAs(persona);
			mine.forEach((e) => {
				cy.visitApp(e.route);
				cy.dt("page-title").should("be.visible"); // read: the list is reachable
				cy.dt("page-actions").contains(e.newText).should("be.visible"); // create affordance
			});
		});
	});
});

describe("Read-only personas: list opens, but no + New", () => {
	PERSONAS.forEach((persona) => {
		// entities the persona may read but not create (incl. the read-only registers)
		const mine = ENTITIES.filter(
			(e) => e.read.includes(persona) && !e.create.includes(persona)
		);
		if (!mine.length) return;
		it(`${persona}: opens ${mine.length} read-only lists with no create affordance`, () => {
			cy.loginAs(persona);
			mine.forEach((e) => {
				cy.visitApp(e.route);
				cy.dt("page-title").should("be.visible"); // read: the list is reachable
				// create: the "+ New" affordance must be gated away (null = register, none to check)
				if (e.newText) cy.dt("page-actions").should("not.contain", e.newText);
			});
		});
	});
});
