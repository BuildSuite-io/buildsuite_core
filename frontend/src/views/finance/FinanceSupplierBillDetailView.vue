<script setup>
// Project Finance › Bills › Supplier bill detail — a full page over one ERPNext Purchase
// Invoice. Summary strip, item lines, taxes, payments, and the docstatus lifecycle:
// Submit/Delete/Edit (Draft), Pay/Cancel (Submitted). Pay = a real Payment Entry from a
// Bank/Cash account. Mirrors the customer-invoice detail.
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import {
	getSupplierBill,
	submitSupplierBill,
	cancelSupplierBill,
	deleteSupplierBill,
	recordSupplierBillPayment,
	listSupplierBillPayments,
	listBillPayAccounts,
	listSupplierBillPaymentModes,
} from "@/data/supplierBillApi";
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

const bill = ref(null);
const payments = ref([]);
const loading = ref(true);
async function load() {
	loading.value = true;
	try {
		bill.value = await getSupplierBill(props.id);
		payments.value = bill.value.docstatus === 1 ? await listSupplierBillPayments(props.id) : [];
	} catch (err) {
		showToast(err.message || "Failed to load bill", "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => bill.value?.docstatus === 0);
const isSubmitted = computed(() => bill.value?.docstatus === 1);
const payment = computed(() => bill.value?.payment || { invoiced: 0, paid: 0, outstanding: 0, status: "Draft" });
const statusPills = computed(() => {
	if (!bill.value) return [];
	const doc = bill.value.docstatus === 2 ? "Cancelled" : bill.value.docstatus === 1 ? "Submitted" : "Draft";
	return isSubmitted.value ? [doc, payment.value.status] : [doc];
});

const breadcrumbs = [
	{ label: "Project Finance", to: "/project-finance" },
	{ label: "Bills", to: "/project-finance/bills" },
	{ label: props.id },
];

const busy = ref(false);
async function onSubmit() {
	const ok = await confirmDialog({ title: "Submit bill?", message: `Submit ${bill.value.name} (${fmtINR(bill.value.grand_total)})? It posts the payable and can then be paid.`, confirmLabel: "Submit" });
	if (!ok) return;
	busy.value = true;
	try {
		await submitSupplierBill(bill.value.name);
		await load();
		showToast("Submitted.");
	} catch (err) {
		showToast(err.message || "Submit failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onCancel() {
	const ok = await confirmDialog({ title: "Cancel bill?", message: `Cancel ${bill.value.name}? Its payable and any allocations are reversed.`, confirmLabel: "Cancel bill", cancelLabel: "Keep", destructive: true });
	if (!ok) return;
	busy.value = true;
	try {
		await cancelSupplierBill(bill.value.name);
		await load();
		showToast("Cancelled.");
	} catch (err) {
		showToast(err.message || "Cancel failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onDelete() {
	const ok = await confirmDialog({ title: "Delete draft?", message: `Permanently delete ${bill.value.name}?`, confirmLabel: "Delete", destructive: true });
	if (!ok) return;
	try {
		await deleteSupplierBill(bill.value.name);
		showToast("Deleted.");
		router.push("/project-finance/bills");
	} catch (err) {
		showToast(err.message || "Delete failed", "error");
	}
}

// --- pay ---
const pay = ref({ open: false, amount: null, pay_from: "", date: "", mode_of_payment: "", reference_no: "", saving: false });
const payAccounts = ref([]);
const payModes = ref([]);
async function openPay() {
	if (!payAccounts.value.length) {
		try {
			[payAccounts.value, payModes.value] = await Promise.all([listBillPayAccounts(), listSupplierBillPaymentModes()]);
		} catch {
			/* fall through */
		}
	}
	pay.value = {
		open: true,
		amount: Number(payment.value.outstanding) || null,
		pay_from: payAccounts.value.find((a) => a.account_type === "Bank")?.name || payAccounts.value[0]?.name || "",
		date: new Date().toISOString().slice(0, 10),
		mode_of_payment: payModes.value[0] || "",
		reference_no: "",
		saving: false,
	};
}
async function savePay() {
	const amt = Number(pay.value.amount) || 0;
	if (amt <= 0) return showToast("Enter an amount greater than zero.", "error");
	if (amt > Number(payment.value.outstanding) + 0.01) return showToast(`Can't exceed the outstanding ${fmtINR(payment.value.outstanding)}.`, "error");
	if (!pay.value.pay_from) return showToast("Pick the account to pay from.", "error");
	pay.value.saving = true;
	try {
		await recordSupplierBillPayment({ name: bill.value.name, amount: amt, date: pay.value.date, mode_of_payment: pay.value.mode_of_payment || undefined, pay_from: pay.value.pay_from, reference_no: pay.value.reference_no || undefined });
		pay.value.open = false;
		await load();
		showToast("Payment made.");
	} catch (err) {
		showToast(err.message || "Payment failed", "error");
	} finally {
		pay.value.saving = false;
	}
}
</script>

<template>
	<DeskPage :title="bill ? bill.name : id" :breadcrumbs="breadcrumbs">
		<template v-if="bill" #actions>
			<div class="flex items-center gap-2">
				<button v-if="isDraft" type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-danger-600 rounded-md" :disabled="busy" @click="onDelete">Delete</button>
				<button v-if="isDraft" type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md" @click="router.push(`/project-finance/supplier-bills/${bill.name}/edit`)">Edit</button>
				<button v-if="isDraft" type="button" class="text-xs desk-save-btn" :disabled="busy" @click="onSubmit">Submit</button>
				<button v-if="isSubmitted && payment.outstanding > 0.01" type="button" class="text-xs desk-save-btn" :disabled="busy" @click="openPay">Pay</button>
				<button v-if="isSubmitted" type="button" class="text-xs px-3 py-1.5 border border-warning-300 bg-warning-50 hover:bg-warning-100 text-warning-700 font-medium rounded-md" :disabled="busy" @click="onCancel">Cancel</button>
			</div>
		</template>

		<div v-if="!bill" class="py-16 text-center text-sm text-ink-400">{{ loading ? "Loading…" : "Bill not found." }}</div>
		<div v-else class="space-y-4">
			<div class="flex items-center gap-2">
				<StatusBadge v-for="s in statusPills" :key="s" :status="s" size="xs" />
			</div>

			<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Supplier</div><div class="text-sm text-ink-900 mt-0.5">{{ bill.supplier_name }}</div></div>
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Project</div><div class="text-sm text-ink-900 mt-0.5">{{ bill.project_name || "—" }}</div></div>
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Bill date</div><div class="text-sm text-ink-900 mt-0.5">{{ fmtDate(bill.date) }}</div></div>
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Due</div><div class="text-sm text-ink-900 mt-0.5">{{ fmtDate(bill.due_date) }}</div></div>
			</div>
			<div v-if="bill.bill_no" class="text-xs text-ink-500">Supplier invoice <span class="font-medium text-ink-700">{{ bill.bill_no }}</span><span v-if="bill.bill_date"> · {{ fmtDate(bill.bill_date) }}</span></div>

			<div v-if="isSubmitted" class="grid grid-cols-2 md:grid-cols-3 gap-2">
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Billed</div><div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">{{ fmtINR(payment.invoiced) }}</div></div>
				<div class="bg-white border border-ink-200 px-3 py-2 rounded-md"><div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Paid</div><div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">{{ fmtINR(payment.paid) }}</div></div>
				<div class="border px-3 py-2 rounded-md" :class="payment.outstanding > 0.01 ? 'bg-warning-50 border-warning-200' : 'bg-success-50 border-success-200'"><div class="text-[10px] uppercase tracking-wider font-medium" :class="payment.outstanding > 0.01 ? 'text-warning-700' : 'text-success-700'">Outstanding</div><div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">{{ fmtINR(payment.outstanding) }}</div></div>
			</div>

			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-ink-50 px-4 py-2 border-b border-ink-200"><h3 class="text-[11px] uppercase tracking-wider font-semibold text-ink-700">Items</h3></div>
				<table class="w-full text-xs">
					<thead class="text-ink-500 uppercase tracking-wider text-[10px]"><tr><th class="text-left px-4 py-2">Description</th><th class="text-right px-4 py-2">Qty</th><th class="text-right px-4 py-2">Rate</th><th class="text-right px-4 py-2">Amount</th></tr></thead>
					<tbody>
						<tr v-for="(l, idx) in bill.items" :key="idx" class="border-t border-ink-100">
							<td class="px-4 py-2 text-ink-900">{{ l.description }}</td>
							<td class="px-4 py-2 text-right tabular-nums text-ink-600">{{ l.qty }}</td>
							<td class="px-4 py-2 text-right tabular-nums text-ink-600">{{ fmtINR(l.rate) }}</td>
							<td class="px-4 py-2 text-right tabular-nums font-medium text-ink-900">{{ fmtINR(l.amount) }}</td>
						</tr>
					</tbody>
					<tfoot class="border-t border-ink-200">
						<tr><td colspan="3" class="px-4 py-1.5 text-right text-ink-500">Net total</td><td class="px-4 py-1.5 text-right tabular-nums text-ink-700">{{ fmtINR(bill.net_total) }}</td></tr>
						<tr v-for="(t, idx) in bill.taxes" :key="'t' + idx"><td colspan="3" class="px-4 py-1.5 text-right text-ink-500">{{ t.description }} ({{ t.rate }}%)</td><td class="px-4 py-1.5 text-right tabular-nums text-ink-700">{{ fmtINR(t.tax_amount) }}</td></tr>
						<tr class="border-t border-ink-200 font-semibold"><td colspan="3" class="px-4 py-2 text-right text-ink-900">Grand total</td><td class="px-4 py-2 text-right tabular-nums text-ink-900">{{ fmtINR(bill.grand_total) }}</td></tr>
					</tfoot>
				</table>
			</section>

			<section v-if="payments.length" class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-ink-50 px-4 py-2 border-b border-ink-200"><h3 class="text-[11px] uppercase tracking-wider font-semibold text-ink-700">Payments</h3></div>
				<table class="w-full text-xs">
					<thead class="text-ink-500 uppercase tracking-wider text-[10px]"><tr><th class="text-left px-4 py-2">Date</th><th class="text-left px-4 py-2">Mode</th><th class="text-left px-4 py-2">Reference</th><th class="text-left px-4 py-2">Entry</th><th class="text-right px-4 py-2">Amount</th></tr></thead>
					<tbody>
						<tr v-for="p in payments" :key="p.payment_entry" class="border-t border-ink-100">
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

		<!-- Pay modal -->
		<div v-if="pay.open" class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto" @click.self="pay.open = false">
			<div class="bg-white border border-ink-200 w-full max-w-md shadow-xl rounded-xl" @click.stop>
				<header class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"><h2 class="text-sm font-semibold text-ink-900">Pay bill</h2><button type="button" class="text-ink-400 hover:text-ink-900" @click="pay.open = false">✕</button></header>
				<div class="px-4 py-4 space-y-3">
					<div class="text-sm text-ink-700">Pay <span class="font-medium">{{ bill.supplier_name }}</span> against <span class="font-mono text-xs">{{ bill.name }}</span>. Outstanding <span class="font-semibold text-ink-900 tabular-nums">{{ fmtINR(payment.outstanding) }}</span>.</div>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Amount" required><DeskInput v-model.number="pay.amount" type="number" min="0" /></DeskField>
						<DeskField label="Date"><DeskInput v-model="pay.date" type="date" /></DeskField>
					</div>
					<DeskField label="Pay from" required>
						<DeskSelect v-model="pay.pay_from"><option value="" disabled>Bank / Cash account…</option><option v-for="a in payAccounts" :key="a.name" :value="a.name">{{ a.name }} ({{ a.account_type }})</option></DeskSelect>
					</DeskField>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Mode of payment"><DeskSelect v-model="pay.mode_of_payment"><option value="">—</option><option v-for="m in payModes" :key="m" :value="m">{{ m }}</option></DeskSelect></DeskField>
						<DeskField label="Reference no."><DeskInput v-model="pay.reference_no" placeholder="UTR / cheque no." /></DeskField>
					</div>
				</div>
				<footer class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2">
					<button type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md" @click="pay.open = false">Cancel</button>
					<button type="button" class="text-xs desk-save-btn" :disabled="pay.saving" @click="savePay">{{ pay.saving ? "Paying…" : "Record payment" }}</button>
				</footer>
			</div>
		</div>
	</DeskPage>
</template>
