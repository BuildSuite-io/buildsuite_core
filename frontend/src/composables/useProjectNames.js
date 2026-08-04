// Shared directory of Project name (id) → project_name. Lists and detail views
// that only carry a project *link* (e.g. a Work Order's `project` = PROJ-0012)
// use this to render the human project title instead of the raw id.
//
// One cached resource is shared across every caller (frappe-ui dedupes by the
// cache key + the module-level singleton), so many lists resolving project names
// trigger a single Project list fetch.

import { computed } from "vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";

let _resource = null;

function rows(resource) {
	const raw = resource?.data;
	if (Array.isArray(raw)) return raw;
	if (Array.isArray(raw?.value)) return raw.value;
	return [];
}

export function useProjectNames() {
	if (!_resource) {
		const adapter = createDataAdapter(useDataStore());
		_resource = adapter.list("Project", {
			fields: ["name", "project_name"],
			pageLength: 0, // every project — the map must resolve any project link
			cache: "buildsuite-project-directory",
		});
	}

	const projectNamesMap = computed(() => {
		const map = {};
		rows(_resource).forEach((p) => {
			map[p.name] = p.project_name || p.name;
		});
		return map;
	});

	// The project_name when known, else the id itself as a sensible placeholder
	// until the directory resolves.
	function projectName(id) {
		if (!id) return "";
		return projectNamesMap.value[id] || id;
	}

	return { projectName, projectNamesMap };
}
