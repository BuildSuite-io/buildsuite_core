import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// One page of rate masters + counts. See buildsuite_core.api.rate_master.
export async function listRateMasters(params) {
	try {
		return await frappeRequest({
			url: "buildsuite_core.api.rate_master.list_rate_masters",
			params: params || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Could not load rates.");
	}
}
