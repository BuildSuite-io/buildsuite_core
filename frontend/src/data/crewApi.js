import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrapper over buildsuite_core.api.crew.save_crew — a Crew is a standing
// gang of field employees. The save goes through here because its `members`
// child table can't go through the generic adapter. Read and delete use it.

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.crew.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const saveCrew = (payload) =>
	call("save_crew", {
		...payload,
		members: JSON.stringify(payload.members || []),
	});
