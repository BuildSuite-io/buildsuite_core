import { frappeRequest } from "frappe-ui-frappe-request";

import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.quotation.* — a quotation's lifecycle: send it (submit),
// then the client accepts (a lead converts) or turns it down (with a reason).

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

export const sendQuotation = (name) => call("send_quotation", { name });
// { name, customer, linked } — customer is null when the user may not create customers (the lead waits)
export const acceptQuotation = (name) => call("accept_quotation", { name });
export const rejectQuotation = (
	name,
	{ lostReasons = [], competitors = [], detailedReason = "" }
) =>
	call("reject_quotation", {
		name,
		lost_reasons: JSON.stringify(lostReasons),
		competitors: JSON.stringify(competitors),
		detailed_reason: detailedReason,
	});
