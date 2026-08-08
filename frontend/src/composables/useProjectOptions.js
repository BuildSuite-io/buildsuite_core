// Projects as DeskSearchableSelect options.
//
// frappe-ui dedupes by the `cache` key and reloads on re-entry. Do NOT hoist
// into a module-level singleton — that skips the reload and the list goes stale.

import { computed } from "vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";

function rows(resource) {
	const raw = resource?.data;
	if (Array.isArray(raw)) return raw;
	if (Array.isArray(raw?.value)) return raw.value;
	return [];
}

export function useProjectOptions() {
	const adapter = createDataAdapter(useDataStore());
	const _resource = adapter.list("Project", {
		fields: ["name", "project_name", "custom_project_id"],
		orderBy: "project_name asc",
		pageLength: 0, // every project — the picker searches client-side
		cache: "buildsuite-project-options",
	});

	const projectOptions = computed(() =>
		rows(_resource).map((p) => ({
			value: p.name,
			label: p.project_name || p.name,
			hint: p.custom_project_id || p.name,
		}))
	);

	// The project's display title when all you hold is the id.
	function projectLabel(id) {
		if (!id) return "";
		return projectOptions.value.find((o) => o.value === id)?.label || id;
	}

	return { projectOptions, projectLabel };
}
