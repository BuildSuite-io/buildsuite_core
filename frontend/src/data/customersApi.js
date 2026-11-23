// Thin wrapper around the buildsuite_core.api.customers whitelisted methods.
// Mirrors data/projectTeamApi.js.
import { serverErrorMessage } from "@/utils/frappeError";

function serverMessage(data, status) {
	const message = serverErrorMessage(data?._server_messages);
	if (message) return message;
	return data?.exception || data?.exc_type || `Request failed (${status})`;
}

async function call(method, args) {
	const res = await fetch(`/api/method/buildsuite_core.api.customers.${method}`, {
		method: "POST",
		credentials: "include",
		headers: {
			"Content-Type": "application/json",
			"X-Frappe-CSRF-Token": window.csrf_token || "",
		},
		body: JSON.stringify(args || {}),
	});
	const data = await res.json().catch(() => ({}));
	if (!res.ok) throw new Error(serverMessage(data, res.status));
	return data.message;
}

// Inline create from the New Project client picker (name + type only).
export const createCustomer = (customerName, customerType = "Company") =>
	call("create_customer", { customer_name: customerName, customer_type: customerType });

// --- Project Finance › Customers master ---
export const listCustomers = () => call("list_customers", {});

// PartyFormModal payload → backend params. Contact person / phone / email persist
// onto the customer's native Contact.
export const addCustomer = (p) =>
	call("create_customer", {
		customer_name: p.name,
		customer_type: p.type || "Company",
		gstin: p.gstin || "",
		contact_person: p.contactPerson || "",
		phone: p.phone || "",
		email: p.email || "",
	});

export const updateCustomer = (id, p) =>
	call("update_customer", {
		name: id,
		new_name: p.name,
		customer_type: p.type || "",
		gstin: p.gstin || "",
		contact_person: p.contactPerson || "",
		phone: p.phone || "",
		email: p.email || "",
	});
