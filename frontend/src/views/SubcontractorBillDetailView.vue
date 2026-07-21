<script setup>
// Subcontractor Bill detail — summary, lines, the Draft-editable billing block
// (taxes template + rows, TDS, discount, retention, advance) with a live totals
// waterfall, Submit (generates the Purchase Invoice), Cancel, and a Payment panel
// (read-through to the generated PI). Country-agnostic: taxes come from any
// Purchase Taxes and Charges Template.

import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import {
	getBill,
	saveBill,
	submitBill,
	cancelBill,
	deleteBill,
	getTaxTemplateRows,
	recordBillPayment,
	listBillPayments,
} from "@/data/subcontractApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate, fmtINR } from "@/utils/format";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();

const bill = ref(null);
const payments = ref([]);
const busy = ref(false);
const savingBilling = ref(false);

async function load() {
	try {
		bill.value = await getBill(props.id);
		payments.value = bill.value.purchase_invoice ? await listBillPayments(props.id) : [];
	} catch (err) {
		showToast(err.message || "Failed to load bill", "error");
	}
}
watch(() => props.id, load, { immediate: true });

const isDraft = computed(() => bill.value?.docstatus === 0);
const isSubmitted = computed(() => bill.value?.docstatus === 1);
const payment = computed(() => bill.value?.payment || { paid: 0, outstanding: 0, status: "Unpaid" });

// --- live waterfall (mirrors the controller; server is authoritative on save) ---
const wf = computed(() => {
	const b = bill.value;
	if (!b) return {};
	const gross = (b.lines || []).reduce((a, l) => a + (Number(l.this_period_amount) || 0), 0);
	const pct = Number(b.additional_discount_percentage) || 0;
	const flat = Number(b.discount_amount) || 0;
	let netDiscount = 0,
		grandDiscount = 0;
	if (b.additional_discount_on === "Net Total") netDiscount = flat || (gross * pct) / 100;
	const taxable = Math.max(0, gross - netDiscount);
	const totalTaxes = (b.taxes || []).reduce((a, t) => a + (taxable * (Number(t.rate) || 0)) / 100, 0);
	const grand = taxable + totalTaxes;
	if (b.additional_discount_on === "Grand Total") grandDiscount = flat || (grand * pct) / 100;
	const invoiceValue = Math.max(0, grand - grandDiscount);
	const tds = b.apply_tds ? (taxable * (Number(b.tds_rate) || 0)) / 100 : 0;
	const retention = (taxable * (Number(b.retention_percent) || 0)) / 100;
	const advance = Number(b.advance_recovery) || 0;
	const net = Math.max(0, invoiceValue - tds - retention - advance);
	return { gross, netDiscount, taxable, totalTaxes, grand, grandDiscount, invoiceValue, tds, retention, advance, net };
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
	bill.value.taxes.push({ charge_type: "On Net Total", account_head: "", description: "", rate: 0 });
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
			additional_discount_percentage: b.additional_discount_percentage,
			discount_amount: b.discount_amount,
			advance_recovery: b.advance_recovery,
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
		bill.value = await saveBill(payload);
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
async function onSubmit() {
	if (wf.value.gross <= 0) {
		showToast("Nothing to bill — add a line with an amount.", "error");
		return;
	}
	const ok = await confirmDialog({
		title: `Submit Bill ${bill.value.ra_no}?`,
		message: `This posts the bill and generates the Purchase Invoice for ${fmtINR(wf.value.net)} net payable. You can't edit it afterwards.`,
		confirmLabel: "Submit",
	});
	if (!ok) return;
	busy.value = true;
	try {
		bill.value = await submitBill(bill.value.name);
		showToast(`Purchase Invoice ${bill.value.purchase_invoice} generated — bill submitted.`);
	} catch (err) {
		showToast(err.message || "Submit failed", "error");
	} finally {
		busy.value = false;
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

// --- payment ---
const payForm = reactive({ open: false, amount: 0, date: new Date().toISOString().slice(0, 10), mode_of_payment: "", reference_no: "" });
function openPay() {
	payForm.open = true;
	payForm.amount = payment.value.outstanding;
}
async function submitPayment() {
	busy.value = true;
	try {
		const res = await recordBillPayment({
			name: bill.value.name,
			amount: payForm.amount,
			date: payForm.date,
			mode_of_payment: payForm.mode_of_payment || undefined,
			reference_no: payForm.reference_no || undefined,
		});
		bill.value.payment = res.payment;
		payments.value = await listBillPayments(bill.value.name);
		payForm.open = false;
		showToast("Payment recorded.");
	} catch (err) {
		showToast(err.message || "Payment failed", "error");
	} finally {
		busy.value = false;
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Subcontractor Bills", to: "/subcontractor-bills" },
	{ label: bill.value?.name || props.id },
]);
const statusPills = computed(() => {
	if (!bill.value) return [];
	const pills = [bill.value.status];
	if (isSubmitted.value) pills.push(payment.value.status);
	return pills;
});
</script>

<template>
	<DeskPage
		v-if="bill"
		:title="`Subcontractor Bill ${bill.ra_no}`"
		:subtitle="`${bill.name} · ${bill.subcontractor_name || bill.subcontractor} · ${bill.project_name || bill.project}`"
		:breadcrumbs="breadcrumbs"
		:status="statusPills"
	>
		<template #actions>
			<button v-if="isDraft" class="desk-btn" :disabled="busy" @click="onEdit">Edit</button>
			<button v-if="isDraft" class="desk-save-btn" :disabled="busy" @click="onSubmit">Submit</button>
			<button
				v-if="isSubmitted && payment.outstanding > 0.01"
				class="desk-save-btn"
				:disabled="busy"
				@click="openPay"
			>
				Record payment
			</button>
			<button v-if="isSubmitted" class="desk-btn" :disabled="busy" @click="onCancel">Cancel</button>
			<button v-if="isDraft" class="desk-btn text-danger-700" :disabled="busy" @click="onDelete">Delete</button>
		</template>

		<!-- PI banner -->
		<div
			v-if="bill.purchase_invoice"
			class="mb-4 text-xs bg-success-50 border border-success-100 rounded-md px-3 py-2 text-success-800"
		>
			Purchase Invoice
			<DeskLink :to="`/app/purchase-invoice/${bill.purchase_invoice}`" class="font-mono">{{
				bill.purchase_invoice
			}}</DeskLink>
			generated · Invoiced {{ fmtINR(payment.invoiced) }} · Paid {{ fmtINR(payment.paid) }} · Outstanding
			<span class="font-medium">{{ fmtINR(payment.outstanding) }}</span>
		</div>

		<!-- summary strip -->
		<div class="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
			<div class="border border-ink-200 rounded-lg px-3 py-2">
				<div class="text-[10px] uppercase tracking-wider text-ink-400">
					{{ bill.is_direct ? "Subcontractor" : "Work Order" }}
				</div>
				<DeskLink
					v-if="!bill.is_direct"
					:to="`/subcontractor-work-orders/${bill.work_order}`"
					class="text-xs font-mono"
					>{{ bill.work_order }}</DeskLink
				>
				<div v-else class="text-xs font-medium text-ink-900">{{ bill.subcontractor_name }}</div>
			</div>
			<div class="border border-ink-200 rounded-lg px-3 py-2">
				<div class="text-[10px] uppercase tracking-wider text-ink-400">Date</div>
				<div class="text-xs text-ink-900">{{ fmtDate(bill.date) }}</div>
			</div>
			<div class="border border-ink-200 rounded-lg px-3 py-2">
				<div class="text-[10px] uppercase tracking-wider text-ink-400">Gross</div>
				<div class="text-sm font-semibold text-ink-900">{{ fmtINR(wf.gross) }}</div>
			</div>
			<div class="border border-ink-200 rounded-lg px-3 py-2">
				<div class="text-[10px] uppercase tracking-wider text-ink-400">Retention</div>
				<div class="text-sm font-semibold text-warning-700">{{ fmtINR(wf.retention) }}</div>
			</div>
			<div class="border border-ink-200 rounded-lg px-3 py-2">
				<div class="text-[10px] uppercase tracking-wider text-ink-400">Net payable</div>
				<div class="text-sm font-semibold text-brand-700">{{ fmtINR(wf.net) }}</div>
			</div>
		</div>

		<!-- lines -->
		<section class="mb-6">
			<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700 mb-2">Bill lines</h3>
			<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
				<table class="w-full text-xs" style="min-width: 560px">
					<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
						<tr>
							<th class="text-left px-3 py-2">Scope</th>
							<th class="text-left px-3 py-2">Cost code</th>
							<th class="text-right px-3 py-2">Qty</th>
							<th class="text-right px-3 py-2">Rate</th>
							<th class="text-right px-3 py-2">Amount</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(l, i) in bill.lines" :key="i" class="border-t border-ink-100">
							<td class="px-3 py-2 text-ink-900">{{ l.scope }}</td>
							<td class="px-3 py-2 text-ink-500">{{ l.cost_code_label || "—" }}</td>
							<td class="px-3 py-2 text-right tabular-nums">
								{{ l.this_period_qty ? Number(l.this_period_qty).toLocaleString("en-IN") : "—" }}
							</td>
							<td class="px-3 py-2 text-right tabular-nums">{{ l.rate ? fmtINR(l.rate) : "—" }}</td>
							<td class="px-3 py-2 text-right tabular-nums font-medium">{{ fmtINR(l.this_period_amount) }}</td>
						</tr>
					</tbody>
				</table>
			</div>
		</section>

		<div class="grid md:grid-cols-2 gap-6">
			<!-- taxes editor -->
			<section>
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700 mb-2">Taxes & charges</h3>
				<DeskField v-if="isDraft" label="Tax template">
					<DeskLinkPicker
						:model-value="bill.taxes_and_charges"
						doctype="Purchase Taxes and Charges Template"
						label-field="name"
						value-field="name"
						placeholder="— No tax —"
						@update:model-value="onPickTemplate"
					/>
				</DeskField>
				<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto mt-2">
					<table class="w-full text-xs" style="min-width: 420px">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-2 py-2">Account head</th>
								<th class="text-right px-2 py-2 w-16">Rate %</th>
								<th class="text-right px-2 py-2 w-24">Amount</th>
								<th v-if="isDraft" class="w-8"></th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="(t, i) in bill.taxes" :key="i" class="border-t border-ink-100">
								<td class="px-2 py-1">
									<DeskLinkPicker
										v-if="isDraft"
										v-model="t.account_head"
										doctype="Account"
										label-field="name"
										value-field="name"
										placeholder="Account…"
									/>
									<span v-else>{{ t.account_head }}</span>
								</td>
								<td class="px-2 py-1 text-right">
									<input
										v-if="isDraft"
										v-model.number="t.rate"
										type="number"
										min="0"
										step="0.5"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1 focus:outline-none"
									/>
									<span v-else class="tabular-nums">{{ t.rate }}</span>
								</td>
								<td class="px-2 py-1 text-right tabular-nums">
									{{ fmtINR((wf.taxable * (Number(t.rate) || 0)) / 100) }}
								</td>
								<td v-if="isDraft" class="px-2 py-1 text-center">
									<button type="button" class="text-ink-400 hover:text-danger-600" @click="removeTaxRow(i)">✕</button>
								</td>
							</tr>
							<tr v-if="!bill.taxes.length">
								<td :colspan="isDraft ? 4 : 3" class="px-2 py-3 text-center text-ink-400 italic">
									No tax. Pick a template or add a row.
								</td>
							</tr>
						</tbody>
					</table>
				</div>
				<button v-if="isDraft" type="button" class="text-xs text-brand-700 hover:underline mt-1" @click="addTaxRow">
					+ Add tax row
				</button>
			</section>

			<!-- adjustments + waterfall -->
			<section>
				<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700 mb-2">Withholding, discount & recovery</h3>
				<div class="grid grid-cols-2 gap-3">
					<DeskField label="Retention (%)">
						<DeskInput v-model.number="bill.retention_percent" type="number" min="0" step="0.5" :disabled="!isDraft" />
					</DeskField>
					<DeskField label="Advance recovery">
						<DeskInput v-model.number="bill.advance_recovery" type="number" min="0" :disabled="!isDraft" />
					</DeskField>
					<DeskField label="Bill type">
						<select
							v-model="bill.bill_type"
							:disabled="!isDraft"
							class="w-full border border-ink-200 rounded-md text-xs px-2 py-1.5 bg-white"
						>
							<option value="Normal">Normal</option>
							<option value="Final">Final (release retention)</option>
						</select>
					</DeskField>
					<DeskField label="Apply TDS">
						<label class="flex items-center gap-2 text-xs pt-1.5">
							<input v-model="bill.apply_tds" type="checkbox" :disabled="!isDraft" class="accent-brand-600" />
							withholding
						</label>
					</DeskField>
					<DeskField v-if="bill.apply_tds" label="Withholding category" class="col-span-2">
						<DeskLinkPicker
							v-model="bill.tax_withholding_category"
							doctype="Tax Withholding Category"
							label-field="name"
							value-field="name"
							placeholder="Pick category…"
							:disabled="!isDraft"
						/>
					</DeskField>
					<DeskField label="Discount on">
						<select
							v-model="bill.additional_discount_on"
							:disabled="!isDraft"
							class="w-full border border-ink-200 rounded-md text-xs px-2 py-1.5 bg-white"
						>
							<option value="Net Total">Net Total</option>
							<option value="Grand Total">Grand Total</option>
						</select>
					</DeskField>
					<DeskField label="Discount (%)">
						<DeskInput v-model.number="bill.additional_discount_percentage" type="number" min="0" step="0.5" :disabled="!isDraft" />
					</DeskField>
				</div>

				<!-- waterfall -->
				<div class="mt-4 bg-ink-50 border border-ink-200 rounded-lg px-3 py-2 text-xs space-y-1">
					<div class="flex justify-between"><span class="text-ink-600">Gross</span><span class="tabular-nums">{{ fmtINR(wf.gross) }}</span></div>
					<div v-if="wf.netDiscount" class="flex justify-between text-ink-500"><span>Less discount (net)</span><span class="tabular-nums">−{{ fmtINR(wf.netDiscount) }}</span></div>
					<div class="flex justify-between border-t border-ink-200 pt-1"><span class="text-ink-600">Taxable</span><span class="tabular-nums">{{ fmtINR(wf.taxable) }}</span></div>
					<div v-if="wf.totalTaxes" class="flex justify-between text-info-700"><span>Add taxes</span><span class="tabular-nums">+{{ fmtINR(wf.totalTaxes) }}</span></div>
					<div class="flex justify-between"><span class="text-ink-600">Grand total</span><span class="tabular-nums">{{ fmtINR(wf.grand) }}</span></div>
					<div v-if="wf.grandDiscount" class="flex justify-between text-ink-500"><span>Less discount (grand)</span><span class="tabular-nums">−{{ fmtINR(wf.grandDiscount) }}</span></div>
					<div v-if="wf.tds" class="flex justify-between text-warning-700"><span>Less TDS @ {{ bill.tds_rate }}%</span><span class="tabular-nums">−{{ fmtINR(wf.tds) }}</span></div>
					<div v-if="wf.retention" class="flex justify-between text-warning-700"><span>Less retention</span><span class="tabular-nums">−{{ fmtINR(wf.retention) }}</span></div>
					<div v-if="wf.advance" class="flex justify-between text-warning-700"><span>Less advance recovery</span><span class="tabular-nums">−{{ fmtINR(wf.advance) }}</span></div>
					<div class="flex justify-between border-t-2 border-ink-300 pt-1 font-bold text-brand-700"><span>Net payable</span><span class="tabular-nums">{{ fmtINR(wf.net) }}</span></div>
				</div>

				<button
					v-if="isDraft"
					class="desk-save-btn mt-3 w-full"
					:disabled="savingBilling"
					@click="saveBilling"
				>
					{{ savingBilling ? "Saving…" : "Save billing" }}
				</button>
			</section>
		</div>

		<!-- payments -->
		<section v-if="isSubmitted" class="mt-6">
			<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700 mb-2">Payments</h3>
			<div v-if="payForm.open" class="bg-white border border-ink-200 rounded-lg p-3 mb-3 grid grid-cols-2 md:grid-cols-4 gap-3">
				<DeskField label="Amount"><DeskInput v-model.number="payForm.amount" type="number" min="0" /></DeskField>
				<DeskField label="Date"><DeskInput v-model="payForm.date" type="date" /></DeskField>
				<DeskField label="Mode"><DeskInput v-model="payForm.mode_of_payment" placeholder="Bank / Cash / Cheque" /></DeskField>
				<DeskField label="Reference"><DeskInput v-model="payForm.reference_no" placeholder="NEFT / cheque no." /></DeskField>
				<div class="col-span-full flex gap-2 justify-end">
					<button class="desk-btn" @click="payForm.open = false">Cancel</button>
					<button class="desk-save-btn" :disabled="busy" @click="submitPayment">Save & pay</button>
				</div>
			</div>
			<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
				<table class="w-full text-xs" style="min-width: 480px">
					<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
						<tr>
							<th class="text-left px-3 py-2">Payment</th>
							<th class="text-left px-3 py-2">Date</th>
							<th class="text-left px-3 py-2">Mode</th>
							<th class="text-left px-3 py-2">Reference</th>
							<th class="text-right px-3 py-2">Amount</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="p in payments" :key="p.payment_entry" class="border-t border-ink-100">
							<td class="px-3 py-2 font-mono text-[11px]">{{ p.payment_entry }}</td>
							<td class="px-3 py-2 text-ink-500">{{ fmtDate(p.date) }}</td>
							<td class="px-3 py-2">{{ p.mode_of_payment || "—" }}</td>
							<td class="px-3 py-2 text-ink-500">{{ p.reference_no || "—" }}</td>
							<td class="px-3 py-2 text-right tabular-nums font-medium">{{ fmtINR(p.amount) }}</td>
						</tr>
						<tr v-if="!payments.length">
							<td colspan="5" class="px-3 py-3 text-center text-ink-400 italic">
								No payments yet.
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</section>
	</DeskPage>
</template>
