import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Generic single-record CRUD over Frappe's standard `frappe.client.*` endpoints,
// used by the generic /records form (DocTypeForm). Permissions are enforced
// server-side; this is a thin, doctype-agnostic wrapper.

async function call(method, params) {
	try {
		return await frappeRequest({ url: method, params: params || {} });
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// Full document incl. child tables.
export const getRecord = (doctype, name) => call("frappe.client.get", { doctype, name });

// Insert a new document. `doc` is a plain object with at least `doctype`.
export const insertRecord = (doc) => call("frappe.client.insert", { doc: JSON.stringify(doc) });

// Save an existing document (round-trips the full doc, so untouched child tables survive).
export const saveRecord = (doc) => call("frappe.client.save", { doc: JSON.stringify(doc) });

export const deleteRecord = (doctype, name) => call("frappe.client.delete", { doctype, name });
