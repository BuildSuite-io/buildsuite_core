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
// Company awareness master switch (BuildSuite Core Settings). Off until the backend says
// otherwise — when off, the filter helpers below return [] so nothing is company-scoped.
const enabled = ref(false);
let started = false;
function ensureLoaded() {
	if (started) return;
	started = true;
	frappeRequest({ url: "buildsuite_core.api.company.company_context" })
		.then((ctx) => {
			if (ctx?.company) company.value = ctx.company;
			enabled.value = !!ctx?.multi_company_enabled;
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

// Authoritative setter for the active company. The topbar switcher (via
// store.setActiveCompany) calls this so `activeCompanyFilter()` re-computes and every bound
// picker re-queries the moment the user switches company. `started` is flipped so the lazy
// initial fetch can't later clobber the user's explicit choice.
export function setActiveCompany(name) {
	if (!name) return;
	started = true;
	company.value = name;
}

// Reactive company-awareness flag (for the switcher + any UI that shows/hides on it).
export function companyAwarenessEnabled() {
	ensureLoaded();
	return enabled;
}

// Sync the flag from the store (which loads it alongside the company list) so the composable and
// the store never disagree. Doesn't flip `started` — the company value still resolves normally.
export function setCompanyAwareness(on) {
	enabled.value = !!on;
}

// A reactive DeskLinkPicker `:filters` fragment limiting a company-partitioned doctype
// (Account, Employee, Project, …) to the active company. Empty until the company is known, so
// the picker degrades to unfiltered rather than showing nothing (the server guard still blocks
// a cross-company save), then narrows once it resolves.
export function activeCompanyFilter() {
	const c = useActiveCompany();
	return computed(() => (enabled.value && c.value ? [["company", "=", c.value]] : []));
}

// Doctypes that carry a `company` field and whose pickers must be scoped to the working
// company. Kept here (the one company-scope seam) so DeskLinkPicker can auto-scope every picker
// of these doctypes — no per-call-site opt-in — keeping all pickers consistent. Covers the
// ERPNext masters we company-scoped (Supplier/Customer/Item/Employee) plus every BuildSuite
// company-scoped doctype and per-company master. Keep in sync when a doctype gains `company`.
const COMPANY_SCOPED_DOCTYPES = new Set([
	"Project",
	"Employee",
	"Supplier",
	"Customer",
	"Item",
	"BOQ",
	"Subcontractor Work Order",
	"Subcontractor Bill",
	"Measurement Book",
	"Scope Change Order",
	"Work Package",
	"Stage Planning",
	"Field Attendance",
	"Machinery",
	"Machinery Usage",
	"Crew",
	"Petty Cash Request",
	"Expense Entry",
	"Assembly",
	"Assembly Category",
	"Construction Rate Master",
	"Rate Master Category",
	"Estimate Template",
	"Project Category",
	"Machinery Type",
	"Subcontract Delivery Type",
	"Construction Trade",
	"Labour Trade",
]);

export function isCompanyScopedDoctype(doctype) {
	return COMPANY_SCOPED_DOCTYPES.has(doctype);
}

// The active-company `:filters` fragment for a specific doctype: the company filter when that
// doctype is company-scoped, else [] (so org-wide pickers like Company/UOM stay unfiltered).
// DeskLinkPicker uses this to auto-scope any company-partitioned picker.
export function companyFilterForDoctype(doctype) {
	const c = useActiveCompany();
	return computed(() =>
		enabled.value && c.value && COMPANY_SCOPED_DOCTYPES.has(doctype)
			? [["company", "=", c.value]]
			: []
	);
}
