<script setup>
// Project Finance › Invoices — LIVE over ERPNext Sales Invoice (money in). An invoice IS a
// Sales Invoice: create a draft, submit (posts the receivable), and receive payments (a real
// Payment Entry into a Bank/Cash account). docstatus lifecycle: Draft → Submitted → Cancelled.
import { computed, reactive, ref } from "vue";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import {
	listInvoices,
	saveInvoice,
	submitInvoice,
	cancelInvoice,
	deleteInvoice,
	recordInvoiceReceipt,
	listDepositAccounts,
	listInvoiceTaxTemplates,
	listInvoicePaymentModes,
} from "@/data/invoiceApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { activeCompanyFilter } from "@/composables/useActiveCompany";
import { fmtDate, fmtINR } from "@/utils/format";

const breadcrumbs = [{ label: "Project Finance", to: "/project-finance" }, { label: "Invoices" }];
const confirmDialog = useConfirm();
const companyFilter = activeCompanyFilter();

const invoices = ref([]);
const loading = ref(true);
async function load() {
	loading.value = true;
	try {
		invoices.value = await listInvoices();
	} catch (err) {
		showToast(err.message || "Failed to load invoices", "error");
	} finally {
		loading.value = false;
	}
}
load();

const totalOutstanding = computed(() => invoices.value.reduce((a, i) => a + (Number(i.outstanding) || 0), 0));

// --- aging (submitted + still owed) ---
function daysOverdue(due) {
	if (!due) return 0;
	return Math.floor((Date.now() - new Date(due).getTime()) / 86400000);
}
function aging(inv) {
	if (inv.docstatus !== 1 || !(Number(inv.outstanding) > 0.01)) return null;
	const d = daysOverdue(inv.due_date);
	if (d <= 0) return { label: "Not due", cls: "bg-ink-100 text-ink-500" };
	const bucket = d <= 30 ? "0–30" : d <= 60 ? "31–60" : d <= 90 ? "61–90" : "90+";
	const cls = d <= 30 ? "bg-warning-50 text-warning-700" : "bg-danger-50 text-danger-700";
	return { label: `${bucket} d`, cls };
}

// --- filters ---
const search = ref("");
const statusFilter = ref("");
const hasFilters = computed(() => search.value || statusFilter.value);
function clearFilters() {
	search.value = "";
	statusFilter.value = "";
}
const rows = computed(() => {
	const term = search.value.trim().toLowerCase();
	return invoices.value.filter(
		(i) =>
			(!statusFilter.value || i.status === statusFilter.value) &&
			(!term ||
				i.name.toLowerCase().includes(term) ||
				(i.customer_name || "").toLowerCase().includes(term) ||
				(i.project_name || "").toLowerCase().includes(term)),
	);
});

// --- create form ---
const modalOpen = ref(false);
const taxTemplates = ref([]);
const form = reactive({ customer: "", project: "", date: "", due_date: "", taxes_and_charges: "", lines: [], saving: false });
function newLine() {
	return { description: "", qty: 1, rate: null };
}
async function openNew() {
	Object.assign(form, {
		customer: "",
		project: "",
		date: new Date().toISOString().slice(0, 10),
		due_date: "",
		taxes_and_charges: "",
		lines: [newLine()],
		saving: false,
	});
	modalOpen.value = true;
	if (!taxTemplates.value.length) {
		try {
			taxTemplates.value = await listInvoiceTaxTemplates();
		} catch {
			/* optional */
		}
	}
}
const formSubtotal = computed(() => form.lines.reduce((a, l) => a + (Number(l.qty) || 0) * (Number(l.rate) || 0), 0));
async function save() {
	if (!form.customer) return showToast("Pick a customer.", "error");
	const lines = form.lines.filter((l) => Number(l.rate) > 0);
	if (!lines.length) return showToast("Add at least one line with an amount.", "error");
	form.saving = true;
	try {
		await saveInvoice({
			customer: form.customer,
			project: form.project || undefined,
			date: form.date,
			due_date: form.due_date || undefined,
			taxes_and_charges: form.taxes_and_charges || undefined,
			items: lines.map((l) => ({ description: l.description, qty: Number(l.qty) || 1, rate: Number(l.rate) })),
		});
		modalOpen.value = false;
		await load();
		showToast("Invoice saved as draft.");
	} catch (err) {
		showToast(err.message || "Failed to save", "error");
	} finally {
		form.saving = false;
	}
}

// --- docstatus actions ---
async function onSubmit(inv) {
	const ok = await confirmDialog({
		title: "Submit invoice?",
		message: `Submit ${inv.name} (${fmtINR(inv.total)})? It posts the receivable and can then be paid.`,
		confirmLabel: "Submit",
	});
	if (!ok) return;
	try {
		await submitInvoice(inv.name);
		await load();
		showToast("Submitted.");
	} catch (err) {
		showToast(err.message || "Submit failed", "error");
	}
}
async function onCancel(inv) {
	const ok = await confirmDialog({
		title: "Cancel invoice?",
		message: `Cancel ${inv.name}? Its receivable and any allocations are reversed.`,
		confirmLabel: "Cancel invoice",
		cancelLabel: "Keep",
		destructive: true,
	});
	if (!ok) return;
	try {
		await cancelInvoice(inv.name);
		await load();
		showToast("Cancelled.");
	} catch (err) {
		showToast(err.message || "Cancel failed", "error");
	}
}
async function onDelete(inv) {
	const ok = await confirmDialog({ title: "Delete draft?", message: `Permanently delete ${inv.name}?`, confirmLabel: "Delete", destructive: true });
	if (!ok) return;
	try {
		await deleteInvoice(inv.name);
		await load();
		showToast("Deleted.");
	} catch (err) {
		showToast(err.message || "Delete failed", "error");
	}
}

// --- receive payment ---
const rec = reactive({ open: false, inv: null, amount: null, deposit_to: "", date: "", mode_of_payment: "", reference_no: "", saving: false });
const depositAccounts = ref([]);
const payModes = ref([]);
async function openReceive(inv) {
	if (!depositAccounts.value.length) {
		try {
			[depositAccounts.value, payModes.value] = await Promise.all([listDepositAccounts(), listInvoicePaymentModes()]);
		} catch {
			/* fall through */
		}
	}
	Object.assign(rec, {
		open: true,
		inv,
		amount: Number(inv.outstanding) || null,
		deposit_to: depositAccounts.value.find((a) => a.account_type === "Bank")?.name || depositAccounts.value[0]?.name || "",
		date: new Date().toISOString().slice(0, 10),
		mode_of_payment: payModes.value[0] || "",
		reference_no: "",
		saving: false,
	});
}
async function saveReceive() {
	const amt = Number(rec.amount) || 0;
	if (amt <= 0) return showToast("Enter an amount greater than zero.", "error");
	if (amt > Number(rec.inv.outstanding) + 0.01) return showToast(`Can't exceed the outstanding ${fmtINR(rec.inv.outstanding)}.`, "error");
	if (!rec.deposit_to) return showToast("Pick the account to deposit into.", "error");
	rec.saving = true;
	try {
		await recordInvoiceReceipt({
			name: rec.inv.name,
			amount: amt,
			date: rec.date,
			mode_of_payment: rec.mode_of_payment || undefined,
			deposit_to: rec.deposit_to,
			reference_no: rec.reference_no || undefined,
		});
		rec.open = false;
		await load();
		showToast("Payment received.");
	} catch (err) {
		showToast(err.message || "Receipt failed", "error");
	} finally {
		rec.saving = false;
	}
}
</script>

<template>
	<DeskPage title="Invoices" :breadcrumbs="breadcrumbs">
		<template #actions><button type="button" class="desk-save-btn" @click="openNew">+ New invoice</button></template>

		<div class="space-y-4">
			<div class="flex items-center gap-4 text-sm">
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md">
					<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Outstanding receivable</div>
					<div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">{{ fmtINR(totalOutstanding) }}</div>
				</div>
			</div>

			<!-- filters -->
			<div class="flex items-center gap-2 flex-wrap">
				<input v-model="search" type="text" placeholder="Search invoice, customer, project…" class="text-xs px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400 w-72 max-w-full" />
				<select v-model="statusFilter" class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200">
					<option value="">All statuses</option>
					<option value="Draft">Draft</option>
					<option value="Unpaid">Unpaid</option>
					<option value="Partly Paid">Partly Paid</option>
					<option value="Paid">Paid</option>
					<option value="Cancelled">Cancelled</option>
				</select>
				<button v-if="hasFilters" type="button" class="text-[11px] text-danger-600 hover:underline" @click="clearFilters">Clear filters</button>
				<span class="text-[11px] text-ink-400 ml-auto">{{ rows.length }} invoice{{ rows.length === 1 ? "" : "s" }}</span>
			</div>

			<section class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
				<table v-if="rows.length" class="w-full text-xs" style="min-width: 760px">
					<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-200">
						<tr><th class="text-left px-3 py-2">Invoice</th><th class="text-left px-3 py-2">Customer</th><th class="text-left px-3 py-2">Project</th><th class="text-left px-3 py-2">Date</th><th class="text-left px-3 py-2">Due</th><th class="text-left px-3 py-2">Aging</th><th class="text-right px-3 py-2">Total</th><th class="text-right px-3 py-2">Outstanding</th><th class="text-left px-3 py-2">Status</th><th class="px-3 py-2"></th></tr>
					</thead>
					<tbody>
						<tr v-for="i in rows" :key="i.name" class="border-t border-ink-100 hover:bg-brand-50/30">
							<td class="px-3 py-2 font-mono text-[11px] text-ink-500">{{ i.name }}</td>
							<td class="px-3 py-2 text-ink-900">{{ i.customer_name }}</td>
							<td class="px-3 py-2 text-ink-500">{{ i.project_name || "—" }}</td>
							<td class="px-3 py-2 text-ink-500 whitespace-nowrap">{{ fmtDate(i.date) }}</td>
							<td class="px-3 py-2 text-ink-500 whitespace-nowrap">{{ fmtDate(i.due_date) }}</td>
							<td class="px-3 py-2"><span v-if="aging(i)" class="text-[10px] px-1.5 py-0.5 rounded-full whitespace-nowrap" :class="aging(i).cls">{{ aging(i).label }}</span><span v-else class="text-ink-300">—</span></td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900">{{ fmtINR(i.total) }}</td>
							<td class="px-3 py-2 text-right tabular-nums font-medium" :class="i.outstanding > 0.01 ? 'text-ink-900' : 'text-ink-400'">{{ fmtINR(i.outstanding) }}</td>
							<td class="px-3 py-2"><StatusBadge :status="i.status" size="xs" /></td>
							<td class="px-3 py-2 text-right whitespace-nowrap">
								<button v-if="i.docstatus === 0" type="button" class="text-[11px] px-2 py-0.5 border border-brand-300 bg-brand-50 text-brand-700 rounded" @click="onSubmit(i)">Submit</button>
								<button v-if="i.docstatus === 0" type="button" class="text-[11px] px-2 py-0.5 ml-1 text-danger-600 hover:underline" @click="onDelete(i)">Delete</button>
								<button v-if="i.docstatus === 1 && i.outstanding > 0.01" type="button" class="text-[11px] px-2 py-0.5 border border-brand-300 bg-brand-50 text-brand-700 rounded" @click="openReceive(i)">Receive</button>
								<button v-if="i.docstatus === 1" type="button" class="text-[11px] px-2 py-0.5 ml-1 border border-warning-300 bg-warning-50 text-warning-700 rounded" @click="onCancel(i)">Cancel</button>
							</td>
						</tr>
					</tbody>
				</table>
				<div v-else class="px-4 py-12 text-center text-xs text-ink-400 italic">{{ loading ? "Loading…" : "No invoices yet." }}</div>
			</section>
		</div>

		<!-- New invoice modal -->
		<div v-if="modalOpen" class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto" @click.self="modalOpen = false">
			<div class="bg-white border border-ink-200 w-full max-w-2xl shadow-xl rounded-xl" @click.stop>
				<header class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"><h2 class="text-sm font-semibold text-ink-900">New invoice</h2><button type="button" class="text-ink-400 hover:text-ink-900" @click="modalOpen = false">✕</button></header>
				<div class="px-4 py-4 space-y-3">
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Customer" required><DeskLinkPicker v-model="form.customer" doctype="Customer" label-field="customer_name" value-field="name" placeholder="Pick a customer…" /></DeskField>
						<DeskField label="Project"><DeskLinkPicker v-model="form.project" doctype="Project" label-field="project_name" value-field="name" :filters="companyFilter" placeholder="Optional…" /></DeskField>
					</div>
					<div class="grid grid-cols-3 gap-3">
						<DeskField label="Date"><DeskInput v-model="form.date" type="date" /></DeskField>
						<DeskField label="Due date"><DeskInput v-model="form.due_date" type="date" /></DeskField>
						<DeskField label="Tax"><DeskSelect v-model="form.taxes_and_charges"><option value="">No tax</option><option v-for="t in taxTemplates" :key="t.name" :value="t.name">{{ t.title || t.name }}</option></DeskSelect></DeskField>
					</div>

					<div class="border border-ink-200 rounded-lg overflow-hidden">
						<table class="w-full text-xs">
							<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]"><tr><th class="text-left px-3 py-2">Description</th><th class="text-right px-3 py-2 w-16">Qty</th><th class="text-right px-3 py-2 w-28">Rate</th><th class="text-right px-3 py-2 w-28">Amount</th><th class="w-8"></th></tr></thead>
							<tbody>
								<tr v-for="(l, idx) in form.lines" :key="idx" class="border-t border-ink-100">
									<td class="px-2 py-1"><input v-model="l.description" type="text" placeholder="What is billed?" class="w-full px-1.5 py-1 border border-transparent hover:border-ink-200 focus:border-brand-400 rounded focus:outline-none" /></td>
									<td class="px-2 py-1"><input v-model.number="l.qty" type="number" min="0" class="w-full text-right px-1.5 py-1 border border-transparent hover:border-ink-200 focus:border-brand-400 rounded focus:outline-none tabular-nums" /></td>
									<td class="px-2 py-1"><input v-model.number="l.rate" type="number" min="0" placeholder="0" class="w-full text-right px-1.5 py-1 border border-transparent hover:border-ink-200 focus:border-brand-400 rounded focus:outline-none tabular-nums" /></td>
									<td class="px-3 py-1 text-right tabular-nums text-ink-700">{{ fmtINR((Number(l.qty) || 0) * (Number(l.rate) || 0)) }}</td>
									<td class="px-2 py-1 text-center"><button v-if="form.lines.length > 1" type="button" class="text-ink-400 hover:text-danger-600" @click="form.lines.splice(idx, 1)">✕</button></td>
								</tr>
							</tbody>
							<tfoot>
								<tr class="border-t border-ink-200 bg-ink-50/40">
									<td colspan="3" class="px-3 py-2"><button type="button" class="text-[11px] text-brand-700 hover:underline" @click="form.lines.push(newLine())">+ Add line</button></td>
									<td class="px-3 py-2 text-right tabular-nums font-semibold text-ink-900">{{ fmtINR(formSubtotal) }}</td>
									<td></td>
								</tr>
							</tfoot>
						</table>
					</div>
					<p class="text-[11px] text-ink-400">Any tax is applied on save; the subtotal above is before tax.</p>
				</div>
				<footer class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2">
					<button type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md" @click="modalOpen = false">Cancel</button>
					<button type="button" class="text-xs desk-save-btn" :disabled="form.saving" @click="save">{{ form.saving ? "Saving…" : "Save as draft" }}</button>
				</footer>
			</div>
		</div>

		<!-- Receive payment modal -->
		<div v-if="rec.open" class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto" @click.self="rec.open = false">
			<div class="bg-white border border-ink-200 w-full max-w-md shadow-xl rounded-xl" @click.stop>
				<header class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"><h2 class="text-sm font-semibold text-ink-900">Receive payment</h2><button type="button" class="text-ink-400 hover:text-ink-900" @click="rec.open = false">✕</button></header>
				<div class="px-4 py-4 space-y-3">
					<div class="text-sm text-ink-700">From <span class="font-medium">{{ rec.inv?.customer_name }}</span> against <span class="font-mono text-xs">{{ rec.inv?.name }}</span>. Outstanding <span class="font-semibold text-ink-900 tabular-nums">{{ fmtINR(rec.inv?.outstanding) }}</span>.</div>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Amount" required><DeskInput v-model.number="rec.amount" type="number" min="0" /></DeskField>
						<DeskField label="Date"><DeskInput v-model="rec.date" type="date" /></DeskField>
					</div>
					<DeskField label="Deposit into" required>
						<DeskSelect v-model="rec.deposit_to"><option value="" disabled>Bank / Cash account…</option><option v-for="a in depositAccounts" :key="a.name" :value="a.name">{{ a.name }} ({{ a.account_type }})</option></DeskSelect>
					</DeskField>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Mode of payment"><DeskSelect v-model="rec.mode_of_payment"><option value="">—</option><option v-for="m in payModes" :key="m" :value="m">{{ m }}</option></DeskSelect></DeskField>
						<DeskField label="Reference no."><DeskInput v-model="rec.reference_no" placeholder="UTR / cheque no." /></DeskField>
					</div>
				</div>
				<footer class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2">
					<button type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md" @click="rec.open = false">Cancel</button>
					<button type="button" class="text-xs desk-save-btn" :disabled="rec.saving" @click="saveReceive">{{ rec.saving ? "Receiving…" : "Record receipt" }}</button>
				</footer>
			</div>
		</div>
	</DeskPage>
</template>
