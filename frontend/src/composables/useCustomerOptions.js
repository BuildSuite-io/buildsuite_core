// Customers as DeskSearchableSelect options, with the customer type as the sub-line.

import { computed } from "vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";

function rows(resource) {
	const raw = resource?.data;
	if (Array.isArray(raw)) return raw;
	if (Array.isArray(raw?.value)) return raw.value;
	return [];
}

export function useCustomerOptions() {
	const adapter = createDataAdapter(useDataStore());
	const _resource = adapter.list("Customer", {
		fields: ["name", "customer_name", "customer_type"],
		filters: [["disabled", "=", 0]],
		orderBy: "customer_name asc",
		pageLength: 0, // every customer — the picker searches client-side
		cache: "buildsuite-customer-options",
	});

	const customerOptions = computed(() =>
		rows(_resource).map((c) => ({
			value: c.name,
			label: c.customer_name || c.name,
			hint: c.customer_type || "",
		}))
	);

	// The customer's display name when all you hold is the id.
	function customerName(id) {
		if (!id) return "";
		return customerOptions.value.find((o) => o.value === id)?.label || id;
	}

	return { customerOptions, customerName };
}
