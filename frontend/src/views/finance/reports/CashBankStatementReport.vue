<script setup>
import { computed, ref } from "vue";
import { useFinanceMock } from "@/data/financeMock";
import DeskPage from "@/components/desk/DeskPage.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const fin = useFinanceMock();
const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Cash & Bank" }];
const cashBankAccounts = computed(() => fin.financeAccounts.filter((a) => a.type !== "Petty Cash"));
const selected = ref(cashBankAccounts.value[0]?.id || "");

const movements = computed(() =>
	fin.allPayments
		.filter((p) => p.account === selected.value)
		.slice()
		.reverse(),
);
const opening = computed(() => fin.accountById(selected.value)?.opening_balance || 0);
const rowsWithRunning = computed(() => {
	let run = opening.value;
	return movements.value.map((p) => {
		run += p.dir === "in" ? p.amount : -p.amount;
		return { ...p, running: run };
	});
});
const closing = computed(() => fin.accountBalance(selected.value));
</script>

<template>
	<DeskPage title="Cash & Bank Statement" :breadcrumbs="breadcrumbs">
		<div class="flex items-center gap-2 mb-3">
			<select v-model="selected" class="desk-input !w-64">
				<option v-for="a in cashBankAccounts" :key="a.id" :value="a.id">{{ a.name }}</option>
			</select>
		</div>
		<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto max-w-3xl">
			<table class="w-full text-xs">
				<thead class="bg-ink-50 text-ink-500 uppercase text-[10px]"><tr><th class="text-left px-3 py-2">Date</th><th class="text-left px-3 py-2">Type</th><th class="text-right px-3 py-2">In</th><th class="text-right px-3 py-2">Out</th><th class="text-right px-3 py-2">Balance</th></tr></thead>
				<tbody>
					<tr class="border-t border-ink-100 bg-ink-50/50"><td class="px-3 py-2 text-ink-500" colspan="4">Opening balance</td><td class="px-3 py-2 text-right tabular-nums font-medium">{{ fmtINR(opening) }}</td></tr>
					<tr v-for="p in rowsWithRunning" :key="p.id" class="border-t border-ink-100">
						<td class="px-3 py-2 text-ink-500">{{ fmtDate(p.date) }}</td>
						<td class="px-3 py-2 text-ink-700">{{ p.type }}</td>
						<td class="px-3 py-2 text-right tabular-nums text-success-700">{{ p.dir === "in" ? fmtINR(p.amount) : "" }}</td>
						<td class="px-3 py-2 text-right tabular-nums text-danger-700">{{ p.dir === "out" ? fmtINR(p.amount) : "" }}</td>
						<td class="px-3 py-2 text-right tabular-nums">{{ fmtINR(p.running) }}</td>
					</tr>
					<tr class="border-t-2 border-ink-200 font-semibold"><td class="px-3 py-2" colspan="4">Closing balance</td><td class="px-3 py-2 text-right tabular-nums">{{ fmtINR(closing) }}</td></tr>
				</tbody>
			</table>
		</div>
	</DeskPage>
</template>
