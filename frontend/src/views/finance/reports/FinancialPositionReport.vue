<script setup>
// Financial Position — two columns (what we have / what we owe) + an emphasised
// net position. Matches the prototype layout (full-width, the whole-company
// subtext, coloured net panel); figures come live from the real ledger via
// getFinancialPosition().
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

const haveRows = computed(() => [
	{ label: "Bank balance", value: fp.value.have.bank },
	{ label: "Cash in hand", value: fp.value.have.cash },
	{ label: "Customers owe us", value: fp.value.have.customersOwe },
	{ label: "Petty cash with holders", value: fp.value.have.pettyCashOut },
	{ label: "Advances paid to suppliers", value: fp.value.have.advancesPaid },
]);
const oweRows = computed(() => [
	{ label: "Suppliers", value: fp.value.owe.suppliers },
	{ label: "Subcontractors", value: fp.value.owe.subcontractors },
	{ label: "Retention held", value: fp.value.owe.retention },
	{ label: "Advances received from customers", value: fp.value.owe.advancesReceived },
	{ label: "To reimburse (own-pocket)", value: fp.value.owe.toReimburse },
]);
const totalHave = computed(() => haveRows.value.reduce((s, r) => s + (Number(r.value) || 0), 0));
const totalOwe = computed(() => oweRows.value.reduce((s, r) => s + (Number(r.value) || 0), 0));
const net = computed(() => totalHave.value - totalOwe.value);
</script>

<template>
	<DeskPage title="Financial Position" :breadcrumbs="breadcrumbs" printable>
		<div v-if="loading" class="text-sm text-ink-500 italic py-10 text-center">Loading…</div>
		<div v-else-if="error" class="text-sm text-danger-600 py-10 text-center">{{ error }}</div>
		<div v-else class="space-y-4">
			<!-- Financial Position is a live whole-company snapshot with no project or
			     date dimension, so it deliberately carries no filter row. -->
			<p class="text-[11px] text-ink-500 mb-3 print:hidden">
				Whole company, as it stands right now — this one has no period or project filter.
			</p>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
				<!-- Have -->
				<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<div class="px-4 py-2.5 bg-success-50 border-b border-success-100">
						<h3 class="text-xs uppercase tracking-wider font-semibold text-success-700">
							What we have
						</h3>
					</div>
					<div class="divide-y divide-ink-100">
						<div
							v-for="r in haveRows"
							:key="r.label"
							class="px-4 py-2.5 flex items-center justify-between text-sm"
						>
							<span class="text-ink-600">{{ r.label }}</span>
							<span class="tabular-nums text-ink-900">{{ fmtINR(r.value) }}</span>
						</div>
					</div>
					<div
						class="px-4 py-2.5 bg-ink-50 border-t border-ink-200 flex items-center justify-between text-sm font-semibold"
					>
						<span class="text-ink-700">Total assets</span>
						<span class="tabular-nums text-ink-900">{{ fmtINR(totalHave) }}</span>
					</div>
				</section>

				<!-- Owe -->
				<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<div class="px-4 py-2.5 bg-danger-50 border-b border-danger-100">
						<h3 class="text-xs uppercase tracking-wider font-semibold text-danger-700">
							What we owe
						</h3>
					</div>
					<div class="divide-y divide-ink-100">
						<div
							v-for="r in oweRows"
							:key="r.label"
							class="px-4 py-2.5 flex items-center justify-between text-sm"
						>
							<span class="text-ink-600">{{ r.label }}</span>
							<span class="tabular-nums text-ink-900">{{ fmtINR(r.value) }}</span>
						</div>
					</div>
					<div
						class="px-4 py-2.5 bg-ink-50 border-t border-ink-200 flex items-center justify-between text-sm font-semibold"
					>
						<span class="text-ink-700">Total liabilities</span>
						<span class="tabular-nums text-ink-900">{{ fmtINR(totalOwe) }}</span>
					</div>
				</section>
			</div>

			<!-- Net -->
			<section
				class="rounded-lg px-5 py-4 flex items-center justify-between"
				:class="
					net >= 0
						? 'bg-brand-50 border border-brand-200'
						: 'bg-danger-50 border border-danger-200'
				"
			>
				<div>
					<div
						class="text-[11px] uppercase tracking-wider font-medium"
						:class="net >= 0 ? 'text-brand-700' : 'text-danger-700'"
					>
						Net position
					</div>
					<div class="text-[11px] text-ink-500">Assets − liabilities</div>
				</div>
				<div class="text-2xl font-semibold tabular-nums text-ink-900">{{ fmtINR(net) }}</div>
			</section>

			<p class="text-[11px] text-ink-400 print:hidden">
				Supplier/customer advances and own-pocket reimbursements aren't broken out yet —
				shown as ₹0 until modelled.
			</p>
		</div>
	</DeskPage>
</template>
