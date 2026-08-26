// Basic CRUD permission ENABLEMENT for every live-module entity outside the 6 PERSONA_CAPS
// ones (procurement / subcontract / estimation / workforce / equipment). For each entity this
// verifies the personas who SHOULD be able to create it can actually reach the list (read
// enablement) and see its "+ New" affordance (create enablement), and that read-only personas
// can still open the list. Expected create/read sets mirror the backend role matrix in
// buildsuite_core/permissions/setup.py.
//
// These list views are gated through usePermissions().canCreate (PERSONA_CAPS now covers these
// entities), so the spec asserts BOTH directions: create-capable personas see "+ New", and
// read-only personas do NOT (while still being able to open the list). Before the caps were
// wired the read-only negative failed for every entity — that delta is the gap this closes.
//
// Requires the persona test users:
//   bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users

// entity -> route, "+ New" affordance label (null = read-only register, no create button),
// and the personas the backend lets create / read it.
const ENTITIES = [
	// --- Procurement ---
	{
		key: "Material Request",
		route: "/procurement/material-requests",
		newText: "New Request",
		create: ["pm", "site-engineer", "foreman", "procurement", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"site-engineer",
			"foreman",
			"procurement",
			"store-keeper",
			"accountant",
			"admin",
			"bsa",
		],
	},
	{
		key: "Purchase Order",
		route: "/procurement/purchase-orders",
		newText: "New PO",
		create: ["procurement", "admin", "bsa"],
		read: ["director", "pm", "procurement", "store-keeper", "accountant", "admin", "bsa"],
	},
	{
		key: "Purchase Receipt",
		route: "/procurement/receipts",
		newText: "New Receipt",
		create: ["procurement", "store-keeper", "admin", "bsa"],
		read: ["director", "pm", "procurement", "store-keeper", "accountant", "admin", "bsa"],
	},
	{
		key: "Material Consumption",
		route: "/material-consumption",
		newText: "Record consumption",
		create: ["site-engineer", "procurement", "store-keeper", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"site-engineer",
			"procurement",
			"store-keeper",
			"accountant",
			"admin",
			"bsa",
		],
	},
	{
		key: "Item",
		route: "/items",
		newText: "New Item",
		create: ["procurement", "store-keeper", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"estimator",
			"qs",
			"procurement",
			"store-keeper",
			"accountant",
			"admin",
			"bsa",
		],
	},

	// --- Estimation ---
	{
		key: "BOQ",
		route: "/boq",
		newText: "New BOQ",
		create: ["director", "pm", "estimator", "qs", "admin", "bsa"],
		read: ["director", "pm", "estimator", "qs", "admin", "bsa"],
	},
	{
		key: "Assembly",
		route: "/assembly",
		newText: "New",
		create: ["director", "pm", "estimator", "qs", "admin", "bsa"],
		read: ["director", "pm", "estimator", "qs", "admin", "bsa"],
	},
	{
		key: "Estimate Template",
		route: "/estimate-template",
		newText: "New",
		create: ["director", "pm", "estimator", "qs", "admin", "bsa"],
		read: ["director", "pm", "estimator", "qs", "admin", "bsa"],
	},
	{
		key: "Rate Master",
		route: "/rate-master",
		newText: "New rate",
		create: ["director", "pm", "estimator", "qs", "admin", "bsa"],
		read: ["director", "pm", "estimator", "qs", "procurement", "admin", "bsa"],
	},

	// --- Subcontract ---
	{
		key: "Subcontractor",
		route: "/subcontractors",
		newText: "New",
		// QS + Accountant maintain subcontractors fully; Estimator is read-only. Site Engineer
		// has backend read (WO read-mirror) but no Subcontractors screen, so it's not listed here.
		create: ["procurement", "pm", "director", "qs", "accountant", "admin", "bsa"],
		read: [
			"procurement",
			"pm",
			"director",
			"qs",
			"accountant",
			"estimator",
			"admin",
			"bsa",
		],
	},
	{
		key: "Subcontractor Work Order",
		route: "/subcontractor-work-orders",
		newText: "New",
		create: ["procurement", "pm", "director", "qs", "admin", "bsa"],
		read: [
			"procurement",
			"pm",
			"director",
			"qs",
			"estimator",
			"site-engineer",
			"accountant",
			"admin",
			"bsa",
		],
	},
	{
		key: "Measurement Book",
		route: "/measurement-books",
		newText: "New",
		// Procurement has NO MB access; Director is oversight-only (read). Site Engineer RAISES
		// (create+read) but never edits/certifies; QS + PM are full. Estimator + Accountant read.
		create: ["pm", "qs", "site-engineer", "admin", "bsa"],
		read: [
			"pm",
			"director",
			"qs",
			"site-engineer",
			"estimator",
			"accountant",
			"admin",
			"bsa",
		],
	},
	{
		key: "Subcontractor Bill",
		route: "/subcontractor-bills",
		newText: "New",
		// Director is oversight-only (read, never raises a bill); Estimator has no bill access.
		// Procurement + PM prepare bills, QS + Accountant raise/submit. Site Engineer reads.
		create: ["procurement", "pm", "qs", "accountant", "admin", "bsa"],
		read: [
			"procurement",
			"pm",
			"director",
			"qs",
			"site-engineer",
			"accountant",
			"admin",
			"bsa",
		],
	},

	// --- Workforce ---
	{
		key: "Field Employee",
		route: "/field-employees",
		newText: "New",
		create: ["pm", "site-engineer", "hr-manager", "admin", "bsa"],
		// Employee is a linked-master read mirror — every persona reads it for pickers.
		read: [
			"director",
			"pm",
			"estimator",
			"qs",
			"site-engineer",
			"foreman",
			"procurement",
			"store-keeper",
			"accountant",
			"hr-manager",
			"admin",
			"bsa",
		],
	},
	{
		key: "Crew",
		route: "/crews",
		newText: "New",
		create: ["pm", "site-engineer", "foreman", "hr-manager", "admin", "bsa"],
		read: ["director", "pm", "site-engineer", "foreman", "hr-manager", "admin", "bsa"],
	},
	{
		key: "Field Attendance",
		route: "/field-attendance",
		newText: "New",
		create: ["pm", "site-engineer", "foreman", "hr-manager", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"site-engineer",
			"foreman",
			"hr-manager",
			"accountant",
			"admin",
			"bsa",
		],
	},
	{
		key: "Labour Attendance Register",
		route: "/labour-attendance",
		newText: null,
		create: [],
		read: [
			"director",
			"pm",
			"qs",
			"site-engineer",
			"foreman",
			"accountant",
			"hr-manager",
			"admin",
			"bsa",
		],
	},
	{
		key: "Overtime Attendance Register",
		route: "/overtime-attendance",
		newText: null,
		create: [],
		read: [
			"director",
			"pm",
			"qs",
			"site-engineer",
			"foreman",
			"accountant",
			"hr-manager",
			"admin",
			"bsa",
		],
	},

	// --- Equipment ---
	{
		key: "Machinery",
		route: "/machinery",
		newText: "New",
		create: ["pm", "procurement", "store-keeper", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"site-engineer",
			"foreman",
			"procurement",
			"store-keeper",
			"accountant",
			"admin",
			"bsa",
		],
	},
	{
		key: "Machinery Usage",
		route: "/machinery-usage",
		newText: "Log usage",
		create: ["pm", "site-engineer", "foreman", "store-keeper", "admin", "bsa"],
		read: [
			"director",
			"pm",
			"site-engineer",
			"foreman",
			"procurement",
			"store-keeper",
			"accountant",
			"admin",
			"bsa",
		],
	},
];

const PERSONAS = [
	"director",
	"pm",
	"estimator",
	"qs",
	"site-engineer",
	"foreman",
	"procurement",
	"store-keeper",
	"accountant",
	"hr-manager",
	"admin",
	"bsa",
];

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
