import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.terms.* — the Terms & Conditions clause library
// (native "Terms and Conditions" doctype), segregated by the document a clause applies to.

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.terms.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// Access + the categories (applicable-for documents) to segregate the library by.
export const getTermsAccess = () => call("terms_access");
// Every clause the user may see (full-access roles; select-only roles get an empty list).
export const listTerms = () => call("list_terms");
// Create / update. payload: { name?, title, applicable_for, terms (HTML), disabled }.
export const saveTerms = (payload) => call("save_terms", payload);
export const deleteTerms = (name) => call("delete_terms", { name });
