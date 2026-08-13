import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

// Wrapper over buildsuite_core.api.material_consumption — the `items` child
// table can't go through the generic adapter. Delete can, so it isn't here.

async function call(method, args) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.material_consumption.${method}`,
			params: args || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

export const getSiteStock = (project) => call("get_site_stock", { project });

export const listMaterialConsumption = (params) => call("list_material_consumption", params);

export const getMaterialConsumption = (name) => call("get_material_consumption", { name });

export const saveMaterialConsumption = (payload) =>
	call("save_material_consumption", {
		...payload,
		items: JSON.stringify(payload.items || []),
		cost_code: payload.cost_code ? JSON.stringify(payload.cost_code) : null,
	});
