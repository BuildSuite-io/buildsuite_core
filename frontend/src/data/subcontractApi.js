import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.subcontract.* — Subcontractor Work Order
// read/save (its SOV child table can't go through the generic adapter), the approval
// workflow actions, and the BOQ cost-code picker. Subcontractor CRUD uses the
// generic data adapter (no child table).

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.subcontract.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getWorkOrder = (name) => call("get_work_order", { name });
export const getWoPrintData = (name) => call("get_wo_print_data", { name });
export const saveWorkOrder = (payload) =>
	call("save_work_order", { ...payload, lines: JSON.stringify(payload.lines || []) });
export const applyWoAction = (workOrder, action) =>
	call("apply_wo_action", { work_order: workOrder, action });
export const getWoTransitions = (name) => call("get_wo_transitions", { name });
export const getProjectCostCodes = (project) => call("get_project_cost_codes", { project });
export const getCommittedByCostCode = (project) => call("committed_by_cost_code", { project });

// Measurement Book — site measurements against a Work Order's SOV lines.
export const getWorkOrderLines = (workOrder) =>
	call("get_work_order_lines", { work_order: workOrder });
export const getMeasurementBook = (name) => call("get_measurement_book", { name });
export const saveMeasurementBook = (payload) =>
	call("save_measurement_book", { ...payload, entries: JSON.stringify(payload.entries || []) });
export const certifyMeasurementBook = (name) => call("certify_measurement_book", { name });
export const revertMeasurementBook = (name) => call("revert_measurement_book", { name });
export const getWoMeasurements = (workOrder) =>
	call("get_wo_measurements", { work_order: workOrder });

// --- Subcontractor Bill -------------------------------------------------
// The bill is the front-end instrument; Submit generates a linked Purchase
// Invoice. Taxes are country-agnostic (any Purchase Taxes and Charges Template).
async function billCall(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.subcontractor_bill.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getBill = (name) => billCall("get_bill", { name });
export const getWoBillContext = (workOrder) => billCall("get_wo_bill_context", { work_order: workOrder });
export const saveBill = (payload) => billCall("save_bill", { payload: JSON.stringify(payload) });
export const submitBill = (name) => billCall("submit_bill", { name });
export const cancelBill = (name) => billCall("cancel_bill", { name });
export const deleteBill = (name) => billCall("delete_bill", { name });
export const listTaxTemplates = (company) => billCall("list_tax_templates", { company });
export const getTaxTemplateRows = (template) => billCall("get_tax_template_rows", { template });
export const listWithholdingCategories = () => billCall("list_withholding_categories", {});
export const recordBillPayment = (args) => billCall("record_payment", args);
export const listBillPayments = (name) => billCall("list_payments", { name });
export const makeBillPaymentEntry = (name) => billCall("make_payment_entry", { name });
// Bank/Cash accounts a bill is paid FROM (default company); Modes of Payment for the modal.
export const listBillPayAccounts = () => billCall("list_pay_accounts", {});
export const listPaymentModes = () => billCall("list_payment_modes", {});
