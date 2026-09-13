import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.quotation.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getQuotationSummary = () => call("get_summary");
