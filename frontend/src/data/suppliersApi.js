// Thin wrapper around the buildsuite_core.api.suppliers whitelisted methods
// (Project Finance › Suppliers master). Mirrors data/customersApi.js.

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
	const res = await fetch(`/api/method/buildsuite_core.api.suppliers.${method}`, {
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

// Every supplier incl. subcontractors (rows carry is_subcontractor + trade).
export const listSuppliers = () => call("list_suppliers", {});

// PartyFormModal payload → backend params (regular suppliers only; subcontractors
// are managed in the Subcontract module). Contact fields persist onto the Contact.
export const addSupplier = (p) =>
	call("create_supplier", {
		supplier_name: p.name,
		supplier_type: p.type || "Company",
		gstin: p.gstin || "",
		contact_person: p.contactPerson || "",
		phone: p.phone || "",
		email: p.email || "",
	});

export const updateSupplier = (id, p) =>
	call("update_supplier", {
		name: id,
		new_name: p.name,
		supplier_type: p.type || "",
		gstin: p.gstin || "",
		contact_person: p.contactPerson || "",
		phone: p.phone || "",
		email: p.email || "",
	});
