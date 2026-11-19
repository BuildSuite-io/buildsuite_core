/**
 * Utilities for parsing Frappe HTTP error responses into user-friendly
 * messages and per-field error objects.
 *
 * Frappe error response shape (HTTP 417 / 409 / 500):
 *   {
 *     exc_type: "MandatoryError",
 *     exc: "...Traceback...\nfrappe.exceptions.MandatoryError: [Project, X]: company\nfield2",
 *     _server_messages: "[{\"message\": \"...\"}]"   ← double-encoded JSON
 *   }
 */

// Human-readable labels for common Frappe field names. Falls back to
// Title-Cased snake_case for anything not listed.
const FIELD_LABELS = {
	company: "Company",
	project_name: "Project Name",
	custom_project_id: "Project ID",
	customer: "Client",
	project_type: "Project Type",
	expected_start_date: "Start Date",
	expected_end_date: "End Date",
	estimated_costing: "Budget",
	owner: "Project Manager",
	task: "Task",
	entry_date: "Entry Date",
	cumulative_progress: "Progress",
	work_package: "Work Package",
	work_package_name: "Work Package Name",
	subject: "Task Name",
	status: "Status",
};

function fieldLabel(name) {
	return FIELD_LABELS[name] ?? name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Strip HTML tags from a Frappe server message and decode HTML entities.
 * Frappe often wraps field names and document links in <strong><a> tags that
 * point to /desk/... URLs, which are useless in the Vue app.
 */
function stripHtml(html) {
	if (!html || !html.includes("<")) return html;
	const div = document.createElement("div");
	div.innerHTML = html;
	return (div.textContent || div.innerText || "").trim();
}

/**
 * Frappe encodes _server_messages as a JSON string whose elements are
 * themselves JSON strings or objects. Unwrap both layers safely into
 * { text, raised, alert } entries, in the order the server logged them.
 */
function serverMessageEntries(raw) {
	if (!raw) return [];
	try {
		const arr = typeof raw === "string" ? JSON.parse(raw) : Array.isArray(raw) ? raw : [];
		return arr
			.map((item) => {
				let entry = item;
				if (typeof item === "string") {
					try {
						entry = JSON.parse(item);
					} catch {
						entry = item;
					}
				}
				if (entry && typeof entry === "object") {
					return {
						text: stripHtml(entry.message ?? ""),
						raised: Boolean(entry.raise_exception),
						alert: Boolean(entry.alert),
					};
				}
				return { text: stripHtml(String(entry ?? "")), raised: false, alert: false };
			})
			.filter((e) => e.text);
	} catch {
		return [];
	}
}

function parseServerMessages(raw) {
	return serverMessageEntries(raw).map((e) => e.text);
}

/**
 * The message a failed call should show, from its raw `_server_messages`.
 *
 * A request can log several messages before it fails: ERPNext validation shows an
 * "Item Price added for …" alert, say, and then throws "The item … is not marked as purchase
 * item". Showing the first hid the real error. Prefer the message raised as the exception, then
 * the last one that isn't a passing alert, then the last. Returns null when there are none.
 */
export function serverErrorMessage(raw) {
	const entries = serverMessageEntries(raw);
	const last = (test) => {
		for (let i = entries.length - 1; i >= 0; i--) if (test(entries[i])) return entries[i];
		return null;
	};
	const pick = last((e) => e.raised) ?? last((e) => !e.alert) ?? last(() => true);
	return pick?.text || null;
}

/**
 * Parse a Frappe error (the rejected value from adapter calls) into:
 *   summary     – one-line human message suitable for a toast
 *   fieldErrors – { backendFieldName: "Field is required" } for field highlights
 *
 * Returns { summary: null, fieldErrors: {} } when nothing can be extracted.
 */
export function parseFrappeError(err) {
	if (!err) return { summary: null, fieldErrors: {} };

	const excType = err.exc_type ?? "";
	const exc = typeof err.exc === "string" ? err.exc : "";
	// frappe-ui pre-parses _server_messages into err.messages (string[]).
	// Check that first; fall back to the raw _server_messages path for
	// non-frappe-ui callers that still carry the double-encoded JSON string.
	const messages =
		Array.isArray(err.messages) && err.messages.length
			? err.messages.map(stripHtml).filter(Boolean)
			: parseServerMessages(err._server_messages);

	const fieldErrors = {};

	if (excType === "MandatoryError" || exc.includes("MandatoryError")) {
		// Extract field names from the traceback tail:
		//   MandatoryError: [DocType, Name]: field1\nfield2
		const tbMatch = exc.match(/MandatoryError:\s*\[.*?\]:\s*([\s\S]+)$/);
		if (tbMatch) {
			tbMatch[1]
				.trim()
				.split(/[\n,]+/)
				.map((f) => f.trim())
				.filter(Boolean)
				.forEach((f) => {
					fieldErrors[f] = `${fieldLabel(f)} is required`;
				});
		}

		// Also scan _server_messages for the same [DocType, Name]: field pattern
		for (const msg of messages) {
			const msgMatch = msg.match(/^\[.*?\]:\s*([\s\S]+)$/);
			if (msgMatch) {
				msgMatch[1]
					.trim()
					.split(/[\n,]+/)
					.map((f) => f.trim())
					.filter(Boolean)
					.forEach((f) => {
						fieldErrors[f] ??= `${fieldLabel(f)} is required`;
					});
			}
		}

		const labels = [
			...new Set(Object.values(fieldErrors).map((e) => e.replace(" is required", ""))),
		];
		return {
			summary: labels.length
				? `Required: ${labels.join(", ")}`
				: "Some required fields are missing",
			fieldErrors,
		};
	}

	// Any other error: the message that failed the request. With the raw _server_messages we can
	// pick the one raised as the exception. frappe-ui's err.messages are plain text in the order
	// the server logged them, and the thrown error is logged last, after any passing alert (e.g.
	// ERPNext's "Item Price added for …"), so take the last, not the first.
	return {
		summary:
			serverErrorMessage(err._server_messages) ??
			messages[messages.length - 1] ??
			stripHtml(err.message) ??
			"An unexpected error occurred",
		fieldErrors: {},
	};
}

/**
 * True when a Frappe error is a permission denial (HTTP 403 / PermissionError) — so a
 * detail view can show the branded "no access" screen instead of a "not found" state.
 */
export function isPermissionDenied(err) {
	if (!err) return false;
	const excType = String(err.exc_type ?? err.exception ?? "");
	if (excType.includes("PermissionError")) return true;
	const status = err.httpStatus ?? err.statusCode ?? err.status;
	if (status === 403) return true;
	const haystack = [
		err.message,
		err.exception,
		...(Array.isArray(err.messages) ? err.messages : []),
	]
		.filter(Boolean)
		.join(" ");
	return /not permitted|no permission|insufficient permission|permissionerror/i.test(haystack);
}
