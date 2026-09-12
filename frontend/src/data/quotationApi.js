import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Totals behind the Quotation KPI cards. See buildsuite_core.api.quotation.
export async function getQuotationSummary() {
	try {
		return await frappeRequest({ url: "buildsuite_core.api.quotation.get_summary" });
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Could not load quotation totals.");
	}
}
