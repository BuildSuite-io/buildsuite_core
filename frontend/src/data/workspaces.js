// Workspace UI helpers. Workspace visibility, ordering, and presentation metadata now
// come from the backend registry (api.workspace_setting.get_visible_workspaces →
// store.workspaces). What remains here: the access-hint label map + the live-count helper.

// Friendly labels for access-level hints (CLAUDE.md §12.3). The DeskShell sidebar uses
// single-letter abbreviations (R, A, C, …); landings have more horizontal space so they
// show the full word.
export const ACCESS_LABEL = {
	read: "Read",
	approve: "Approve",
	"create-own": "Create",
	"self-service": "Self-service",
	"team-only": "Team",
	"pay-only": "Pay",
	"mr-only": "MR raise",
};

// One-line "live metric" string for a workspace tile. Returns null when the seed/store
// doesn't have data to back a real number — callers should omit the metric line rather
// than display a fake count. Reading the store here keeps the call site's computed()
// reactive to the underlying state.
export function workspaceMetric(slug, store) {
	switch (slug) {
		case "site-execution": {
			// Session 33: includes pending-SCO count since Scope Change merged here.
			const projects = store.activeProjectsCount;
			const scos = store.pendingScosCount;
			const base = `${projects} active project${projects === 1 ? "" : "s"}`;
			return scos ? `${base} · ${scos} pending SCO${scos === 1 ? "" : "s"}` : base;
		}
		case "estimation": {
			const active = store.activeBoqsCount;
			const draft = store.draftBoqsCount;
			if (!active && !draft) return null;
			return `${active} active · ${draft} draft BOQ${draft === 1 ? "" : "s"}`;
		}
		// The four below have no domain data in seed yet — return null to omit the metric.
		case "procurement":
		case "subcontract":
		case "workforce":
		case "project-finance":
			return null;
		// ERPNext workspaces — placeholder data only.
		case "accounting":
		case "buying":
		case "stock":
		case "assets":
		case "hr":
			return null;
		default:
			return null;
	}
}
