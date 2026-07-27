<script setup>
// LIVE petty-cash statement — reconciled per holder from the GL: disbursed float
// in, verified expense out, and the net balance in hand. Both legs (Petty Cash
// Request disburse + Expense Entry spend) roll into one figure.
import { computed, ref } from "vue";
import { pettyCashHolderBalances } from "@/data/pettyCashApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import { fmtINR } from "@/utils/format";

const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Petty Cash Statement" }];
const rows = ref([]);
const loading = ref(true);
pettyCashHolderBalances()
	.then((r) => (rows.value = r))
	.catch(() => {})
	.finally(() => (loading.value = false));

const totals = computed(() =>
	rows.value.reduce(
		(a, b) => ({ disbursed: a.disbursed + (b.disbursed || 0), spent: a.spent + (b.spent || 0), balance: a.balance + (b.balance || 0) }),
		{ disbursed: 0, spent: 0, balance: 0 },
	),
);
</script>

<template>
	<DeskPage title="Petty Cash Statement" :breadcrumbs="breadcrumbs">
		<div class="bg-white border border-ink-200 rounded-lg overflow-hidden max-w-2xl">
			<div class="bg-ink-50 px-4 py-2 border-b border-ink-200"><h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">Balance in hand per holder (live)</h3></div>
			<table class="w-full text-sm">
				<thead class="text-ink-500 uppercase text-[10px]"><tr><th class="text-left px-4 py-2">Holder</th><th class="text-right px-4 py-2">Disbursed</th><th class="text-right px-4 py-2">Verified spend</th><th class="text-right px-4 py-2">Balance</th></tr></thead>
				<tbody>
					<tr v-for="b in rows" :key="b.employee || b.holder" class="border-t border-ink-100">
						<td class="px-4 py-2 text-ink-900">{{ b.holder }}</td>
						<td class="px-4 py-2 text-right tabular-nums text-ink-700">{{ fmtINR(b.disbursed) }}</td>
						<td class="px-4 py-2 text-right tabular-nums text-ink-700">{{ fmtINR(b.spent) }}</td>
						<td class="px-4 py-2 text-right tabular-nums font-semibold" :class="b.balance < 0 ? 'text-danger-700' : 'text-ink-900'">{{ fmtINR(b.balance) }}</td>
					</tr>
					<tr v-if="!rows.length && !loading"><td colspan="4" class="px-4 py-4 text-center text-ink-400 italic">No petty-cash activity yet.</td></tr>
					<tr v-if="loading"><td colspan="4" class="px-4 py-4 text-center text-ink-400">Loading…</td></tr>
					<tr v-if="rows.length" class="border-t-2 border-ink-200 font-semibold">
						<td class="px-4 py-2">Total</td>
						<td class="px-4 py-2 text-right tabular-nums">{{ fmtINR(totals.disbursed) }}</td>
						<td class="px-4 py-2 text-right tabular-nums">{{ fmtINR(totals.spent) }}</td>
						<td class="px-4 py-2 text-right tabular-nums">{{ fmtINR(totals.balance) }}</td>
					</tr>
				</tbody>
			</table>
			<p class="px-4 py-2 text-[11px] text-ink-400 border-t border-ink-100">Balance = disbursed float − approved expenses. Per-holder movement detail is on the Expenses › Ledger tab.</p>
		</div>
	</DeskPage>
</template>
