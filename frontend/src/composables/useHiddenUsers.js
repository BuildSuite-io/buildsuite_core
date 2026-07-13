// User accounts BuildSuite Core's own UI must never surface — its user lists, team
// pickers, assignee dropdowns and mention/autocomplete. That's the built-in system
// accounts (Administrator, Guest) plus platform admins (System Manager holders that
// aren't BuildSuite users). Fetched once from the backend and cached module-wide,
// then fed into the User link pickers + the user directory. Frappe Desk is
// unaffected — this only shapes the SPA's own UI.

import { ref } from "vue";
import { frappeRequest } from "frappe-ui-frappe-request";

const hiddenUsers = ref(["Administrator", "Guest"]);
let _started = false;

function ensureLoaded() {
	if (_started) return;
	_started = true;
	frappeRequest({ url: "buildsuite_core.api.users.get_hidden_user_names" })
		.then((names) => {
			if (Array.isArray(names) && names.length) hiddenUsers.value = names;
		})
		.catch(() => {
			// Keep the built-in accounts hidden even if the endpoint is unreachable.
		});
}

export function useHiddenUsers() {
	ensureLoaded();
	return { hiddenUsers };
}
