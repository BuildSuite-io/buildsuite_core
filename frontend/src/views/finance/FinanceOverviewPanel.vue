<script setup>
import { computed } from "vue";
import { useFinanceMock } from "@/data/financeMock";
import DeskPage from "@/components/desk/DeskPage.vue";
import { fmtDate, fmtINR, fmtCompactINR } from "@/utils/format";

const fin = useFinanceMock();
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Overview" }];
const kpis = computed(() => [
	{ label: "Cash & bank", value: fin.totalCashBank, color: "text-ink-900" },
	{ label: "Receivable", value: fin.totalReceivable, color: "text-success-700" },
	{ label: "Payable", value: fin.totalPayable, color: "text-danger-700" },
	{ label: "Retention held", value: fin.retentionHeld, color: "text-warning-700" },
	{ label: "Net position", value: fin.totalCashBank + fin.totalReceivable - fin.totalPayable, color: "text-brand-700" },
]);
const recent = computed(() => fin.allPayments.slice(0, 6));
</script>

<template>
	<DeskPage title="Finance Overview" :breadcrumbs="breadcrumbs">
		<div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
			<div v-for="k in kpis" :key="k.label" class="bg-white border border-ink-200 rounded-lg px-3 py-2.5">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">{{ k.label }}</div>
				<div class="text-base font-semibold tabular-nums mt-0.5" :class="k.color">{{ fmtCompactINR(k.value) }}</div>
			</div>
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-ink-50 px-4 py-2 border-b border-ink-200"><h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">Account balances</h3></div>
				<table class="w-full text-xs">
					<tbody>
						<tr v-for="a in fin.sortedFinanceAccounts" :key="a.id" class="border-t border-ink-100">
							<td class="px-4 py-2 text-ink-900">{{ a.name }} <span class="text-ink-400 text-[10px]">{{ a.type }}</span></td>
							<td class="px-4 py-2 text-right tabular-nums font-medium">{{ fmtINR(fin.accountBalance(a.id)) }}</td>
						</tr>
					</tbody>
				</table>
			</section>

			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-ink-50 px-4 py-2 border-b border-ink-200"><h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">Recent movements</h3></div>
				<table class="w-full text-xs">
					<tbody>
						<tr v-for="p in recent" :key="p.id" class="border-t border-ink-100">
							<td class="px-4 py-2 text-ink-500">{{ fmtDate(p.date) }}</td>
							<td class="px-4 py-2 text-ink-700">{{ p.type }}</td>
							<td class="px-4 py-2 text-right tabular-nums font-medium" :class="p.dir === 'in' ? 'text-success-700' : 'text-danger-700'">{{ p.dir === "in" ? "+" : "−" }}{{ fmtINR(p.amount) }}</td>
						</tr>
						<tr v-if="!recent.length"><td colspan="3" class="px-4 py-3 text-center text-ink-400 italic">No movements yet.</td></tr>
					</tbody>
				</table>
			</section>
		</div>
	</DeskPage>
</template>
