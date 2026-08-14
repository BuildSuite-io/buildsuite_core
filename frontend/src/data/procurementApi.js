import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

async function call(method) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.procurement.${method}`,
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getProcurementDashboard = () => call("get_dashboard");

// --- In-app procurement documents (Material Request / Purchase Order / Purchase
// Receipt) — read/save their child `items` tables + the native submittable
// lifecycle (Draft → Submit → Cancel → Amend). Backed by api.procurement_docs.*.
async function docCall(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.procurement_docs.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// Material Request
export const getMaterialRequest = (name) => docCall("get_material_request", { name });
export const saveMaterialRequest = (payload) =>
	docCall("save_material_request", { ...payload, items: JSON.stringify(payload.items || []) });
export const submitMaterialRequest = (name) => docCall("submit_material_request", { name });
export const cancelMaterialRequest = (name) => docCall("cancel_material_request", { name });
export const amendMaterialRequest = (name) => docCall("amend_material_request", { name });
export const deleteMaterialRequest = (name) => docCall("delete_material_request", { name });

// Purchase Order
export const getPurchaseOrder = (name) => docCall("get_purchase_order", { name });
export const getMrForPo = (materialRequest) =>
	docCall("get_mr_for_po", { material_request: materialRequest });
export const savePurchaseOrder = (payload) =>
	docCall("save_purchase_order", { ...payload, items: JSON.stringify(payload.items || []) });
export const submitPurchaseOrder = (name) => docCall("submit_purchase_order", { name });
export const cancelPurchaseOrder = (name) => docCall("cancel_purchase_order", { name });
export const amendPurchaseOrder = (name) => docCall("amend_purchase_order", { name });
export const deletePurchaseOrder = (name) => docCall("delete_purchase_order", { name });

// Purchase Receipt (derived from a submitted PO)
export const getOpenPurchaseOrders = () => docCall("get_open_purchase_orders");
export const getReceiptDraft = (purchaseOrder) =>
	docCall("get_receipt_draft", { purchase_order: purchaseOrder });
export const getPurchaseReceipt = (name) => docCall("get_purchase_receipt", { name });
export const savePurchaseReceipt = (payload) =>
	docCall("save_purchase_receipt", { ...payload, items: JSON.stringify(payload.items || []) });
export const submitPurchaseReceipt = (name) => docCall("submit_purchase_receipt", { name });
export const cancelPurchaseReceipt = (name) => docCall("cancel_purchase_receipt", { name });
export const amendPurchaseReceipt = (name) => docCall("amend_purchase_receipt", { name });
export const deletePurchaseReceipt = (name) => docCall("delete_purchase_receipt", { name });
