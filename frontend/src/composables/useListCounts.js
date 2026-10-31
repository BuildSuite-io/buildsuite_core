import { computed, ref, watch } from "vue";
import { frappeRequest } from "frappe-ui-frappe-request";
import { activeCompanyFilter } from "@/composables/useActiveCompany";

// Server-side counts for a list's KPI strip — one frappe.client.get_count per key — that follow the
// working company (when the doctype is company-partitioned) the same way the list itself does.
//
//   const { counts, reload } = useListCounts("BOQ", () => ({
//     total: [],
//     draft: [["status", "=", "Draft"]],
//   }));
//   counts.draft  // number | null while loading
export function useListCounts(doctype, defs, { companyScoped = true } = {}) {
	const scope = activeCompanyFilter();
	const counts = ref({});
	let seq = 0;

	const requests = computed(() => {
		const base = companyScoped ? scope.value : [];
		return Object.fromEntries(
			Object.entries(defs()).map(([key, filters]) => [key, [...(filters || []), ...base]])
		);
	});

	async function reload() {
		const mine = ++seq;
		const entries = Object.entries(requests.value);
		const results = await Promise.all(
			entries.map(([, filters]) =>
				frappeRequest({
					url: "frappe.client.get_count",
					params: { doctype, filters },
				}).catch(() => null)
			)
		);
		if (mine !== seq) return;
		counts.value = Object.fromEntries(entries.map(([key], i) => [key, results[i]]));
	}
	watch(() => JSON.stringify(requests.value), reload, { immediate: true });

	return { counts, reload };
}
