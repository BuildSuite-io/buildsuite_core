// Drift guard for the permission e2e oracle.
//
// support/personaCaps.js is a committed snapshot of each persona's backend-derived caps
// (buildsuite_core.api.permission.get_resource_permissions). The other permission specs
// assert the rendered UI against it. If the backend DocPerms change but the snapshot isn't
// regenerated, those specs would silently validate against stale expectations — so this
// spec re-fetches the caps live per persona and asserts they still equal the snapshot.
//
// If this fails: regenerate the oracle (see the header in support/personaCaps.js) and
// commit the result.
//
// Requires the persona test users:
//   bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users

import { PERSONA_CAPS } from "../support/personaCaps";

const scopeToCap = (s) => (s === "all" ? true : s === "own" ? "own" : false);

// Rebuild the {c,r,e,d,x} tri-state the snapshot stores from a live payload — the same
// reconstruction usePermissions and the generator use.
function reconstruct(payload) {
	const out = {};
	for (const [key, p] of Object.entries(payload || {})) {
		out[key] = {
			c: p.c === true,
			r: p.r === true,
			e: scopeToCap(p.writeScope),
			d: scopeToCap(p.deleteScope),
			x: p.x === true,
		};
	}
	return out;
}

describe("Permission oracle is in sync with the backend", () => {
	Object.keys(PERSONA_CAPS).forEach((persona) => {
		it(`${persona}: committed personaCaps.js matches live get_resource_permissions`, () => {
			cy.loginAs(persona);
			cy.request(
				"/api/method/buildsuite_core.api.permission.get_resource_permissions"
			).then((res) => {
				const live = reconstruct(res.body.message);
				expect(live, `${persona} caps drifted — regenerate support/personaCaps.js`).to.deep.equal(
					PERSONA_CAPS[persona]
				);
			});
		});
	});
});
