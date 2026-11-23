// Whether the user may open a bespoke report route. Those routes are gated by a backend Report
// record (report_access), which an admin can re-role; the access context lists the routes this
// user may open. A button that leads to such a report checks this, not a doctype's read
// permission, so it never leads to a denied page.
import { useSessionStore } from "@/stores/session";

export function useReportAccess() {
	const session = useSessionStore();
	const canOpenReport = (route) => (session.access?.reportRoutes || []).includes(route);
	return { canOpenReport };
}
