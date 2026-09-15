import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.quotation.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getQuotationSummary = () => call("get_summary");
// A terms template is the same record whoever pulls it in; invoice.py:830 owns the reader.
export { getInvoiceTerms as getQuotationTerms } from "@/data/invoiceApi";
export const getQuotation = (name) => call("get_quotation", { name });
export const saveQuotation = (payload) =>
	call("save_quotation", { payload: JSON.stringify(payload) });
export const markQuotationSent = (name) => call("mark_sent", { name });
export const markQuotationAccepted = (name) => call("mark_accepted", { name });
export const markQuotationRejected = (name, reason) => call("mark_rejected", { name, reason });
export const copyQuotation = (name) => call("copy_quotation", { name });
