<script setup>
import { computed, ref } from "vue";
import { useFinanceMock } from "@/data/financeMock";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const fin = useFinanceMock();
const search = ref("");
const dir = ref("");
const rows = computed(() => {
	const q = search.value.trim().toLowerCase();
	return fin.allPayments.filter(
		(p) => (!dir.value || p.dir === dir.value) && (!q || (p.type || "").toLowerCase().includes(q) || (p.party || "").toLowerCase().includes(q) || (p.ref || "").toLowerCase().includes(q)),
	);
});
const totalIn = computed(() => fin.allPayments.filter((p) => p.dir === "in").reduce((a, p) => a + p.amount, 0));
const totalOut = computed(() => fin.allPayments.filter((p) => p.dir === "out").reduce((a, p) => a + p.amount, 0));
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Payments" }];
</script>

<template>
	<DeskPage title="Payments" :breadcrumbs="breadcrumbs">
		<div class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
			<div class="bg-white border border-ink-200 rounded-lg px-3 py-2"><div class="text-[10px] uppercase tracking-wider text-ink-500">Money in</div><div class="text-base font-semibold text-success-700 tabular-nums">{{ fmtINR(totalIn) }}</div></div>
			<div class="bg-white border border-ink-200 rounded-lg px-3 py-2"><div class="text-[10px] uppercase tracking-wider text-ink-500">Money out</div><div class="text-base font-semibold text-danger-700 tabular-nums">{{ fmtINR(totalOut) }}</div></div>
			<div class="bg-white border border-ink-200 rounded-lg px-3 py-2"><div class="text-[10px] uppercase tracking-wider text-ink-500">Net</div><div class="text-base font-semibold text-ink-900 tabular-nums">{{ fmtINR(totalIn - totalOut) }}</div></div>
		</div>
		<div class="flex items-center gap-2 mb-2">
			<input v-model="search" placeholder="Search type / party / ref…" class="desk-input max-w-xs" />
			<DeskSelect v-model="dir" class="!w-40"><option value="">Direction: Any</option><option value="in">Money in</option><option value="out">Money out</option></DeskSelect>
		</div>
		<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<table class="w-full text-xs" style="min-width: 640px">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr><th class="text-left px-3 py-2">Date</th><th class="text-left px-3 py-2">Type</th><th class="text-left px-3 py-2">Party</th><th class="text-left px-3 py-2">Account</th><th class="text-right px-3 py-2">Amount</th></tr>
				</thead>
				<tbody>
					<tr v-for="p in rows" :key="p.id" class="border-t border-ink-100">
						<td class="px-3 py-2 text-ink-500">{{ fmtDate(p.date) }}</td>
						<td class="px-3 py-2 text-ink-900">{{ p.type }}</td>
						<td class="px-3 py-2 text-ink-700">{{ p.party || "—" }}</td>
						<td class="px-3 py-2 text-ink-500">{{ fin.accountById(p.account)?.name || p.account }}</td>
						<td class="px-3 py-2 text-right tabular-nums font-medium" :class="p.dir === 'in' ? 'text-success-700' : 'text-danger-700'">{{ p.dir === "in" ? "+" : "−" }}{{ fmtINR(p.amount) }}</td>
					</tr>
					<tr v-if="!rows.length"><td colspan="5" class="px-3 py-4 text-center text-ink-400 italic">No movements.</td></tr>
				</tbody>
			</table>
		</div>
	</DeskPage>
</template>
