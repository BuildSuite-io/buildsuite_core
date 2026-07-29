// The company every finance transaction (and its pickers) is scoped to.
//
// Single-company for now: the site's default company, resolved by the backend
// `buildsuite_core.utils.project.default_company()` — the SAME value the server-side company
// guard uses, so picker filters and the guard always agree. We fetch it (once, cached) rather
// than read `window.sysdefaults.company`, which isn't reliably injected (e.g. the standalone
// Vite dev server) and can also point at a different company than default_company() resolves.
//
// This is the ONE seam for company scope. When multi-company ships, change this to derive the
// company from context (the active project, or a user selection) and every picker + guard that
// reads it follows automatically — no hardcoded default company scattered around.
import { computed, ref } from "vue";
import { frappeRequest } from "frappe-ui-frappe-request";

// Module-cached so the round-trip happens once per app load, shared by every caller.
const company = ref((typeof window !== "undefined" && window.sysdefaults?.company) || null);
let started = false;
function ensureLoaded() {
	if (started) return;
	started = true;
	frappeRequest({ url: "buildsuite_core.api.company.active_company" })
		.then((c) => {
			if (c) company.value = c;
		})
		.catch(() => {
			/* keep the sysdefaults fallback */
		});
}

// Returns a ref that resolves to the active company (may start null, then fill in). Pickers
// bind it via a reactive filter, and DeskLinkPicker re-queries when the filter changes.
export function useActiveCompany() {
	ensureLoaded();
	return company;
}

// A reactive DeskLinkPicker `:filters` fragment limiting a company-partitioned doctype
// (Account, Employee, Project, …) to the active company. Empty until the company is known, so
// the picker degrades to unfiltered rather than showing nothing (the server guard still blocks
// a cross-company save), then narrows once it resolves.
export function activeCompanyFilter() {
	const c = useActiveCompany();
	return computed(() => (c.value ? [["company", "=", c.value]] : []));
}
