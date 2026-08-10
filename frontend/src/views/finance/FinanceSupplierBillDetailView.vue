<script setup>
// Project Finance › Bills › Supplier bill detail — a full page over one ERPNext Purchase
// Invoice. Summary strip, item lines, payments, supplier-advance adjustment, and the docstatus
// lifecycle: Submit/Delete/Edit (Draft), Pay/Cancel (Submitted). Pay = a real Payment Entry
// from a Bank/Cash account. Mirrors the customer-invoice detail (payable side).
import { computed, reactive, ref, watch } from "vue";
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
	availableSupplierBillAdvances,
	linkSupplierBillAdvance,
	unlinkSupplierBillAdvance,
} from "@/data/supplierBillApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { useWorkflow } from "@/composables/useWorkflow";
import { fmtDate, fmtINR } from "@/utils/format";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();
const confirmDialog = useConfirm();

// Defer to an active Frappe Workflow on Purchase Invoice when one is configured;
// otherwise the plain docstatus Submit/Cancel buttons render as before.
const {
	active: wfActive,
	state: wfState,
	transitions: wfTransitions,
	refresh: refreshWorkflow,
	applyAction: applyWorkflowAction,
} = useWorkflow("Purchase Invoice");

const bill = ref(null);
const payments = ref([]);
const availableAdvances = ref([]);
const loading = ref(true);
async function load() {
	loading.value = true;
	try {
		bill.value = await getSupplierBill(props.id);
		payments.value =
			bill.value.docstatus === 1 ? await listSupplierBillPayments(props.id) : [];
		// On-account advances to this supplier that can still be adjusted (draft or submitted).
		availableAdvances.value =
			bill.value.docstatus === 2 ? [] : await availableSupplierBillAdvances(props.id);
		await refreshWorkflow(props.id);
	} catch (err) {
		showToast(err.message || "Failed to load bill", "error");
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => bill.value?.docstatus === 0);
const isSubmitted = computed(() => bill.value?.docstatus === 1);
const state = computed(() => {
	if (!bill.value) return "";
	if (bill.value.docstatus === 2) return "Cancelled";
	if (bill.value.docstatus === 1) return "Submitted";
	return "Draft";
});
const payment = computed(
	() => bill.value?.payment || { invoiced: 0, paid: 0, outstanding: 0, status: "Draft" }
);
const lifecycleLabel = computed(() =>
	wfActive.value ? wfState.value || state.value : state.value
);
const statusPills = computed(() => {
	if (!bill.value) return [];
	return isSubmitted.value
		? [lifecycleLabel.value, payment.value.status]
		: [lifecycleLabel.value];
});

const breadcrumbs = [
	{ label: "Project Finance", to: "/project-finance" },
	{ label: "Bills", to: "/project-finance/bills" },
	{ label: props.id },
];

// --- lifecycle ---
const busy = ref(false);
async function onSubmit() {
	const ok = await confirmDialog({
		title: "Submit bill?",
		message: `Submit ${bill.value.name} (${fmtINR(
			bill.value.grand_total
		)})? It posts the payable and can then be paid.`,
		confirmLabel: "Submit",
	});
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
	const ok = await confirmDialog({
		title: "Cancel bill?",
		message: `Cancel ${bill.value.name}? Its payable and any allocations are reversed.`,
		confirmLabel: "Cancel bill",
		cancelLabel: "Keep",
		destructive: true,
	});
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
// Workflow-driven transition (only rendered when an active workflow governs the doctype).
async function onWorkflowAction(action) {
	busy.value = true;
	try {
		await applyWorkflowAction(bill.value.name, action);
		await load();
		showToast(`${action} done.`);
	} catch (err) {
		showToast(err.message || "Action failed", "error");
	} finally {
		busy.value = false;
	}
}
async function onDelete() {
	const ok = await confirmDialog({
		title: "Delete draft?",
		message: `Permanently delete ${bill.value.name}?`,
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await deleteSupplierBill(bill.value.name);
		showToast("Deleted.");
		router.push("/project-finance/bills");
	} catch (err) {
		showToast(err.message || "Delete failed", "error");
	}
}
function onPrint() {
	// Opens ERPNext's native Purchase Invoice print view in a new tab.
	window.open(
		`/printview?doctype=Purchase%20Invoice&name=${encodeURIComponent(
			bill.value.name
		)}&trigger_print=1`,
		"_blank"
	);
}

// --- pay ---
const pay = ref({
	open: false,
	amount: null,
	pay_from: "",
	date: "",
	mode_of_payment: "",
	reference_no: "",
	saving: false,
});
const payAccounts = ref([]);
const payModes = ref([]);
async function openPay() {
	if (!payAccounts.value.length) {
		try {
			[payAccounts.value, payModes.value] = await Promise.all([
				listBillPayAccounts(),
				listSupplierBillPaymentModes(),
			]);
		} catch {
			/* fall through */
		}
	}
	pay.value = {
		open: true,
		amount: Number(payment.value.outstanding) || null,
		pay_from:
			payAccounts.value.find((a) => a.account_type === "Bank")?.name ||
			payAccounts.value[0]?.name ||
			"",
		date: new Date().toISOString().slice(0, 10),
		mode_of_payment: payModes.value[0] || "",
		reference_no: "",
		saving: false,
	};
}
async function savePay() {
	const amt = Number(pay.value.amount) || 0;
	if (amt <= 0) return showToast("Enter an amount greater than zero.", "error");
	if (amt > Number(payment.value.outstanding) + 0.01)
		return showToast(
			`Can't exceed the outstanding ${fmtINR(payment.value.outstanding)}.`,
			"error"
		);
	if (!pay.value.pay_from) return showToast("Pick the account to pay from.", "error");
	pay.value.saving = true;
	try {
		await recordSupplierBillPayment({
			name: bill.value.name,
			amount: amt,
			date: pay.value.date,
			mode_of_payment: pay.value.mode_of_payment || undefined,
			pay_from: pay.value.pay_from,
			reference_no: pay.value.reference_no || undefined,
		});
		pay.value.open = false;
		await load();
		showToast("Payment made.");
	} catch (err) {
		showToast(err.message || "Payment failed", "error");
	} finally {
		pay.value.saving = false;
	}
}

// --- advance payments (ERPNext-native adjustment) ---
// Draft adjusts via the Purchase Invoice `advances` table; Submitted via Payment Reconciliation.
const linkedAdvances = computed(() => bill.value?.advances || []);
const advanceAdjusted = computed(() => Number(bill.value?.advance_adjusted) || 0);
const unlinkedTotal = computed(() =>
	availableAdvances.value.reduce((a, x) => a + Number(x.unallocated || 0), 0)
);
const canLink = computed(() => bill.value && bill.value.docstatus !== 2);
// Amount still owed the advance can settle: outstanding (submitted) or grand − advances (draft).
const remainingOutstanding = computed(() => {
	if (!bill.value) return 0;
	if (isSubmitted.value) return Number(payment.value.outstanding) || 0;
	return Math.max(Number(bill.value.grand_total) - advanceAdjusted.value, 0);
});

const adv = ref({ open: false, msg: "", error: "", saving: "" });
const advAlloc = reactive({});
function suggestAllocations() {
	for (const a of availableAdvances.value)
		advAlloc[a.payment_entry] = Math.min(Number(a.unallocated), remainingOutstanding.value);
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
		await linkSupplierBillAdvance({
			name: bill.value.name,
			payment_entry: a.payment_entry,
			amount: amt,
		});
		adv.value.open = false;
		await load();
		adv.value.msg = `Linked ${fmtINR(amt)} from ${
			a.payment_entry
		} — outstanding is now ${fmtINR(remainingOutstanding.value)}.`;
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
		await unlinkSupplierBillAdvance({
			name: bill.value.name,
			payment_entry: row.payment_entry,
		});
		await load();
		showToast("Advance unlinked.");
	} catch (err) {
		showToast(err.message || "Unlink failed", "error");
	}
}
</script>

<template>
	<DeskPage
		:title="bill ? bill.name : id"
		:subtitle="bill ? `Billed ${fmtDate(bill.date)} · due ${fmtDate(bill.due_date)}` : ''"
		:breadcrumbs="breadcrumbs"
	>
		<template v-if="bill" #actions>
			<div class="flex items-center gap-2">
				<StatusBadge v-for="s in statusPills" :key="s" :status="s" size="xs" />
				<button
					type="button"
					class="text-xs px-2.5 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md flex items-center gap-1.5"
					@click="onPrint"
				>
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="1.75"
							d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
						/>
					</svg>
					Print / PDF
				</button>
				<button
					v-if="isDraft"
					type="button"
					class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-danger-600 rounded-md"
					:disabled="busy"
					@click="onDelete"
				>
					Delete
				</button>
				<button
					v-if="isDraft"
					type="button"
					class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
					@click="router.push(`/project-finance/supplier-bills/${bill.name}/edit`)"
				>
					Edit
				</button>
				<!-- Plain docstatus lifecycle (no workflow configured) -->
				<button
					v-if="!wfActive && isDraft"
					type="button"
					class="text-xs desk-save-btn"
					:disabled="busy"
					@click="onSubmit"
				>
					Submit
				</button>
				<button
					v-if="isSubmitted && payment.outstanding > 0.01"
					type="button"
					class="text-xs desk-save-btn"
					:disabled="busy"
					@click="openPay"
				>
					Pay
				</button>
				<button
					v-if="!wfActive && isSubmitted"
					type="button"
					class="text-xs px-3 py-1.5 border border-warning-300 bg-warning-50 hover:bg-warning-100 text-warning-700 font-medium rounded-md"
					:disabled="busy"
					@click="onCancel"
				>
					Cancel
				</button>
				<!-- Workflow transitions (active workflow) -->
				<button
					v-for="t in wfActive ? wfTransitions : []"
					:key="t.action"
					type="button"
					class="text-xs desk-save-btn"
					:disabled="busy"
					@click="onWorkflowAction(t.action)"
				>
					{{ t.action }}
				</button>
			</div>
		</template>

		<div v-if="!bill" class="py-16 text-center text-sm text-ink-400">
			{{ loading ? "Loading…" : "Bill not found." }}
		</div>
		<div v-else class="space-y-4">
			<!-- draft / cancelled notice -->
			<div
				v-if="state === 'Draft'"
				class="px-4 py-2.5 bg-warning-50 border border-warning-200 rounded-lg text-sm text-warning-700"
			>
				Draft — not posted yet. Submit it to make it a payable and enable payment.
			</div>
			<div
				v-if="state === 'Cancelled'"
				class="px-4 py-2.5 bg-danger-50 border border-danger-200 rounded-lg text-sm text-danger-700"
			>
				Cancelled — no longer a payable and excluded from costs.
			</div>

			<!-- advance linked confirmation -->
			<div
				v-if="adv.msg"
				class="px-4 py-2.5 bg-success-50 border border-success-200 rounded-md text-xs text-success-700 flex items-center gap-2"
			>
				<span class="text-sm">✓</span><span class="font-medium">{{ adv.msg }}</span>
			</div>

			<!-- unlinked-advance suggestion -->
			<div
				v-if="canLink && availableAdvances.length && remainingOutstanding > 0.01"
				class="px-4 py-2.5 bg-info-50 border border-info-200 rounded-md text-xs text-ink-700 flex items-center justify-between gap-3 flex-wrap"
			>
				<span>
					<span class="font-medium text-ink-900"
						>{{ bill.supplier_name }} has {{ fmtINR(unlinkedTotal) }} in unlinked
						advance payment{{ availableAdvances.length === 1 ? "" : "s" }}</span
					>
					— link {{ availableAdvances.length === 1 ? "it" : "them" }} to this bill to
					settle the payable.
				</span>
				<button
					type="button"
					class="text-xs px-2.5 py-1 border border-info-200 bg-white hover:bg-info-50 text-info-700 font-medium flex-shrink-0 rounded-md"
					@click="openLinkAdvance"
				>
					Link advance →
				</button>
			</div>

			<!-- summary strip -->
			<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
				<div class="border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500">Supplier</div>
					<div class="text-sm font-medium text-ink-900 mt-0.5">
						{{ bill.supplier_name }}
					</div>
					<div
						v-if="bill.supplier_gstin"
						class="text-[10px] font-mono text-ink-400 mt-0.5"
					>
						{{ bill.supplier_gstin }}
					</div>
				</div>
				<div class="border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500">Project</div>
					<DeskLink
						v-if="bill.project"
						:to="`/projects/${bill.project}`"
						class="text-sm"
						>{{ bill.project_name || bill.project }}</DeskLink
					>
					<div v-else class="text-sm text-ink-500 mt-0.5">—</div>
				</div>
				<div class="border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500">Bill total</div>
					<div class="text-sm font-semibold text-ink-900 tabular-nums mt-0.5">
						{{ fmtINR(bill.grand_total) }}
					</div>
				</div>
				<div class="border border-ink-200 rounded-lg p-3">
					<div class="text-[10px] uppercase tracking-wider text-ink-500">
						{{ isSubmitted ? "Outstanding" : "Status" }}
					</div>
					<div
						v-if="isSubmitted"
						class="text-sm font-semibold tabular-nums mt-0.5"
						:class="
							payment.outstanding > 0.01 ? 'text-danger-700' : 'text-success-700'
						"
					>
						{{ fmtINR(payment.outstanding) }}
					</div>
					<div v-else class="text-sm text-ink-700 mt-0.5">{{ state }}</div>
				</div>
			</div>
			<div v-if="bill.bill_no" class="text-xs text-ink-500">
				Supplier invoice <span class="font-medium text-ink-700">{{ bill.bill_no }}</span
				><span v-if="bill.bill_date"> · {{ fmtDate(bill.bill_date) }}</span>
			</div>

			<!-- line items -->
			<section class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="bg-ink-50 px-4 py-2 border-b border-ink-200">
					<h3 class="text-[11px] uppercase tracking-wider font-semibold text-ink-700">
						Items
					</h3>
				</div>
				<table class="w-full text-xs">
					<thead class="text-ink-500 uppercase tracking-wider text-[10px]">
						<tr>
							<th class="text-left px-4 py-2">Description</th>
							<th class="text-right px-4 py-2">Qty</th>
							<th class="text-right px-4 py-2">Rate</th>
							<th class="text-right px-4 py-2">Amount</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="(l, idx) in bill.items"
							:key="idx"
							class="border-t border-ink-100"
						>
							<td class="px-4 py-2 text-ink-900">{{ l.description }}</td>
							<td class="px-4 py-2 text-right tabular-nums text-ink-600">
								{{ l.qty }}
							</td>
							<td class="px-4 py-2 text-right tabular-nums text-ink-600">
								{{ fmtINR(l.rate) }}
							</td>
							<td class="px-4 py-2 text-right tabular-nums font-medium text-ink-900">
								{{ fmtINR(l.amount) }}
							</td>
						</tr>
					</tbody>
				</table>
			</section>

			<!-- payments + advances (left) · totals waterfall (right) -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
				<section class="space-y-4">
					<!-- payments -->
					<div
						v-if="payments.length"
						class="bg-white border border-ink-200 rounded-lg overflow-hidden"
					>
						<div
							class="bg-ink-50 px-4 py-2 border-b border-ink-200 text-[11px] uppercase tracking-wider font-semibold text-ink-700"
						>
							Payments ({{ payments.length }})
						</div>
						<div
							v-for="p in payments"
							:key="p.payment_entry"
							class="flex items-center justify-between px-4 py-2.5 border-t border-ink-100 text-sm gap-2"
						>
							<span class="text-ink-600 min-w-0 truncate"
								>{{ fmtDate(p.date)
								}}<span v-if="p.mode_of_payment">
									· {{ p.mode_of_payment }}</span
								></span
							>
							<span class="flex items-center gap-2 flex-shrink-0">
								<DeskLink
									:to="`/app/payment-entry/${p.payment_entry}`"
									class="font-mono text-[11px] text-ink-500"
									>{{ p.payment_entry }}</DeskLink
								>
								<span class="tabular-nums text-success-700 font-medium">{{
									fmtINR(p.amount)
								}}</span>
							</span>
						</div>
					</div>

					<!-- Advance Payments (ERPNext PI "Advance Payments") -->
					<div
						v-if="linkedAdvances.length || (canLink && availableAdvances.length)"
						class="bg-white border border-ink-200 rounded-lg overflow-hidden"
					>
						<div
							class="bg-ink-50 px-4 py-2 border-b border-ink-200 flex items-center justify-between gap-3"
						>
							<span
								class="text-[11px] uppercase tracking-wider font-semibold text-ink-700"
								>Advance Payments</span
							>
							<button
								v-if="canLink && availableAdvances.length"
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
										v-if="canLink"
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
						<div
							v-else
							class="px-4 py-3 text-xs text-ink-400 italic border-t border-ink-100"
						>
							No advances linked yet — {{ bill.supplier_name }} has
							{{ fmtINR(unlinkedTotal) }} unallocated.
						</div>
					</div>
				</section>

				<!-- totals waterfall -->
				<section class="bg-ink-50 rounded-lg px-4 py-3 text-sm space-y-1 self-start">
					<div class="flex justify-between text-ink-600">
						<span>Net total</span
						><span class="tabular-nums">{{ fmtINR(bill.net_total) }}</span>
					</div>
					<div
						v-for="(t, idx) in bill.taxes"
						:key="'t' + idx"
						class="flex justify-between text-ink-600"
					>
						<span>{{ t.description }} ({{ t.rate }}%)</span
						><span class="tabular-nums">{{ fmtINR(t.tax_amount) }}</span>
					</div>
					<div
						class="flex justify-between font-semibold text-ink-900 border-t border-ink-200 pt-1.5"
					>
						<span>Bill total</span
						><span class="tabular-nums">{{ fmtINR(bill.grand_total) }}</span>
					</div>
					<div v-if="advanceAdjusted > 0" class="flex justify-between text-ink-600">
						<span>Advance adjusted</span
						><span class="tabular-nums text-info-700"
							>− {{ fmtINR(advanceAdjusted) }}</span
						>
					</div>
					<template v-if="isSubmitted">
						<div class="flex justify-between text-ink-600">
							<span>Paid</span
							><span class="tabular-nums">{{ fmtINR(payment.paid) }}</span>
						</div>
						<div
							class="flex justify-between font-semibold"
							:class="
								payment.outstanding > 0.01 ? 'text-danger-700' : 'text-success-700'
							"
						>
							<span>Outstanding</span
							><span class="tabular-nums">{{ fmtINR(payment.outstanding) }}</span>
						</div>
					</template>
					<div v-else-if="advanceAdjusted > 0" class="text-[10px] text-ink-400">
						Settles the payable when the bill is submitted.
					</div>
				</section>
			</div>
		</div>

		<!-- Pay modal -->
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
					<h2 class="text-sm font-semibold text-ink-900">Pay bill</h2>
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
						Pay <span class="font-medium">{{ bill.supplier_name }}</span> against
						<span class="font-mono text-xs">{{ bill.name }}</span
						>. Outstanding
						<span class="font-semibold text-ink-900 tabular-nums">{{
							fmtINR(payment.outstanding)
						}}</span
						>.
					</div>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Amount" required
							><DeskInput v-model.number="pay.amount" type="number" min="0"
						/></DeskField>
						<DeskField label="Date"
							><DeskInput v-model="pay.date" type="date"
						/></DeskField>
					</div>
					<DeskField label="Pay from" required>
						<DeskSelect v-model="pay.pay_from"
							><option value="" disabled>Bank / Cash account…</option>
							<option v-for="a in payAccounts" :key="a.name" :value="a.name">
								{{ a.name }} ({{ a.account_type }})
							</option></DeskSelect
						>
					</DeskField>
					<div class="grid grid-cols-2 gap-3">
						<DeskField label="Mode of payment"
							><DeskSelect v-model="pay.mode_of_payment"
								><option value="">—</option>
								<option v-for="m in payModes" :key="m" :value="m">
									{{ m }}
								</option></DeskSelect
							></DeskField
						>
						<DeskField label="Reference no."
							><DeskInput v-model="pay.reference_no" placeholder="UTR / cheque no."
						/></DeskField>
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
						@click="savePay"
					>
						{{ pay.saving ? "Paying…" : "Record payment" }}
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
						<span class="font-medium text-ink-900">{{ bill.supplier_name }}</span
						>. Current outstanding
						<span class="font-semibold text-ink-900 tabular-nums">{{
							fmtINR(remainingOutstanding)
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
						No unlinked advances left for this supplier.
					</div>
					<div v-if="adv.error" class="text-[11px] text-danger-600">{{ adv.error }}</div>
				</div>
			</div>
		</div>
	</DeskPage>
</template>
