// Generate cypress/support/personaCaps.js from the LIVE backend — the oracle for the
// permission e2e specs, replacing the deleted src/data/roles.js PERSONA_CAPS export.
const BASE = "http://localhost:8000";
const PWD = "Cypress-Suite-2026!";
const PERSONA_IDS = [
	"director", "pm", "estimator", "qs", "site-engineer", "foreman",
	"procurement", "store-keeper", "accountant", "hr-manager", "admin", "bsa",
];
const scope = (s) => (s === "all" ? true : s === "own" ? "own" : false);

async function login(usr) {
	const res = await fetch(`${BASE}/api/method/login`, {
		method: "POST",
		headers: { "Content-Type": "application/x-www-form-urlencoded" },
		body: new URLSearchParams({ usr, pwd: PWD }),
	});
	const cookie = (res.headers.getSetCookie?.() || []).map((c) => c.split(";")[0]).join("; ");
	if (!cookie) throw new Error(`login failed for ${usr}`);
	return cookie;
}
async function caps(cookie) {
	const res = await fetch(`${BASE}/api/method/buildsuite_core.api.permission.get_resource_permissions`, {
		headers: { Cookie: cookie },
	});
	return (await res.json()).message || {};
}

const matrix = {};
for (const id of PERSONA_IDS) {
	const rp = await caps(await login(`cypress-${id}@buildsuite.test`));
	const out = {};
	for (const [k, p] of Object.entries(rp)) {
		out[k] = { c: p.c === true, r: p.r === true, e: scope(p.writeScope), d: scope(p.deleteScope), x: p.x === true };
	}
	matrix[id] = out;
}

// Emit as a .js module. Keys sorted for a stable diff on regeneration.
const fmtCap = (c) => `{ c: ${c.c}, r: ${c.r}, e: ${JSON.stringify(c.e)}, d: ${JSON.stringify(c.d)}, x: ${c.x} }`;
let body = "";
for (const id of PERSONA_IDS) {
	body += `\t"${id}": {\n`;
	for (const key of Object.keys(matrix[id]).sort()) body += `\t\t${key}: ${fmtCap(matrix[id][key])},\n`;
	body += `\t},\n`;
}
const header = `// AUTO-GENERATED — do not edit by hand.
// The permission e2e oracle: each persona's UI caps DERIVED FROM THE BACKEND
// (buildsuite_core.api.permission.get_resource_permissions). Replaces the retired
// src/data/roles.js PERSONA_CAPS matrix so the specs assert the UI against the same
// backend source usePermissions now reads. Shape mirrors the old export exactly:
// PERSONA_CAPS[personaId][resourceKey] = { c, r, e, d, x } with e/d as true | "own" | false.
//
// Regenerate after any backend DocPerm change (site must be running on :8000 with the
// persona users provisioned):
//   bench --site <site> execute buildsuite_core.api.cypress_setup.ensure_cypress_users
//   node cypress/support/gen_persona_caps.mjs > cypress/support/personaCaps.js
// The persona_caps_fresh.cy.js spec fails loudly if this drifts from the live backend.

export const PERSONA_CAPS = {\n`;
process.stdout.write(header + body + "};\n");
