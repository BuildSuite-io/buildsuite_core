// Actual expense booked on a project, read from the posted ledger
// (buildsuite_core.api.finance_report.project_actual_expense). Resolves to a number, or null
// when it can't be read so callers fall back to their own figure.
export async function getProjectActualExpense(project) {
	if (!project) return null;
	try {
		const res = await fetch(
			"/api/method/buildsuite_core.api.finance_report.project_actual_expense?" +
				new URLSearchParams({ project }),
			{
				credentials: "include",
				headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
			}
		);
		if (!res.ok) return null;
		const data = await res.json();
		const v = data?.message?.actual;
		return typeof v === "number" ? v : null;
	} catch {
		return null;
	}
}
