<script setup>
// S229 — Project Finance › Payments. Unified register of party payments
// (invoice receipts, customer/supplier/subcontractor advances, bill payments,
// subcontractor payment entries) with a Cancel action per row. Petty-cash
// disbursements are NOT payments (internal float transfer); they're managed
// under Petty Cash. Backed by real ERPNext Payment Entries
// (buildsuite_core.api.finance_payment.*).
// ERPNext discipline: posted transactions are CANCELLED (reversed), never
// edited — cancel the wrong entry and record a fresh one. Because all balances
// are derived, cancelling recomputes accounts / outstandings / floats cleanly.
import { ref, computed, onMounted } from "vue";
import { useDataStore } from "@/stores";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import { fmtINR, fmtDate } from "@/utils/format";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { listFinancePayments, cancelFinancePayment } from "@/data/financePaymentApi";

const store = useDataStore();
const confirmDialog = useConfirm();

// Per M3, the Accountant cancels payments alongside the admin tier — mirror the
// Payment Entry cancel permission the backend enforces (cancel_payment →
// check_permission("cancel")), so the UI doesn't hide an action the user is allowed.
const canManage = computed(() => store.isAdmin || store.role === "accountant");

const movements = ref([]);
const loading = ref(true);
async function load() {
	loading.value = true;
	try {
		movements.value = await listFinancePayments();
	} catch (err) {
		showToast(err.message || "Failed to load payments", "error");
	} finally {
		loading.value = false;
	}
}
onMounted(load);

// ---- filters (S244f — full set, S243 pattern) ----
const search = ref("");
const dirFilter = ref(""); // '' | 'in' | 'out'
const accFilter = ref(""); // '' | account name
const typeFilter = ref(""); // '' | movement type label
const partyFilter = ref(""); // '' | party display name
const from = ref("");
const to = ref("");
const amtMin = ref("");
const amtMax = ref("");

const MOVEMENT_TYPES = [
	"Invoice receipt",
	"Customer advance",
	"Bill payment",
	"Supplier advance",
	"Subcontractor advance",
	"Subcontractor payment",
];
const hasFilters = computed(
	() =>
		search.value ||
		dirFilter.value ||
		accFilter.value ||
		typeFilter.value ||
		partyFilter.value ||
		from.value ||
		to.value ||
		amtMin.value !== "" ||
		amtMax.value !== "",
);
function clearFilters() {
	search.value = "";
	dirFilter.value = "";
	accFilter.value = "";
	typeFilter.value = "";
	partyFilter.value = "";
	from.value = "";
	to.value = "";
	amtMin.value = "";
	amtMax.value = "";
}
function inPeriod(d) {
	return (!from.value || d >= from.value) && (!to.value || d <= to.value);
}
function inAmountRange(n) {
	return (
		(amtMin.value === "" || n >= (Number(amtMin.value) || 0)) &&
		(amtMax.value === "" || n <= (Number(amtMax.value) || Infinity))
	);
}

// Distinct accounts + parties across the register — the filter pools.
const accountOptions = computed(() =>
	[...new Set(movements.value.map((m) => m.account).filter(Boolean))].sort((a, b) =>
		a.localeCompare(b),
	),
);
const partyOptions = computed(() => {
	const names = [...new Set(movements.value.map((m) => m.party).filter(Boolean))].sort((a, b) =>
		a.localeCompare(b),
	);
	return names.map((n) => ({ value: n, label: n }));
});

const filtered = computed(() => {
	const term = search.value.trim().toLowerCase();
	return movements.value.filter(
		(m) =>
			(!dirFilter.value || m.dir === dirFilter.value) &&
			(!accFilter.value || m.account === accFilter.value) &&
			(!typeFilter.value || m.type === typeFilter.value) &&
			(!partyFilter.value || m.party === partyFilter.value) &&
			inPeriod(m.date) &&
			inAmountRange(m.amount) &&
			(!term ||
				m.type.toLowerCase().includes(term) ||
				(m.party || "").toLowerCase().includes(term) ||
				(m.account || "").toLowerCase().includes(term) ||
				(m.ref || "").toLowerCase().includes(term)),
	);
});
const totalIn = computed(() =>
	filtered.value.filter((m) => m.dir === "in").reduce((a, m) => a + m.amount, 0),
);
const totalOut = computed(() =>
	filtered.value.filter((m) => m.dir === "out").reduce((a, m) => a + m.amount, 0),
);

const CANCEL_NOTE = {
	in: "The invoice's outstanding goes back up (or the customer advance is removed).",
	out: "The bill's outstanding goes back up (or the advance paid is removed).",
};
async function onCancel(m) {
	const ok = await confirmDialog({
		title: `Cancel this ${m.type.toLowerCase()}?`,
		message: `${m.type} of ${fmtINR(m.amount)} — ${m.party} (${fmtDate(m.date)}).\n\n${
			CANCEL_NOTE[m.dir]
		} Record a fresh transaction if it was entered wrongly — posted entries are cancelled, not edited.`,
		confirmLabel: "Cancel transaction",
		destructive: true,
	});
	if (!ok) return;
	try {
		await cancelFinancePayment(m.name);
		await load();
		showToast("Transaction cancelled.");
	} catch (err) {
		showToast(err.message || "Cancel failed", "error");
	}
}

const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Payments" }];
</script>

<template>
	<DeskPage title="Payments" :breadcrumbs="breadcrumbs">
		<div class="space-y-4">
			<div class="flex items-center gap-2 flex-wrap">
				<input
					v-model="search"
					type="text"
					placeholder="Search type, party, account, reference…"
					class="text-xs px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400 w-64 max-w-full"
				/>
				<select
					v-model="typeFilter"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200"
				>
					<option value="">All types</option>
					<option v-for="t in MOVEMENT_TYPES" :key="t" :value="t">{{ t }}</option>
				</select>
				<select
					v-model="dirFilter"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200"
				>
					<option value="">In &amp; out</option>
					<option value="in">Money in</option>
					<option value="out">Money out</option>
				</select>
				<select
					v-model="accFilter"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200"
				>
					<option value="">All accounts</option>
					<option v-for="a in accountOptions" :key="a" :value="a">{{ a }}</option>
				</select>
				<div class="w-52">
					<DeskSearchableSelect
						v-model="partyFilter"
						:options="partyOptions"
						allow-clear
						placeholder="All parties"
						search-placeholder="Search parties…"
					/>
				</div>
				<div class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>From</span
					>
					<input
						v-model="from"
						type="date"
						class="text-xs px-2 py-1 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200"
					/>
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>To</span
					>
					<input
						v-model="to"
						type="date"
						class="text-xs px-2 py-1 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200"
					/>
				</div>
				<div class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>₹</span
					>
					<input
						v-model.number="amtMin"
						type="number"
						min="0"
						placeholder="Min"
						class="text-xs px-2 py-1 border border-ink-200 rounded-md w-20 text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-brand-200"
					/>
					<span class="text-ink-400 text-xs">–</span>
					<input
						v-model.number="amtMax"
						type="number"
						min="0"
						placeholder="Max"
						class="text-xs px-2 py-1 border border-ink-200 rounded-md w-24 text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-brand-200"
					/>
				</div>
				<button
					v-if="hasFilters"
					type="button"
					class="text-[11px] text-danger-600 hover:underline"
					@click="clearFilters"
				>
					Clear filters
				</button>
				<div class="ml-auto flex items-center gap-4 text-xs">
					<div>
						<span class="text-ink-500">In</span>
						<span class="tabular-nums text-success-700 font-medium">{{
							fmtINR(totalIn)
						}}</span>
					</div>
					<div>
						<span class="text-ink-500">Out</span>
						<span class="tabular-nums text-danger-700 font-medium">{{
							fmtINR(totalOut)
						}}</span>
					</div>
					<span class="text-ink-400"
						>{{ filtered.length }} transaction{{
							filtered.length === 1 ? "" : "s"
						}}</span
					>
				</div>
			</div>

			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<table v-if="filtered.length" class="w-full text-xs">
					<thead
						class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200 bg-ink-50"
					>
						<tr>
							<th class="text-left px-4 py-2">Date</th>
							<th class="text-left px-4 py-2">Type</th>
							<th class="text-left px-4 py-2">Party</th>
							<th class="text-left px-4 py-2">Account</th>
							<th class="text-left px-4 py-2">Ref</th>
							<th class="text-right px-4 py-2">In</th>
							<th class="text-right px-4 py-2">Out</th>
							<th class="px-4 py-2"></th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="m in filtered"
							:key="m.name"
							class="border-b border-ink-100 last:border-0 hover:bg-brand-50/30"
						>
							<td class="px-4 py-2.5 text-ink-500 whitespace-nowrap">
								{{ fmtDate(m.date) }}
							</td>
							<td class="px-4 py-2.5">
								<span
									class="text-[10px] px-1.5 py-0.5 rounded-full"
									:class="
										m.dir === 'in'
											? 'bg-success-50 text-success-700'
											: 'bg-warning-50 text-warning-700'
									"
									>{{ m.type }}</span
								>
							</td>
							<td class="px-4 py-2.5 text-ink-900">{{ m.party }}</td>
							<td class="px-4 py-2.5 text-ink-500">{{ m.account || "—" }}</td>
							<td class="px-4 py-2.5 font-mono text-ink-400 text-[10px]">
								{{ m.ref || "—" }}
							</td>
							<td class="px-4 py-2.5 text-right tabular-nums text-success-700">
								{{ m.dir === "in" ? fmtINR(m.amount) : "" }}
							</td>
							<td class="px-4 py-2.5 text-right tabular-nums text-danger-700">
								{{ m.dir === "out" ? fmtINR(m.amount) : "" }}
							</td>
							<td class="px-4 py-2.5 text-right">
								<button
									v-if="canManage"
									type="button"
									class="text-[11px] text-danger-600 hover:underline"
									@click="onCancel(m)"
								>
									Cancel
								</button>
							</td>
						</tr>
					</tbody>
				</table>
				<div v-else class="px-4 py-12 text-center text-xs text-ink-400 italic">
					{{
						loading
							? "Loading payments…"
							: hasFilters
								? "No transactions match the filters."
								: "No transactions recorded yet."
					}}
				</div>
			</section>
			<p class="text-[11px] text-ink-400">
				Posted transactions are cancelled, not edited — cancel the wrong entry and record a
				fresh one. All balances and outstandings recompute automatically.
			</p>
		</div>
	</DeskPage>
</template>
