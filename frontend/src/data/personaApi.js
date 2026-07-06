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

export const listPersonas = () => call("list_personas");
export const getPersona = (name) => call("get_persona", { name });
export const listAssignableRoles = () => call("list_assignable_roles");
export const deletePersona = (name) => call("delete_persona", { name });
export const savePersona = (args) =>
	call("save_persona", { ...args, roles: JSON.stringify(args.roles || []) });
