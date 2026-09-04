<script setup>
// Project Finance › Expenses — a faithful port of the prototype panel, wired to
// the live Expense Entry doctype. ERPNext docstatus lifecycle: Draft → Submitted →
// Cancelled. Submit = accountant verification; only Submitted expenses hit balances
// & reports. Tabs: To Submit / All Expenses / My Expenses.
import { computed, reactive, ref } from "vue";
import FileUploadHandler from "frappe-ui-file-upload-handler";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import {
	expenseContext,
	listExpenses,
	getExpense,
	saveExpense,
	submitExpense,
	cancelExpense,
	listExpensePayAccounts,
} from "@/data/expenseEntryApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import CostCodePicker from "@/components/CostCodePicker.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { activeCompanyFilter } from "@/composables/useActiveCompany";
import { usePermissions } from "@/composables/usePermissions";
import { usePagination } from "@/composables/usePagination";
import DeskPaginationFooter from "@/components/desk/DeskPaginationFooter.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const { canCreate, canEdit, canDelete } = usePermissions();

// Every account/project/employee picker is scoped to the active (default) company. This is
// the single-company seam — see useActiveCompany. Empty pre-boot → picker unfiltered, but
// the server-side company guard still blocks a cross-company save.
const companyFilter = activeCompanyFilter();

const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Expenses" }];
const confirmDialog = useConfirm();

const ctx = ref({ employee: null, can_submit: false });
async function loadContext() {
	try {
		ctx.value = await expenseContext();
	} catch {
		/* ignore */
	}
}
loadContext();
const canLog = computed(() => !!ctx.value.employee);
const canVerify = computed(() => !!ctx.value.can_submit);

// --- data ---
const expenses = ref([]);
const loading = ref(true);
async function loadExpenses() {
	loading.value = true;
	try {
		expenses.value = await listExpenses();
	} catch (err) {
		showToast(err.message || "Failed to load expenses", "error");
	} finally {
		loading.value = false;
	}
}
loadExpenses();

function holderName(e) {
	return e.employee_name || e.employee || "—";
}
function projectName(e) {
	return e.project_name || e.project || "—";
}
function sourceChipClass(source) {
	return source === "Petty Cash" ? "bg-info-50 text-info-700" : "bg-ink-100 text-ink-600";
}

// --- tabs ---
const toSubmit = computed(() =>
	expenses.value.filter((e) => e.status === "Draft").slice().sort((a, b) => (a.date || "").localeCompare(b.date || "")),
);
const myExpensesAll = computed(() => expenses.value.filter((e) => e.employee === ctx.value.employee));
const tabs = computed(() => {
	const t = [];
	if (canVerify.value) {
		t.push({ id: "queue", label: "To Submit", count: toSubmit.value.length });
		t.push({ id: "all", label: "All Expenses" });
	}
	t.push({ id: "mine", label: "My Expenses" });
	return t;
});
const tab = ref(null);
const activeTab = computed(() => (tab.value && tabs.value.some((t) => t.id === tab.value) ? tab.value : tabs.value[0]?.id));

// --- filters (All / My) ---
const search = ref("");
const statusFilter = ref("");
const from = ref("");
const to = ref("");
const hasFilters = computed(() => search.value || statusFilter.value || from.value || to.value);
function clearFilters() {
	search.value = "";
	statusFilter.value = "";
	from.value = "";
	to.value = "";
}
function inPeriod(d) {
	return (!from.value || d >= from.value) && (!to.value || d <= to.value);
}
const allExpenses = computed(() => {
	const term = search.value.trim().toLowerCase();
	return expenses.value.filter(
		(e) =>
			(!statusFilter.value || e.status === statusFilter.value) &&
			inPeriod(e.date) &&
			(!term ||
				(e.description || "").toLowerCase().includes(term) ||
				holderName(e).toLowerCase().includes(term) ||
				projectName(e).toLowerCase().includes(term) ||
				(e.expense_account || "").toLowerCase().includes(term) ||
				e.name.toLowerCase().includes(term)),
	);
});
const myExpenses = computed(() => myExpensesAll.value.filter((e) => inPeriod(e.date)));

// Client-side pagers for the three bespoke expense tables (they render raw <table>s, not DeskList).
const toSubmitPager = usePagination(toSubmit);
const allExpensesPager = usePagination(allExpenses);
const myExpensesPager = usePagination(myExpenses);

// --- detail modal ---
const detail = ref(null);
function openDetail(e) {
	detail.value = e;
}
function closeDetail() {
	detail.value = null;
}

// --- docstatus actions ---
async function refresh() {
	await loadExpenses();
	loadContext();
	if (detail.value) detail.value = expenses.value.find((e) => e.name === detail.value.name) || null;
}
async function onSubmit(e) {
	const ok = await confirmDialog({
		title: "Submit expense?",
		message: `Submit "${e.description}" (${fmtINR(e.amount)})? Submitting posts it — it will hit the ${e.source} balance and the reports.`,
		confirmLabel: "Submit",
	});
	if (!ok) return;
	try {
		await submitExpense(e.name);
		await refresh();
		showToast("Submitted — Journal Entry posted.");
	} catch (err) {
		showToast(err.message || "Submit failed", "error");
	}
}
async function onCancel(e) {
	const ok = await confirmDialog({
		title: "Cancel expense?",
		message: `Cancel "${e.description}" (${fmtINR(e.amount)})? Its effect on balances and reports is reversed. A cancelled expense can then be deleted.`,
		confirmLabel: "Cancel expense",
		cancelLabel: "Keep",
		destructive: true,
	});
	if (!ok) return;
	try {
		await cancelExpense(e.name);
		await refresh();
		showToast("Cancelled — Journal Entry reversed.");
	} catch (err) {
		showToast(err.message || "Cancel failed", "error");
	}
}
async function onDelete(e) {
	const ok = await confirmDialog({
		title: "Delete expense?",
		message: `Permanently delete "${e.description}" (${fmtINR(e.amount)})${e.status === "Cancelled" ? " — already cancelled, no balance impact" : ""}?`,
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await cancelExpense(e.name);
		if (detail.value?.name === e.name) closeDetail();
		await refresh();
		showToast("Deleted.");
	} catch (err) {
		showToast(err.message || "Delete failed", "error");
	}
}

// --- create / edit form modal ---
const PAID_FROM = [
	{ value: "petty", label: "Petty Cash" },
	{ value: "company", label: "Company" },
];
const modalOpen = ref(false);
const editingId = ref(null);
const form = reactive({ date: "", amount: null, description: "", project: "", expense_account: "", cost_code: null, paid_from: "petty", company_account: "", employee: "", attachment: "", uploading: false, saving: false });
function resetForm() {
	Object.assign(form, { date: new Date().toISOString().slice(0, 10), amount: null, description: "", project: "", expense_account: "", cost_code: null, paid_from: "petty", company_account: "", employee: "", attachment: "", uploading: false, saving: false });
}

// Bank/Cash accounts for the Company-paid source — the active (default) company, excluding
// Petty Cash. Petty-cash spend needs no account: it Crs the holder's float.
const payAccounts = ref([]);
async function loadPayAccounts() {
	try {
		payAccounts.value = await listExpensePayAccounts();
	} catch {
		payAccounts.value = [];
	}
}
function onPaidFromChange() {
	if (form.paid_from === "company" && !payAccounts.value.length) loadPayAccounts();
}

function openNew() {
	editingId.value = null;
	resetForm();
	payAccounts.value = [];
	modalOpen.value = true;
}
async function openEdit(e) {
	editingId.value = e.name;
	resetForm();
	// The list row only carries the cost-code label; fetch the full entry so the picker
	// binds the { type, group_code, item_code, label } object and edits round-trip.
	const full = await getExpense(e.name).catch(() => null);
	const row = full?.rows?.[0] || {};
	Object.assign(form, {
		date: e.date,
		amount: e.amount,
		description: e.description,
		project: e.project,
		expense_account: row.expense_account || e.expense_account || "",
		cost_code: row.cost_code || null,
		paid_from: e.source === "Company" ? "company" : "petty",
		company_account: e.source === "Company" ? e.payment_account || "" : "",
		employee: e.employee || "",
		attachment: e.attachment || "",
	});
	closeDetail();
	if (form.paid_from === "company") loadPayAccounts();
	modalOpen.value = true;
}
async function uploadReceipt(ev) {
	const file = ev.target.files?.[0];
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
		if (ev.target) ev.target.value = "";
	}
}
async function save() {
	if (!form.description.trim()) return showToast("Description is required.", "error");
	if (!(Number(form.amount) > 0)) return showToast("Enter an amount greater than zero.", "error");
	if (!form.project) return showToast("Pick a project.", "error");
	if (!form.expense_account) return showToast("Pick an expense account.", "error");
	if (form.paid_from === "company" && !form.company_account) return showToast("Pick the company account to pay from.", "error");
	form.saving = true;
	try {
		await saveExpense({
			name: editingId.value || undefined,
			project: form.project,
			date: form.date,
			paid_from: form.paid_from,
			company_account: form.paid_from === "company" ? form.company_account : undefined,
			employee: canVerify.value && form.paid_from === "petty" ? form.employee || undefined : undefined,
			rows: [{ expense_account: form.expense_account, cost_code: form.cost_code, amount: form.amount, description: form.description, attachment: form.attachment }],
		});
		modalOpen.value = false;
		await refresh();
		showToast(editingId.value ? "Expense updated." : "Expense saved.");
	} catch (err) {
		showToast(err.message || "Failed to save", "error");
	} finally {
		form.saving = false;
	}
}

const expenseAccountFilters = computed(() => [
	["root_type", "=", "Expense"],
	["is_group", "=", 0],
	...companyFilter.value,
]);
</script>

<template>
	<DeskPage title="Expenses" :breadcrumbs="breadcrumbs">
		<div class="space-y-4">
			<div class="flex items-center justify-between gap-3">
				<div class="text-sm text-ink-600">Log site spend. It hits balances &amp; reports once <span class="font-medium">Submitted</span>.</div>
				<button v-if="canCreate('expense') && canLog" type="button" class="text-xs desk-save-btn whitespace-nowrap" @click="openNew">+ New expense</button>
			</div>

			<div v-if="canCreate('expense') && !canLog" class="bg-warning-50 border border-warning-200 rounded-lg px-4 py-3 text-sm text-warning-700">
				Your user account isn't linked to an Employee, so spend can't be logged. Ask an administrator to set the Employee's User ID.
			</div>

			<!-- Tab strip -->
			<div class="border-b border-ink-200 flex gap-4 text-xs overflow-x-auto overflow-y-hidden">
				<button
					v-for="t in tabs"
					:key="t.id"
					type="button"
					class="pb-2 -mb-px border-b-2 transition-colors whitespace-nowrap"
					:class="activeTab === t.id ? 'border-brand-600 text-brand-700 font-medium' : 'border-transparent text-ink-500 hover:text-ink-800'"
					@click="tab = t.id"
				>
					{{ t.label }}<span v-if="t.count != null" class="ml-1" :class="t.count > 0 ? 'text-warning-700 font-semibold' : 'text-ink-400'">({{ t.count }})</span>
				</button>
			</div>

			<!-- To Submit queue -->
			<section v-if="activeTab === 'queue'" class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<table v-if="toSubmit.length" class="w-full text-xs">
					<thead class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200 bg-ink-50">
						<tr><th class="text-left px-4 py-2">Date</th><th class="text-left px-4 py-2">Description</th><th class="text-left px-4 py-2">By</th><th class="text-left px-4 py-2">Source</th><th class="text-left px-4 py-2">Account</th><th class="text-right px-4 py-2">Amount</th><th class="px-4 py-2"></th></tr>
					</thead>
					<tbody>
						<tr v-for="e in toSubmitPager.pagedRows" :key="e.name" class="border-b border-ink-100 last:border-0 hover:bg-brand-50/40 cursor-pointer" @click="openDetail(e)">
							<td class="px-4 py-2.5 text-ink-500">{{ fmtDate(e.date) }}</td>
							<td class="px-4 py-2.5 text-ink-900">{{ e.description }}<span v-if="e.attachment" class="ml-1 text-ink-400">📎</span><div class="text-[10px] text-ink-400">{{ projectName(e) }}</div></td>
							<td class="px-4 py-2.5 text-ink-700"><div class="flex items-center gap-1.5"><UserAvatar :name="holderName(e)" size="xs" /><span>{{ holderName(e) }}</span></div></td>
							<td class="px-4 py-2.5"><span class="text-[10px] px-1.5 py-0.5 rounded-full whitespace-nowrap" :class="sourceChipClass(e.source)">{{ e.source }}</span></td>
							<td class="px-4 py-2.5 text-ink-600">{{ e.expense_account || e.cost_code || "—" }}</td>
							<td class="px-4 py-2.5 text-right tabular-nums font-medium text-ink-900">{{ fmtINR(e.amount) }}</td>
							<td class="px-4 py-2.5 text-right"><button type="button" class="desk-save-btn" @click.stop="onSubmit(e)">Submit</button></td>
						</tr>
					</tbody>
				</table>
				<div v-else class="px-4 py-10 text-center text-xs text-ink-400 italic">{{ loading ? "Loading…" : "No draft expenses awaiting submission." }}</div>
				<DeskPaginationFooter :pager="toSubmitPager" />
			</section>

			<!-- All Expenses -->
			<template v-else-if="activeTab === 'all'">
				<div class="flex items-center gap-2 flex-wrap">
					<input v-model="search" type="text" placeholder="Search description, holder, project, account…" class="text-xs px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400 w-72 max-w-full" />
					<select v-model="statusFilter" class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200">
						<option value="">All statuses</option>
						<option value="Draft">Draft</option>
						<option value="Submitted">Submitted</option>
						<option value="Cancelled">Cancelled</option>
					</select>
					<div class="flex items-center gap-1.5">
						<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">From</span>
						<input v-model="from" type="date" class="text-xs px-2 py-1 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200" />
						<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">To</span>
						<input v-model="to" type="date" class="text-xs px-2 py-1 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200" />
					</div>
					<button v-if="hasFilters" type="button" class="text-[11px] text-danger-600 hover:underline" @click="clearFilters">Clear filters</button>
					<span class="text-[11px] text-ink-400 ml-auto">{{ allExpenses.length }} expense{{ allExpenses.length === 1 ? "" : "s" }}</span>
				</div>
				<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<table v-if="allExpenses.length" class="w-full text-xs">
						<thead class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200 bg-ink-50">
							<tr><th class="text-left px-4 py-2">Date</th><th class="text-left px-4 py-2">Description</th><th class="text-left px-4 py-2">By</th><th class="text-left px-4 py-2">Source</th><th class="text-left px-4 py-2">Account</th><th class="text-right px-4 py-2">Amount</th><th class="text-left px-4 py-2">Status</th></tr>
						</thead>
						<tbody>
							<tr v-for="e in allExpensesPager.pagedRows" :key="e.name" class="border-b border-ink-100 last:border-0 hover:bg-brand-50/30 cursor-pointer" @click="openDetail(e)">
								<td class="px-4 py-2.5 text-ink-500">{{ fmtDate(e.date) }}</td>
								<td class="px-4 py-2.5 text-ink-900">{{ e.description }}<span v-if="e.attachment" class="ml-1 text-ink-400">📎</span><div class="text-[10px] text-ink-400">{{ projectName(e) }}</div></td>
								<td class="px-4 py-2.5 text-ink-700"><div class="flex items-center gap-1.5"><UserAvatar :name="holderName(e)" size="xs" /><span>{{ holderName(e) }}</span></div></td>
								<td class="px-4 py-2.5"><span class="text-[10px] px-1.5 py-0.5 rounded-full whitespace-nowrap" :class="sourceChipClass(e.source)">{{ e.source }}</span></td>
								<td class="px-4 py-2.5 text-ink-600">{{ e.expense_account || e.cost_code || "—" }}</td>
								<td class="px-4 py-2.5 text-right tabular-nums font-medium text-ink-900">{{ fmtINR(e.amount) }}</td>
								<td class="px-4 py-2.5"><StatusBadge :status="e.status" size="xs" /></td>
							</tr>
						</tbody>
					</table>
					<div v-else class="px-4 py-10 text-center text-xs text-ink-400 italic">No expenses match.</div>
					<DeskPaginationFooter :pager="allExpensesPager" />
				</section>
			</template>

			<!-- My Expenses -->
			<template v-else-if="activeTab === 'mine'">
				<div class="flex items-center gap-2 flex-wrap">
					<div class="flex items-center gap-1.5">
						<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">From</span>
						<input v-model="from" type="date" class="text-xs px-2 py-1 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200" />
						<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">To</span>
						<input v-model="to" type="date" class="text-xs px-2 py-1 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200" />
					</div>
					<button v-if="from || to" type="button" class="text-[11px] text-danger-600 hover:underline" @click="from = ''; to = ''">Clear</button>
					<span class="text-[11px] text-ink-400 ml-auto">{{ myExpenses.length }} expense{{ myExpenses.length === 1 ? "" : "s" }}</span>
				</div>
				<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
					<table v-if="myExpenses.length" class="w-full text-xs">
						<thead class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200 bg-ink-50">
							<tr><th class="text-left px-4 py-2">Date</th><th class="text-left px-4 py-2">Description</th><th class="text-left px-4 py-2">Project</th><th class="text-left px-4 py-2">Source</th><th class="text-left px-4 py-2">Account</th><th class="text-right px-4 py-2">Amount</th><th class="text-left px-4 py-2">Status</th></tr>
						</thead>
						<tbody>
							<tr v-for="e in myExpensesPager.pagedRows" :key="e.name" class="border-b border-ink-100 last:border-0 hover:bg-brand-50/30 cursor-pointer" @click="openDetail(e)">
								<td class="px-4 py-2.5 text-ink-500">{{ fmtDate(e.date) }}</td>
								<td class="px-4 py-2.5 text-ink-900">{{ e.description }}<span v-if="e.attachment" class="ml-1 text-ink-400">📎</span></td>
								<td class="px-4 py-2.5 text-ink-500">{{ projectName(e) }}</td>
								<td class="px-4 py-2.5"><span class="text-[10px] px-1.5 py-0.5 rounded-full whitespace-nowrap" :class="sourceChipClass(e.source)">{{ e.source }}</span></td>
								<td class="px-4 py-2.5 text-ink-600">{{ e.expense_account || e.cost_code || "—" }}</td>
								<td class="px-4 py-2.5 text-right tabular-nums font-medium text-ink-900">{{ fmtINR(e.amount) }}</td>
								<td class="px-4 py-2.5"><StatusBadge :status="e.status" size="xs" /></td>
							</tr>
						</tbody>
					</table>
					<div v-else class="px-4 py-10 text-center text-xs text-ink-400 italic">{{ loading ? "Loading…" : "You haven't logged any expenses." }}</div>
					<DeskPaginationFooter :pager="myExpensesPager" />
				</section>
			</template>

			<!-- Detail modal -->
			<div v-if="detail" class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto" @click.self="closeDetail">
				<div class="bg-white border border-ink-200 w-full max-w-lg shadow-xl rounded-xl flex flex-col" style="max-height: 88vh" @click.stop>
					<header class="px-4 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0">
						<div class="flex items-center gap-2 min-w-0">
							<h2 class="text-sm font-semibold text-ink-900 truncate">{{ detail.description }}</h2>
							<StatusBadge :status="detail.status" size="xs" />
						</div>
						<button type="button" class="text-ink-400 hover:text-ink-900 flex-shrink-0" @click="closeDetail">✕</button>
					</header>
					<div class="px-4 py-4 overflow-y-auto flex-1 space-y-4">
						<div class="flex items-center justify-between bg-ink-50 rounded-lg px-4 py-3">
							<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Amount</div>
							<div class="text-xl font-semibold text-ink-900 tabular-nums">{{ fmtINR(detail.amount) }}</div>
						</div>
						<div class="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
							<div><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Date</div><div class="text-ink-900 mt-0.5">{{ fmtDate(detail.date) }}</div></div>
							<div><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Holder</div><div class="mt-0.5 flex items-center gap-1.5"><UserAvatar :name="holderName(detail)" size="xs" /><span class="text-ink-900">{{ holderName(detail) }}</span></div></div>
							<div><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Project</div><div class="text-ink-900 mt-0.5">{{ projectName(detail) }}</div></div>
							<div><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Paid from</div><div class="mt-0.5"><span class="text-[10px] px-1.5 py-0.5 rounded-full" :class="sourceChipClass(detail.source)">{{ detail.source }}</span></div></div>
							<div><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Expense account</div><div class="text-ink-900 mt-0.5">{{ detail.expense_account || "—" }}</div></div>
							<div><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Cost code</div><div class="text-ink-900 mt-0.5">{{ detail.cost_code || "—" }}</div></div>
						</div>
						<div>
							<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1.5">Receipt</div>
							<a v-if="detail.attachment" :href="detail.attachment" target="_blank" rel="noopener" class="text-xs text-brand-700 hover:underline">View receipt</a>
							<div v-else class="text-xs text-ink-400 italic">No receipt attached.</div>
						</div>
						<div v-if="detail.status === 'Cancelled'" class="px-3 py-2 bg-danger-50 border border-danger-200 rounded-md text-[11px] text-danger-700">
							Cancelled — this expense no longer affects balances or reports. It can be deleted.
						</div>
					</div>
					<footer class="px-4 py-3 border-t border-ink-200 flex items-center justify-between gap-2 flex-shrink-0">
						<div class="flex items-center gap-2">
							<button v-if="(detail.status === 'Draft' || (detail.status === 'Cancelled' && canVerify)) && canDelete('expense')" type="button" class="text-xs px-2.5 py-1.5 text-danger-600 hover:underline" @click="onDelete(detail)">Delete</button>
						</div>
						<div class="flex items-center gap-2">
							<button type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md" @click="closeDetail">Close</button>
							<button v-if="detail.status === 'Draft' && canEdit('expense')" type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md" @click="openEdit(detail)">Edit</button>
							<button v-if="detail.status === 'Draft' && canVerify" type="button" class="text-xs desk-save-btn" @click="onSubmit(detail)">Submit</button>
							<button v-if="detail.status === 'Submitted' && canVerify" type="button" class="text-xs px-3 py-1.5 border border-warning-300 bg-warning-50 hover:bg-warning-100 text-warning-700 font-medium rounded-md" @click="onCancel(detail)">Cancel</button>
						</div>
					</footer>
				</div>
			</div>

			<!-- Create / edit form modal -->
			<div v-if="modalOpen" class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto" @click.self="modalOpen = false">
				<div class="bg-white border border-ink-200 w-full max-w-lg shadow-xl rounded-xl" @click.stop>
					<header class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"><h2 class="text-sm font-semibold text-ink-900">{{ editingId ? "Edit expense" : "New expense" }}</h2><button type="button" class="text-ink-400 hover:text-ink-900" @click="modalOpen = false">✕</button></header>
					<div class="px-4 py-4 space-y-3">
						<div class="grid grid-cols-2 gap-3">
							<DeskField label="Date"><DeskInput v-model="form.date" type="date" /></DeskField>
							<DeskField label="Amount" required><DeskInput v-model.number="form.amount" type="number" min="0" placeholder="0" /></DeskField>
						</div>
						<DeskField label="Description" required><DeskInput v-model="form.description" placeholder="What was bought?" /></DeskField>
						<DeskField label="Project" required><DeskLinkPicker v-model="form.project" doctype="Project" label-field="project_name" value-field="name" :filters="companyFilter" placeholder="Pick a project…" /></DeskField>
						<div class="grid grid-cols-2 gap-3">
							<DeskField label="Expense account" required><DeskLinkPicker v-model="form.expense_account" doctype="Account" label-field="name" value-field="name" :filters="expenseAccountFilters" placeholder="Pick an account…" /></DeskField>
							<DeskField label="Cost code">
								<CostCodePicker v-model="form.cost_code" :project-id="form.project" placeholder="— Pick cost code —" />
							</DeskField>
						</div>
						<div class="grid grid-cols-2 gap-3">
							<DeskField label="Paid from">
								<DeskSelect v-model="form.paid_from" @update:model-value="onPaidFromChange"><option v-for="p in PAID_FROM" :key="p.value" :value="p.value">{{ p.label }}</option></DeskSelect>
							</DeskField>
							<DeskField v-if="form.paid_from === 'company'" label="Company account" required>
								<DeskSelect v-model="form.company_account">
									<option value="" disabled>Pick an account…</option>
									<option v-for="a in payAccounts" :key="a.name" :value="a.name">{{ a.name }}</option>
								</DeskSelect>
							</DeskField>
						</div>
						<DeskField v-if="canVerify && form.paid_from === 'petty'" label="Holder (petty cash float)">
							<DeskLinkPicker v-model="form.employee" doctype="Employee" label-field="employee_name" value-field="name" :filters="companyFilter" placeholder="Defaults to you…" />
						</DeskField>
						<p v-if="form.paid_from === 'petty'" class="text-[11px] text-ink-500 -mt-1">
							Paid from the holder's petty-cash float. If they fronted the money themselves, this simply pushes their balance negative — the amount owed back to them, settled on the next disbursement.
						</p>
						<DeskField label="Receipt (optional)">
							<label class="inline-flex items-center gap-2 text-xs cursor-pointer px-2.5 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 rounded-md" :class="form.attachment ? 'text-success-700' : 'text-ink-700'">
								{{ form.uploading ? "Uploading…" : form.attachment ? "✓ Receipt attached" : "📷 Attach receipt" }}
								<input type="file" class="hidden" accept="image/*,application/pdf" @change="uploadReceipt($event)" />
							</label>
						</DeskField>
					</div>
					<footer class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2">
						<button type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md" @click="modalOpen = false">Cancel</button>
						<button type="button" class="text-xs desk-save-btn" :disabled="form.saving" @click="save">{{ form.saving ? "Saving…" : editingId ? "Save" : "Save as draft" }}</button>
					</footer>
				</div>
			</div>
		</div>
	</DeskPage>
</template>

<style scoped>
/* CTA buttons read black-on-green in dark mode (prototype). The shared .desk-save-btn is
   green-bg/white-text in dark; scope the black text to this view for now. */
html.dark .desk-save-btn {
	color: #0f172a;
}
</style>
