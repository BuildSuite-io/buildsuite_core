import { frappeRequest } from "frappe-ui-frappe-request";

import { parseFrappeError } from "@/utils/frappeError";

// Real-data backends for the six bespoke Procurement report views
// (buildsuite_core.api.procurement_report.*). Each takes an optional `project` that narrows the
// report to that project and its direct sub-projects; without it the report runs portfolio-wide.
async function call(method, project) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.procurement_report.${method}`,
			params: project ? { project } : {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getRequestsToOrder = (project) => call("requests_to_order", project);
export const getDeliveryFollowup = (project) => call("delivery_followup", project);
export const getSiteStock = (project) => call("site_stock", project);
export const getRateCheck = (project) => call("rate_check", project);
export const getPurchaseRegister = (project) => call("purchase_register", project);
export const getConsumptionByCostCode = (project) => call("consumption_by_cost_code", project);

// slug → fetcher, so the dispatcher view can load whichever report the route asks for.
export const PROCUREMENT_REPORTS = {
	"requests-to-order": getRequestsToOrder,
	"delivery-followup": getDeliveryFollowup,
	"site-stock": getSiteStock,
	"rate-check": getRateCheck,
	"purchase-register": getPurchaseRegister,
	"consumption-by-cost-code": getConsumptionByCostCode,
};
