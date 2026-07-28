<script setup>
// Petty Cash report — a LIVE personal statement per holder. Nothing renders until a
// holder is picked (deep-linkable via ?holder=). One combined ledger over both legs:
// Petty Cash Request disbursements (money in) and petty-cash Expense Entries (money
// out, drafts + submitted). Filters — date · project · expense account · status ·
// entry type — plus CSV export (summary block + ledger, properly quoted).
import { ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { pettyCashHolderBalances, pettyCashStatement } from "@/data/pettyCashApi";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtINR, fmtDate } from "@/utils/format";

const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Petty Cash Statement" }];
const route = useRoute();
const router = useRouter();

// --- holders (with activity) ---
const holders = ref([]);
pettyCashHolderBalances()
	.then((r) => (holders.value = r))
	.catch(() => {});
const holderOptions = computed(() =>
	holders.value.map((h) => ({ value: h.employee, label: h.holder, hint: h.balance < 0 ? `${fmtINR(-h.balance)} owed` : `${fmtINR(h.balance)} in hand` })),
);
const holder = ref(route.query.holder || null);
const selectedHolder = computed(() => holders.value.find((h) => h.employee === holder.value) || null);
function holderName(id) {
	return holders.value.find((h) => h.employee === id)?.holder || id;
}

// --- statement rows for the picked holder ---
const rows = ref([]);
const loading = ref(false);
async function loadStatement() {
	if (!holder.value) {
		rows.value = [];
		return;
	}
	loading.value = true;
	try {
		rows.value = await pettyCashStatement(holder.value);
	} catch (err) {
		rows.value = [];
		showToast(err.message || "Failed to load statement", "error");
	} finally {
		loading.value = false;
	}
}
watch(
	holder,
	(v) => {
		router.replace({ query: v ? { holder: v } : {} }).catch(() => {});
		loadStatement();
	},
	{ immediate: true },
);

// --- filters ---
const from = ref("");
const to = ref("");
const projectFilter = ref(null);
const accountFilter = ref(null);
const statusFilter = ref("");
const entryType = ref(""); // '' all | 'disbursement' | 'expense'

const projectOptions = computed(() => {
	const seen = new Map();
	for (const r of rows.value) if (r.project && !seen.has(r.project)) seen.set(r.project, r.project_name || r.project);
	return [...seen].map(([value, label]) => ({ value, label }));
});
const accountOptions = computed(() => {
	const set = new Set();
	for (const r of rows.value) if (r.account) set.add(r.account);
	return [...set].map((a) => ({ value: a, label: a }));
});
function projectName(id) {
	return id ? rows.value.find((r) => r.project === id)?.project_name || id : "—";
}
function inPeriod(d) {
	return (!from.value || d >= from.value) && (!to.value || d <= to.value);
}

const filteredRows = computed(() => {
	if (!holder.value) return [];
	return rows.value.filter((r) => {
		if (!inPeriod(r.date)) return false;
		if (projectFilter.value && r.project !== projectFilter.value) return false;
		if (r.kind === "Disbursement") {
			// Disbursements carry no expense account or expense status — an expense-only
			// filter (account / status) or the expense-only entry type hides them.
			if (entryType.value === "expense" || accountFilter.value || statusFilter.value) return false;
			return true;
		}
		if (entryType.value === "disbursement") return false;
		if (accountFilter.value && r.account !== accountFilter.value) return false;
		if (statusFilter.value && r.status !== statusFilter.value) return false;
		return true;
	});
});

// --- summary (filtered window; balance in hand is all-time from the reconciled ledger) ---
const totalIn = computed(() => filteredRows.value.reduce((a, r) => a + (r.in || 0), 0));
const verifiedOut = computed(() => filteredRows.value.filter((r) => r.kind === "Expense" && r.status === "Submitted").reduce((a, r) => a + r.out, 0));
const pendingOut = computed(() => filteredRows.value.filter((r) => r.kind === "Expense" && r.status === "Draft").reduce((a, r) => a + r.out, 0));
const balanceInHand = computed(() => (selectedHolder.value ? selectedHolder.value.balance : 0));

const hasFilters = computed(() => from.value || to.value || projectFilter.value || accountFilter.value || statusFilter.value || entryType.value);
function clearFilters() {
	from.value = "";
	to.value = "";
	projectFilter.value = null;
	accountFilter.value = null;
	statusFilter.value = "";
	entryType.value = "";
}

// --- CSV export (summary block + ledger; fields quoted) ---
function csvCell(v) {
	const s = String(v ?? "");
	return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
function exportCsv() {
	if (!holder.value) return;
	const lines = [];
	lines.push(["Petty Cash Statement"].map(csvCell).join(","));
	lines.push(["Holder", holderName(holder.value)].map(csvCell).join(","));
	lines.push(["Period", `${from.value || "Beginning"} to ${to.value || "Today"}`].map(csvCell).join(","));
	if (projectFilter.value) lines.push(["Project", projectName(projectFilter.value)].map(csvCell).join(","));
	if (accountFilter.value) lines.push(["Expense account", accountFilter.value].map(csvCell).join(","));
	if (statusFilter.value) lines.push(["Status", statusFilter.value].map(csvCell).join(","));
	lines.push(["Generated", new Date().toLocaleString("en-IN")].map(csvCell).join(","));
	lines.push("");
	lines.push(["Disbursed (period)", totalIn.value].map(csvCell).join(","));
	lines.push(["Submitted spend (period)", verifiedOut.value].map(csvCell).join(","));
	lines.push(["Pending spend (period)", pendingOut.value].map(csvCell).join(","));
	lines.push(["Balance in hand (all-time)", balanceInHand.value].map(csvCell).join(","));
	lines.push("");
	lines.push(["Date", "Entry", "Description", "Project", "Expense Account", "Status", "Money In", "Money Out", "Ref"].map(csvCell).join(","));
	for (const r of filteredRows.value.slice().reverse()) {
		lines.push([r.date, r.kind, r.description, projectName(r.project), r.account || "", r.status, r.in || "", r.out || "", r.ref].map(csvCell).join(","));
	}
	const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
	const a = document.createElement("a");
	a.href = URL.createObjectURL(blob);
	a.download = `petty-cash-${holderName(holder.value).replace(/\s+/g, "-").toLowerCase()}-${new Date().toISOString().slice(0, 10)}.csv`;
	a.click();
	URL.revokeObjectURL(a.href);
}
</script>

<template>
	<DeskPage title="Petty Cash Statement" :breadcrumbs="breadcrumbs">
		<div class="space-y-4">
			<!-- Holder picker -->
			<div class="flex items-end gap-3 flex-wrap">
				<div class="w-72">
					<label class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1">Petty cash holder <span class="text-danger-600">*</span></label>
					<DeskSearchableSelect v-model="holder" :options="holderOptions" placeholder="— Pick a holder —" search-placeholder="Search holders…" />
				</div>
				<button v-if="holder" type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md mb-0.5" @click="exportCsv">⇩ Export CSV</button>
			</div>

			<div v-if="!holder" class="bg-white border border-ink-200 rounded-lg px-4 py-16 text-center text-sm text-ink-500">
				Pick a petty cash holder to see their personal statement — disbursements received, spend logged, and balance in hand.
			</div>

			<template v-else>
				<!-- Summary strip -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
					<div class="bg-white border border-ink-200 px-3 py-2 rounded-md">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Disbursed (period)</div>
						<div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">{{ fmtINR(totalIn) }}</div>
					</div>
					<div class="bg-white border border-ink-200 px-3 py-2 rounded-md">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Submitted spend (period)</div>
						<div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">{{ fmtINR(verifiedOut) }}</div>
					</div>
					<div class="bg-white border border-ink-200 px-3 py-2 rounded-md">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Pending spend (period)</div>
						<div class="text-base font-semibold tabular-nums mt-0.5" :class="pendingOut > 0 ? 'text-warning-700' : 'text-ink-900'">{{ fmtINR(pendingOut) }}</div>
					</div>
					<div class="border px-3 py-2 rounded-md" :class="balanceInHand < 0 ? 'bg-danger-50 border-danger-200' : 'bg-brand-50 border-brand-200'">
						<div class="text-[10px] uppercase tracking-wider font-medium" :class="balanceInHand < 0 ? 'text-danger-700' : 'text-brand-700'">Balance in hand (all-time)</div>
						<div class="text-base font-semibold tabular-nums mt-0.5" :class="balanceInHand < 0 ? 'text-danger-700' : 'text-ink-900'">
							<template v-if="balanceInHand < 0">{{ fmtINR(-balanceInHand) }} owed</template>
							<template v-else>{{ fmtINR(balanceInHand) }}</template>
						</div>
					</div>
				</div>

				<!-- Filters -->
				<div class="flex items-center gap-2 flex-wrap">
					<div class="flex items-center gap-1.5">
						<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">From</span>
						<input v-model="from" type="date" class="text-xs px-2 py-1 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200" />
						<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">To</span>
						<input v-model="to" type="date" class="text-xs px-2 py-1 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200" />
					</div>
					<div class="w-48"><DeskSearchableSelect v-model="projectFilter" :options="projectOptions" placeholder="All projects" search-placeholder="Search projects…" allow-clear /></div>
					<div class="w-52"><DeskSearchableSelect v-model="accountFilter" :options="accountOptions" placeholder="All expense accounts" search-placeholder="Search accounts…" allow-clear /></div>
					<select v-model="statusFilter" class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200">
						<option value="">All statuses</option>
						<option value="Draft">Draft</option>
						<option value="Submitted">Submitted</option>
					</select>
					<select v-model="entryType" class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200">
						<option value="">All entries</option>
						<option value="disbursement">Disbursements only</option>
						<option value="expense">Expenses only</option>
					</select>
					<button v-if="hasFilters" type="button" class="text-[11px] text-danger-600 hover:underline" @click="clearFilters">Clear filters</button>
					<span class="text-[11px] text-ink-400 ml-auto">{{ filteredRows.length }} entr{{ filteredRows.length === 1 ? "y" : "ies" }}</span>
				</div>

				<!-- Ledger -->
				<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<table v-if="filteredRows.length" class="w-full text-xs">
						<thead class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200 bg-ink-50">
							<tr>
								<th class="text-left px-4 py-2">Date</th>
								<th class="text-left px-4 py-2">Entry</th>
								<th class="text-left px-4 py-2">Description</th>
								<th class="text-left px-4 py-2">Project</th>
								<th class="text-left px-4 py-2">Expense account</th>
								<th class="text-left px-4 py-2">Status</th>
								<th class="text-right px-4 py-2">In</th>
								<th class="text-right px-4 py-2">Out</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="r in filteredRows" :key="r.key" class="border-b border-ink-100 last:border-0 hover:bg-brand-50/30">
								<td class="px-4 py-2.5 text-ink-500 whitespace-nowrap">{{ fmtDate(r.date) }}</td>
								<td class="px-4 py-2.5"><span class="text-[10px] px-1.5 py-0.5 rounded-full whitespace-nowrap" :class="r.kind === 'Disbursement' ? 'bg-success-50 text-success-700' : 'bg-info-50 text-info-700'">{{ r.kind }}</span></td>
								<td class="px-4 py-2.5 text-ink-900">{{ r.description }}</td>
								<td class="px-4 py-2.5 text-ink-500">{{ projectName(r.project) }}</td>
								<td class="px-4 py-2.5 text-ink-600">{{ r.account || "—" }}</td>
								<td class="px-4 py-2.5"><StatusBadge :status="r.status" size="xs" /></td>
								<td class="px-4 py-2.5 text-right tabular-nums text-success-700">{{ r.in ? fmtINR(r.in) : "" }}</td>
								<td class="px-4 py-2.5 text-right tabular-nums text-danger-700">{{ r.out ? fmtINR(r.out) : "" }}</td>
							</tr>
						</tbody>
					</table>
					<div v-else class="px-4 py-12 text-center text-xs text-ink-400 italic">{{ loading ? "Loading…" : "No entries match the filters." }}</div>
				</section>
				<p class="text-[11px] text-ink-400">
					Disbursement rows hide automatically when an expense-only filter (account / status) is applied. Balance in hand is all-time; the other totals respect the filters.
					A negative balance is money the holder fronted — owed back to them, cleared on the next disbursement.
				</p>
			</template>
		</div>
	</DeskPage>
</template>
