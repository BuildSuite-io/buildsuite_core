import { frappeRequest } from "frappe-ui-frappe-request";

import { parseFrappeError } from "@/utils/frappeError";

// The backend half of the command palette (buildsuite_core.api.search.command_palette): the same
// permission-safe Frappe global-search index the Desk omnibar uses, plus name-matched doctypes.
// Returns { doctypes: [{doctype, label}], records: [{doctype, name, title}] }; both [] for a query
// under 2 chars. May throw — the caller treats a failure as empty.
export async function commandPalette(text, limit = 12) {
	try {
		const r = await frappeRequest({
			url: "buildsuite_core.api.search.command_palette",
			params: { text, limit },
		});
		return { doctypes: r?.doctypes || [], records: r?.records || [] };
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Search failed.");
	}
}
