<script setup>
// Cash & Bank statement (PF). Per account: opening balance, every in/out movement from the
// GL (with the voucher behind it), a running balance, and closing. A period can be set; the
// opening carries everything posted before it, so the running balance stays correct even when
// rows are clipped. Petty Cash is excluded — it has its own imprest report.
import { computed, onMounted, ref, watch } from "vue";

import DeskInput from "@/components/desk/DeskInput.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import { getCashBankAccounts, getCashBankStatement } from "@/data/financeReportApi";
import { fmtDate, fmtINR } from "@/utils/format";

const breadcrumbs = [
	{ label: "Project Finance", to: "/project-finance" },
	{ label: "Cash & Bank" },
];

const accounts = ref([]);
const accountId = ref("");
const from = ref("");
const to = ref("");

const statement = ref(null);
const loading = ref(true);
const error = ref("");

const anyFilter = computed(() => !!from.value || !!to.value);
function clearFilters() {
	from.value = "";
	to.value = "";
}

async function load() {
	if (!accountId.value) return;
	loading.value = true;
	error.value = "";
	try {
		statement.value = await getCashBankStatement(accountId.value, from.value, to.value);
	} catch (e) {
		error.value = e.message || "Failed to load the statement.";
	} finally {
		loading.value = false;
	}
}

onMounted(async () => {
	try {
		accounts.value = (await getCashBankAccounts()) || [];
		accountId.value = accounts.value[0]?.name || "";
	} catch (e) {
		error.value = e.message || "Failed to load accounts.";
	}
	if (accountId.value) await load();
	else loading.value = false;
});

watch([accountId, from, to], load);

const rows = computed(() => statement.value?.movements || []);
const opening = computed(() => statement.value?.opening || 0);
const totalIn = computed(() => statement.value?.totalIn || 0);
const totalOut = computed(() => statement.value?.totalOut || 0);
const closing = computed(() => statement.value?.closing || 0);
</script>

<template>
	<DeskPage title="Cash & Bank Statement" :breadcrumbs="breadcrumbs">
		<div v-if="error" class="text-sm text-danger-600 py-10 text-center">{{ error }}</div>
		<div v-else class="space-y-4">
			<ReportFilters
				:active="anyFilter"
				:shown="rows.length"
				noun="movements"
				@clear="clearFilters"
			>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Account</span
					>
					<DeskSelect v-model="accountId" class="!w-64">
						<option v-for="a in accounts" :key="a.name" :value="a.name">
							{{ a.account_name }} ({{ a.account_type }})
						</option>
					</DeskSelect>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Period</span
					>
					<DeskInput v-model="from" type="date" class="!w-36" />
					<span class="text-[11px] text-ink-400">to</span>
					<DeskInput v-model="to" type="date" class="!w-36" />
				</label>
				<span v-if="from" class="text-[11px] text-ink-500"
					>Opening carries everything before this date.</span
				>
			</ReportFilters>

			<div class="flex items-center gap-4 flex-wrap text-xs justify-end">
				<div>
					<span class="text-ink-500">In</span>
					<span class="tabular-nums text-success-700 font-medium">
						{{ fmtINR(totalIn) }}</span
					>
				</div>
				<div>
					<span class="text-ink-500">Out</span>
					<span class="tabular-nums text-danger-700 font-medium">
						{{ fmtINR(totalOut) }}</span
					>
				</div>
				<div>
					<span class="text-ink-500">Closing</span>
					<span class="tabular-nums text-ink-900 font-semibold">
						{{ fmtINR(closing) }}</span
					>
				</div>
			</div>

			<div v-if="loading" class="text-sm text-ink-500 italic py-10 text-center">
				Loading…
			</div>
			<div v-else class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
				<table class="w-full text-xs">
					<thead
						class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200 bg-ink-50"
					>
						<tr>
							<th class="text-left px-4 py-2">Date</th>
							<th class="text-left px-4 py-2">Particulars</th>
							<th class="text-left px-4 py-2">Ref</th>
							<th class="text-right px-4 py-2">In</th>
							<th class="text-right px-4 py-2">Out</th>
							<th class="text-right px-4 py-2">Balance</th>
						</tr>
					</thead>
					<tbody>
						<tr class="border-b border-ink-100 bg-ink-50/40">
							<td class="px-4 py-2 text-ink-500">{{ from ? fmtDate(from) : "" }}</td>
							<td class="px-4 py-2 text-ink-700 font-medium" colspan="4">
								Opening balance
							</td>
							<td class="px-4 py-2 text-right tabular-nums text-ink-900">
								{{ fmtINR(opening) }}
							</td>
						</tr>
						<tr
							v-for="(m, i) in rows"
							:key="i"
							class="border-b border-ink-100 last:border-0"
						>
							<td class="px-4 py-2 text-ink-500">{{ fmtDate(m.date) }}</td>
							<td class="px-4 py-2 text-ink-800">{{ m.label }}</td>
							<td class="px-4 py-2 font-mono text-ink-400 text-[10px]">
								{{ m.ref }}
							</td>
							<td class="px-4 py-2 text-right tabular-nums text-success-700">
								{{ m.in ? fmtINR(m.in) : "" }}
							</td>
							<td class="px-4 py-2 text-right tabular-nums text-danger-700">
								{{ m.out ? fmtINR(m.out) : "" }}
							</td>
							<td class="px-4 py-2 text-right tabular-nums text-ink-900">
								{{ fmtINR(m.balance) }}
							</td>
						</tr>
						<tr v-if="!rows.length">
							<td
								colspan="6"
								class="px-4 py-8 text-center text-xs text-ink-400 italic"
							>
								No movements in this period.
							</td>
						</tr>
						<tr class="border-t-2 border-ink-200 bg-ink-50">
							<td class="px-4 py-2 font-semibold text-ink-700" colspan="3">
								Closing balance
							</td>
							<td
								class="px-4 py-2 text-right tabular-nums text-success-700 font-medium"
							>
								{{ fmtINR(totalIn) }}
							</td>
							<td
								class="px-4 py-2 text-right tabular-nums text-danger-700 font-medium"
							>
								{{ fmtINR(totalOut) }}
							</td>
							<td
								class="px-4 py-2 text-right tabular-nums text-ink-900 font-semibold"
							>
								{{ fmtINR(closing) }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>
	</DeskPage>
</template>
