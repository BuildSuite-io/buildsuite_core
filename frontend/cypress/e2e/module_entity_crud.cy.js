// Basic CRUD permission ENABLEMENT for every live-module entity outside the 6 PERSONA_CAPS
// ones (procurement / subcontract / estimation / workforce / equipment). For each entity this
// verifies the personas who SHOULD be able to create it can actually reach the list (read
// enablement) and see its "+ New" affordance (create enablement), and that read-only personas
// can still open the list. Expected create/read sets mirror the backend role matrix in
// buildsuite_core/permissions/setup.py.
//
// IMPORTANT — scope note: unlike the 6 PERSONA_CAPS views, these list views do NOT gate their
// "+ New" button (no usePermissions / canCreate) — it is shown to every persona that reaches
// the route. So this spec asserts the POSITIVE (authorised personas are enabled); it does not
// assert the negative (button hidden from read-only personas) because the UI does not currently
// enforce that. Closing that gap = extending PERSONA_CAPS + usePermissions to these entities;
// once done, flip the read-only personas to a "New must be hidden" assertion.
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
		create: ["procurement", "pm", "director", "admin", "bsa"],
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
		create: ["procurement", "pm", "director", "qs", "site-engineer", "admin", "bsa"],
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
	{
		key: "Subcontractor Bill",
		route: "/subcontractor-bills",
		newText: "New",
		create: ["procurement", "pm", "director", "qs", "admin", "bsa"],
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

describe("Read enablement — read-only personas can open each entity's list", () => {
	PERSONAS.forEach((persona) => {
		// entities the persona may read but not create (incl. the read-only registers)
		const mine = ENTITIES.filter(
			(e) => e.read.includes(persona) && !e.create.includes(persona)
		);
		if (!mine.length) return;
		it(`${persona}: can open its ${mine.length} read-only lists`, () => {
			cy.loginAs(persona);
			mine.forEach((e) => {
				cy.visitApp(e.route);
				cy.dt("page-title").should("be.visible");
			});
		});
	});
});
