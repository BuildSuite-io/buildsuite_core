import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Live Project Finance › Bills endpoints for the SUPPLIER bill (buildsuite_core.api.supplier_bill.*).
// A supplier bill IS an ERPNext Purchase Invoice; subcontractor bills use their own module.
async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.supplier_bill.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const listPayables = (args = {}) => call("list_payables", args);
export const payablesSummary = () => call("payables_summary", {});
export const getSupplierBill = (name) => call("get_bill", { name });
export const saveSupplierBill = (payload) =>
	call("save_bill", { payload: JSON.stringify(payload) });
export const submitSupplierBill = (name) => call("submit_bill", { name });
export const cancelSupplierBill = (name) => call("cancel_bill", { name });
export const deleteSupplierBill = (name) => call("delete_bill", { name });
export const recordSupplierBillPayment = (args) => call("record_payment", args);
export const listSupplierBillPayments = (name) => call("list_payments", { name });
export const recordSupplierAdvance = (args) => call("record_advance", args);
export const availableSupplierBillAdvances = (name) => call("available_advances", { name });
export const linkSupplierBillAdvance = (args) => call("link_advance", args);
export const unlinkSupplierBillAdvance = (args) => call("unlink_advance", args);
export const listBillPayAccounts = () => call("list_pay_accounts", {});
export const getSupplierBillTaxRows = (template) => call("get_tax_template_rows", { template });
export const getSupplierBillTerms = (name) => call("get_terms", { name });
export const listSupplierBillPaymentModes = () => call("list_payment_modes", {});
// From-Purchase-Order flow: billable POs, PO→bill-line prefill, and Item-master defaults.
export const listBillablePurchaseOrders = (company) =>
	call("list_billable_purchase_orders", company ? { company } : {});
export const getPoBillLines = (purchaseOrder) =>
	call("get_po_bill_lines", { purchase_order: purchaseOrder });
export const getSupplierBillItemDetails = (itemCode) =>
	call("get_item_details", { item_code: itemCode });
