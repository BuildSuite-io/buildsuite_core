<script setup>
// Project Finance › Invoice detail — a full page over one ERPNext Sales Invoice. Summary
// strip, item lines, taxes, receipts, and the docstatus lifecycle: Submit/Delete (Draft),
// Receive/Cancel (Submitted). Payment is a real Payment Entry into a Bank/Cash account.
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import {
	getInvoice,
	submitInvoice,
	cancelInvoice,
	deleteInvoice,
	recordInvoiceReceipt,
	listInvoiceReceipts,
	listDepositAccounts,
	listInvoicePaymentModes,
} from "@/data/invoiceApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();
const confirmDialog = useConfirm();

const inv = ref(null);
const receipts = ref([]);
const loading = ref(true);
async function load() {
	loading.value = true;
	try {
		inv.value = await getInvoice(props.id);
		receipts.value = inv.value.docstatus === 1 ? await listInvoiceReceipts(props.id) : [];
	} catch (err) {
		showToast(err.message || "Failed to load invoice", "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => inv.value?.docstatus === 0);
const isSubmitted = computed(() => inv.value?.docstatus === 1);
const payment = computed(() => inv.value?.payment || { invoiced: 0, received: 0, outstanding: 0, status: "Draft" });
const statusPills = computed(() => {
	if (!inv.value) return [];
	const doc = inv.value.docstatus === 2 ? "Cancelled" : inv.value.docstatus === 1 ? "Submitted" : "Draft";
	return isSubmitted.value ? [doc, payment.value.status] : [doc];
});

const breadcrumbs = [
	{ label: "Project Finance", to: "/project-finance" },
	{ label: "Invoices", to: "/project-finance/invoices" },
	{ label: props.id },
];

// --- lifecycle ---
const busy = ref(false);
async function onSubmit() {
	const ok = await confirmDialog({ title: "Submit invoice?", message: `Submit ${inv.value.name} (${fmtINR(payment.value.invoiced || inv.value.grand_total)})? It posts the receivable and counts as income.`, confirmLabel: "Submit" });
	if (!ok) return;
	busy.value = true;
	try {
		await submitInvoice(inv.value.name);
		await load();
		showToast("Submitted.");
	} catch (err) {
		showToast(err.message || "Submit failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onCancel() {
	const ok = await confirmDialog({ title: "Cancel invoice?", message: `Cancel ${inv.value.name}? Its receivable and any allocations are reversed.`, confirmLabel: "Cancel invoice", cancelLabel: "Keep", destructive: true });
	if (!ok) return;
	busy.value = true;
	try {
		await cancelInvoice(inv.value.name);
		await load();
		showToast("Cancelled.");
	} catch (err) {
		showToast(err.message || "Cancel failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onDelete() {
	const ok = await confirmDialog({ title: "Delete draft?", message: `Permanently delete ${inv.value.name}?`, confirmLabel: "Delete", destructive: true });
	if (!ok) return;
	try {
		await deleteInvoice(inv.value.name);
		showToast("Deleted.");
		router.push("/project-finance/invoices");
	} catch (err) {
		showToast(err.message || "Delete failed", "error");
	}
}

// --- receive ---
const rec = ref({ open: false, amount: null, deposit_to: "", date: "", mode_of_payment: "", reference_no: "", saving: false });
const depositAccounts = ref([]);
const payModes = ref([]);
async function openReceive() {
	if (!depositAccounts.value.length) {
		try {
			[depositAccounts.value, payModes.value] = await Promise.all([listDepositAccounts(), listInvoicePaymentModes()]);
		} catch {
			/* fall through */
		}
	}
	rec.value = {
		open: true,
		amount: Number(payment.value.outstanding) || null,
		deposit_to: depositAccounts.value.find((a) => a.account_type === "Bank")?.name || depositAccounts.value[0]?.name || "",
		date: new Date().toISOString().slice(0, 10),
		mode_of_payment: payModes.value[0] || "",
		reference_no: "",
		saving: false,
	};
}
async function saveReceive() {
	const amt = Number(rec.value.amount) || 0;
	if (amt <= 0) return showToast("Enter an amount greater than zero.", "error");
	if (amt > Number(payment.value.outstanding) + 0.01) return showToast(`Can't exceed the outstanding ${fmtINR(payment.value.outstanding)}.`, "error");
	if (!rec.value.deposit_to) return showToast("Pick the account to deposit into.", "error");
	rec.value.saving = true;
	try {
		await recordInvoiceReceipt({ name: inv.value.name, amount: amt, date: rec.value.date, mode_of_payment: rec.value.mode_of_payment || undefined, deposit_to: rec.value.deposit_to, reference_no: rec.value.reference_no || undefined });
		rec.value.open = false;
		await load();
		showToast("Payment received.");
	} catch (err) {
		showToast(err.message || "Receipt failed", "error");
	} finally {
		rec.value.saving = false;
	}
}
</script>

<template>
	<DeskPage :title="inv ? inv.name : id" :breadcrumbs="breadcrumbs">
		<template v-if="inv" #actions>
			<div class="flex items-center gap-2">
				<button v-if="isDraft" type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-danger-600 rounded-md" :disabled="busy" @click="onDelete">Delete</button>
				<button v-if="isDraft" type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md" @click="router.push(`/project-finance/invoices/${inv.name}/edit`)">Edit</button>
				<button v-if="isDraft" type="button" class="text-xs desk-save-btn" :disabled="busy" @click="onSubmit">Submit</button>
				<button v-if="isSubmitted && payment.outstanding > 0.01" type="button" class="text-xs desk-save-btn" :disabled="busy" @click="openReceive">Receive payment</button>
				<button v-if="isSubmitted" type="button" class="text-xs px-3 py-1.5 border border-warning-300 bg-warning-50 hover:bg-warning-100 text-warning-700 font-medium rounded-md" :disabled="busy" @click="onCancel">Cancel</button>
			</div>
		</template>

		<div v-if="!inv" class="py-16 text-center text-sm text-ink-400">{{ loading ? "Loading…" : "Invoice not found." }}</div>
		<div v-else class="space-y-4">
			<div class="flex items-center gap-2">
				<StatusBadge v-for="s in statusPills" :key="s" :status="s" size="xs" />
			</div>

			<!-- header facts -->
			<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Customer</div><div class="text-sm text-ink-900 mt-0.5">{{ inv.customer_name }}</div></div>
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Project</div><div class="text-sm text-ink-900 mt-0.5">{{ inv.project_name || "—" }}</div></div>
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Date</div><div class="text-sm text-ink-900 mt-0.5">{{ fmtDate(inv.date) }}</div></div>
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Due</div><div class="text-sm text-ink-900 mt-0.5">{{ fmtDate(inv.due_date) }}</div></div>
			</div>

			<!-- money strip (submitted) -->
			<div v-if="isSubmitted" class="grid grid-cols-2 md:grid-cols-3 gap-2">
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Invoiced</div><div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">{{ fmtINR(payment.invoiced) }}</div></div>
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Received</div><div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">{{ fmtINR(payment.received) }}</div></div>
				<div class="border px-3 py-2 rounded-md" :class="payment.outstanding > 0.01 ? 'bg-warning-50 border-warning-200' : 'bg-success-50 border-success-200'"><div class="text-[10px] uppercase tracking-wider font-medium" :class="payment.outstanding > 0.01 ? 'text-warning-700' : 'text-success-700'">Outstanding</div><div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">{{ fmtINR(payment.outstanding) }}</div></div>
			</div>

			<!-- line items -->
			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-ink-50 px-4 py-2 border-b border-ink-200"><h3 class="text-[11px] uppercase tracking-wider font-semibold text-ink-700">Items</h3></div>
				<table class="w-full text-xs">
					<thead class="text-ink-500 uppercase tracking-wider text-[10px]"><tr><th class="text-left px-4 py-2">Description</th><th class="text-right px-4 py-2">Qty</th><th class="text-right px-4 py-2">Rate</th><th class="text-right px-4 py-2">Amount</th></tr></thead>
					<tbody>
						<tr v-for="(l, idx) in inv.items" :key="idx" class="border-t border-ink-100">
							<td class="px-4 py-2 text-ink-900">{{ l.description }}</td>
							<td class="px-4 py-2 text-right tabular-nums text-ink-600">{{ l.qty }}</td>
							<td class="px-4 py-2 text-right tabular-nums text-ink-600">{{ fmtINR(l.rate) }}</td>
							<td class="px-4 py-2 text-right tabular-nums font-medium text-ink-900">{{ fmtINR(l.amount) }}</td>
						</tr>
					</tbody>
					<tfoot class="border-t border-ink-200">
						<tr><td colspan="3" class="px-4 py-1.5 text-right text-ink-500">Net total</td><td class="px-4 py-1.5 text-right tabular-nums text-ink-700">{{ fmtINR(inv.net_total) }}</td></tr>
						<tr v-for="(t, idx) in inv.taxes" :key="'t' + idx"><td colspan="3" class="px-4 py-1.5 text-right text-ink-500">{{ t.description }} ({{ t.rate }}%)</td><td class="px-4 py-1.5 text-right tabular-nums text-ink-700">{{ fmtINR(t.tax_amount) }}</td></tr>
						<tr class="border-t border-ink-200 font-semibold"><td colspan="3" class="px-4 py-2 text-right text-ink-900">Grand total</td><td class="px-4 py-2 text-right tabular-nums text-ink-900">{{ fmtINR(inv.grand_total) }}</td></tr>
					</tfoot>
				</table>
			</section>

			<!-- receipts -->
			<section v-if="receipts.length" class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-ink-50 px-4 py-2 border-b border-ink-200"><h3 class="text-[11px] uppercase tracking-wider font-semibold text-ink-700">Receipts</h3></div>
				<table class="w-full text-xs">
					<thead class="text-ink-500 uppercase tracking-wider text-[10px]"><tr><th class="text-left px-4 py-2">Date</th><th class="text-left px-4 py-2">Mode</th><th class="text-left px-4 py-2">Reference</th><th class="text-left px-4 py-2">Entry</th><th class="text-right px-4 py-2">Amount</th></tr></thead>
					<tbody>
						<tr v-for="p in receipts" :key="p.payment_entry" class="border-t border-ink-100">
							<td class="px-4 py-2 text-ink-500 whitespace-nowrap">{{ fmtDate(p.date) }}</td>
							<td class="px-4 py-2 text-ink-700">{{ p.mode_of_payment || "—" }}</td>
							<td class="px-4 py-2 text-ink-600">{{ p.reference_no || "—" }}</td>
							<td class="px-4 py-2"><DeskLink :to="`/app/payment-entry/${p.payment_entry}`" class="font-mono text-ink-700">{{ p.payment_entry }}</DeskLink></td>
							<td class="px-4 py-2 text-right tabular-nums font-medium text-ink-900">{{ fmtINR(p.amount) }}</td>
						</tr>
					</tbody>
				</table>
			</section>
		</div>

		<!-- Receive payment modal -->
		<div v-if="rec.open" class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto" @click.self="rec.open = false">
			<div class="bg-white border border-ink-200 w-full max-w-md shadow-xl rounded-xl" @click.stop>
				<header class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"><h2 class="text-sm font-semibold text-ink-900">Receive payment</h2><button type="button" class="text-ink-400 hover:text-ink-900" @click="rec.open = false">✕</button></header>
				<div class="px-4 py-4 space-y-3">
					<div class="text-sm text-ink-700">From <span class="font-medium">{{ inv.customer_name }}</span> against <span class="font-mono text-xs">{{ inv.name }}</span>. Outstanding <span class="font-semibold text-ink-900 tabular-nums">{{ fmtINR(payment.outstanding) }}</span>.</div>
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
