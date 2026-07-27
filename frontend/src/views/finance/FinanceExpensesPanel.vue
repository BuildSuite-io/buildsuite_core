<script setup>
// Project Finance › Expenses — LIVE. The signed-in holder logs spend against their
// petty-cash float as an Expense Entry (draft = pending approval); a finance approver
// approves it, posting the Journal Entry. Balances + ledger come from the employee
// petty-cash ledger (buildsuite_core.utils.petty_cash).
import { computed, reactive, ref } from "vue";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { useDocTypeList } from "@/composables/useDocTypeList";
import {
	expenseContext,
	expenseLedger,
	saveExpense,
	submitExpense,
	cancelExpense,
	expenseToReimburse,
	reimburseExpense,
} from "@/data/expenseEntryApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Expenses" }];
const confirmDialog = useConfirm();

// --- caller's petty-cash position ---
const ctx = ref({ employee: null, employee_name: null, can_submit: false, approved: 0, pending: 0, available: 0 });
async function loadContext() {
	try {
		ctx.value = await expenseContext();
	} catch (err) {
		showToast(err.message || "Failed to load balance", "error");
	}
}
loadContext();
const canSubmit = computed(() => !!ctx.value.can_submit);
const hasEmployee = computed(() => !!ctx.value.employee);

// --- entries list ---
const res = useDocTypeList("Expense Entry", {
	fields: ["name", "date", "project", "employee", "total_amount", "docstatus", "payment_account"],
	orderBy: "creation desc",
	pageLength: 0,
	cache: "buildsuite-expense-entry-list",
});
const entries = computed(() => res.data || []);
function statusLabel(d) {
	if (d === 2) return "Cancelled";
	if (d === 1) return "Approved";
	return "Pending Approval";
}

// Draft = pending a finance approver's verification (the demo's Draft → Submitted).
const drafts = computed(() => entries.value.filter((e) => e.docstatus === 0));
const mine = computed(() => entries.value.filter((e) => e.employee === ctx.value.employee));

const tabs = computed(() => {
	const t = [];
	if (canSubmit.value) {
		t.push({ id: "verify", label: "To Verify", count: drafts.value.length, alert: true });
		t.push({ id: "reimburse", label: "To Reimburse", count: reimburseRows.value.length, alert: true });
		t.push({ id: "all", label: "All", count: entries.value.length });
	}
	t.push({ id: "mine", label: "My Expenses", count: null });
	t.push({ id: "ledger", label: "Ledger", count: null });
	return t;
});
const tab = ref(null);
const activeTab = computed(() =>
	tab.value && tabs.value.some((t) => t.id === tab.value) ? tab.value : tabs.value[0]?.id,
);
const tableRows = computed(() => {
	if (activeTab.value === "verify") return drafts.value;
	if (activeTab.value === "mine") return mine.value;
	return entries.value;
});

// --- ledger ---
const ledgerRows = ref([]);
const ledgerLoading = ref(false);
async function loadLedger() {
	ledgerLoading.value = true;
	try {
		ledgerRows.value = await expenseLedger();
	} catch (err) {
		showToast(err.message || "Failed to load ledger", "error");
	} finally {
		ledgerLoading.value = false;
	}
}

// --- reimbursement queue (approvers) ---
const reimburseRows = ref([]);
const reimburseTotal = ref(0);
async function loadReimburse() {
	try {
		const r = await expenseToReimburse();
		reimburseRows.value = r.rows || [];
		reimburseTotal.value = r.total || 0;
	} catch (err) {
		showToast(err.message || "Failed to load reimbursements", "error");
	}
}
if (canSubmit.value) loadReimburse();

const reimb = reactive({ open: false, row: null, bank: "", saving: false });
function openReimburse(row) {
	Object.assign(reimb, { open: true, row, bank: "", saving: false });
}
const reimburseAccountFilters = computed(() => [
	["account_type", "in", ["Bank", "Cash"]],
	["is_group", "=", 0],
	["company", "=", reimb.row?.company],
]);
async function confirmReimburse() {
	if (!reimb.bank) return showToast("Pick the account to pay from.", "error");
	reimb.saving = true;
	try {
		await reimburseExpense(reimb.row.name, reimb.bank);
		reimb.open = false;
		loadReimburse();
		res.reload?.();
		showToast("Reimbursed — Journal Entry posted.");
	} catch (err) {
		showToast(err.message || "Reimburse failed", "error");
	} finally {
		reimb.saving = false;
	}
}

function openTab(t) {
	tab.value = t;
	if (t === "ledger" && !ledgerRows.value.length) loadLedger();
	if (t === "reimburse") loadReimburse();
}

// --- create modal ---
const COST_TYPES = ["Material", "Labour", "Plant & Machinery", "Subcontract", "Overhead"];
const blankRow = () => ({ expense_account: "", cost_type: "Overhead", amount: 0, description: "" });
const form = reactive({ open: false, project: "", date: new Date().toISOString().slice(0, 10), reimbursable: false, rows: [blankRow()], saving: false });
function openForm() {
	Object.assign(form, { open: true, project: "", date: new Date().toISOString().slice(0, 10), reimbursable: false, rows: [blankRow()], saving: false });
}
const formTotal = computed(() => form.rows.reduce((s, r) => s + (Number(r.amount) || 0), 0));
function addRow() {
	form.rows.push(blankRow());
}
function removeRow(i) {
	form.rows.splice(i, 1);
	if (!form.rows.length) form.rows.push(blankRow());
}
async function submitForm() {
	if (!form.project) return showToast("Pick a project.", "error");
	const rows = form.rows.filter((r) => r.expense_account && Number(r.amount) > 0);
	if (!rows.length) return showToast("Add at least one line with an account and amount.", "error");
	form.saving = true;
	try {
		await saveExpense({ project: form.project, date: form.date, reimbursable: form.reimbursable, rows });
		form.open = false;
		res.reload?.();
		loadContext();
		showToast("Expense entry saved — pending approval.");
	} catch (err) {
		showToast(err.message || "Failed to save", "error");
	} finally {
		form.saving = false;
	}
}

// --- actions ---
async function onApprove(row) {
	const ok = await confirmDialog({
		title: "Approve expense entry?",
		message: `Post ${fmtINR(row.total_amount)} for ${row.name}? This posts a Journal Entry against petty cash.`,
		confirmLabel: "Approve & post",
	});
	if (!ok) return;
	try {
		await submitExpense(row.name);
		res.reload?.();
		loadContext();
		if (activeTab.value === "ledger") loadLedger();
		showToast("Verified — Journal Entry posted.");
	} catch (err) {
		showToast(err.message || "Approve failed", "error");
	}
}
async function onCancel(row) {
	const submitted = row.docstatus === 1;
	const ok = await confirmDialog({
		title: submitted ? "Cancel expense entry?" : "Delete draft?",
		message: submitted ? `Reverse the Journal Entry for ${row.name}?` : `Delete draft ${row.name}?`,
		confirmLabel: submitted ? "Cancel entry" : "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await cancelExpense(row.name);
		res.reload?.();
		loadContext();
		showToast(submitted ? "Entry cancelled." : "Draft deleted.");
	} catch (err) {
		showToast(err.message || "Action failed", "error");
	}
}

const expenseAccountFilters = [
	["root_type", "=", "Expense"],
	["is_group", "=", 0],
];
</script>

<template>
	<DeskPage title="Expenses" :breadcrumbs="breadcrumbs">
		<template #actions>
			<button type="button" class="desk-save-btn" :disabled="!hasEmployee" @click="openForm">+ Log Expense</button>
		</template>

		<!-- balance strip -->
		<div v-if="hasEmployee" class="grid grid-cols-3 gap-3 mb-4 max-w-2xl">
			<div class="bg-white border border-ink-200 rounded-lg px-4 py-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Approved balance</div>
				<div class="text-lg font-semibold text-ink-900 tabular-nums">{{ fmtINR(ctx.approved) }}</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg px-4 py-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Pending approval</div>
				<div class="text-lg font-semibold text-warning-700 tabular-nums">{{ fmtINR(ctx.pending) }}</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg px-4 py-3">
				<div class="text-[10px] uppercase tracking-wider text-ink-500">Available (incl. review)</div>
				<div class="text-lg font-semibold text-brand-700 tabular-nums">{{ fmtINR(ctx.available) }}</div>
			</div>
		</div>
		<div v-else class="bg-warning-50 border border-warning-200 rounded-lg px-4 py-3 mb-4 text-sm text-warning-700 max-w-2xl">
			Your user account isn't linked to an Employee, so petty-cash spend can't be logged. Ask an administrator to set the Employee's User ID.
		</div>

		<!-- tabs -->
		<div class="border-b border-ink-200 flex mb-4 overflow-x-auto scrollbar-thin">
			<button
				v-for="t in tabs"
				:key="t.id"
				type="button"
				class="px-3 py-2 text-xs font-medium whitespace-nowrap"
				:class="activeTab === t.id ? 'text-brand-600' : 'text-ink-600 hover:text-ink-900'"
				:style="activeTab === t.id ? 'border-bottom:2px solid currentColor;margin-bottom:-1px;' : 'border-bottom:2px solid transparent;margin-bottom:-1px;'"
				@click="openTab(t.id)"
			>
				{{ t.label
				}}<span v-if="t.count !== null" class="ml-1 tabular-nums" :class="t.alert && t.count > 0 ? 'text-warning-700 font-semibold' : 'text-ink-400'">({{ t.count }})</span>
			</button>
		</div>

		<!-- entries (verify / all / mine) -->
		<div v-if="activeTab === 'verify' || activeTab === 'all' || activeTab === 'mine'" class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<table class="w-full text-xs" style="min-width: 720px">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr><th class="text-left px-3 py-2">ID</th><th class="text-left px-3 py-2">Date</th><th class="text-left px-3 py-2">Project</th><th class="text-right px-3 py-2">Amount</th><th class="text-left px-3 py-2">Status</th><th></th></tr>
				</thead>
				<tbody>
					<tr v-for="row in tableRows" :key="row.name" class="border-t border-ink-100">
						<td class="px-3 py-2 font-mono text-ink-400 text-[10px]">{{ row.name }}</td>
						<td class="px-3 py-2 text-ink-500">{{ fmtDate(row.date) }}</td>
						<td class="px-3 py-2 text-ink-500">{{ row.project }}</td>
						<td class="px-3 py-2 text-right tabular-nums font-medium text-ink-900">{{ fmtINR(row.total_amount) }}</td>
						<td class="px-3 py-2"><StatusBadge :status="statusLabel(row.docstatus)" /></td>
						<td class="px-3 py-2 text-right">
							<div class="flex justify-end gap-2">
								<button v-if="row.docstatus === 0 && canSubmit" type="button" class="text-[11px] px-2 py-0.5 border border-brand-300 bg-brand-50 text-brand-700 rounded" @click="onApprove(row)">Verify</button>
								<button v-if="row.docstatus !== 2" type="button" class="text-[11px] px-2 py-0.5 border border-ink-200 text-danger-700 rounded" @click="onCancel(row)">{{ row.docstatus === 1 ? "Cancel" : "Delete" }}</button>
							</div>
						</td>
					</tr>
					<tr v-if="!tableRows.length"><td colspan="6" class="px-3 py-8 text-center text-ink-400 italic">{{ res.loading ? "Loading…" : "Nothing here." }}</td></tr>
				</tbody>
			</table>
		</div>

		<!-- to reimburse (approvers) -->
		<div v-else-if="activeTab === 'reimburse'" class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<table class="w-full text-xs" style="min-width: 720px">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr><th class="text-left px-3 py-2">ID</th><th class="text-left px-3 py-2">Date</th><th class="text-left px-3 py-2">Employee</th><th class="text-left px-3 py-2">Project</th><th class="text-right px-3 py-2">Amount</th><th></th></tr>
				</thead>
				<tbody>
					<tr v-for="row in reimburseRows" :key="row.name" class="border-t border-ink-100">
						<td class="px-3 py-2 font-mono text-ink-400 text-[10px]">{{ row.name }}</td>
						<td class="px-3 py-2 text-ink-500">{{ fmtDate(row.date) }}</td>
						<td class="px-3 py-2 text-ink-900">{{ row.employee_name || row.employee }}</td>
						<td class="px-3 py-2 text-ink-500">{{ row.project }}</td>
						<td class="px-3 py-2 text-right tabular-nums font-medium text-ink-900">{{ fmtINR(row.total_amount) }}</td>
						<td class="px-3 py-2 text-right"><button type="button" class="text-[11px] px-2 py-0.5 border border-brand-300 bg-brand-50 text-brand-700 rounded" @click="openReimburse(row)">Reimburse</button></td>
					</tr>
					<tr v-if="reimburseRows.length" class="border-t-2 border-ink-200 font-semibold"><td colspan="4" class="px-3 py-2">Total to reimburse</td><td class="px-3 py-2 text-right tabular-nums">{{ fmtINR(reimburseTotal) }}</td><td></td></tr>
					<tr v-if="!reimburseRows.length"><td colspan="6" class="px-3 py-8 text-center text-ink-400 italic">Nothing awaiting reimbursement.</td></tr>
				</tbody>
			</table>
		</div>

		<!-- ledger -->
		<div v-else class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
			<table class="w-full text-xs" style="min-width: 720px">
				<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
					<tr><th class="text-left px-3 py-2">Date</th><th class="text-left px-3 py-2">Voucher</th><th class="text-left px-3 py-2">Project</th><th class="text-right px-3 py-2">In</th><th class="text-right px-3 py-2">Out</th><th class="text-right px-3 py-2">Balance</th></tr>
				</thead>
				<tbody>
					<tr v-for="row in ledgerRows" :key="row.name" class="border-t border-ink-100">
						<td class="px-3 py-2 text-ink-500">{{ row.posting_date }}</td>
						<td class="px-3 py-2 text-ink-700">{{ row.title }}</td>
						<td class="px-3 py-2 text-ink-500">{{ row.project || "—" }}</td>
						<td class="px-3 py-2 text-right tabular-nums text-success-700">{{ row.received ? fmtINR(row.received) : "" }}</td>
						<td class="px-3 py-2 text-right tabular-nums text-danger-700">{{ row.paid ? fmtINR(row.paid) : "" }}</td>
						<td class="px-3 py-2 text-right tabular-nums font-medium">{{ fmtINR(row.balance) }}</td>
					</tr>
					<tr v-if="!ledgerRows.length"><td colspan="6" class="px-3 py-8 text-center text-ink-400 italic">{{ ledgerLoading ? "Loading…" : "No petty-cash movements yet." }}</td></tr>
				</tbody>
			</table>
		</div>

		<!-- create modal -->
		<div v-if="form.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="form.open = false">
			<div class="bg-white rounded-lg shadow-xl w-full max-w-2xl p-5">
				<h3 class="text-sm font-semibold text-ink-900 mb-4">Log petty-cash expense</h3>
				<div class="grid grid-cols-2 gap-3 mb-3">
					<DeskField label="Project" required><DeskLinkPicker v-model="form.project" doctype="Project" label-field="project_name" value-field="name" placeholder="Pick a project…" /></DeskField>
					<DeskField label="Date"><DeskInput v-model="form.date" type="date" /></DeskField>
				</div>
				<div class="border border-ink-200 rounded-lg overflow-hidden mb-3">
					<table class="w-full text-xs">
						<thead class="bg-ink-50 text-ink-500 uppercase text-[10px]"><tr><th class="text-left px-3 py-2">Expense account</th><th class="text-left px-3 py-2 w-36">Cost type</th><th class="text-left px-3 py-2">Description</th><th class="text-right px-3 py-2 w-28">Amount</th><th class="w-8"></th></tr></thead>
						<tbody>
							<tr v-for="(r, i) in form.rows" :key="i" class="border-t border-ink-100">
								<td class="px-2 py-1.5"><DeskLinkPicker v-model="r.expense_account" doctype="Account" label-field="name" value-field="name" :filters="expenseAccountFilters" placeholder="Expense account…" /></td>
								<td class="px-2 py-1.5"><DeskSelect v-model="r.cost_type"><option v-for="c in COST_TYPES" :key="c" :value="c">{{ c }}</option></DeskSelect></td>
								<td class="px-2 py-1.5"><DeskInput v-model="r.description" placeholder="What was it for?" /></td>
								<td class="px-2 py-1.5"><DeskInput v-model.number="r.amount" type="number" min="0" class="text-right" /></td>
								<td class="px-2 py-1.5 text-center"><button type="button" class="text-ink-400 hover:text-danger-600" @click="removeRow(i)">✕</button></td>
							</tr>
						</tbody>
					</table>
				</div>
				<div class="flex items-center justify-between mb-3">
					<button type="button" class="text-xs text-brand-700 hover:underline" @click="addRow">+ Add line</button>
					<div class="text-sm">Total <span class="font-semibold text-ink-900 tabular-nums">{{ fmtINR(formTotal) }}</span></div>
				</div>
				<label class="flex items-center gap-2 text-xs text-ink-700 mb-3 cursor-pointer">
					<input v-model="form.reimbursable" type="checkbox" class="rounded border-ink-300" />
					I paid out of my own pocket — reimburse me
				</label>
				<p class="text-[11px] text-ink-500 mb-4">{{ form.reimbursable ? "Booked to Employee Reimbursements (a payable); pay it out from the To Reimburse queue." : "Paid from your Petty Cash float." }} Saved as a draft pending a finance approver.</p>
				<div class="flex justify-end gap-2">
					<button class="desk-btn" @click="form.open = false">Cancel</button>
					<button class="desk-save-btn" :disabled="form.saving" @click="submitForm">{{ form.saving ? "Saving…" : "Save" }}</button>
				</div>
			</div>
		</div>

		<!-- reimburse modal -->
		<div v-if="reimb.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="reimb.open = false">
			<div class="bg-white rounded-lg shadow-xl w-full max-w-md p-5">
				<h3 class="text-sm font-semibold text-ink-900 mb-1">Reimburse {{ fmtINR(reimb.row?.total_amount) }}</h3>
				<p class="text-xs text-ink-500 mb-4">to {{ reimb.row?.employee_name || reimb.row?.employee }} · posts a Journal Entry (Dr Employee Reimbursements / Cr the account).</p>
				<DeskField label="Pay from" required>
					<DeskLinkPicker v-model="reimb.bank" doctype="Account" label-field="name" value-field="name" :filters="reimburseAccountFilters" placeholder="Bank / Cash account…" />
				</DeskField>
				<div class="flex justify-end gap-2 mt-5">
					<button class="desk-btn" @click="reimb.open = false">Cancel</button>
					<button class="desk-save-btn" :disabled="reimb.saving" @click="confirmReimburse">{{ reimb.saving ? "Posting…" : "Reimburse" }}</button>
				</div>
			</div>
		</div>
	</DeskPage>
</template>
