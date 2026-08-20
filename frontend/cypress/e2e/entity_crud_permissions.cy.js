// Basic CRUD permission gating in the UI — the create/read affordances a persona sees on
// each entity's list must match PERSONA_CAPS (the same table usePermissions() reads). This
// verifies every list view actually WIRES canCreate() — a view that forgot to gate its
// "+ New" button would show a create affordance the backend then rejects.
//
// The matrix is data-driven from PERSONA_CAPS itself, so it stays correct as caps change.
// Scope is the create affordance (the list-level CRUD gate) plus read-visibility; edit and
// delete are record-scoped detail-page affordances (own-scope resolves against the record's
// creator) and are covered separately.
//
// Requires the persona test users:
//   bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users

import { PERSONA_CAPS } from "../../src/data/roles";

// entity key (matches PERSONA_CAPS) -> its list route + the "+ New" affordance label.
const ENTITIES = [
	{ key: "project", route: "/projects", newText: "New" },
	{ key: "workPackage", route: "/work-packages", newText: "New" },
	{ key: "task", route: "/tasks", newText: "New" },
	{ key: "taskProgressEntry", route: "/progress-entries", newText: "New Entry" },
	{ key: "stagePlanning", route: "/stage-plannings", newText: "New Stage" },
	{ key: "sco", route: "/sco", newText: "New" },
];

const PERSONAS = Object.keys(PERSONA_CAPS);

describe("Create/read affordances follow persona capabilities", () => {
	PERSONAS.forEach((persona) => {
		it(`${persona}: list affordances match PERSONA_CAPS`, () => {
			cy.loginAs(persona);

			ENTITIES.forEach(({ key, route, newText }) => {
				const caps = PERSONA_CAPS[persona][key];
				// No-read entities render a restricted state (or aren't reachable), gated
				// differently per view — covered by permissions.cy.js, skipped here.
				if (!caps || caps.r === false) return;

				cy.visitApp(route);
				cy.dt("page-title").should("be.visible"); // the list is readable

				if (caps.c === true) {
					// Create-capable personas (full + own-scope) get the "+ New" affordance.
					cy.dt("page-actions").contains(newText).should("be.visible");
				} else {
					// Read-only personas must NOT see a create affordance in the header.
					cy.dt("page-actions").should("not.contain", newText);
				}
			});
		});
	});
});
