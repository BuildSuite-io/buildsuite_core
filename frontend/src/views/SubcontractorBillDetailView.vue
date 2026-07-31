<script setup>
// Subcontractor Bill detail — Desk-styled to match the demo: summary strip, lines,
// Taxes & Charges table, side-by-side Retention/TDS/discount + the live waterfall, and
// Attachments. Real data throughout — company-scoped tax-template / account / expense pickers,
// a generated Purchase Invoice, and (on submit) a Desk Payment Entry link-out. Draft-editable.

import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { createDataAdapter } from "@/data/adapters";
import { useDataStore } from "@/stores";
import FileUploadHandler from "frappe-ui-file-upload-handler";
import {
	getBill,
	saveBill,
	submitBill,
	cancelBill,
	deleteBill,
	getTaxTemplateRows,
	recordBillPayment,
	listBillPayments,
	listBillPayAccounts,
	listPaymentModes,
	availableBillAdvances,
	linkBillAdvance,
	unlinkBillAdvance,
} from "@/data/subcontractApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import FrappeUserBadge from "@/components/FrappeUserBadge.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());

const bill = ref(null);
const busy = ref(false);
const savingBilling = ref(false);
const submitMsg = ref("");

// Discount is stored as two fields (percentage + amount); the UI toggles between them.
const discType = ref("%");
const discValue = ref(0);

async function load() {
	try {
		bill.value = await getBill(props.id);
		if (Number(bill.value.discount_amount) > 0) {
			discType.value = "₹";
			discValue.value = Number(bill.value.discount_amount);
		} else {
			discType.value = "%";
			discValue.value = Number(bill.value.additional_discount_percentage) || 0;
		}
	} catch (err) {
		showToast(err.message || "Failed to load bill", "error");
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => bill.value?.docstatus === 0);
const isSubmitted = computed(() => bill.value?.docstatus === 1);
const editable = computed(() => isDraft.value);
const payment = computed(
	() => bill.value?.payment || { paid: 0, outstanding: 0, invoiced: 0, status: "Unpaid" }
);
const retPct = computed(() => Number(bill.value?.retention_percent) || 0);
const taxRatePct = computed(() =>
	(bill.value?.taxes || []).reduce((a, t) => a + (Number(t.rate) || 0), 0)
);

const statusPills = computed(() => {
	if (!bill.value) return [];
	return isSubmitted.value ? [bill.value.status, payment.value.status] : [bill.value.status];
});

// --- live waterfall (server is authoritative on save) ---
const wf = computed(() => {
	const b = bill.value;
	if (!b) return {};
	const gross = (b.lines || []).reduce((a, l) => a + (Number(l.this_period_amount) || 0), 0);
	const discBase = (base) =>
		Math.min(
			discType.value === "%"
				? (base * (Number(discValue.value) || 0)) / 100
				: Number(discValue.value) || 0,
			base
		);
	const netDiscount = b.additional_discount_on === "Net Total" ? discBase(gross) : 0;
	const taxable = Math.max(0, gross - netDiscount);
	const taxRows = (b.taxes || []).map((t) => ({
		...t,
		amount: (taxable * (Number(t.rate) || 0)) / 100,
	}));
	const tax = taxRows.reduce((a, t) => a + t.amount, 0);
	const grandTotal = taxable + tax;
	const grandDiscount = b.additional_discount_on === "Grand Total" ? discBase(grandTotal) : 0;
	const invoiceValue = grandTotal - grandDiscount;
	const tds = b.apply_tds ? (taxable * (Number(b.tds_rate) || 0)) / 100 : 0;
	const retention = (taxable * (Number(b.retention_percent) || 0)) / 100;
	const advance = Number(b.advance_recovery) || 0;
	const netPayable = Math.max(0, invoiceValue - tds - retention - advance);
	return {
		gross,
		netDiscount,
		grandDiscount,
		taxable,
		taxRows,
		tax,
		grandTotal,
		invoiceValue,
		tds,
		retention,
		advance,
		netPayable,
	};
});

// --- taxes editor ---
async function onPickTemplate(tpl) {
	bill.value.taxes_and_charges = tpl;
	if (!tpl) return;
	try {
		bill.value.taxes = await getTaxTemplateRows(tpl);
	} catch (err) {
		showToast(err.message || "Failed to load template rows", "error");
	}
}
function addTaxRow() {
	bill.value.taxes.push({ charge_type: "On Net Total", account_head: "", rate: 0 });
}
function removeTaxRow(i) {
	bill.value.taxes.splice(i, 1);
}

async function saveBilling() {
	savingBilling.value = true;
	try {
		const b = bill.value;
		const payload = {
			name: b.name,
			is_direct: b.is_direct,
			work_order: b.work_order,
			subcontractor: b.subcontractor,
			project: b.project,
			date: b.date,
			bill_type: b.bill_type,
			retention_percent: b.retention_percent,
			taxes_and_charges: b.taxes_and_charges,
			tax_category: b.tax_category,
			apply_tds: b.apply_tds ? 1 : 0,
			tax_withholding_category: b.tax_withholding_category,
			additional_discount_on: b.additional_discount_on,
			additional_discount_percentage: discType.value === "%" ? discValue.value : 0,
			discount_amount: discType.value === "₹" ? discValue.value : 0,
			advance_recovery: b.advance_recovery,
			expense_account: b.expense_account,
			taxes: (b.taxes || []).map((t) => ({
				charge_type: t.charge_type,
				account_head: t.account_head,
				description: t.description,
				rate: t.rate,
			})),
		};
		if (b.is_direct)
			payload.lines = (b.lines || []).map((l) => ({
				scope: l.scope,
				cost_code: l.cost_code_label,
				amount: l.this_period_amount,
			}));
		const saved = await saveBill(payload);
		bill.value = { ...saved };
		showToast("Billing saved.");
	} catch (err) {
		showToast(err.message || "Failed to save", "error");
	} finally {
		savingBilling.value = false;
	}
}

// --- actions ---
function onEdit() {
	router.push(`/subcontractor-bills/${bill.value.name}/edit`);
}
function onOpenAccounting() {
	if (bill.value.purchase_invoice)
		window.open(`/app/purchase-invoice/${bill.value.purchase_invoice}`, "_blank", "noopener");
}
async function onSubmit() {
	if (wf.value.gross <= 0) {
		showToast("Nothing to bill — add a line with an amount.", "error");
		return;
	}
	const ok = await confirmDialog({
		title: `Submit Bill ${bill.value.ra_no}?`,
		message: `This posts the bill and generates the Purchase Invoice for ${fmtINR(
			wf.value.netPayable
		)} net payable. A submitted bill is read-only.`,
		confirmLabel: "Submit",
	});
	if (!ok) return;
	busy.value = true;
	try {
		bill.value = await submitBill(bill.value.name);
		submitMsg.value = `Purchase Invoice ${bill.value.purchase_invoice} generated — bill submitted.`;
	} catch (err) {
		showToast(err.message || "Submit failed", "error");
	} finally {
		busy.value = false;
	}
}
// --- payments: inline, minimalist (no Desk redirect) ---
const MODE_FALLBACK = ["Cash", "Cheque", "Bank Draft", "Wire Transfer"];
const payAccounts = ref([]);
const payModes = ref([]);
const payments = ref([]);

async function loadPayments() {
	if (!isSubmitted.value) {
		payments.value = [];
		return;
	}
	try {
		payments.value = await listBillPayments(bill.value.name);
	} catch {
		payments.value = [];
	}
}
watch(isSubmitted, loadPayments, { immediate: true });

const pay = ref({
	open: false,
	amount: null,
	account: "",
	date: "",
	mode_of_payment: "",
	reference_no: "",
	saving: false,
});
async function onMakePayment() {
	if (!payAccounts.value.length) {
		try {
			[payAccounts.value, payModes.value] = await Promise.all([
				listBillPayAccounts(),
				listPaymentModes(),
			]);
		} catch {
			/* fall back to the built-in modes; accounts stay empty and the field warns */
		}
	}
	if (!payModes.value.length) payModes.value = MODE_FALLBACK;
	pay.value = {
		open: true,
		amount: Number(payment.value.outstanding) || null,
		account:
			payAccounts.value.find((a) => a.account_type === "Bank")?.name ||
			payAccounts.value[0]?.name ||
			"",
		date: new Date().toISOString().slice(0, 10),
		mode_of_payment: payModes.value[0] || "",
		reference_no: "",
		saving: false,
	};
}
async function savePayment() {
	const amt = Number(pay.value.amount) || 0;
	if (amt <= 0) return showToast("Enter an amount greater than zero.", "error");
	if (amt > Number(payment.value.outstanding) + 0.01)
		return showToast(
			`Can't exceed the outstanding ${fmtINR(payment.value.outstanding)}.`,
			"error"
		);
	if (!pay.value.account) return showToast("Pick the account to pay from.", "error");
	pay.value.saving = true;
	try {
		await recordBillPayment({
			name: bill.value.name,
			amount: amt,
			date: pay.value.date,
			mode_of_payment: pay.value.mode_of_payment || undefined,
			paid_from: pay.value.account,
			reference_no: pay.value.reference_no || undefined,
		});
		pay.value.open = false;
		await load();
		await loadPayments();
		showToast("Payment recorded.");
	} catch (err) {
		showToast(err.message || "Payment failed", "error");
	} finally {
		pay.value.saving = false;
	}
}

// --- advance payments: adjust the subcontractor's on-account advances against this bill.
// The bill has no Purchase Invoice until submit, so advance linking is submitted-only. ---
const availableAdvances = ref([]);
const linkedAdvances = computed(() => bill.value?.advances || []);
const advanceAdjusted = computed(() => Number(bill.value?.advance_adjusted) || 0);
const unlinkedTotal = computed(() =>
	availableAdvances.value.reduce((a, x) => a + Number(x.unallocated || 0), 0)
);
const canLinkAdv = computed(() => isSubmitted.value);
const advAlloc = reactive({});
const adv = ref({ open: false, msg: "", error: "", saving: "" });
async function loadAdvances() {
	if (!isSubmitted.value) {
		availableAdvances.value = [];
		return;
	}
	try {
		availableAdvances.value = await availableBillAdvances(bill.value.name);
	} catch {
		availableAdvances.value = [];
	}
}
watch(isSubmitted, loadAdvances, { immediate: true });
function suggestAllocations() {
	for (const a of availableAdvances.value)
		advAlloc[a.payment_entry] = Math.min(
			Number(a.unallocated),
			Number(payment.value.outstanding) || 0
		);
}
function openLinkAdvance() {
	adv.value.error = "";
	adv.value.msg = "";
	suggestAllocations();
	adv.value.open = true;
}
async function doLink(a) {
	const amt = Number(advAlloc[a.payment_entry]) || 0;
	if (amt <= 0) {
		adv.value.error = "Enter an amount greater than zero.";
		return;
	}
	if (amt > Number(a.unallocated) + 0.01) {
		adv.value.error = `Only ${fmtINR(a.unallocated)} is unadjusted on ${a.payment_entry}.`;
		return;
	}
	adv.value.saving = a.payment_entry;
	adv.value.error = "";
	try {
		await linkBillAdvance({
			name: bill.value.name,
			payment_entry: a.payment_entry,
			amount: amt,
		});
		adv.value.open = false;
		await load();
		await loadPayments();
		await loadAdvances();
		adv.value.msg = `Linked ${fmtINR(amt)} from ${
			a.payment_entry
		} — outstanding is now ${fmtINR(payment.value.outstanding)}.`;
		showToast("Advance linked.");
	} catch (err) {
		adv.value.error = err.message || "Could not link the advance.";
	} finally {
		adv.value.saving = "";
	}
}
async function unlinkAdvance(row) {
	const ok = await confirmDialog({
		title: "Unlink advance?",
		message: `Return ${fmtINR(row.allocated)} to ${
			row.payment_entry
		}'s unallocated balance? The net payable goes back up.`,
		confirmLabel: "Unlink",
	});
	if (!ok) return;
	adv.value.msg = "";
	try {
		await unlinkBillAdvance({ name: bill.value.name, payment_entry: row.payment_entry });
		await load();
		await loadPayments();
		await loadAdvances();
		showToast("Advance unlinked.");
	} catch (err) {
		showToast(err.message || "Unlink failed", "error");
	}
}
async function onCancel() {
	const ok = await confirmDialog({
		title: `Cancel Bill ${bill.value.ra_no}?`,
		message: "This cancels the bill and its Purchase Invoice, reversing the postings.",
		confirmLabel: "Cancel bill",
		destructive: true,
	});
	if (!ok) return;
	busy.value = true;
	try {
		bill.value = await cancelBill(bill.value.name);
		showToast("Bill cancelled.");
	} catch (err) {
		showToast(err.message || "Cancel failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onDelete() {
	const ok = await confirmDialog({
		title: `Delete Bill ${bill.value.ra_no}?`,
		message: "This draft bill will be removed permanently.",
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await deleteBill(bill.value.name);
		router.push("/subcontractor-bills");
	} catch (err) {
		showToast(err.message || "Delete failed", "error");
	}
}

// --- attachments (real Frappe File on the bill) ---
const filesRes = useDocTypeList("File", {
	fields: ["name", "file_name", "file_url", "file_size", "creation", "owner"],
	filters: [
		["attached_to_doctype", "=", "Subcontractor Bill"],
		["attached_to_name", "=", props.id],
	],
	orderBy: "creation desc",
	pageLength: 0,
	cache: `buildsuite-bill-files-${props.id}`,
});
const attachments = computed(() => filesRes.data || []);
const fileInput = ref(null);
const uploading = ref(0);
async function onFilesPicked(e) {
	const files = Array.from(e.target.files || []);
	if (!files.length) return;
	uploading.value += files.length;
	for (const f of files) {
		try {
			await new FileUploadHandler().upload(f, {
				doctype: "Subcontractor Bill",
				docname: props.id,
				private: false,
			});
		} catch (err) {
			showToast(`Failed to upload ${f.name}`, "error");
		} finally {
			uploading.value--;
		}
	}
	if (e.target) e.target.value = "";
	filesRes.reload?.();
}
async function onDeleteFile(row) {
	const ok = await confirmDialog({
		title: "Delete attachment",
		message: `Delete "${row.file_name}"?`,
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("File", row.name);
		filesRes.reload?.();
	} catch (err) {
		showToast(err.message || "Failed to delete attachment", "error");
	}
}
function fileIcon(url) {
	const ext = (url || "").split(".").pop().toLowerCase().split("?")[0];
	if (["jpg", "jpeg", "png", "gif", "webp", "svg"].includes(ext)) return "🖼️";
	if (ext === "pdf") return "📕";
	if (["dwg", "dxf"].includes(ext)) return "📐";
	if (["doc", "docx"].includes(ext)) return "📝";
	if (["xls", "xlsx", "csv"].includes(ext)) return "📊";
	if (["zip", "rar", "7z"].includes(ext)) return "🗜️";
	return "📄";
}
function formatFileSize(bytes) {
	if (!bytes) return "0 B";
	const units = ["B", "KB", "MB", "GB"];
	let i = 0;
	let n = bytes;
	while (n >= 1024 && i < units.length - 1) {
		n /= 1024;
		i++;
	}
	return (i === 0 ? n : n.toFixed(n < 10 ? 1 : 0)) + " " + units[i];
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Subcontractor Bills", to: "/subcontractor-bills" },
	{ label: bill.value?.name || props.id },
]);
const accountFilters = computed(() =>
	bill.value?.company
		? [
				["is_group", "=", 0],
				["company", "=", bill.value.company],
		  ]
		: [["is_group", "=", 0]]
);
</script>

<template>
	<DeskPage
		v-if="bill"
		:title="`Subcontractor Bill ${bill.ra_no}`"
		:subtitle="`${bill.name} · ${bill.subcontractor_name || bill.subcontractor} · ${
			bill.project_name || bill.project
		}`"
		:breadcrumbs="breadcrumbs"
		:status="statusPills"
	>
		<template #actions>
			<button
				v-if="bill.purchase_invoice"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				title="Open the generated Purchase Invoice in the Accounting desk"
				@click="onOpenAccounting"
			>
				Open in Accounting →
			</button>
			<button
				v-if="isDraft"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onEdit"
			>
				Edit
			</button>
			<button
				v-if="isDraft"
				type="button"
				class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onSubmit"
			>
				Submit
			</button>
			<template v-if="isSubmitted">
				<button
					v-if="payment.status !== 'Paid'"
					type="button"
					class="text-xs px-2.5 py-1 border border-brand-300 bg-brand-50 hover:bg-brand-100 text-brand-700 font-medium"
					style="border-radius: 6px"
					@click="onMakePayment"
				>
					Make Payment
				</button>
				<button
					type="button"
					class="text-xs px-2.5 py-1 border border-warning-300 bg-warning-50 hover:bg-warning-100 text-warning-700 font-medium"
					style="border-radius: 6px"
					:disabled="busy"
					@click="onCancel"
				>
					Cancel
				</button>
			</template>
			<button
				v-if="isDraft"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				:disabled="busy"
				@click="onDelete"
			>
				Delete
			</button>
		</template>

		<!-- Submit success + PI reference -->
		<div
			v-if="submitMsg"
			class="mb-4 px-4 py-2.5 bg-success-50 border border-success-200 rounded-md text-xs text-success-700 flex items-center gap-2"
		>
			<span class="text-sm">✓</span><span class="font-medium">{{ submitMsg }}</span>
		</div>
		<div v-else-if="bill.purchase_invoice" class="mb-4 text-xs text-ink-600">
			Purchase Invoice
			<DeskLink
				:to="`/app/purchase-invoice/${bill.purchase_invoice}`"
				class="font-mono font-medium text-ink-900"
				>{{ bill.purchase_invoice }}</DeskLink
			>
		</div>
		<div v-if="isSubmitted && payment.status !== 'Paid'" class="mb-4 text-xs text-ink-600">
			Outstanding
			<span class="font-semibold text-ink-900 tabular-nums">{{
				fmtINR(payment.outstanding)
			}}</span>
			<span v-if="payment.paid > 0">
				· paid {{ fmtINR(payment.paid) }} of {{ fmtINR(payment.invoiced) }}</span
			>
		</div>
		<div
			v-else-if="isSubmitted && payment.status === 'Paid'"
			class="mb-4 text-xs text-success-700"
		>
			Fully paid — {{ fmtINR(payment.paid) }} of {{ fmtINR(payment.invoiced) }}
		</div>

		<!-- advance linked confirmation -->
		<div
			v-if="adv.msg"
			class="mb-4 px-4 py-2.5 bg-success-50 border border-success-200 rounded-md text-xs text-success-700 flex items-center gap-2"
		>
			<span class="text-sm">✓</span><span class="font-medium">{{ adv.msg }}</span>
		</div>
		<!-- unlinked-advance suggestion (submitted — the bill's PI exists) -->
		<div
			v-if="canLinkAdv && availableAdvances.length && payment.outstanding > 0.01"
			class="mb-4 px-4 py-2.5 bg-info-50 border border-info-200 rounded-md text-xs text-ink-700 flex items-center justify-between gap-3 flex-wrap"
		>
			<span>
				<span class="font-medium text-ink-900"
					>{{ bill.subcontractor_name }} has {{ fmtINR(unlinkedTotal) }} in unlinked
					advance payment{{ availableAdvances.length === 1 ? "" : "s" }}</span
				>
				— link {{ availableAdvances.length === 1 ? "it" : "them" }} to this bill to settle
				the payable.
			</span>
			<button
				type="button"
				class="text-xs px-2.5 py-1 border border-info-200 bg-white hover:bg-info-50 text-info-700 font-medium flex-shrink-0 rounded-md"
				@click="openLinkAdvance"
			>
				Link advance →
			</button>
		</div>

		<!-- Payments made against this bill -->
		<div
			v-if="isSubmitted && payments.length"
			class="mb-4 bg-white border border-ink-200 rounded-lg overflow-hidden"
		>
			<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
				<h3 class="text-[11px] uppercase tracking-wider font-semibold text-ink-700">
					Payments
				</h3>
			</div>
			<table class="w-full text-xs">
				<thead class="text-ink-500 uppercase tracking-wider text-[10px]">
					<tr>
						<th class="text-left px-4 py-2">Date</th>
						<th class="text-left px-4 py-2">Mode</th>
						<th class="text-left px-4 py-2">Reference</th>
						<th class="text-left px-4 py-2">Entry</th>
						<th class="text-right px-4 py-2">Amount</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="p in payments"
						:key="p.payment_entry"
						class="border-t border-ink-100"
					>
						<td class="px-4 py-2 text-ink-500 whitespace-nowrap">
							{{ fmtDate(p.date) }}
						</td>
						<td class="px-4 py-2 text-ink-700">{{ p.mode_of_payment || "—" }}</td>
						<td class="px-4 py-2 text-ink-600">{{ p.reference_no || "—" }}</td>
						<td class="px-4 py-2">
							<DeskLink
								:to="`/app/payment-entry/${p.payment_entry}`"
								class="font-mono text-ink-700"
								>{{ p.payment_entry }}</DeskLink
							>
						</td>
						<td class="px-4 py-2 text-right tabular-nums font-medium text-ink-900">
							{{ fmtINR(p.amount) }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>

		<!-- Advance Payments (subcontractor advances adjusted against the bill's PI) -->
		<div
			v-if="isSubmitted && (linkedAdvances.length || availableAdvances.length)"
			class="mb-4 bg-white border border-ink-200 rounded-lg overflow-hidden"
		>
			<div
				class="bg-ink-50 px-4 py-2 border-b border-ink-200 flex items-center justify-between gap-3"
			>
				<h3 class="text-[11px] uppercase tracking-wider font-semibold text-ink-700">
					Advance Payments
				</h3>
				<button
					v-if="availableAdvances.length"
					type="button"
					class="text-xs text-brand-700 hover:underline"
					@click="openLinkAdvance"
				>
					+ Link advance
				</button>
			</div>
			<template v-if="linkedAdvances.length">
				<div
					v-for="row in linkedAdvances"
					:key="row.payment_entry"
					class="flex items-center justify-between px-4 py-2.5 border-t border-ink-100 text-sm gap-2"
				>
					<DeskLink
						:to="`/app/payment-entry/${row.payment_entry}`"
						class="font-mono text-xs text-ink-900 min-w-0 truncate"
						>{{ row.payment_entry }}</DeskLink
					>
					<span class="flex items-center gap-2 flex-shrink-0">
						<span class="tabular-nums text-info-700 font-medium">{{
							fmtINR(row.allocated)
						}}</span>
						<button
							type="button"
							class="text-ink-400 hover:text-danger-600 text-xs"
							:title="`Unlink ${row.payment_entry}`"
							@click="unlinkAdvance(row)"
						>
							✕
						</button>
					</span>
				</div>
				<div
					class="px-4 py-2 border-t border-ink-100 flex items-center justify-between text-[11px]"
				>
					<span class="uppercase tracking-wider text-ink-500 font-medium"
						>Total advance adjusted</span
					>
					<span class="tabular-nums font-semibold text-ink-900">{{
						fmtINR(advanceAdjusted)
					}}</span>
				</div>
			</template>
			<div v-else class="px-4 py-3 text-xs text-ink-400 italic border-t border-ink-100">
				No advances linked yet — {{ bill.subcontractor_name }} has
				{{ fmtINR(unlinkedTotal) }} unallocated.
			</div>
		</div>

		<!-- Summary strip -->
		<div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ bill.is_direct ? "Subcontractor" : "Work Order" }}
				</div>
				<DeskLink
					v-if="!bill.is_direct"
					:to="`/subcontractor-work-orders/${bill.work_order}`"
					class="text-sm mt-0.5 block"
					>{{ bill.work_order }}</DeskLink
				>
				<div v-else class="text-sm text-ink-900 mt-0.5">{{ bill.subcontractor_name }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Date
				</div>
				<div class="text-sm text-ink-900 mt-0.5">{{ fmtDate(bill.date) }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Gross this period
				</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">
					{{ fmtINR(wf.gross) }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Retention
				</div>
				<div class="text-base font-semibold text-warning-700 tabular-nums mt-0.5">
					{{ fmtINR(wf.retention) }}
				</div>
				<div class="text-[10px] text-ink-500">{{ retPct }}% withheld</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 6px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Net payable
				</div>
				<div class="text-base font-semibold text-ink-900 tabular-nums mt-0.5">
					{{ fmtINR(wf.netPayable) }}
				</div>
			</div>
		</div>

		<!-- Bill lines -->
		<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
			<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					Lines — claimed against schedule of values
				</h3>
			</div>
			<div
				v-if="!bill.is_direct"
				class="px-4 py-2 bg-info-50 border-b border-info-200 text-[11px] text-ink-700"
			>
				<span class="font-medium text-ink-900">How qty is computed:</span>
				This period qty = (Measured to date from Certified MBs) − (Previously billed qty).
				Read-only on this bill.
			</div>
			<div
				v-else
				class="px-4 py-2 bg-info-50 border-b border-info-200 text-[11px] text-ink-700"
			>
				<span class="font-medium text-ink-900">Direct bill</span> — manual charge lines,
				not tied to a Work Order.
			</div>
			<div class="overflow-x-auto">
				<table class="w-full text-xs" style="min-width: 640px">
					<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
						<tr>
							<th class="text-left px-3 py-2">Scope</th>
							<th class="text-left px-3 py-2">Cost code</th>
							<th class="text-right px-3 py-2">Rate</th>
							<th class="text-right px-3 py-2">Measured to date</th>
							<th class="text-right px-3 py-2">Previously billed</th>
							<th class="text-right px-3 py-2">This period qty</th>
							<th class="text-right px-3 py-2">This period amount</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="(l, i) in bill.lines"
							:key="i"
							class="border-t border-ink-100 align-top"
						>
							<td class="px-3 py-2 text-ink-900">{{ l.scope || "—" }}</td>
							<td class="px-3 py-2">
								<span
									v-if="l.cost_code_label"
									class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-info-50 text-info-700"
									>{{ l.cost_code_label }}</span
								>
								<span v-else class="text-ink-300">—</span>
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-700">
								{{ l.rate ? fmtINR(l.rate) + "/" + (l.uom || "") : "—" }}
							</td>
							<td
								class="px-3 py-2 text-right tabular-nums text-info-700 font-medium"
							>
								{{
									l.measured_qty_to_date != null
										? Number(l.measured_qty_to_date).toLocaleString("en-IN")
										: "—"
								}}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-500">
								{{
									l.previous_qty != null
										? Number(l.previous_qty).toLocaleString("en-IN")
										: "—"
								}}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium">
								{{
									l.this_period_qty != null
										? Number(l.this_period_qty).toLocaleString("en-IN")
										: "—"
								}}
							</td>
							<td class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium">
								{{ fmtINR(l.this_period_amount) }}
							</td>
						</tr>
					</tbody>
					<tfoot>
						<tr class="border-t-2 border-ink-200 bg-ink-50">
							<td
								colspan="6"
								class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
							>
								Gross bill value
							</td>
							<td
								class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
							>
								{{ fmtINR(wf.gross) }}
							</td>
						</tr>
					</tfoot>
				</table>
			</div>
		</section>

		<!-- Taxes and Charges -->
		<section class="mt-6 bg-white border border-ink-200 rounded-lg overflow-hidden">
			<div
				class="bg-ink-50 px-4 py-2 border-b border-ink-200 flex items-center justify-between gap-3"
			>
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					Taxes and Charges
				</h3>
				<div v-if="editable" class="flex items-center gap-2">
					<label class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
						>Template</label
					>
					<div class="w-48">
						<DeskLinkPicker
							:model-value="bill.taxes_and_charges"
							doctype="Purchase Taxes and Charges Template"
							label-field="name"
							value-field="name"
							:filters="bill.company ? [['company', '=', bill.company]] : []"
							placeholder="— No tax —"
							@update:model-value="onPickTemplate"
						/>
					</div>
				</div>
				<span v-else class="text-[11px] text-ink-500">{{
					bill.taxes_and_charges || "No tax"
				}}</span>
			</div>
			<div class="overflow-x-auto">
				<table class="w-full text-xs" style="min-width: 480px">
					<thead class="bg-white text-ink-500 uppercase tracking-wider text-[10px]">
						<tr>
							<th class="text-left px-3 py-2 w-8">#</th>
							<th class="text-left px-3 py-2">Account Head</th>
							<th class="text-right px-3 py-2 w-24">Tax Rate</th>
							<th class="text-right px-3 py-2 w-32">Amount</th>
							<th v-if="editable" class="w-8"></th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(t, i) in wf.taxRows" :key="i" class="border-t border-ink-100">
							<td class="px-3 py-1.5 text-ink-500">{{ i + 1 }}</td>
							<td class="px-3 py-1.5">
								<DeskLinkPicker
									v-if="editable"
									v-model="bill.taxes[i].account_head"
									doctype="Account"
									label-field="name"
									value-field="name"
									:filters="accountFilters"
									placeholder="Account…"
								/>
								<span v-else class="text-ink-900">{{
									t.account_head || "—"
								}}</span>
							</td>
							<td class="px-3 py-1.5 text-right">
								<input
									v-if="editable"
									v-model.number="bill.taxes[i].rate"
									type="number"
									min="0"
									step="0.5"
									class="w-full bg-transparent text-right tabular-nums focus:outline-none py-1"
								/>
								<span v-else class="tabular-nums text-ink-700">{{ t.rate }}</span>
							</td>
							<td
								class="px-3 py-1.5 text-right tabular-nums text-ink-900 font-medium"
							>
								{{ fmtINR(t.amount) }}
							</td>
							<td v-if="editable" class="px-2 py-1.5 text-center">
								<button
									type="button"
									class="text-ink-400 hover:text-danger-600"
									@click="removeTaxRow(i)"
								>
									✕
								</button>
							</td>
						</tr>
						<tr v-if="!wf.taxRows.length">
							<td
								:colspan="editable ? 5 : 4"
								class="px-3 py-3 text-center text-ink-400 italic"
							>
								No tax. Pick a template or add a row.
							</td>
						</tr>
					</tbody>
					<tfoot v-if="wf.taxRows.length">
						<tr class="border-t border-ink-200 bg-ink-50">
							<td
								colspan="3"
								class="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-ink-700"
							>
								Total taxes
							</td>
							<td
								class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
							>
								{{ fmtINR(wf.tax) }}
							</td>
							<td v-if="editable"></td>
						</tr>
					</tfoot>
				</table>
			</div>
			<div v-if="editable" class="px-3 py-2 border-t border-ink-100">
				<button
					type="button"
					class="text-xs text-brand-700 hover:underline"
					@click="addTaxRow"
				>
					+ Add row
				</button>
			</div>
		</section>

		<!-- Retention/TDS/discount + waterfall -->
		<section class="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
			<div class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						Retention, TDS &amp; discount
					</h3>
				</div>
				<div class="p-4 space-y-3 text-xs">
					<div class="grid grid-cols-2 gap-3">
						<div>
							<label
								class="block text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Retention %</label
							>
							<input
								v-model.number="bill.retention_percent"
								:readonly="!editable"
								type="number"
								min="0"
								max="20"
								step="0.5"
								class="desk-input"
							/>
						</div>
						<div>
							<label
								class="block text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Advance recovery (₹)</label
							>
							<input
								v-model.number="bill.advance_recovery"
								:readonly="!editable"
								type="number"
								min="0"
								step="0.01"
								class="desk-input"
							/>
						</div>
					</div>
					<div class="grid grid-cols-2 gap-3">
						<div>
							<label
								class="block text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Bill type</label
							>
							<select
								v-model="bill.bill_type"
								:disabled="!editable"
								class="desk-input"
							>
								<option value="Normal">Normal</option>
								<option value="Final">Final (release retention)</option>
							</select>
						</div>
						<div>
							<label
								class="block text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Expense account</label
							>
							<DeskLinkPicker
								v-model="bill.expense_account"
								doctype="Account"
								label-field="name"
								value-field="name"
								:filters="
									bill.company
										? [
												['root_type', '=', 'Expense'],
												['is_group', '=', 0],
												['company', '=', bill.company],
										  ]
										: []
								"
								placeholder="Default (Subcontractor Charges)"
								:disabled="!editable"
							/>
						</div>
					</div>
					<div>
						<label class="flex items-center gap-2 py-0.5"
							><input
								type="checkbox"
								v-model="bill.apply_tds"
								:disabled="!editable"
								class="accent-brand-600"
							/><span class="text-ink-800">Apply TDS (withholding)</span></label
						>
						<div v-if="bill.apply_tds" class="mt-1.5">
							<label
								class="block text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Withholding category</label
							>
							<DeskLinkPicker
								v-model="bill.tax_withholding_category"
								doctype="Tax Withholding Category"
								label-field="name"
								value-field="name"
								placeholder="Pick category…"
								:disabled="!editable"
							/>
						</div>
					</div>
					<div>
						<label
							class="block text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1"
							>Additional Discount</label
						>
						<div class="flex items-center gap-2">
							<select
								v-model="bill.additional_discount_on"
								:disabled="!editable"
								class="desk-input !w-32"
							>
								<option>Net Total</option>
								<option>Grand Total</option>
							</select>
							<input
								v-model.number="discValue"
								:readonly="!editable"
								type="number"
								min="0"
								step="0.01"
								class="desk-input flex-1"
							/>
							<div class="flex border border-ink-200 rounded-md overflow-hidden">
								<button
									type="button"
									:disabled="!editable"
									class="px-2.5 py-1"
									:class="
										discType === '%'
											? 'bg-brand-50 text-brand-700 font-medium'
											: 'bg-white text-ink-600'
									"
									@click="discType = '%'"
								>
									%
								</button>
								<button
									type="button"
									:disabled="!editable"
									class="px-2.5 py-1 border-l border-ink-200"
									:class="
										discType === '₹'
											? 'bg-brand-50 text-brand-700 font-medium'
											: 'bg-white text-ink-600'
									"
									@click="discType = '₹'"
								>
									₹
								</button>
							</div>
						</div>
						<p class="text-[10px] text-ink-400 mt-1">
							Apply on <span class="font-medium">Net Total</span> (before tax) or
							<span class="font-medium">Grand Total</span> (after tax).
						</p>
					</div>
					<button
						v-if="editable"
						class="desk-save-btn w-full"
						:disabled="savingBilling"
						@click="saveBilling"
					>
						{{ savingBilling ? "Saving…" : "Save billing" }}
					</button>
				</div>
			</div>

			<div class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						Net payable
					</h3>
				</div>
				<div class="p-4 text-xs">
					<div class="flex justify-between py-1">
						<span class="text-ink-600">Gross bill value</span
						><span class="tabular-nums font-medium">{{ fmtINR(wf.gross) }}</span>
					</div>
					<div
						v-if="bill.additional_discount_on === 'Net Total' && wf.netDiscount"
						class="flex justify-between py-1"
					>
						<span class="text-ink-500">Less: Discount (on Net Total)</span
						><span class="tabular-nums text-ink-600"
							>({{ fmtINR(wf.netDiscount) }})</span
						>
					</div>
					<div class="flex justify-between py-1 border-t border-ink-100">
						<span class="text-ink-700 font-medium">Taxable value</span
						><span class="tabular-nums font-medium">{{ fmtINR(wf.taxable) }}</span>
					</div>
					<div class="flex justify-between py-1">
						<span class="text-ink-500"
							>Add: Taxes<span v-if="taxRatePct"> (@ {{ taxRatePct }}%)</span></span
						><span class="tabular-nums text-ink-700">+ {{ fmtINR(wf.tax) }}</span>
					</div>
					<div class="flex justify-between py-1 border-t border-ink-100">
						<span class="text-ink-700 font-medium">{{
							bill.additional_discount_on === "Grand Total"
								? "Grand total"
								: "Invoice value"
						}}</span
						><span class="tabular-nums font-medium">{{ fmtINR(wf.grandTotal) }}</span>
					</div>
					<template
						v-if="bill.additional_discount_on === 'Grand Total' && wf.grandDiscount"
					>
						<div class="flex justify-between py-1">
							<span class="text-ink-500">Less: Discount (on Grand Total)</span
							><span class="tabular-nums text-ink-600"
								>({{ fmtINR(wf.grandDiscount) }})</span
							>
						</div>
						<div class="flex justify-between py-1 border-t border-ink-100">
							<span class="text-ink-700 font-medium">Invoice value</span
							><span class="tabular-nums font-medium">{{
								fmtINR(wf.invoiceValue)
							}}</span>
						</div>
					</template>
					<div v-if="wf.tds" class="flex justify-between py-1">
						<span class="text-ink-500">Less: TDS withheld @ {{ bill.tds_rate }}%</span
						><span class="tabular-nums text-ink-600">({{ fmtINR(wf.tds) }})</span>
					</div>
					<div class="flex justify-between py-1">
						<span class="text-ink-500"
							>Less: Retention held @ {{ bill.retention_percent }}%</span
						>
						<span class="tabular-nums text-warning-700"
							>({{ fmtINR(wf.retention) }})</span
						>
					</div>
					<div class="text-[10px] text-ink-400 -mt-0.5 mb-0.5">
						Held on your books, released on the final bill.
					</div>
					<div v-if="wf.advance" class="flex justify-between py-1">
						<span class="text-ink-500">Less: Advance recovery</span
						><span class="tabular-nums text-ink-600">({{ fmtINR(wf.advance) }})</span>
					</div>
					<div class="flex justify-between py-2 border-t-2 border-ink-200 mt-1">
						<span class="font-semibold text-ink-900"
							>Net payable to subcontractor</span
						>
						<span class="tabular-nums font-bold text-base text-brand-700">{{
							fmtINR(wf.netPayable)
						}}</span>
					</div>
					<!-- advances settle the payable (like payments), shown below the total -->
					<div v-if="advanceAdjusted > 0" class="flex justify-between py-1">
						<span class="text-ink-500">Advance adjusted</span
						><span class="tabular-nums text-info-700"
							>− {{ fmtINR(advanceAdjusted) }}</span
						>
					</div>
					<template v-if="isSubmitted && advanceAdjusted > 0">
						<div class="flex justify-between py-1">
							<span class="text-ink-500">Paid</span
							><span class="tabular-nums text-ink-600">{{
								fmtINR(payment.paid)
							}}</span>
						</div>
						<div class="flex justify-between py-1">
							<span
								class="font-medium"
								:class="
									payment.outstanding > 0.01
										? 'text-danger-700'
										: 'text-success-700'
								"
								>Outstanding</span
							><span
								class="tabular-nums font-medium"
								:class="
									payment.outstanding > 0.01
										? 'text-danger-700'
										: 'text-success-700'
								"
								>{{ fmtINR(payment.outstanding) }}</span
							>
						</div>
					</template>
				</div>
			</div>
		</section>

		<!-- Attachments -->
		<section class="mt-6">
			<input ref="fileInput" type="file" multiple class="hidden" @change="onFilesPicked" />
			<div class="flex items-center justify-between mb-2 gap-3">
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
					Attachments
					<span v-if="attachments.length" class="text-ink-400 font-normal"
						>({{ attachments.length }})</span
					>
				</h3>
				<button
					type="button"
					class="desk-save-btn !text-xs"
					:disabled="uploading > 0"
					@click="fileInput?.click()"
				>
					{{ uploading > 0 ? `Uploading… (${uploading})` : "+ Upload" }}
				</button>
			</div>
			<div
				v-if="attachments.length"
				class="bg-white border border-ink-200 rounded-lg overflow-hidden"
			>
				<table class="w-full text-xs">
					<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
						<tr>
							<th class="w-8"></th>
							<th class="text-left px-3 py-1.5">File</th>
							<th class="text-right px-3 py-1.5">Size</th>
							<th class="text-left px-3 py-1.5">Uploaded</th>
							<th class="text-left px-3 py-1.5">By</th>
							<th class="w-8"></th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="att in attachments"
							:key="att.name"
							class="border-t border-ink-100 hover:bg-brand-50/40"
						>
							<td class="px-2 py-2 text-base text-center">
								{{ fileIcon(att.file_url || att.file_name) }}
							</td>
							<td class="px-3 py-2">
								<a
									v-if="att.file_url"
									:href="att.file_url"
									target="_blank"
									rel="noopener"
									class="text-brand-700 hover:underline truncate block max-w-xs"
									:title="att.file_name"
									>{{ att.file_name }}</a
								>
								<span v-else class="text-ink-700">{{ att.file_name }}</span>
							</td>
							<td class="px-3 py-2 text-right text-ink-600 tabular-nums">
								{{ formatFileSize(att.file_size) }}
							</td>
							<td class="px-3 py-2 text-ink-600">{{ fmtDate(att.creation) }}</td>
							<td class="px-3 py-2">
								<FrappeUserBadge :user-id="att.owner" size="xs" />
							</td>
							<td class="px-1 py-2 text-center">
								<button
									type="button"
									class="text-xs px-1.5 py-0.5 border border-ink-200 bg-white hover:bg-danger-50 text-danger-700"
									style="border-radius: 4px"
									:title="`Delete ${att.file_name}`"
									@click="onDeleteFile(att)"
								>
									✕
								</button>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
			<div v-else class="py-6 text-center border border-dashed border-ink-200 rounded-lg">
				<div class="text-sm text-ink-500 mb-1">No attachments yet.</div>
				<div class="text-xs text-ink-400 italic">
					Invoices, measurement sheets, and site photos go here.
				</div>
			</div>
		</section>

		<!-- Make Payment modal (inline — posts a Payment Entry, no Desk redirect) -->
		<div
			v-if="pay.open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto"
			@click.self="pay.open = false"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-md shadow-xl rounded-xl"
				@click.stop
			>
				<header
					class="px-4 py-3 border-b border-ink-200 flex items-center justify-between"
				>
					<h2 class="text-sm font-semibold text-ink-900">Make payment</h2>
					<button
						type="button"
						class="text-ink-400 hover:text-ink-900"
						@click="pay.open = false"
					>
						✕
					</button>
				</header>
				<div class="px-4 py-4 space-y-3">
					<div class="text-sm text-ink-700">
						Pay <span class="font-medium">{{ bill.subcontractor_name }}</span> against
						<span class="font-mono text-xs">{{ bill.ra_no || bill.name }}</span
						>. Outstanding
						<span class="font-semibold text-ink-900 tabular-nums">{{
							fmtINR(payment.outstanding)
						}}</span
						>.
					</div>
					<div class="grid grid-cols-2 gap-3">
						<div>
							<label
								class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Amount <span class="text-danger-600">*</span></label
							>
							<input
								v-model.number="pay.amount"
								type="number"
								min="0"
								class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
							/>
						</div>
						<div>
							<label
								class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Date</label
							>
							<input
								v-model="pay.date"
								type="date"
								class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
							/>
						</div>
					</div>
					<div>
						<label
							class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
							>Paid from account <span class="text-danger-600">*</span></label
						>
						<select
							v-model="pay.account"
							class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
						>
							<option value="" disabled>Bank / Cash account…</option>
							<option v-for="a in payAccounts" :key="a.name" :value="a.name">
								{{ a.name }} ({{ a.account_type }})
							</option>
						</select>
					</div>
					<div class="grid grid-cols-2 gap-3">
						<div>
							<label
								class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Mode of payment</label
							>
							<select
								v-model="pay.mode_of_payment"
								class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
							>
								<option v-for="m in payModes" :key="m" :value="m">{{ m }}</option>
							</select>
						</div>
						<div>
							<label
								class="block text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1"
								>Reference no.
								<span class="text-ink-400 normal-case">(optional)</span></label
							>
							<input
								v-model="pay.reference_no"
								type="text"
								placeholder="UTR / cheque no."
								class="w-full text-sm px-2.5 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
							/>
						</div>
					</div>
				</div>
				<footer
					class="px-4 py-3 border-t border-ink-200 flex items-center justify-end gap-2"
				>
					<button
						type="button"
						class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
						@click="pay.open = false"
					>
						Cancel
					</button>
					<button
						type="button"
						class="text-xs desk-save-btn"
						:disabled="pay.saving"
						@click="savePayment"
					>
						{{ pay.saving ? "Recording…" : "Record payment" }}
					</button>
				</footer>
			</div>
		</div>

		<!-- Link advance modal -->
		<div
			v-if="adv.open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6 overflow-y-auto"
			@click.self="adv.open = false"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-lg shadow-xl rounded-xl flex flex-col max-h-[85vh]"
				@click.stop
			>
				<header
					class="px-4 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0"
				>
					<h2 class="text-sm font-semibold text-ink-900">Link advance payment</h2>
					<button
						type="button"
						class="text-ink-400 hover:text-ink-900"
						@click="adv.open = false"
					>
						✕
					</button>
				</header>
				<div class="px-4 py-4 overflow-y-auto flex-1 space-y-3">
					<div class="text-xs text-ink-600">
						Unlinked advances paid to
						<span class="font-medium text-ink-900">{{ bill.subcontractor_name }}</span
						>. Current outstanding
						<span class="font-semibold text-ink-900 tabular-nums">{{
							fmtINR(payment.outstanding)
						}}</span>
						— the suggested allocation settles as much of it as each advance allows.
					</div>
					<div v-if="availableAdvances.length" class="space-y-2">
						<div
							v-for="a in availableAdvances"
							:key="a.payment_entry"
							class="border border-ink-200 rounded-lg px-3 py-2.5"
						>
							<div class="flex items-center justify-between gap-2">
								<div class="min-w-0">
									<div class="font-mono text-xs text-ink-900 truncate">
										{{ a.payment_entry }}
									</div>
									<div class="text-[11px] text-ink-500">
										{{ fmtDate(a.date)
										}}<span v-if="a.mode_of_payment">
											· {{ a.mode_of_payment }}</span
										>
									</div>
								</div>
								<div class="text-right flex-shrink-0">
									<div class="text-xs text-ink-500">Unallocated</div>
									<div class="text-sm font-semibold text-ink-900 tabular-nums">
										{{ fmtINR(a.unallocated) }}
									</div>
								</div>
							</div>
							<div class="flex items-center gap-2 mt-2">
								<label
									class="text-[10px] uppercase tracking-wider text-ink-500 font-medium flex-shrink-0"
									>Adjust</label
								>
								<input
									v-model.number="advAlloc[a.payment_entry]"
									type="number"
									min="0"
									:max="a.unallocated"
									class="flex-1 text-sm px-2.5 py-1.5 border border-ink-200 rounded-md text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
								/>
								<button
									type="button"
									class="text-xs px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-medium rounded-md flex-shrink-0 disabled:opacity-60"
									:disabled="adv.saving === a.payment_entry"
									@click="doLink(a)"
								>
									{{ adv.saving === a.payment_entry ? "Linking…" : "Link" }}
								</button>
							</div>
						</div>
					</div>
					<div v-else class="text-xs text-ink-400 italic py-2">
						No unlinked advances left for this subcontractor.
					</div>
					<div v-if="adv.error" class="text-[11px] text-danger-600">{{ adv.error }}</div>
				</div>
			</div>
		</div>
	</DeskPage>
</template>
