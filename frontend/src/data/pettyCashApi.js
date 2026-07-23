import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Live Petty Cash Request endpoints (buildsuite_core.api.petty_cash.*). Request → Disburse
// (posts a Journal Entry) → reverse. The rest of the Project Finance workspace is mock data.
async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.petty_cash.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const pettyCashCanDisburse = () => call("can_disburse", {});
export const getPettyCash = (name) => call("get_request", { name });
export const savePettyCash = (payload) => call("save_request", { payload: JSON.stringify(payload) });
export const disbursePettyCash = (name, paidFrom) => call("disburse", { name, paid_from: paidFrom });
export const undisbursePettyCash = (name) => call("undisburse", { name });
export const cancelPettyCash = (name) => call("cancel_request", { name });
export const deletePettyCash = (name) => call("delete_request", { name });
export const listCashBankAccounts = (company) => call("list_cash_bank_accounts", { company });
export const pettyCashHolderBalances = (company) => call("holder_balances", { company });
