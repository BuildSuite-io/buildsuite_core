import { computed } from "vue";
import { useDocTypeList } from "@/composables/useDocTypeList";

// Core scheduling types the engine keys behaviour off; always offered even before
// the master list loads (and protected from deletion on the backend).
const CORE_TASK_TYPES = ["Activity", "Milestone", "Inspection"];

/**
 * Task Type master names for the scheduling-type picker. Surfaces admin-added
 * types (the native `type` Link points at this master) and always includes the
 * core three. Works in both remote and local data modes.
 */
export function useTaskTypes() {
	const resource = useDocTypeList("Task Type", {
		fields: ["name"],
		orderBy: "name asc",
		pageLength: 100,
		cache: "buildsuite-task-types",
	});

	const taskTypes = computed(() => {
		const data = resource.data;
		const rows = Array.isArray(data) ? data : Array.isArray(data?.value) ? data.value : [];
		const names = rows.map((r) => r?.name).filter(Boolean);
		// Union: core types first (stable order), then any admin-added extras.
		const extras = names.filter((n) => !CORE_TASK_TYPES.includes(n));
		const present = names.length
			? [...CORE_TASK_TYPES.filter((n) => names.includes(n)), ...extras]
			: [];
		return present.length ? present : CORE_TASK_TYPES;
	});

	return { taskTypes, taskTypesResource: resource };
}
