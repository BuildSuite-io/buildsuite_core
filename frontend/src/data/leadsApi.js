import { frappeRequest } from "frappe-ui-frappe-request";

import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.leads.* — Sales › Leads on ERPNext's own Lead.

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.leads.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// [{ name, lead_name, company_name, mobile_no, city, utm_source, status, lead_owner, creation,
//    quotation_count, latest_quotation_total, latest_lost_reasons, customer, party_name, … }]
export const listLeads = () => call("list_leads");
// { lead, quotations: [...], customer, mobile_matches: [...], can: { write, delete, convert } }
export const getLead = (name) => call("get_lead", { name });
// [{ kind: 'Lead' | 'Customer', id, name, status }] — the "same person again" warning.
export const findMobileMatches = (mobile, exceptLead) =>
	call("find_mobile_matches", { mobile, except_lead: exceptLead || null });
// { name, lead_name, party_name, mobile_no, status }
export const createLead = (values) => call("create_lead", values || {});
// Returns the same shape as getLead.
export const updateLead = (name, values) => call("update_lead", { name, ...(values || {}) });
export const deleteLead = (name) => call("delete_lead", { name });
// { customer, customer_name, linked?, existing? }
export const convertLead = (name) => call("convert_lead", { name });
