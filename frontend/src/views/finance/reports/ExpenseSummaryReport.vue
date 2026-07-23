<script setup>
import { computed } from "vue";
import { useFinanceMock } from "@/data/financeMock";
import DeskPage from "@/components/desk/DeskPage.vue";
import { fmtINR } from "@/utils/format";

const fin = useFinanceMock();
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Expense Summary" }];
const byType = computed(() => {
	const m = {};
	fin.verifiedExpenses.forEach((e) => {
		const k = e.cost_type || "Uncategorised";
		m[k] = m[k] || { count: 0, total: 0 };
		m[k].count++;
		m[k].total += e.amount;
	});
	return Object.entries(m).map(([k, v]) => ({ category: k, ...v }));
});
const total = computed(() => byType.value.reduce((a, r) => a + r.total, 0));
</script>

<template>
	<DeskPage title="Expense Summary" :breadcrumbs="breadcrumbs">
		<div class="bg-white border border-ink-200 rounded-lg overflow-hidden max-w-xl">
			<table class="w-full text-sm">
				<thead class="bg-ink-50 text-ink-500 uppercase text-[10px]"><tr><th class="text-left px-4 py-2">Cost type</th><th class="text-right px-4 py-2">Count</th><th class="text-right px-4 py-2">Total</th></tr></thead>
				<tbody>
					<tr v-for="r in byType" :key="r.category" class="border-t border-ink-100"><td class="px-4 py-2 text-ink-900">{{ r.category }}</td><td class="px-4 py-2 text-right tabular-nums text-ink-600">{{ r.count }}</td><td class="px-4 py-2 text-right tabular-nums font-medium">{{ fmtINR(r.total) }}</td></tr>
					<tr v-if="!byType.length"><td colspan="3" class="px-4 py-4 text-center text-ink-400 italic">No verified expenses.</td></tr>
					<tr v-if="byType.length" class="border-t-2 border-ink-200 font-semibold"><td class="px-4 py-2">Total</td><td></td><td class="px-4 py-2 text-right tabular-nums">{{ fmtINR(total) }}</td></tr>
				</tbody>
			</table>
		</div>
	</DeskPage>
</template>
