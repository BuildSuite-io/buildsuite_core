import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Server-rendered print HTML for the SPA print views. Renders whatever Frappe would
// render in Desk — the doctype's DEFAULT Print Format + the default (or the document's
// own) Letter Head — so changing the default format or letter head in Desk changes the
// SPA print view with no frontend change. Read permission is enforced server-side.
//
// Returns { html, style, print_format }. Pass opts.print_format / opts.letterhead /
// opts.language to override; omit them for the Desk defaults.
export async function getPrintHtml(doctype, name, opts = {}) {
	try {
		return await frappeRequest({
			url: "buildsuite_core.api.printing.get_print_html",
			params: { doctype, name, ...opts },
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Failed to render print format.");
	}
}
