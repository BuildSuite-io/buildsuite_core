<script setup>
// The one report backed by LIVE data — per-holder disbursed float from Petty Cash Requests.
import { ref } from "vue";
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
</script>

<template>
	<DeskPage title="Petty Cash Statement" :breadcrumbs="breadcrumbs">
		<div class="bg-white border border-ink-200 rounded-lg overflow-hidden max-w-xl">
			<div class="bg-ink-50 px-4 py-2 border-b border-ink-200"><h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">Float disbursed per holder (live)</h3></div>
			<table class="w-full text-sm">
				<tbody>
					<tr v-for="b in rows" :key="b.holder" class="border-t border-ink-100"><td class="px-4 py-2 text-ink-900">{{ b.holder }}</td><td class="px-4 py-2 text-right tabular-nums font-medium">{{ fmtINR(b.disbursed) }}</td></tr>
					<tr v-if="!rows.length && !loading"><td colspan="2" class="px-4 py-4 text-center text-ink-400 italic">No disbursements yet.</td></tr>
					<tr v-if="loading"><td colspan="2" class="px-4 py-4 text-center text-ink-400">Loading…</td></tr>
				</tbody>
			</table>
			<p class="px-4 py-2 text-[11px] text-ink-400 border-t border-ink-100">Verified spend against these floats is tracked on the (dummy) Expenses tab.</p>
		</div>
	</DeskPage>
</template>
