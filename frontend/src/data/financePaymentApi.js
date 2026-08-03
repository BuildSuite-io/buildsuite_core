import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Project Finance › Payments — the unified party-payment register over ERPNext Payment Entries
// (buildsuite_core.api.finance_payment.*). Cancel reverses a posted Payment Entry.
async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.finance_payment.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const listFinancePayments = () => call("list_payments", {});
export const cancelFinancePayment = (name) => call("cancel_payment", { name });
