// Labour contractors — Suppliers of type "Subcontractor", the same narrowing the
// rest of the app applies to Supplier links.

import { computed } from "vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";

function rows(resource) {
	const raw = resource?.data;
	if (Array.isArray(raw)) return raw;
	if (Array.isArray(raw?.value)) return raw.value;
	return [];
}

export function useContractorOptions() {
	const adapter = createDataAdapter(useDataStore());
	const _resource = adapter.list("Supplier", {
		fields: ["name", "supplier_name", "custom_trade"],
		filters: [
			["supplier_type", "=", "Subcontractor"],
			["disabled", "=", 0],
		],
		orderBy: "supplier_name asc",
		pageLength: 0, // every contractor — the picker searches client-side
		cache: "buildsuite-contractor-options",
	});

	const contractorOptions = computed(() =>
		rows(_resource).map((s) => ({
			value: s.name,
			label: s.supplier_name || s.name,
			hint: s.custom_trade || "",
		}))
	);

	// The contractor's display name when all you hold is the id. Returns "" for a
	// blank value — a worker with no contractor is engaged directly.
	function contractorName(id) {
		if (!id) return "";
		return contractorOptions.value.find((o) => o.value === id)?.label || id;
	}

	return { contractorOptions, contractorName };
}
