import { frappeRequest } from "frappe-ui-frappe-request";

// Enabled payment term templates an offer can load. With a project category picked,
// only that category's templates; with none, all of them.
export const listPaymentTermTemplates = (category) =>
	frappeRequest({
		url: "frappe.client.get_list",
		params: {
			doctype: "BuildSuite Payment Term Template",
			fields: ["name"],
			filters: category ? { enabled: 1, project_category: category } : { enabled: 1 },
			order_by: "name asc",
			limit_page_length: 0,
		},
	});
