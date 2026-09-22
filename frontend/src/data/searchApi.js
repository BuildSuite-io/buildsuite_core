import { frappeRequest } from "frappe-ui-frappe-request";

import { parseFrappeError } from "@/utils/frappeError";

// Records for the command palette — the permission-safe Frappe global-search index the Desk
// omnibar uses (buildsuite_core.api.search.global_search), narrowed to the app's record doctypes.
// Returns [{ doctype, name, title }], most relevant first; [] for a query under 2 chars.
export async function searchRecords(text, limit = 12) {
	try {
		return (
			(await frappeRequest({
				url: "buildsuite_core.api.search.global_search",
				params: { text, limit },
			})) || []
		);
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Search failed.");
	}
}
