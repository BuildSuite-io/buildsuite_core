<script setup>
import { computed } from "vue";
import { useFinanceMock } from "@/data/financeMock";
import DeskPage from "@/components/desk/DeskPage.vue";
import { fmtINR } from "@/utils/format";

const fin = useFinanceMock();
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Financial Position" }];

const bank = computed(() => fin.financeAccounts.filter((a) => a.type === "Bank").reduce((s, a) => s + fin.accountBalance(a.id), 0));
const cash = computed(() => fin.financeAccounts.filter((a) => a.type === "Cash").reduce((s, a) => s + fin.accountBalance(a.id), 0));
const advPaid = computed(() => fin.supplierAdvances.reduce((s, a) => s + (a.amount - a.allocated), 0));
const advRecd = computed(() => fin.customerAdvances.reduce((s, a) => s + (a.amount - a.allocated), 0));
const payableReg = computed(() => fin.bills.reduce((s, b) => s + fin.billOutstanding(b), 0));
const payableSub = computed(() => fin.subcontractorBills.reduce((s, b) => s + fin.scBillOutstanding(b), 0));

const have = computed(() => [
	{ label: "Bank balance", value: bank.value },
	{ label: "Cash in hand", value: cash.value },
	{ label: "Customers owe us", value: fin.totalReceivable },
	{ label: "Advances paid to suppliers", value: advPaid.value },
]);
const owe = computed(() => [
	{ label: "Suppliers", value: payableReg.value },
	{ label: "Subcontractors", value: payableSub.value },
	{ label: "Retention held", value: fin.retentionHeld },
	{ label: "Advances received from customers", value: advRecd.value },
]);
const haveTotal = computed(() => have.value.reduce((s, r) => s + r.value, 0));
const oweTotal = computed(() => owe.value.reduce((s, r) => s + r.value, 0));
</script>

<template>
	<DeskPage title="Financial Position" :breadcrumbs="breadcrumbs">
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-3xl">
			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-success-50 px-4 py-2 border-b border-ink-200"><h3 class="text-xs uppercase tracking-wider font-semibold text-success-800">What we have</h3></div>
				<table class="w-full text-sm">
					<tbody>
						<tr v-for="r in have" :key="r.label" class="border-t border-ink-100"><td class="px-4 py-2 text-ink-700">{{ r.label }}</td><td class="px-4 py-2 text-right tabular-nums">{{ fmtINR(r.value) }}</td></tr>
						<tr class="border-t-2 border-ink-200 font-semibold"><td class="px-4 py-2">Total assets</td><td class="px-4 py-2 text-right tabular-nums">{{ fmtINR(haveTotal) }}</td></tr>
					</tbody>
				</table>
			</section>
			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-danger-50 px-4 py-2 border-b border-ink-200"><h3 class="text-xs uppercase tracking-wider font-semibold text-danger-800">What we owe</h3></div>
				<table class="w-full text-sm">
					<tbody>
						<tr v-for="r in owe" :key="r.label" class="border-t border-ink-100"><td class="px-4 py-2 text-ink-700">{{ r.label }}</td><td class="px-4 py-2 text-right tabular-nums">{{ fmtINR(r.value) }}</td></tr>
						<tr class="border-t-2 border-ink-200 font-semibold"><td class="px-4 py-2">Total liabilities</td><td class="px-4 py-2 text-right tabular-nums">{{ fmtINR(oweTotal) }}</td></tr>
					</tbody>
				</table>
			</section>
		</div>
		<div class="mt-4 bg-white border border-ink-200 rounded-lg px-4 py-3 max-w-3xl flex items-center justify-between">
			<span class="text-sm font-semibold text-ink-900">Net position</span>
			<span class="text-lg font-bold tabular-nums text-brand-700">{{ fmtINR(haveTotal - oweTotal) }}</span>
		</div>
	</DeskPage>
</template>
