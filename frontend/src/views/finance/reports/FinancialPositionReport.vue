<script setup>
import { computed, ref, onMounted } from "vue";

import DeskPage from "@/components/desk/DeskPage.vue";
import { getFinancialPosition } from "@/data/financeReportApi";
import { fmtINR } from "@/utils/format";

const breadcrumbs = [
	{ label: "Project Finance", to: "/project-finance" },
	{ label: "Financial Position" },
];

const fp = ref({ have: {}, owe: {}, net: 0 });
const loading = ref(true);
const error = ref("");

onMounted(async () => {
	try {
		fp.value = await getFinancialPosition();
	} catch (e) {
		error.value = e.message || "Failed to load.";
	} finally {
		loading.value = false;
	}
});

const have = computed(() => [
	{ label: "Bank balance", value: fp.value.have.bank },
	{ label: "Cash in hand", value: fp.value.have.cash },
	{ label: "Petty cash with holders", value: fp.value.have.pettyCashOut },
	{ label: "Customers owe us", value: fp.value.have.customersOwe },
	{ label: "Advances paid to suppliers", value: fp.value.have.advancesPaid },
]);
const owe = computed(() => [
	{ label: "Suppliers", value: fp.value.owe.suppliers },
	{ label: "Subcontractors", value: fp.value.owe.subcontractors },
	{ label: "Retention held", value: fp.value.owe.retention },
	{ label: "Advances received from customers", value: fp.value.owe.advancesReceived },
	{ label: "To reimburse (own-pocket)", value: fp.value.owe.toReimburse },
]);
const haveTotal = computed(() => have.value.reduce((s, r) => s + (Number(r.value) || 0), 0));
const oweTotal = computed(() => owe.value.reduce((s, r) => s + (Number(r.value) || 0), 0));
</script>

<template>
	<DeskPage title="Financial Position" :breadcrumbs="breadcrumbs">
		<div v-if="loading" class="text-sm text-ink-500 italic py-10 text-center">Loading…</div>
		<div v-else-if="error" class="text-sm text-danger-600 py-10 text-center">{{ error }}</div>
		<template v-else>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
				<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<div class="bg-success-50 px-4 py-2 border-b border-ink-200">
						<h3
							class="text-xs uppercase tracking-wider font-semibold text-success-800"
						>
							What we have
						</h3>
					</div>
					<table class="w-full text-sm">
						<tbody>
							<tr v-for="r in have" :key="r.label" class="border-t border-ink-100">
								<td class="px-4 py-2 text-ink-700">{{ r.label }}</td>
								<td class="px-4 py-2 text-right tabular-nums">
									{{ fmtINR(r.value) }}
								</td>
							</tr>
							<tr class="border-t-2 border-ink-200 font-semibold">
								<td class="px-4 py-2">Total assets</td>
								<td class="px-4 py-2 text-right tabular-nums">
									{{ fmtINR(haveTotal) }}
								</td>
							</tr>
						</tbody>
					</table>
				</section>
				<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<div class="bg-danger-50 px-4 py-2 border-b border-ink-200">
						<h3 class="text-xs uppercase tracking-wider font-semibold text-danger-800">
							What we owe
						</h3>
					</div>
					<table class="w-full text-sm">
						<tbody>
							<tr v-for="r in owe" :key="r.label" class="border-t border-ink-100">
								<td class="px-4 py-2 text-ink-700">{{ r.label }}</td>
								<td class="px-4 py-2 text-right tabular-nums">
									{{ fmtINR(r.value) }}
								</td>
							</tr>
							<tr class="border-t-2 border-ink-200 font-semibold">
								<td class="px-4 py-2">Total liabilities</td>
								<td class="px-4 py-2 text-right tabular-nums">
									{{ fmtINR(oweTotal) }}
								</td>
							</tr>
						</tbody>
					</table>
				</section>
			</div>
			<div
				class="mt-4 bg-white border border-ink-200 rounded-lg px-4 py-3 max-w-3xl flex items-center justify-between"
			>
				<span class="text-sm font-semibold text-ink-900">Net position</span>
				<span class="text-lg font-bold tabular-nums text-brand-700">{{
					fmtINR(haveTotal - oweTotal)
				}}</span>
			</div>
			<p class="text-[11px] text-ink-400 mt-2 max-w-3xl">
				Supplier/customer advances and own-pocket reimbursements aren't broken out yet —
				shown as ₹0 until modelled.
			</p>
		</template>
	</DeskPage>
</template>
