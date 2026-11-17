import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Thin wrappers over buildsuite_core.api.persona.* — admin CRUD for the Persona
// master and its role mapping (Settings → Personas).

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.persona.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// Persona.project_visibility — which projects (and their tasks, work packages, progress entries
// and stage plans) the persona's users see. `value` is the stored option (permissions/project.py).
export const PROJECT_VISIBILITY_OPTIONS = [
	{
		value: "Team projects only",
		label: "Team projects only",
		hint: "Only the projects whose team they are on.",
	},
	{
		value: "All projects until added to a team",
		label: "All projects until added to a team",
		hint: "Every project until they join any project team, then only their teams.",
	},
	{
		value: "All projects",
		label: "All projects",
		hint: "Every project their role permissions allow, team or not.",
	},
];
export const DEFAULT_PROJECT_VISIBILITY = "Team projects only";

export const listPersonas = () => call("list_personas");
export const getPersona = (name) => call("get_persona", { name });
export const listAssignableRoles = () => call("list_assignable_roles");
export const deletePersona = (name) => call("delete_persona", { name });
export const savePersona = (args) =>
	call("save_persona", { ...args, roles: JSON.stringify(args.roles || []) });
