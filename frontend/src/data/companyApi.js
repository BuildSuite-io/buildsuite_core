import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

async function call(method) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.company.${method}`,
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// The logged-in user's default company (User → user default → site default).
export const getActiveCompany = () => call("active_company");
