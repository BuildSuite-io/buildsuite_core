// The company every finance transaction (and its pickers) is scoped to.
//
// Single-company for now: the site's default company, exposed to the browser as
// `window.sysdefaults.company` — the same value the backend's
// `buildsuite_core.utils.project.default_company()` resolves to, so the picker filters
// and the server-side company guard always agree.
//
// This is the ONE seam for company scope. When multi-company ships, change this to derive
// the company from context (the active project, or a user selection) and every picker +
// guard that reads it follows automatically — no hardcoded default company scattered around.
export function useActiveCompany() {
	return (typeof window !== "undefined" && window.sysdefaults?.company) || null;
}

// Convenience: a DeskLinkPicker `:filters` fragment that limits a company-partitioned
// doctype (Account, Employee, Project, …) to the active company. Empty when the company is
// unknown, so the picker degrades to unfiltered rather than showing nothing (the server
// guard still blocks a cross-company save).
export function activeCompanyFilter() {
	const company = useActiveCompany();
	return company ? [["company", "=", company]] : [];
}
