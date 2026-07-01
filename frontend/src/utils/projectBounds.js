// One-shot fetch of a Project's expected start/end dates, for client-side
// hierarchy date-boundary checks (see utils/dateBounds.js). Returns
// { start, end } with nulls when the project or a boundary is unset.

export async function fetchProjectBounds(project) {
	if (!project) return { start: null, end: null };
	const params = new URLSearchParams({
		doctype: "Project",
		filters: JSON.stringify({ name: project }),
		fieldname: JSON.stringify(["expected_start_date", "expected_end_date"]),
	});
	try {
		const res = await fetch(`/api/method/frappe.client.get_value?${params.toString()}`, {
			credentials: "include",
			headers: { Accept: "application/json" },
		});
		const payload = await res.json().catch(() => ({}));
		const m = payload?.message || {};
		return { start: m.expected_start_date || null, end: m.expected_end_date || null };
	} catch {
		// Network/permission failure → impose no client bound; the server still validates.
		return { start: null, end: null };
	}
}
