import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Live Project Finance › Invoices endpoints (buildsuite_core.api.invoice.*). An invoice IS an
// ERPNext Sales Invoice; these create drafts, list them, submit/cancel, and receive payments.
async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.invoice.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const listInvoices = (args = {}) => call("list_invoices", args);
export const getInvoice = (name) => call("get_invoice", { name });
export const saveInvoice = (payload) => call("save_invoice", { payload: JSON.stringify(payload) });
export const submitInvoice = (name) => call("submit_invoice", { name });
export const cancelInvoice = (name) => call("cancel_invoice", { name });
export const deleteInvoice = (name) => call("delete_invoice", { name });
export const recordInvoiceReceipt = (args) => call("record_receipt", args);
export const listInvoiceReceipts = (name) => call("list_receipts", { name });
export const recordCustomerAdvance = (args) => call("record_advance", args);
export const invoiceAdvancesSummary = () => call("advances_summary", {});
export const availableInvoiceAdvances = (name) => call("available_advances", { name });
export const linkInvoiceAdvance = (args) => call("link_advance", args);
export const unlinkInvoiceAdvance = (args) => call("unlink_advance", args);
export const invoiceReceivablesSummary = () => call("receivables_summary", {});
export const listDepositAccounts = () => call("list_deposit_accounts", {});
export const listInvoiceTaxTemplates = () => call("list_tax_templates", {});
export const getInvoiceTaxTemplateRows = (template) => call("get_tax_template_rows", { template });
export const getInvoiceTerms = (name) => call("get_terms", { name });
export const listInvoicePaymentModes = () => call("list_payment_modes", {});
