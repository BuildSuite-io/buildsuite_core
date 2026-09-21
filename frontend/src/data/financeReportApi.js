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

// company is optional — the backend falls back to default_company() (the single-company seam);
// pass the active company so these follow the topbar switcher when multi-company is enabled.
export const getReceivablesPayables = (company) =>
	call("receivables_and_payables", company ? { company } : {});
export const getFinancialPosition = (company) =>
	call("financial_position", company ? { company } : {});
export const getCashBankAccounts = (company) =>
	call("cash_bank_accounts", company ? { company } : {});
export const getCashBankStatement = (account, from_date, to_date) =>
	call("cash_bank_statement", { account, from_date, to_date });
export const getProfitAndLoss = ({ project, from_date, to_date } = {}) =>
	call("profit_and_loss", { project, from_date, to_date });
