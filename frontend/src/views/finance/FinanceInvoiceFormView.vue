<script setup>
// Project Finance › Invoice form — a full PAGE (not a modal), for create
// (/project-finance/invoices/new) and edit of a Draft (/project-finance/invoices/:id/edit;
// a non-Draft bounces to the detail page). Item lines (qty × rate), then taxes & discount
// via templates + a live waterfall — the same pattern as the Subcontractor Bill. Saves a
// draft Sales Invoice via api.invoice.
import { computed, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { getInvoice, saveInvoice, getInvoiceTaxTemplateRows, getInvoiceTerms } from "@/data/invoiceApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { activeCompanyFilter } from "@/composables/useActiveCompany";
import { fmtINR } from "@/utils/format";

const props = defineProps({ id: { type: String, default: "" } });
const router = useRouter();
const companyFilter = activeCompanyFilter();
const isEdit = computed(() => !!props.id);

function blankLine() {
	return { description: "", qty: 1, rate: null };
}
const form = reactive({
	customer: "",
	project: "",
	date: new Date().toISOString().slice(0, 10),
	due_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
	lines: [blankLine()],
	taxes_and_charges: "",
	taxes: [],
	discount_on: "Net Total",
	discount_type: "%", // "%" | "₹"
	discount_value: 0,
	tc_name: "",
	terms: "",
});
const termsOpen = ref(false);
const errors = reactive({ customer: "", lines: "" });
const saving = ref(false);
const loading = ref(isEdit.value);

if (isEdit.value) {
	getInvoice(props.id)
		.then((inv) => {
			if (inv.docstatus !== 0) {
				router.replace(`/project-finance/invoices/${props.id}`);
				return;
			}
			Object.assign(form, {
				customer: inv.customer,
				project: inv.project || "",
				date: inv.date,
				due_date: inv.due_date || "",
				lines: (inv.items || []).map((l) => ({ description: l.description, qty: l.qty ?? 1, rate: l.rate })),
				taxes_and_charges: inv.taxes_and_charges || "",
				taxes: (inv.taxes || []).map((t) => ({ charge_type: t.charge_type, account_head: t.account_head, description: t.description, rate: t.rate })),
				discount_on: inv.additional_discount_on || "Net Total",
				discount_type: Number(inv.discount_amount) > 0 ? "₹" : "%",
				discount_value: Number(inv.discount_amount) > 0 ? Number(inv.discount_amount) : Number(inv.additional_discount_percentage) || 0,
				tc_name: inv.tc_name || "",
				terms: inv.terms || "",
			});
			if (!form.lines.length) form.lines = [blankLine()];
			termsOpen.value = !!inv.terms;
		})
		.catch((err) => showToast(err.message || "Failed to load invoice", "error"))
		.finally(() => (loading.value = false));
}

// --- items ---
function lineAmount(l) {
	return (Number(l.qty) || 0) * (Number(l.rate) || 0);
}
function addLine() {
	form.lines.push(blankLine());
}
function removeLine(idx) {
	form.lines.splice(idx, 1);
	if (!form.lines.length) form.lines.push(blankLine());
}

// --- taxes (template → rows, editable; Bill pattern) ---
async function applyTemplate(tpl) {
	form.taxes_and_charges = tpl || "";
	if (!tpl) return;
	try {
		form.taxes = await getInvoiceTaxTemplateRows(tpl);
	} catch (err) {
		showToast(err.message || "Failed to load tax template", "error");
	}
}
function addTaxRow() {
	form.taxes.push({ charge_type: "On Net Total", account_head: "", rate: 0 });
	form.taxes_and_charges = "";
}
function removeTaxRow(idx) {
	form.taxes.splice(idx, 1);
	form.taxes_and_charges = "";
}

// --- terms ---
async function onPickTerms(name) {
	form.tc_name = name || "";
	if (!name) return;
	try {
		form.terms = (await getInvoiceTerms(name)).terms || "";
		termsOpen.value = true;
	} catch {
		/* ignore */
	}
}

// --- live waterfall ---
const wf = computed(() => {
	const net = form.lines.reduce((a, l) => a + lineAmount(l), 0);
	const discBase = (base) => (form.discount_type === "%" ? (base * (Number(form.discount_value) || 0)) / 100 : Number(form.discount_value) || 0);
	const netDiscount = form.discount_on === "Net Total" ? discBase(net) : 0;
	const taxable = Math.max(0, net - netDiscount);
	const taxRows = form.taxes.map((t) => ({ ...t, amount: (taxable * (Number(t.rate) || 0)) / 100 }));
	const tax = taxRows.reduce((a, r) => a + r.amount, 0);
	const grandTotal = taxable + tax;
	const grandDiscount = form.discount_on === "Grand Total" ? discBase(grandTotal) : 0;
	const invoiceTotal = Math.max(0, grandTotal - grandDiscount);
	return { net, netDiscount, taxable, taxRows, tax, grandTotal, grandDiscount, invoiceTotal };
});

const breadcrumbs = computed(() => [
	{ label: "Project Finance", to: "/project-finance" },
	{ label: "Invoices", to: "/project-finance/invoices" },
	{ label: isEdit.value ? `Edit ${props.id}` : "New" },
]);

async function save() {
	errors.customer = "";
	errors.lines = "";
	if (!form.customer) errors.customer = "Customer is required.";
	const lines = form.lines.filter((l) => (l.description || "").trim() && lineAmount(l) > 0);
	if (!lines.length) errors.lines = "Add at least one item with a quantity and rate.";
	if (errors.customer || errors.lines) return;

	saving.value = true;
	try {
		const res = await saveInvoice({
			name: isEdit.value ? props.id : undefined,
			customer: form.customer,
			project: form.project || undefined,
			date: form.date,
			due_date: form.due_date || undefined,
			items: lines.map((l) => ({ description: l.description.trim(), qty: Number(l.qty) || 1, rate: Number(l.rate) })),
			taxes_and_charges: form.taxes_and_charges || undefined,
			taxes: form.taxes.filter((t) => t.account_head).map((t) => ({ charge_type: t.charge_type, account_head: t.account_head, description: t.description, rate: Number(t.rate) || 0 })),
			additional_discount_on: form.discount_on,
			additional_discount_percentage: form.discount_type === "%" ? Number(form.discount_value) || 0 : 0,
			discount_amount: form.discount_type === "₹" ? Number(form.discount_value) || 0 : 0,
			tc_name: form.tc_name || undefined,
			terms: form.terms || undefined,
		});
		showToast(isEdit.value ? "Invoice updated." : "Invoice saved as draft.");
		router.push(`/project-finance/invoices/${res.name}`);
	} catch (err) {
		showToast(err.message || "Failed to save", "error");
	} finally {
		saving.value = false;
	}
}
</script>

<template>
	<DeskPage :title="isEdit ? `Edit ${id}` : 'New Invoice'" :breadcrumbs="breadcrumbs" subtitle="Bills the customer — Submit posts it as a receivable.">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar :save-label="isEdit ? 'Save invoice' : 'Create invoice'" :saving="saving" @save="save" @cancel="router.back()" />
			</template>

			<div v-if="loading" class="py-16 text-center text-sm text-ink-400">Loading…</div>
			<template v-else>
				<DeskSection title="Invoice details" :cols="4">
					<DeskField label="Customer" required :error="errors.customer">
						<DeskLinkPicker v-model="form.customer" doctype="Customer" label-field="customer_name" value-field="name" placeholder="Pick a customer…" />
					</DeskField>
					<DeskField label="Project" hint="Optional — tags the income to a project.">
						<DeskLinkPicker v-model="form.project" doctype="Project" label-field="project_name" value-field="name" :filters="companyFilter" placeholder="None" />
					</DeskField>
					<DeskField label="Invoice date"><DeskInput v-model="form.date" type="date" /></DeskField>
					<DeskField label="Due date"><DeskInput v-model="form.due_date" type="date" /></DeskField>
				</DeskSection>

				<DeskSection title="Items" :cols="1">
					<div>
						<div class="hidden md:grid grid-cols-[1fr_110px_140px_140px_36px] gap-2 text-[10px] uppercase tracking-wider text-ink-500 font-medium px-1 mb-1">
							<span>Description</span><span class="text-right">Qty</span><span class="text-right">Rate</span><span class="text-right">Amount</span><span></span>
						</div>
						<div v-for="(l, idx) in form.lines" :key="idx" class="grid grid-cols-2 md:grid-cols-[1fr_110px_140px_140px_36px] gap-2 items-center mb-2">
							<DeskInput v-model="l.description" placeholder="e.g. Block A — RA-4 milestone" class="col-span-2 md:col-span-1" />
							<DeskInput v-model.number="l.qty" type="number" min="0" placeholder="Qty" class="text-right" />
							<DeskInput v-model.number="l.rate" type="number" min="0" placeholder="Rate" class="text-right" />
							<div class="text-xs tabular-nums text-ink-700 text-right">{{ fmtINR(lineAmount(l)) }}</div>
							<button type="button" class="text-ink-400 hover:text-danger-600 text-sm" aria-label="Remove line" @click="removeLine(idx)">✕</button>
						</div>
						<p v-if="errors.lines" class="text-[11px] text-danger-600 mb-2">{{ errors.lines }}</p>
						<button type="button" class="text-xs text-brand-700 hover:underline" @click="addLine">+ Add item</button>
					</div>
				</DeskSection>

				<!-- taxes + collapsible terms on the left, live totals pinned on the right -->
				<div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] gap-6 mb-6">
					<div class="space-y-5 min-w-0">
						<!-- taxes & discount (template-driven, Bill pattern) -->
						<div>
							<h3 class="desk-section-title">Taxes &amp; discount</h3>
							<hr class="desk-divider" />
							<div class="flex items-center gap-2 mb-2 mt-2">
								<div class="w-64">
									<DeskLinkPicker :model-value="form.taxes_and_charges" doctype="Sales Taxes and Charges Template" label-field="title" value-field="name" placeholder="Tax template…" @update:model-value="applyTemplate" />
								</div>
								<button type="button" class="text-[11px] text-brand-700 hover:underline whitespace-nowrap" @click="addTaxRow">+ Add row</button>
							</div>
							<div v-if="form.taxes.length" class="space-y-1.5">
								<div v-for="(row, idx) in form.taxes" :key="idx" class="flex items-center gap-2">
									<input v-model="row.account_head" type="text" placeholder="Tax account head" class="w-56 text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200" />
									<input v-model.number="row.rate" type="number" min="0" step="0.5" class="w-16 text-xs px-2 py-1.5 border border-ink-200 rounded-md text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-brand-200" />
									<span class="text-[10px] text-ink-400">%</span>
									<button type="button" class="text-ink-400 hover:text-danger-600 text-xs" @click="removeTaxRow(idx)">✕</button>
								</div>
							</div>
							<div class="flex items-center gap-2 flex-wrap mt-3">
								<span class="text-xs text-ink-500">Discount</span>
								<select v-model="form.discount_on" class="text-xs px-2 py-1.5 border border-ink-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-200">
									<option value="Net Total">On Net Total</option>
									<option value="Grand Total">On Grand Total</option>
								</select>
								<input v-model.number="form.discount_value" type="number" min="0" class="w-24 text-xs px-2 py-1.5 border border-ink-200 rounded-md text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-brand-200" />
								<div class="flex rounded-md border border-ink-200 overflow-hidden text-[11px]">
									<button type="button" class="px-2 py-1" :class="form.discount_type === '₹' ? 'bg-ink-900 text-white' : 'text-ink-600'" @click="form.discount_type = '₹'">₹</button>
									<button type="button" class="px-2 py-1" :class="form.discount_type === '%' ? 'bg-ink-900 text-white' : 'text-ink-600'" @click="form.discount_type = '%'">%</button>
								</div>
							</div>
						</div>

						<!-- collapsible terms -->
						<div>
							<button type="button" class="w-full flex items-center gap-2 text-left" @click="termsOpen = !termsOpen">
								<h3 class="desk-section-title">Terms &amp; conditions</h3>
								<span v-if="form.terms && !termsOpen" class="text-[10px] px-1.5 py-0.5 bg-brand-50 text-brand-700 rounded-full">set</span>
								<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-ink-400 transition-transform" :class="termsOpen ? 'rotate-90' : ''"><path d="M9 18l6-6-6-6" /></svg>
							</button>
							<hr class="desk-divider" />
							<div v-if="termsOpen" class="mt-2">
								<div class="w-64 mb-2">
									<DeskLinkPicker :model-value="form.tc_name" doctype="Terms and Conditions" label-field="name" value-field="name" placeholder="Import from template…" @update:model-value="onPickTerms" />
								</div>
								<textarea v-model="form.terms" rows="5" placeholder="Terms printed on the invoice — import a template above or write your own." class="w-full text-xs px-3 py-2 border border-ink-200 rounded-md leading-relaxed focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"></textarea>
							</div>
						</div>
					</div>

					<!-- live totals waterfall -->
					<div class="bg-ink-50 rounded-lg px-4 py-3 text-sm space-y-1 self-start">
						<div class="flex justify-between text-ink-600"><span>Net total</span><span class="tabular-nums">{{ fmtINR(wf.net) }}</span></div>
						<div v-if="wf.netDiscount > 0" class="flex justify-between text-ink-600"><span>Discount (on net)</span><span class="tabular-nums text-danger-700">− {{ fmtINR(wf.netDiscount) }}</span></div>
						<div v-if="wf.taxable !== wf.net" class="flex justify-between text-ink-600"><span>Taxable value</span><span class="tabular-nums">{{ fmtINR(wf.taxable) }}</span></div>
						<div v-for="(row, idx) in wf.taxRows" :key="idx" class="flex justify-between text-ink-600"><span>{{ row.account_head || "Tax" }} ({{ row.rate }}%)</span><span class="tabular-nums">{{ fmtINR(row.amount) }}</span></div>
						<div v-if="wf.grandDiscount > 0" class="flex justify-between text-ink-600"><span>Discount (on grand total)</span><span class="tabular-nums text-danger-700">− {{ fmtINR(wf.grandDiscount) }}</span></div>
						<div class="flex justify-between font-semibold text-ink-900 border-t border-ink-200 pt-1.5"><span>Invoice total</span><span class="tabular-nums">{{ fmtINR(wf.invoiceTotal) }}</span></div>
					</div>
				</div>
			</template>
		</DeskForm>
	</DeskPage>
</template>
