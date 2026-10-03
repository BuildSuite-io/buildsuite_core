<script setup>
// Petty Cash — the LIVE part of Project Finance. Request → Disburse (posts a Journal Entry
// server-side). Everything else in the finance workspace is mock data.

import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useSessionStore } from "@/stores/session";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { useDocTypeList } from "@/composables/useDocTypeList";
import {
	pettyCashCanDisburse,
	savePettyCash,
	disbursePettyCash,
	issueDirectPettyCash,
	cancelPettyCash,
	undisbursePettyCash,
	pettyCashHolderBalances,
	listCashBankAccounts,
} from "@/data/pettyCashApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { useUserNames } from "@/composables/useUserNames";
import { usePermissions } from "@/composables/usePermissions";
import { usePagination } from "@/composables/usePagination";
import DeskPaginationFooter from "@/components/desk/DeskPaginationFooter.vue";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { fmtDate, fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const session = useSessionStore();
// Funding-source accounts are scoped to the working company (default when awareness is off,
// selected when on) so a site holding more than one company's ledgers never offers another
// company's Bank/Cash account to disburse from.
const activeCompany = useActiveCompany();
const { canCreate } = usePermissions();
const { userName } = useUserNames();
const confirmDialog = useConfirm();
const router = useRouter();

// Balances rows drill into the Petty Cash report with the holder pre-selected.
function openHolderReport(employee) {
	if (!employee) return;
	router.push(`/project-finance/report/petty?holder=${encodeURIComponent(employee)}`);
}

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
		"is_direct",
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
const statusFilter = ref(""); // All Requests tab status dropdown
const tabs = computed(() => [
	...(canDisburse.value
		? [{ id: "disburse", label: __("To Disburse"), count: requested.value.length }]
		: []),
	{ id: "all", label: __("All Requests"), count: all.value.length },
	{ id: "balances", label: __("Balances"), count: null },
	{ id: "mine", label: __("My Requests"), count: mine.value.length },
]);
if (!canDisburse.value) tab.value = "mine";

const requested = computed(() => all.value.filter((r) => r.status === "Requested"));
const mine = computed(() => all.value.filter((r) => r.requested_by === session.user));
const filteredAll = computed(() => {
	const q = search.value.trim().toLowerCase();
	return all.value.filter((r) => {
		if (statusFilter.value && r.status !== statusFilter.value) return false;
		if (!q) return true;
		return (
			(r.name || "").toLowerCase().includes(q) ||
			(r.purpose || "").toLowerCase().includes(q) ||
			(r.requested_by || "").toLowerCase().includes(q) ||
			userName(r.requested_by).toLowerCase().includes(q)
		);
	});
});

// Columns are tailored per tab (mirrors the prototype): the All Requests register
// carries ID + From account; the queue and My Requests are leaner.
const columns = computed(() => {
	if (tab.value === "all")
		return [
			{ key: "name", label: __("ID") },
			{ key: "requested_by", label: __("Holder") },
			{ key: "purpose", label: __("Purpose") },
			{ key: "request_date", label: __("Date") },
			{ key: "from_account", label: __("From account") },
			{ key: "amount", label: __("Amount"), align: "right" },
			{ key: "status", label: __("Status") },
			{ key: "actions", label: "" },
		];
	if (tab.value === "mine")
		return [
			{ key: "request_date", label: __("Date") },
			{ key: "purpose", label: __("Purpose") },
			{ key: "amount", label: __("Amount"), align: "right" },
			{ key: "status", label: __("Status") },
			{ key: "actions", label: "" },
		];
	// disburse queue
	return [
		{ key: "requested_by", label: __("Holder") },
		{ key: "purpose", label: __("Purpose") },
		{ key: "request_date", label: __("Date") },
		{ key: "amount", label: __("Amount"), align: "right" },
		{ key: "actions", label: "" },
	];
});

// --- balances ---
const balances = ref([]);
// Balances is a bespoke table (the requests list uses DeskList) — give it a client-side pager too.
const balancesPager = usePagination(balances);
async function loadBalances() {
	try {
		balances.value = await pettyCashHolderBalances();
	} catch (err) {
		showToast(err.message || __("Failed to load balances"), "error");
	}
}
loadBalances();

// --- request modal ---
const reqForm = reactive({ open: false, amount: 0, purpose: "", saving: false });
function openRequest() {
	Object.assign(reqForm, { open: true, amount: 0, purpose: "", saving: false });
}
async function submitRequest() {
	if (!(Number(reqForm.amount) > 0)) return showToast(__("Enter an amount."), "error");
	if (!reqForm.purpose.trim()) return showToast(__("Enter a purpose."), "error");
	reqForm.saving = true;
	try {
		await savePettyCash({ amount: reqForm.amount, purpose: reqForm.purpose });
		reqForm.open = false;
		res.reload?.();
		showToast(__("Petty cash requested."));
	} catch (err) {
		showToast(err.message || __("Failed to save"), "error");
	} finally {
		reqForm.saving = false;
	}
}

// --- direct issue modal (S273) — float straight to a holder, no request ---
const direct = reactive({
	open: false,
	holder: "",
	amount: 0,
	paidFrom: "",
	purpose: "",
	accounts: [],
	saving: false,
});
async function openDirect() {
	Object.assign(direct, {
		open: true,
		holder: "",
		amount: 0,
		paidFrom: "",
		purpose: "",
		accounts: [],
		saving: false,
	});
	try {
		direct.accounts = await listCashBankAccounts(activeCompany.value);
	} catch (err) {
		showToast(err.message || __("Failed to load accounts"), "error");
	}
}
const accountOptions = computed(() =>
	(direct.accounts || []).map((a) => ({ value: a.name, label: a.name, hint: a.account_type }))
);
async function submitDirect() {
	if (!direct.holder) return showToast(__("Pick who is receiving the float."), "error");
	if (!(Number(direct.amount) > 0)) return showToast(__("Enter an amount."), "error");
	if (!direct.paidFrom) return showToast(__("Pick the account to pay from."), "error");
	if (!direct.purpose.trim()) return showToast(__("A short reason is required."), "error");
	direct.saving = true;
	try {
		await issueDirectPettyCash({
			requested_by: direct.holder,
			amount: direct.amount,
			paid_from: direct.paidFrom,
			purpose: direct.purpose,
		});
		direct.open = false;
		res.reload?.();
		loadBalances();
		showToast(__("Petty cash issued — Journal Entry posted."));
	} catch (err) {
		showToast(err.message || __("Issue failed"), "error");
	} finally {
		direct.saving = false;
	}
}

// --- disburse modal ---
const disb = reactive({ open: false, row: null, paidFrom: "", accounts: [], saving: false });
async function openDisburse(row) {
	Object.assign(disb, { open: true, row, paidFrom: "", accounts: [], saving: false });
	try {
		// The funding source — Bank/Cash accounts for the active (default) company, EXCLUDING
		// Petty Cash (Cr must be a real source, never Petty Cash itself, a no-op JE).
		disb.accounts = await listCashBankAccounts(activeCompany.value);
	} catch (err) {
		showToast(err.message || "Failed to load accounts", "error");
	}
}
async function confirmDisburse() {
	if (!disb.paidFrom) return showToast(__("Pick the account to pay from."), "error");
	disb.saving = true;
	try {
		await disbursePettyCash(disb.row.name, disb.paidFrom);
		disb.open = false;
		res.reload?.();
		loadBalances();
		showToast(__("Disbursed — Journal Entry posted."));
	} catch (err) {
		showToast(err.message || __("Disburse failed"), "error");
	} finally {
		disb.saving = false;
	}
}

async function onWithdraw(row) {
	const mine = row.requested_by === session.user;
	const ok = await confirmDialog({
		title: mine ? __("Withdraw request?") : __("Cancel request?"),
		message: mine
			? __("Cancel your petty cash request {0}?", [row.name])
			: __("Cancel petty cash request {0} for {1}?", [row.name, userName(row.requested_by)]),
		confirmLabel: mine ? __("Withdraw") : __("Cancel"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await cancelPettyCash(row.name);
		res.reload?.();
		showToast(mine ? __("Request withdrawn.") : __("Request cancelled."));
	} catch (err) {
		showToast(err.message || (mine ? __("Withdraw failed") : __("Cancel failed")), "error");
	}
}

// Reverse a disbursement (cancel the JE and drop the holder's float). A direct issue has no
// request behind it, so reversing removes the record; a disbursed request goes back to the
// queue. Only petty-cash managers (canDisburse) see this.
async function onUndisburse(row) {
	const ok = await confirmDialog({
		title: __("Cancel disbursement?"),
		message: row.is_direct
			? __("Reverse the {0} issued to {1}? It was issued directly, so the record is removed and their float drops.", [fmtINR(row.amount), userName(row.requested_by)])
			: __("Reverse the {0} disbursed to {1}? The request returns to the disburse queue and their float drops.", [fmtINR(row.amount), userName(row.requested_by)]),
		confirmLabel: __("Cancel disbursement"),
		cancelLabel: __("Keep"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await undisbursePettyCash(row.name);
		res.reload?.();
		loadBalances();
		showToast(__("Disbursement reversed."));
	} catch (err) {
		showToast(err.message || __("Reversal failed"), "error");
	}
}

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Project Finance"), to: "/project-finance" },
	{ label: __("Petty Cash") },
];
const rowsForTab = computed(() => {
	if (tab.value === "disburse") return requested.value;
	if (tab.value === "mine") return mine.value;
	return filteredAll.value;
});
</script>

<template>
	<DeskPage :title="__('Petty Cash')" :breadcrumbs="breadcrumbs">
		<div class="flex items-center justify-between gap-3 mb-4">
			<div class="text-sm text-ink-600">
				{{ __("Advances to site holders. Spend is logged separately under") }}
				<span class="font-medium">{{ __("Expenses") }}</span>.
			</div>
			<div class="flex items-center gap-2 flex-shrink-0">
				<button
					v-if="canDisburse"
					type="button"
					class="text-xs px-2.5 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 whitespace-nowrap"
					style="border-radius: 6px"
					@click="openDirect"
				>
					{{ __("+ Issue directly") }}
				</button>
				<button
					v-if="canCreate('pettyCash')"
					type="button"
					class="text-xs desk-save-btn whitespace-nowrap"
					@click="openRequest"
				>
					{{ __("+ Request petty cash") }}
				</button>
			</div>
		</div>

		<!-- tabs -->
		<div class="border-b border-ink-200 flex overflow-x-auto scrollbar-thin mb-4">
			<button
				v-for="t in tabs"
				:key="t.id"
				type="button"
				class="px-3 py-2 text-xs font-medium whitespace-nowrap"
				:class="tab === t.id ? 'text-brand-600' : 'text-ink-600 hover:text-ink-900'"
				:style="
					tab === t.id
						? 'border-bottom: 2px solid currentColor; margin-bottom: -1px;'
						: 'border-bottom: 2px solid transparent; margin-bottom: -1px;'
				"
				@click="tab = t.id"
			>
				{{ t.label
				}}<span v-if="t.count !== null" class="ml-1 text-ink-500 tabular-nums"
					>({{ t.count }})</span
				>
			</button>
		</div>

		<!-- balances — reconciled: disbursed float in − verified spend out = in hand -->
		<div
			v-if="tab === 'balances'"
			class="bg-white border border-ink-200 rounded-lg overflow-hidden"
		>
			<table class="w-full text-xs">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-3 py-2">{{ __("Holder") }}</th>
						<th class="text-right px-3 py-2">{{ __("Disbursed") }}</th>
						<th class="text-right px-3 py-2">{{ __("Submitted spend") }}</th>
						<th class="text-right px-3 py-2">{{ __("Balance") }}</th>
						<th class="px-3 py-2"></th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="b in balancesPager.pagedRows"
						:key="b.employee || b.holder"
						class="border-t border-ink-100 hover:bg-brand-50/40 cursor-pointer"
						:title="__('Open {0}\'s petty-cash report', [b.holder])"
						@click="openHolderReport(b.employee)"
					>
						<td class="px-3 py-2 text-ink-900">
							<div class="flex items-center gap-1.5">
								<UserAvatar :name="b.holder" size="xs" /><span>{{
									b.holder
								}}</span>
							</div>
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ fmtINR(b.disbursed) }}
						</td>
						<td class="px-3 py-2 text-right tabular-nums text-ink-700">
							{{ fmtINR(b.spent) }}
						</td>
						<td
							class="px-3 py-2 text-right tabular-nums font-semibold"
							:class="b.balance < 0 ? 'text-danger-700' : 'text-ink-900'"
						>
							<template v-if="b.balance < 0"
								>{{ __("{0} owed to holder", [fmtINR(-b.balance)]) }}</template
							>
							<template v-else>{{ fmtINR(b.balance) }}</template>
						</td>
						<td class="px-3 py-2 text-right whitespace-nowrap">
							<span class="text-[11px] text-brand-700">{{ __("Report") }} →</span>
						</td>
					</tr>
					<tr v-if="!balances.length">
						<td colspan="5" class="px-3 py-4 text-center text-ink-400 italic">
							{{ __("No petty-cash activity yet.") }}
						</td>
					</tr>
				</tbody>
			</table>
			<DeskPaginationFooter :pager="balancesPager" />
			<p class="px-3 py-2 text-[11px] text-ink-400 border-t border-ink-100">
				{{ __("Balance in hand = disbursed float − approved expenses (from the Expenses tab). A negative balance means the holder fronted their own money — it's owed back to them and cleared on the next disbursement.") }}
			</p>
		</div>

		<!-- request lists -->
		<DeskList
			v-else
			v-model="search"
			:rows="rowsForTab"
			:columns="columns"
			row-key="name"
			:search-placeholder="tab === 'all' ? __('Search requests…') : ''"
		>
			<template v-if="tab === 'all'" #filter-chips>
				<select
					v-model="statusFilter"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-700 focus:outline-none focus:ring-2 focus:ring-brand-200"
				>
					<option value="">{{ __("All statuses") }}</option>
					<option value="Requested">{{ __("Requested") }}</option>
					<option value="Disbursed">{{ __("Disbursed") }}</option>
					<option value="Cancelled">{{ __("Cancelled") }}</option>
				</select>
			</template>
			<template #cell-name="{ row }">
				<span class="font-mono text-ink-400 text-[10px]">{{ row.name }}</span>
			</template>
			<template #cell-from_account="{ row }">
				<span class="text-xs text-ink-500">{{
					row.status === "Disbursed" ? row.paid_from || "—" : "—"
				}}</span>
			</template>
			<template #cell-requested_by="{ row }">
				<div class="flex items-center gap-1.5">
					<UserAvatar :user-id="row.requested_by" size="xs" /><span
						class="text-xs text-ink-900"
						>{{ userName(row.requested_by) }}</span
					>
				</div>
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
				<div class="flex items-center gap-1.5">
					<StatusBadge :status="row.status" />
					<span
						v-if="row.is_direct"
						class="text-[9px] px-1 py-0.5 rounded bg-info-50 text-info-700 font-medium uppercase tracking-wider"
						:title="__('Issued directly to the holder, no request behind it')"
						>{{ __("Direct") }}</span
					>
				</div>
			</template>
			<template #cell-actions="{ row }">
				<div class="flex justify-end gap-2">
					<button
						v-if="row.status === 'Requested' && canDisburse"
						type="button"
						class="text-[11px] px-2 py-1 bg-brand-600 hover:bg-brand-700 text-white rounded-md"
						@click.stop="openDisburse(row)"
					>
						{{ __("Disburse") }}
					</button>
					<button
						v-if="
							row.status === 'Requested' &&
							(row.requested_by === session.user || canDisburse)
						"
						type="button"
						class="text-[11px] px-2 py-0.5 border border-ink-200 text-ink-600 rounded"
						@click.stop="onWithdraw(row)"
					>
						{{ row.requested_by === session.user ? __("Withdraw") : __("Cancel") }}
					</button>
					<button
						v-if="row.status === 'Disbursed' && canDisburse"
						type="button"
						class="text-[11px] px-2 py-1 text-danger-600 hover:text-danger-700 hover:underline"
						@click.stop="onUndisburse(row)"
					>
						{{ __("Cancel") }}
					</button>
				</div>
			</template>
			<template #empty>
				<div class="text-sm text-ink-500">
					{{ res.loading ? __("Loading…") : __("Nothing here.") }}
				</div>
			</template>
		</DeskList>

		<!-- request modal -->
		<div
			v-if="reqForm.open"
			class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
			@click.self="reqForm.open = false"
		>
			<div class="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
				<h3 class="text-sm font-semibold text-ink-900 mb-4">{{ __("Request petty cash") }}</h3>
				<div class="space-y-3">
					<DeskField :label="__('Amount')" required
						><DeskInput v-model.number="reqForm.amount" type="number" min="0"
					/></DeskField>
					<DeskField :label="__('Purpose')" required
						><DeskInput v-model="reqForm.purpose" :placeholder="__('What is it for?')"
					/></DeskField>
				</div>
				<div class="flex justify-end gap-2 mt-5">
					<button class="desk-btn" @click="reqForm.open = false">{{ __("Cancel") }}</button>
					<button
						class="desk-save-btn"
						:disabled="reqForm.saving"
						@click="submitRequest"
					>
						{{ reqForm.saving ? __("Saving…") : __("Request") }}
					</button>
				</div>
			</div>
		</div>

		<!-- direct issue modal (S273) -->
		<div
			v-if="direct.open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6"
			@click.self="direct.open = false"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-md shadow-xl rounded-xl"
				@click.stop
			>
				<header
					class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"
				>
					<h2 class="text-sm font-semibold text-ink-900">{{ __("Issue petty cash directly") }}</h2>
					<button
						type="button"
						class="text-ink-400 hover:text-ink-900"
						@click="direct.open = false"
					>
						✕
					</button>
				</header>
				<div class="px-4 py-4 space-y-3">
					<p
						class="text-[11px] text-warning-700 bg-warning-50 border border-warning-200 rounded-md px-2.5 py-2"
					>
						{{ __("No request precedes this — the record you create here is the only trail. Use it when cash genuinely moved before anyone could raise a request.") }}
					</p>
					<div>
						<label
							class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
							>{{ __("Issue to") }} <span class="text-danger-600">*</span></label
						>
						<DeskLinkPicker
							v-model="direct.holder"
							doctype="User"
							label-field="full_name"
							value-field="name"
							:placeholder="__('Pick the holder…')"
						/>
					</div>
					<div>
						<label
							class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
							>{{ __("Amount") }} <span class="text-danger-600">*</span></label
						>
						<input
							v-model.number="direct.amount"
							type="number"
							min="0"
							placeholder="0"
							class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
						/>
					</div>
					<div>
						<label
							class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
							>{{ __("From account") }} <span class="text-danger-600">*</span></label
						>
						<DeskSearchableSelect
							v-model="direct.paidFrom"
							:options="accountOptions"
							:placeholder="__('Pick an account…')"
							:search-placeholder="__('Search accounts…')"
						/>
					</div>
					<div>
						<label
							class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
							>{{ __("Reason") }} <span class="text-danger-600">*</span></label
						>
						<input
							v-model="direct.purpose"
							type="text"
							:placeholder="__('What\'s it for?')"
							class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
						/>
					</div>
				</div>
				<footer
					class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2"
				>
					<button
						type="button"
						class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
						@click="direct.open = false"
					>
						{{ __("Cancel") }}
					</button>
					<button
						type="button"
						class="text-xs desk-save-btn"
						:disabled="direct.saving"
						@click="submitDirect"
					>
						{{ direct.saving ? __("Issuing…") : __("Issue float") }}
					</button>
				</footer>
			</div>
		</div>

		<!-- disburse modal -->
		<div
			v-if="disb.open"
			class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4"
			@click.self="disb.open = false"
		>
			<div class="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
				<h3 class="text-sm font-semibold text-ink-900 mb-1">
					{{ __("Disburse {0}", [fmtINR(disb.row?.amount)]) }}
				</h3>
				<p class="text-xs text-ink-500 mb-4">
					{{ __("to {0} · posts a Journal Entry (Dr Petty Cash / Cr the source account).", [userName(disb.row?.requested_by)]) }}
				</p>
				<DeskField :label="__('Pay from')" required>
					<DeskSelect v-model="disb.paidFrom">
						<option value="" disabled>{{ __("Bank / Cash account…") }}</option>
						<option v-for="a in disb.accounts" :key="a.name" :value="a.name">
							{{ a.name }}
						</option>
					</DeskSelect>
				</DeskField>
				<div class="flex justify-end gap-2 mt-5">
					<button class="desk-btn" @click="disb.open = false">{{ __("Cancel") }}</button>
					<button class="desk-save-btn" :disabled="disb.saving" @click="confirmDisburse">
						{{ disb.saving ? __("Posting…") : __("Disburse") }}
					</button>
				</div>
			</div>
		</div>
	</DeskPage>
</template>
