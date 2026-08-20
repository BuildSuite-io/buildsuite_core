import { frappeRequest } from "frappe-ui-frappe-request";

import { parseFrappeError } from "@/utils/frappeError";

// Real-data backends for the two bespoke Project Finance views (buildsuite_core.api.finance_report.*).
async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.finance_report.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getReceivablesPayables = () => call("receivables_and_payables", {});
export const getFinancialPosition = () => call("financial_position", {});
