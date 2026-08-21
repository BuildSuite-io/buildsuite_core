import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

async function call(method) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.equipment.${method}`,
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getEquipmentDashboard = () => call("get_dashboard");
export const getMachineryUsageReport = () => call("machinery_usage_report");
export const getMachineryRegister = () => call("machinery_register");
