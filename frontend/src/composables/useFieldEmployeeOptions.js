// Field employees (Employee rows with `is_labour`) as DeskSearchableSelect
// options. Hint is "HR-EMP-00006 · Mason" to separate same-named workers.

import { computed } from "vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";

function rows(resource) {
	const raw = resource?.data;
	if (Array.isArray(raw)) return raw;
	if (Array.isArray(raw?.value)) return raw.value;
	return [];
}

export function useFieldEmployeeOptions() {
	const adapter = createDataAdapter(useDataStore());
	const _resource = adapter.list("Employee", {
		fields: ["name", "employee_name", "custom_trade", "custom_wage"],
		filters: [["is_labour", "=", 1]],
		orderBy: "employee_name asc",
		pageLength: 0, // every worker — the picker searches client-side
		cache: "buildsuite-field-employee-options",
	});

	const workerOptions = computed(() =>
		rows(_resource).map((w) => ({
			value: w.name,
			label: w.employee_name || w.name,
			hint: [w.name, w.custom_trade].filter(Boolean).join(" · "),
		}))
	);

	// The worker's display name when all you hold is the id.
	function workerName(id) {
		if (!id) return "";
		return workerOptions.value.find((o) => o.value === id)?.label || id;
	}

	// The worker's trade and daily wage, for filling a crew member row the moment
	// the worker is picked. The server's `fetch_from` still owns both on save —
	// this only spares the user an empty row until then.
	function workerDefaults(id) {
		const row = rows(_resource).find((w) => w.name === id);
		return { trade: row?.custom_trade || "", wage: row?.custom_wage ?? null };
	}

	return { workerOptions, workerName, workerDefaults };
}
