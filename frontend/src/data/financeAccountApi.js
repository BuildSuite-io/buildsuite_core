import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Settings › Bank & Cash Accounts (S229). The finance-account master backed by ERPNext
// Account (Bank / Cash, company-scoped) — see buildsuite_core.api.finance_account.
// Balances are derived server-side: current = opening ± recorded movements.

export async function listFinanceAccounts() {
	try {
		return await frappeRequest({
			url: "buildsuite_core.api.finance_account.list_finance_accounts",
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Failed to load accounts.");
	}
}

export async function saveFinanceAccount(payload) {
	try {
		return await frappeRequest({
			url: "buildsuite_core.api.finance_account.save_finance_account",
			method: "POST",
			params: payload,
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Failed to save the account.");
	}
}

export async function deleteFinanceAccount(account) {
	try {
		return await frappeRequest({
			url: "buildsuite_core.api.finance_account.delete_finance_account",
			method: "POST",
			params: { account },
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Failed to delete the account.");
	}
}
