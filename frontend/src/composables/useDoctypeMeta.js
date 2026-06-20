import { ref } from "vue";
import { frappeRequest } from "frappe-ui-frappe-request";

/**
 * Fetches a DocType's merged meta (standard + custom fields) from the standard
 * Frappe endpoint `frappe.desk.form.load.getdoctype`.
 *
 * Uses frappeRequest — the app's configured frappe-ui fetcher (see main.js,
 * `setConfig('resourceFetcher', frappeRequest)`) — so CSRF, credentials and
 * error normalisation are handled the same way as every other backend call.
 *
 * `selectOptions(fieldname)` returns a Select field's options as a string[],
 * straight from the field definition — so adding an option on the backend
 * surfaces in the UI automatically, no frontend change needed.
 *
 * @param {string} doctype  e.g. 'User'
 * @returns {{ meta, loading, error, reload, selectOptions }}
 */
const _cache = new Map(); // session cache: doctype -> meta doc

export function useDoctypeMeta(doctype) {
	const meta = ref(null);
	const loading = ref(false);
	const error = ref(null);

	async function load() {
		const mode = import.meta.env.VITE_DATA_MODE || "remote";
		if (mode === "local") {
			meta.value = { fields: [] }; // no backend in local mode
			return;
		}
		if (_cache.has(doctype)) {
			meta.value = _cache.get(doctype);
			return;
		}

		loading.value = true;
		error.value = null;
		try {
			// getdoctype returns { docs: [meta, ...] }; frappeRequest passes the
			// payload through untouched when it carries `docs`. (frappeRequest
			// defaults to POST.)
			const data = await frappeRequest({
				url: "frappe.desk.form.load.getdoctype",
				params: { doctype },
			});
			meta.value = data?.docs?.[0] || null;
			if (meta.value) _cache.set(doctype, meta.value);
		} catch (err) {
			error.value = err;
			meta.value = null;
			console.warn("[buildsuite] Failed to fetch doctype meta", err);
		} finally {
			loading.value = false;
		}
	}

	/** A Select field's options as a string[] (Frappe stores them newline-separated). */
	function selectOptions(fieldname) {
		const field = (meta.value?.fields || []).find((f) => f.fieldname === fieldname);
		if (!field || !field.options) return [];
		return field.options
			.split("\n")
			.map((o) => o.trim())
			.filter(Boolean);
	}

	load();

	return { meta, loading, error, reload: load, selectOptions };
}
