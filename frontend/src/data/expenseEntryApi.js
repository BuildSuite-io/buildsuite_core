import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Live Expense Entry endpoints (buildsuite_core.api.expense_entry.*). The signed-in
// holder spends against their petty-cash float; a finance approver submits to post
// the Journal Entry. Balances + ledger come from the employee petty-cash ledger.
async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.expense_entry.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const expenseContext = () => call("context", {});
export const listExpenses = () => call("list_expenses", {});
export const getExpense = (name) => call("get_expense", { name });
export const expenseLedger = (filters = {}) => call("ledger", filters);
export const saveExpense = (payload) => call("save_expense", { payload: JSON.stringify(payload) });
export const submitExpense = (name) => call("submit_expense", { name });
export const cancelExpense = (name) => call("cancel_expense", { name });
export const listExpenseAccounts = (company) => call("list_expense_accounts", { company });
export const expenseToReimburse = () => call("to_reimburse", {});
export const reimburseExpense = (name, bankAccount) => call("reimburse", { name, bank_account: bankAccount });
export const listReimburseAccounts = (company) => call("list_cash_bank_accounts", { company });
