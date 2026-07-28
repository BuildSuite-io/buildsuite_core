<script setup>
// Petty Cash — the LIVE part of Project Finance. Request → Disburse (posts a Journal Entry
// server-side). Everything else in the finance workspace is mock data.

import { computed, reactive, ref } from "vue";
import { useSessionStore } from "@/stores/session";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { useDocTypeList } from "@/composables/useDocTypeList";
import {
	pettyCashCanDisburse,
	savePettyCash,
	disbursePettyCash,
	cancelPettyCash,
	pettyCashHolderBalances,
	listCashBankAccounts,
} from "@/data/pettyCashApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const session = useSessionStore();
const confirmDialog = useConfirm();

const canDisburse = ref(false);
pettyCashCanDisburse()
	.then((r) => (canDisburse.value = !!r.can_disburse))
	.catch(() => {});

const res = useDocTypeList("Petty Cash Request", {
	fields: [
		"name",
		"requested_by",
		"request_date",
		"amount",
		"purpose",
		"status",
		"company",
		"paid_from",
		"disbursed_by",
	],
	orderBy: "request_date desc",
	pageLength: 0,
	cache: "buildsuite-petty-cash-list",
});
const all = computed(() => res.data || []);

const tab = ref("disburse");
const search = ref("");
const tabs = computed(() => [
	...(canDisburse.value ? [{ id: "disburse", label: "To Disburse", count: requested.value.length }] : []),
	{ id: "all", label: "All Requests", count: all.value.length },
	{ id: "balances", label: "Balances", count: null },
	{ id: "mine", label: "My Requests", count: mine.value.length },
]);
if (!canDisburse.value) tab.value = "mine";

const requested = computed(() => all.value.filter((r) => r.status === "Requested"));
const mine = computed(() => all.value.filter((r) => r.requested_by === session.user));
const filteredAll = computed(() => {
	const q = search.value.trim().toLowerCase();
	if (!q) return all.value;
	return all.value.filter(
		(r) =>
			(r.name || "").toLowerCase().includes(q) ||
			(r.purpose || "").toLowerCase().includes(q) ||
			(r.requested_by || "").toLowerCase().includes(q),
	);
});

const columns = [
	{ key: "requested_by", label: "Holder" },
	{ key: "purpose", label: "Purpose" },
	{ key: "request_date", label: "Date" },
	{ key: "amount", label: "Amount", align: "right" },
	{ key: "status", label: "Status" },
	{ key: "actions", label: "" },
];

// --- balances ---
const balances = ref([]);
async function loadBalances() {
	try {
		balances.value = await pettyCashHolderBalances();
	} catch (err) {
		showToast(err.message || "Failed to load balances", "error");
	}
}
loadBalances();

// --- request modal ---
const reqForm = reactive({ open: false, amount: 0, purpose: "", saving: false });
function openRequest() {
	Object.assign(reqForm, { open: true, amount: 0, purpose: "", saving: false });
}
async function submitRequest() {
	if (!(Number(reqForm.amount) > 0)) return showToast("Enter an amount.", "error");
	if (!reqForm.purpose.trim()) return showToast("Enter a purpose.", "error");
	reqForm.saving = true;
	try {
		await savePettyCash({ amount: reqForm.amount, purpose: reqForm.purpose });
		reqForm.open = false;
		res.reload?.();
		showToast("Petty cash requested.");
	} catch (err) {
		showToast(err.message || "Failed to save", "error");
	} finally {
		reqForm.saving = false;
	}
}

// --- disburse modal ---
const disb = reactive({ open: false, row: null, paidFrom: "", accounts: [], saving: false });
async function openDisburse(row) {
	Object.assign(disb, { open: true, row, paidFrom: "", accounts: [], saving: false });
	try {
		// The funding source — Bank/Cash accounts EXCLUDING Petty Cash (Cr must be a real
		// source, never Petty Cash itself, which would make the JE a no-op).
		disb.accounts = await listCashBankAccounts(row.company);
	} catch (err) {
		showToast(err.message || "Failed to load accounts", "error");
	}
}
async function confirmDisburse() {
	if (!disb.paidFrom) return showToast("Pick the account to pay from.", "error");
	disb.saving = true;
	try {
		await disbursePettyCash(disb.row.name, disb.paidFrom);
		disb.open = false;
		res.reload?.();
		loadBalances();
		showToast("Disbursed — Journal Entry posted.");
	} catch (err) {
		showToast(err.message || "Disburse failed", "error");
	} finally {
		disb.saving = false;
	}
}

async function onWithdraw(row) {
	const ok = await confirmDialog({
		title: "Withdraw request?",
		message: `Cancel your petty cash request ${row.name}?`,
		confirmLabel: "Withdraw",
		destructive: true,
	});
	if (!ok) return;
	try {
		await cancelPettyCash(row.name);
		res.reload?.();
		showToast("Request withdrawn.");
	} catch (err) {
		showToast(err.message || "Withdraw failed", "error");
	}
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Project Finance", to: "/project-finance" },
	{ label: "Petty Cash" },
];
const rowsForTab = computed(() => {
	if (tab.value === "disburse") return requested.value;
	if (tab.value === "mine") return mine.value;
	return filteredAll.value;
});
</script>

<template>
	<DeskPage title="Petty Cash" :breadcrumbs="breadcrumbs">
		<div class="flex items-center justify-between gap-3 mb-4">
			<div class="text-sm text-ink-600">Advances to site holders. Spend is logged separately under <span class="font-medium">Expenses</span>.</div>
			<button type="button" class="text-xs desk-save-btn whitespace-nowrap" @click="openRequest">+ Request petty cash</button>
		</div>

		<!-- tabs -->
		<div class="border-b border-ink-200 flex overflow-x-auto scrollbar-thin mb-4">
			<button
				v-for="t in tabs"
				:key="t.id"
				type="button"
				class="px-3 py-2 text-xs font-medium whitespace-nowrap"
				:class="tab === t.id ? 'text-brand-600' : 'text-ink-600 hover:text-ink-900'"
				:style="tab === t.id ? 'border-bottom: 2px solid currentColor; margin-bottom: -1px;' : 'border-bottom: 2px solid transparent; margin-bottom: -1px;'"
				@click="tab = t.id"
			>
				{{ t.label }}<span v-if="t.count !== null" class="ml-1 text-ink-500 tabular-nums">({{ t.count }})</span>
			</button>
		</div>

		<!-- balances — reconciled: disbursed float in − verified spend out = in hand -->
		<div v-if="tab === 'balances'" class="bg-white border border-ink-200 rounded-lg overflow-hidden">
			<table class="w-full text-xs">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">Holder</th>
						<th class="text-right px-3 py-2">Disbursed</th>
						<th class="text-right px-3 py-2">Verified spend</th>
						<th class="text-right px-3 py-2">Balance in hand</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="b in balances" :key="b.employee || b.holder" class="border-t border-ink-100">
						<td class="px-3 py-2 text-ink-900">{{ b.holder }}</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">{{ fmtINR(b.disbursed) }}</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">{{ fmtINR(b.spent) }}</td>
						<td class="px-3 py-2 text-right tabular-nums font-semibold" :class="b.balance < 0 ? 'text-danger-700' : 'text-ink-900'">
							<template v-if="b.balance < 0">{{ fmtINR(-b.balance) }} owed to holder</template>
							<template v-else>{{ fmtINR(b.balance) }}</template>
						</td>
					</tr>
					<tr v-if="!balances.length">
						<td colspan="4" class="px-3 py-4 text-center text-ink-400 italic">No petty-cash activity yet.</td>
					</tr>
				</tbody>
			</table>
			<p class="px-3 py-2 text-[11px] text-ink-400 border-t border-ink-100">
				Balance in hand = disbursed float − approved expenses (from the Expenses tab).
				A negative balance means the holder fronted their own money — it's owed back to them and cleared on the next disbursement.
			</p>
		</div>

		<!-- request lists -->
		<DeskList
			v-else
			v-model="search"
			:rows="rowsForTab"
			:columns="columns"
			row-key="name"
			:search-placeholder="tab === 'all' ? 'Search requests…' : ''"
		>
			<template #cell-requested_by="{ row }">
				<span class="text-xs text-ink-900">{{ row.requested_by }}</span>
			</template>
			<template #cell-purpose="{ row }">
				<span class="text-xs text-ink-700">{{ (row.purpose || "").slice(0, 60) }}</span>
			</template>
			<template #cell-request_date="{ row }">
				<span class="text-xs text-ink-500">{{ fmtDate(row.request_date) }}</span>
			</template>
			<template #cell-amount="{ row }">
				<span class="text-xs tabular-nums font-medium">{{ fmtINR(row.amount) }}</span>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" />
			</template>
			<template #cell-actions="{ row }">
				<div class="flex justify-end gap-2">
					<button
						v-if="row.status === 'Requested' && canDisburse"
						type="button"
						class="text-[11px] px-2 py-0.5 border border-brand-300 bg-brand-50 text-brand-700 rounded"
						@click.stop="openDisburse(row)"
					>
						Disburse
					</button>
					<button
						v-if="row.status === 'Requested' && row.requested_by === session.user"
						type="button"
						class="text-[11px] px-2 py-0.5 border border-ink-200 text-ink-600 rounded"
						@click.stop="onWithdraw(row)"
					>
						Withdraw
					</button>
				</div>
			</template>
			<template #empty>
				<div class="text-sm text-ink-500">{{ res.loading ? "Loading…" : "Nothing here." }}</div>
			</template>
		</DeskList>

		<!-- request modal -->
		<div v-if="reqForm.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="reqForm.open = false">
			<div class="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
				<h3 class="text-sm font-semibold text-ink-900 mb-4">Request petty cash</h3>
				<div class="space-y-3">
					<DeskField label="Amount" required><DeskInput v-model.number="reqForm.amount" type="number" min="0" /></DeskField>
					<DeskField label="Purpose" required><DeskInput v-model="reqForm.purpose" placeholder="What is it for?" /></DeskField>
				</div>
				<div class="flex justify-end gap-2 mt-5">
					<button class="desk-btn" @click="reqForm.open = false">Cancel</button>
					<button class="desk-save-btn" :disabled="reqForm.saving" @click="submitRequest">{{ reqForm.saving ? "Saving…" : "Request" }}</button>
				</div>
			</div>
		</div>

		<!-- disburse modal -->
		<div v-if="disb.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="disb.open = false">
			<div class="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
				<h3 class="text-sm font-semibold text-ink-900 mb-1">Disburse {{ fmtINR(disb.row?.amount) }}</h3>
				<p class="text-xs text-ink-500 mb-4">to {{ disb.row?.requested_by }} · posts a Journal Entry (Dr Petty Cash / Cr the source account).</p>
				<DeskField label="Pay from" required>
					<DeskSelect v-model="disb.paidFrom">
						<option value="" disabled>Bank / Cash account…</option>
						<option v-for="a in disb.accounts" :key="a.name" :value="a.name">{{ a.name }}</option>
					</DeskSelect>
				</DeskField>
				<div class="flex justify-end gap-2 mt-5">
					<button class="desk-btn" @click="disb.open = false">Cancel</button>
					<button class="desk-save-btn" :disabled="disb.saving" @click="confirmDisburse">{{ disb.saving ? "Posting…" : "Disburse" }}</button>
				</div>
			</div>
		</div>
	</DeskPage>
</template>
