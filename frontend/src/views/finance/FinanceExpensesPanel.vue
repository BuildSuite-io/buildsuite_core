<script setup>
// Project Finance › Expenses — LIVE. The signed-in holder logs spend against their
// petty-cash float as an Expense Entry (draft = pending approval); a finance approver
// approves it, posting the Journal Entry. Balances + ledger come from the employee
// petty-cash ledger (buildsuite_core.utils.petty_cash).
import { computed, reactive, ref } from "vue";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { useDocTypeList } from "@/composables/useDocTypeList";
import FileUploadHandler from "frappe-ui-file-upload-handler";
import {
	expenseContext,
	getExpense,
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

// --- detail modal ---
const detail = reactive({ open: false, loading: false, doc: null });
async function openDetail(name) {
	Object.assign(detail, { open: true, loading: true, doc: null });
	try {
		detail.doc = await getExpense(name);
	} catch (err) {
		showToast(err.message || "Failed to load entry", "error");
		detail.open = false;
	} finally {
		detail.loading = false;
	}
}
function detailApprove() {
	const d = detail.doc;
	detail.open = false;
	onApprove(d);
}
function detailCancel() {
	const d = detail.doc;
	detail.open = false;
	onCancel(d);
}
function detailReimburse() {
	const d = detail.doc;
	detail.open = false;
	openReimburse(d);
}

function openTab(t) {
	tab.value = t;
	if (t === "ledger" && !ledgerRows.value.length) loadLedger();
	if (t === "reimburse") loadReimburse();
}

// --- create modal ---
// One expense per record (matches the prototype's single-expense form).
const COST_TYPES = ["Material", "Labour", "Plant & Machinery", "Subcontract", "Overhead"];
const PAID_FROM = [
	{ value: "petty", label: "Petty Cash float" },
	{ value: "own", label: "My own pocket (reimburse me)" },
];
const blankForm = () => ({
	open: false,
	date: new Date().toISOString().slice(0, 10),
	amount: 0,
	description: "",
	project: "",
	expense_account: "",
	cost_type: "Overhead",
	paid_from: "petty",
	attachment: "",
	uploading: false,
	saving: false,
});
const form = reactive(blankForm());
function openForm() {
	Object.assign(form, blankForm(), { open: true });
}
async function uploadReceipt(e) {
	const file = e.target.files?.[0];
	if (!file) return;
	form.uploading = true;
	try {
		const handler = new FileUploadHandler();
		const r = await handler.upload(file, { private: true });
		const url = r?.file_url || r?.message?.file_url || "";
		if (!url) throw new Error("no url");
		form.attachment = url;
		showToast("Receipt attached.");
	} catch {
		showToast("Upload failed.", "error");
	} finally {
		form.uploading = false;
		if (e.target) e.target.value = "";
	}
}
async function submitForm() {
	if (!form.description.trim()) return showToast("Enter a description.", "error");
	if (!(Number(form.amount) > 0)) return showToast("Enter an amount.", "error");
	if (!form.project) return showToast("Pick a project.", "error");
	if (!form.expense_account) return showToast("Pick an expense account.", "error");
	form.saving = true;
	try {
		await saveExpense({
			project: form.project,
			date: form.date,
			reimbursable: form.paid_from === "own",
			rows: [
				{
					expense_account: form.expense_account,
					cost_type: form.cost_type,
					amount: form.amount,
					description: form.description,
					attachment: form.attachment,
				},
			],
		});
		form.open = false;
		res.reload?.();
		loadContext();
		showToast("Expense saved — pending approval.");
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
			<button type="button" class="desk-save-btn" :disabled="!hasEmployee" @click="openForm">+ New expense</button>
		</template>

		<p class="text-sm text-ink-600 mb-4">Log site spend. It hits balances once <span class="font-medium text-ink-700">verified</span>.</p>
		<div v-if="!hasEmployee" class="bg-warning-50 border border-warning-200 rounded-lg px-4 py-3 mb-4 text-sm text-warning-700 max-w-2xl">
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
					<tr v-for="row in tableRows" :key="row.name" class="border-t border-ink-100 hover:bg-brand-50/30 cursor-pointer" @click="openDetail(row.name)">
						<td class="px-3 py-2 font-mono text-ink-400 text-[10px]">{{ row.name }}</td>
						<td class="px-3 py-2 text-ink-500">{{ fmtDate(row.date) }}</td>
						<td class="px-3 py-2 text-ink-500">{{ row.project }}</td>
						<td class="px-3 py-2 text-right tabular-nums font-medium text-ink-900">{{ fmtINR(row.total_amount) }}</td>
						<td class="px-3 py-2"><StatusBadge :status="statusLabel(row.docstatus)" /></td>
						<td class="px-3 py-2 text-right">
							<div class="flex justify-end gap-2">
								<button v-if="row.docstatus === 0 && canSubmit" type="button" class="text-[11px] px-2 py-0.5 border border-brand-300 bg-brand-50 text-brand-700 rounded" @click.stop="onApprove(row)">Verify</button>
								<button v-if="row.docstatus !== 2" type="button" class="text-[11px] px-2 py-0.5 border border-ink-200 text-danger-700 rounded" @click.stop="onCancel(row)">{{ row.docstatus === 1 ? "Cancel" : "Delete" }}</button>
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

		<!-- create modal — one expense, matching the prototype's New expense form -->
		<div v-if="form.open" class="fixed inset-0 z-50 flex items-start justify-center bg-black/30 p-6 overflow-y-auto" @click.self="form.open = false">
			<div class="bg-white rounded-lg shadow-xl w-full max-w-lg p-5">
				<h3 class="text-sm font-semibold text-ink-900 mb-4">New expense</h3>
				<div class="grid grid-cols-2 gap-3">
					<DeskField label="Date"><DeskInput v-model="form.date" type="date" /></DeskField>
					<DeskField label="Amount" required><DeskInput v-model.number="form.amount" type="number" min="0" placeholder="0" /></DeskField>
				</div>
				<DeskField label="Description" required class="mt-3"><DeskInput v-model="form.description" placeholder="What was bought?" /></DeskField>
				<DeskField label="Project" required class="mt-3"><DeskLinkPicker v-model="form.project" doctype="Project" label-field="project_name" value-field="name" placeholder="Pick a project…" /></DeskField>
				<div class="grid grid-cols-2 gap-3 mt-3">
					<DeskField label="Expense account" required><DeskLinkPicker v-model="form.expense_account" doctype="Account" label-field="name" value-field="name" :filters="expenseAccountFilters" placeholder="Pick an account…" /></DeskField>
					<DeskField label="Cost type"><DeskSelect v-model="form.cost_type"><option v-for="c in COST_TYPES" :key="c" :value="c">{{ c }}</option></DeskSelect></DeskField>
				</div>
				<DeskField label="Paid from" class="mt-3">
					<DeskSelect v-model="form.paid_from"><option v-for="p in PAID_FROM" :key="p.value" :value="p.value">{{ p.label }}</option></DeskSelect>
				</DeskField>
				<DeskField label="Receipt (optional)" class="mt-3">
					<label class="inline-flex items-center gap-2 text-xs cursor-pointer px-2.5 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 rounded-md" :class="form.attachment ? 'text-success-700' : 'text-ink-700'">
						{{ form.uploading ? "Uploading…" : form.attachment ? "✓ Receipt attached" : "Attach receipt" }}
						<input type="file" class="hidden" accept="image/*,application/pdf" @change="uploadReceipt($event)" />
					</label>
				</DeskField>
				<p class="text-[11px] text-ink-500 mt-4 mb-4">{{ form.paid_from === "own" ? "Booked to Employee Reimbursements; pay it out from the To Reimburse queue." : "Paid from your Petty Cash float." }} Saved as a draft pending a finance approver.</p>
				<div class="flex justify-end gap-2">
					<button class="desk-btn" @click="form.open = false">Cancel</button>
					<button class="desk-save-btn" :disabled="form.saving" @click="submitForm">{{ form.saving ? "Saving…" : "Save as draft" }}</button>
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

		<!-- detail modal -->
		<div v-if="detail.open" class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" @click.self="detail.open = false">
			<div class="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[85vh] overflow-y-auto">
				<div class="flex items-center gap-2 px-5 py-3 border-b border-ink-200 sticky top-0 bg-white">
					<span class="font-mono text-xs text-ink-500">{{ detail.doc?.name || "" }}</span>
					<StatusBadge v-if="detail.doc" :status="statusLabel(detail.doc.docstatus)" />
					<span v-if="detail.doc?.reimbursable" class="text-[9px] px-1 py-0.5 bg-info-50 text-info-700 font-medium uppercase tracking-wider" style="border-radius: 2px">{{ detail.doc.reimbursed ? "Reimbursed" : "Out of pocket" }}</span>
					<button type="button" class="ml-auto text-ink-400 hover:text-ink-900" @click="detail.open = false">✕</button>
				</div>

				<div v-if="detail.loading" class="px-5 py-10 text-center text-ink-400 text-sm">Loading…</div>
				<div v-else-if="detail.doc" class="px-5 py-4">
					<div class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4 text-xs">
						<div><div class="text-[10px] uppercase tracking-wider text-ink-500">Date</div><div class="text-ink-900 mt-0.5">{{ fmtDate(detail.doc.date) }}</div></div>
						<div><div class="text-[10px] uppercase tracking-wider text-ink-500">Project</div><div class="text-ink-900 mt-0.5">{{ detail.doc.project }}</div></div>
						<div><div class="text-[10px] uppercase tracking-wider text-ink-500">Employee</div><div class="text-ink-900 mt-0.5">{{ detail.doc.employee_name || detail.doc.employee }}</div></div>
						<div><div class="text-[10px] uppercase tracking-wider text-ink-500">Paid from</div><div class="text-ink-900 mt-0.5">{{ detail.doc.payment_account }}</div></div>
						<div><div class="text-[10px] uppercase tracking-wider text-ink-500">Total</div><div class="text-ink-900 mt-0.5 tabular-nums font-medium">{{ fmtINR(detail.doc.total_amount) }}</div></div>
						<div v-if="detail.doc.reimbursed_on"><div class="text-[10px] uppercase tracking-wider text-ink-500">Reimbursed</div><div class="text-ink-900 mt-0.5">{{ fmtDate(detail.doc.reimbursed_on) }}</div></div>
					</div>

					<div class="border border-ink-200 rounded-lg overflow-x-auto mb-3">
						<table class="w-full text-xs">
							<thead class="bg-ink-50 text-ink-500 uppercase text-[10px]"><tr><th class="text-left px-3 py-2">Expense account</th><th class="text-left px-3 py-2">Cost type</th><th class="text-left px-3 py-2">Description</th><th class="text-right px-3 py-2">Amount</th><th class="text-center px-3 py-2">Receipt</th></tr></thead>
							<tbody>
								<tr v-for="(r, i) in detail.doc.rows" :key="i" class="border-t border-ink-100">
									<td class="px-3 py-2 text-ink-900">{{ r.expense_account }}</td>
									<td class="px-3 py-2 text-ink-600">{{ r.cost_type }}</td>
									<td class="px-3 py-2 text-ink-500">{{ r.description || "—" }}</td>
									<td class="px-3 py-2 text-right tabular-nums">{{ fmtINR(r.amount) }}</td>
									<td class="px-3 py-2 text-center"><a v-if="r.attachment" :href="r.attachment" target="_blank" rel="noopener" class="text-brand-700 hover:underline">View</a><span v-else class="text-ink-300">—</span></td>
								</tr>
							</tbody>
						</table>
					</div>

					<div v-if="detail.doc.journal_entry || detail.doc.reimbursement_journal_entry" class="text-[11px] text-ink-500 space-x-3 mb-1">
						<span v-if="detail.doc.journal_entry">Posting JE: <span class="font-mono text-ink-700">{{ detail.doc.journal_entry }}</span></span>
						<span v-if="detail.doc.reimbursement_journal_entry">Reimbursement JE: <span class="font-mono text-ink-700">{{ detail.doc.reimbursement_journal_entry }}</span></span>
					</div>
				</div>

				<div v-if="detail.doc" class="flex items-center justify-end gap-2 px-5 py-3 border-t border-ink-200 sticky bottom-0 bg-white">
					<button v-if="detail.doc.docstatus === 0 && canSubmit" type="button" class="text-xs px-3 py-1.5 border border-brand-300 bg-brand-50 text-brand-700 rounded" @click="detailApprove">Verify</button>
					<button v-if="detail.doc.docstatus === 1 && detail.doc.reimbursable && !detail.doc.reimbursed && canSubmit" type="button" class="text-xs px-3 py-1.5 border border-brand-300 bg-brand-50 text-brand-700 rounded" @click="detailReimburse">Reimburse</button>
					<button v-if="detail.doc.docstatus !== 2" type="button" class="text-xs px-3 py-1.5 border border-ink-200 text-danger-700 rounded" @click="detailCancel">{{ detail.doc.docstatus === 1 ? "Cancel" : "Delete" }}</button>
					<button type="button" class="desk-btn" @click="detail.open = false">Close</button>
				</div>
			</div>
		</div>
	</DeskPage>
</template>
