import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.sales.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getPaymentTermsAccess = () => call("payment_terms_access");
export const listPaymentTermsTemplates = () => call("list_payment_terms_templates");
export const savePaymentTermsTemplate = (payload) =>
	call("save_payment_terms_template", {
		...payload,
		milestones: JSON.stringify(payload.milestones || []),
	});
export const deletePaymentTermsTemplate = (name) =>
	call("delete_payment_terms_template", { name });
