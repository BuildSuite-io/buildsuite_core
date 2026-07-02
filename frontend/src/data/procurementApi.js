import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

async function call(method) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.procurement.${method}`,
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getProcurementDashboard = () => call("get_dashboard");
