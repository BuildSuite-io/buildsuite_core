// Thin wrapper around the buildsuite_core.api.customers whitelisted methods.
// Mirrors data/projectTeamApi.js.

function serverMessage(data, status) {
	if (data?._server_messages) {
		try {
			const first = JSON.parse(data._server_messages)[0];
			const parsed = JSON.parse(first);
			if (parsed?.message) return String(parsed.message).replace(/<[^>]*>/g, "");
		} catch {
			/* fall through */
		}
	}
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

export const createCustomer = (customerName, customerType = "Company") =>
	call("create_customer", { customer_name: customerName, customer_type: customerType });
