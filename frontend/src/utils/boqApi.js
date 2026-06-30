// Thin wrappers over the buildsuite_core.api.boq.* whitelisted methods (the BOQ
// operations that aren't a single-document save). POST with the CSRF token; throws
// Error(<server message>) so callers can surface the reason.

const BASE = "/api/method/buildsuite_core.api.boq.";

function serverMessage(payload, status) {
	try {
		const sm = payload?._server_messages;
		if (sm) {
			const first = JSON.parse(JSON.parse(sm)[0]);
			if (first?.message) return first.message;
		}
	} catch (_) {
		/* fall through */
	}
	return payload?.exception || `Request failed (${status})`;
}

async function request(method, body) {
	const res = await fetch(BASE + method, {
		method: "POST",
		credentials: "include",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json",
			"X-Frappe-CSRF-Token": window.csrf_token || "",
		},
		body: JSON.stringify(body || {}),
	});
	const payload = await res.json().catch(() => ({}));
	if (!res.ok) throw new Error(serverMessage(payload, res.status));
	return payload.message;
}

export const submitBoq = (boq) => request("submit_boq", { boq });
export const approveBoq = (boq) => request("approve_boq", { boq });
export const explodeItem = (boqItem) => request("explode_item", { boq_item: boqItem });
export const recalculateActuals = (boq) => request("recalculate_actuals", { boq });
export const createRevision = (boq, sourceSco = null, title = null) =>
	request("create_revision", { boq, source_sco: sourceSco, title });
export const cloneBoq = (payload) => request("clone_boq", payload);
export const importTemplate = (boq, estimateTemplate) =>
	request("import_template", { boq, estimate_template: estimateTemplate });
