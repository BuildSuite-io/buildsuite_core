import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Request for Quotation, Supplier Quotation and their comparison (ERPNext's Buying documents) —
// read/save their child tables + the native submittable lifecycle (Draft → Submit → Cancel →
// Amend), the per-supplier email / print, and the comparison. Backed by api.rfq.*.
async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.rfq.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// Request for Quotation
export const getRfq = (name) => call("get_request_for_quotation", { name });
export const getMrForRfq = (materialRequest) =>
	call("get_mr_for_rfq", { material_request: materialRequest });
export const getSupplierContact = (supplier) => call("get_supplier_contact", { supplier });
export const saveRfq = (payload) =>
	call("save_request_for_quotation", {
		...payload,
		suppliers: JSON.stringify(payload.suppliers || []),
		items: JSON.stringify(payload.items || []),
	});
export const submitRfq = (name) => call("submit_request_for_quotation", { name });
export const cancelRfq = (name) => call("cancel_request_for_quotation", { name });
export const amendRfq = (name) => call("amend_request_for_quotation", { name });
export const deleteRfq = (name) => call("delete_request_for_quotation", { name });
export const getRfqListSummaries = (names) =>
	call("rfq_list_summaries", { names: JSON.stringify(names || []) });

// The person / address a request goes to, corrected on the request and offered back to the master.
export const setRfqSupplierContact = (name, supplier, values) =>
	call("set_rfq_supplier_contact", { name, supplier, ...values });
export const saveRfqContactToSupplier = (name, supplier) =>
	call("save_rfq_contact_to_supplier", { name, supplier });

// One copy per supplier: the print view's HTML and the email that carries it.
export const getRfqPrintHtml = (name, supplier) =>
	call("get_rfq_print_html", { name, supplier: supplier || undefined });
export const sendRfqEmails = (name, suppliers) =>
	call("send_rfq_emails", { name, suppliers: JSON.stringify(suppliers || []) });

// Supplier Quotation
export const getSupplierQuotation = (name) => call("get_supplier_quotation", { name });
// Stamp Expired on lapsed quotations before the list loads (ERPNext's daily job, run now).
export const expireLapsedQuotations = () =>
	frappeRequest({
		url: "buildsuite_core.api.rfq.expire_lapsed_quotations",
		method: "POST",
	});
export const getRfqForSq = (rfq) => call("get_rfq_for_sq", { request_for_quotation: rfq });
export const saveSupplierQuotation = (payload) =>
	call("save_supplier_quotation", { ...payload, items: JSON.stringify(payload.items || []) });
export const submitSupplierQuotation = (name) => call("submit_supplier_quotation", { name });
export const cancelSupplierQuotation = (name) => call("cancel_supplier_quotation", { name });
export const amendSupplierQuotation = (name) => call("amend_supplier_quotation", { name });
export const deleteSupplierQuotation = (name) => call("delete_supplier_quotation", { name });
// Prefill for a Purchase Order raised from a submitted quotation.
export const getSqForPo = (sq) => call("get_sq_for_po", { supplier_quotation: sq });

// Supplier Quotation Comparison
export const getComparisonRequests = () => call("comparison_requests");
export const getSupplierQuotationComparison = (rfq) =>
	call("supplier_quotation_comparison", { request_for_quotation: rfq });

export const isEmail = (v) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(v || "").trim());
export const todayISO = () => {
	const d = new Date();
	return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};
