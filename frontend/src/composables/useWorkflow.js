import { ref } from "vue";
import { getWorkflowInfo, applyWorkflowAction } from "@/data/workflowApi";

/**
 * Workflow-awareness for a doctype's detail view.
 *
 * When an active Frappe Workflow governs `doctype`, `active` becomes true and
 * `transitions` holds the actions the signed-in user may take from the doc's current
 * state — Frappe filters these by the user's roles (which personas grant, see
 * utils/user.sync_persona_roles) and each transition's condition, so the buttons
 * are already permission-correct. When no workflow is configured, `active` stays
 * false and the caller keeps its existing docstatus (Submit / Cancel) buttons.
 *
 * Refs are returned individually so callers destructure them (`const { active } =
 * useWorkflow(...)`) and get template auto-unwrapping.
 *
 * @param {string} doctype
 */
export function useWorkflow(doctype) {
	const active = ref(false);
	const stateField = ref(null);
	const state = ref(null);
	const transitions = ref([]);
	const loading = ref(false);

	async function refresh(name) {
		loading.value = true;
		try {
			const info = await getWorkflowInfo(doctype, name);
			active.value = !!info.active;
			stateField.value = info.state_field;
			state.value = info.state;
			transitions.value = info.transitions || [];
		} finally {
			loading.value = false;
		}
	}

	// Apply an action, then hand the fresh snapshot back to the caller (which usually
	// reloads the whole doc anyway).
	async function applyAction(name, action) {
		return await applyWorkflowAction(doctype, name, action);
	}

	return { active, stateField, state, transitions, loading, refresh, applyAction };
}
