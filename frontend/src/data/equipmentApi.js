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

async function post(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.equipment.${method}`,
			method: "POST",
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const submitMachineryUsage = (name) => post("submit_machinery_usage", { name });
export const cancelMachineryUsage = (name) => post("cancel_machinery_usage", { name });

export const getEquipmentDashboard = () => call("get_dashboard");
export const getMachineryUsageReport = () => call("machinery_usage_report");
export const getMachineryRegister = () => call("machinery_register");
