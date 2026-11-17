<script setup>
// Supplier Quotation form — create + edit (draft only): what one supplier answered. Honors
// ?rfq=<id>&supplier=<id> to answer a Request for Quotation: the project and items come
// across (each line linked to the request line it answers) and the supplier's rates and lead
// times are typed against them. A line left without a rate reads as not quoted in the
// comparison. Taxes are a Purchase Taxes and Charges Template. Saved via save_supplier_quotation.
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { getSupplierQuotation, getRfqForSq, saveSupplierQuotation, todayISO } from "@/data/rfqApi";
import { getSupplierBillItemDetails, getSupplierBillTaxRows } from "@/data/supplierBillApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import CostCodePicker from "@/components/CostCodePicker.vue";
import { usePermissions } from "@/composables/usePermissions";
import { fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";

const route = useRoute();
const router = useRouter();
const { canEdit, canCreate } = usePermissions();

const editingId = computed(() => route.params.id || null);
const isEdit = computed(() => !!editingId.value);
const canSaveForm = computed(() =>
	isEdit.value ? canEdit("supplierQuotation") : canCreate("supplierQuotation")
);

function emptyLine() {
	return {
		item_code: "",
		description: "",
		qty: null,
		uom: "",
		rate: null,
		lead_time_days: null,
		cost_code: null,
		request_for_quotation_item: null,
		material_request: null,
		material_request_item: null,
	};
}
function toLine(l) {
	return {
		item_code: l.item_code || "",
		description: l.description || "",
		qty: l.qty,
		uom: l.uom || "",
		rate: l.rate || null,
		lead_time_days: l.lead_time_days ?? null,
		cost_code: l.cost_code || null,
		request_for_quotation_item: l.request_for_quotation_item || null,
		material_request: l.material_request || null,
		material_request_item: l.material_request_item || null,
	};
}

const form = ref({
	request_for_quotation: "",
	supplier: "",
	project: "",
	transaction_date: todayISO(),
	valid_till: "",
	quotation_number: "",
	payment_terms: "",
	notes: "",
	taxes_and_charges: "",
	lines: [emptyLine()],
});
// The request being answered: its suppliers (the only ones who may quote on it) and subject.
const rfq = ref(null);
const errors = ref({});
const saving = ref(false);

// Picking (or arriving with) a request brings its project and items across.
async function loadFromRfq(name, { keepLines = false } = {}) {
	form.value.request_for_quotation = name || "";
	if (!name) {
		rfq.value = null;
		return;
	}
	try {
		const pre = await getRfqForSq(name);
		rfq.value = pre;
		form.value.project = pre.project || form.value.project;
		if (!keepLines) form.value.lines = pre.lines.map(toLine);
		if (form.value.supplier && !pre.suppliers.some((s) => s.supplier === form.value.supplier))
			form.value.supplier = "";
	} catch (err) {
		rfq.value = null;
		form.value.request_for_quotation = "";
		showToast(err.message || __("Failed to load the request for quotation"), "error");
	}
}

watch(
	editingId,
	async (id) => {
		if (id) {
			try {
				const q = await getSupplierQuotation(id);
				if (q.state !== "Draft") {
					showToast(__("Only a draft quotation can be edited."), "error");
					router.replace(`/procurement/supplier-quotations/${id}`);
					return;
				}
				form.value = {
					request_for_quotation: q.request_for_quotation || "",
					supplier: q.supplier || "",
					project: q.project || "",
					transaction_date: q.transaction_date || todayISO(),
					valid_till: q.valid_till || "",
					quotation_number: q.quotation_number || "",
					payment_terms: q.payment_terms || "",
					notes: q.notes || "",
					taxes_and_charges: q.taxes_and_charges || "",
					lines: (q.items || []).map(toLine),
				};
				if (!form.value.lines.length) form.value.lines = [emptyLine()];
				if (q.request_for_quotation)
					await loadFromRfq(q.request_for_quotation, { keepLines: true });
			} catch (err) {
				showToast(err.message || __("Failed to load quotation"), "error");
			}
			return;
		}
		if (route.query.rfq) {
			form.value.supplier = route.query.supplier || "";
			await loadFromRfq(route.query.rfq);
		}
	},
	{ immediate: true }
);

async function onPickItem(line) {
	if (!line.item_code) return;
	try {
		const d = await getSupplierBillItemDetails(line.item_code);
		if (d.uom) line.uom = d.uom;
	} catch {
		/* leave the row for manual entry */
	}
}
function addLine() {
	form.value.lines.push(emptyLine());
}
function removeLine(idx) {
	form.value.lines.splice(idx, 1);
	if (!form.value.lines.length) addLine();
}
function lineAmount(l) {
	return (Number(l.qty) || 0) * (Number(l.rate) || 0);
}
const validLines = computed(() =>
	form.value.lines.filter((l) => l.item_code && Number(l.qty) > 0)
);
const net = computed(() => validLines.value.reduce((a, l) => a + lineAmount(l), 0));

// Taxes: the template's rows, each a rate on the net. The saved quotation carries the amounts
// the controller works out; this is the same sum shown while typing.
const taxRows = ref([]);
watch(
	() => form.value.taxes_and_charges,
	async (tpl) => {
		taxRows.value = [];
		if (!tpl) return;
		try {
			taxRows.value = (await getSupplierBillTaxRows(tpl)) || [];
		} catch {
			taxRows.value = [];
		}
	},
	{ immediate: true }
);
const tax = computed(() =>
	taxRows.value.reduce((a, r) => a + (net.value * (Number(r.rate) || 0)) / 100, 0)
);

function validate() {
	const e = {};
	if (!form.value.supplier) e.supplier = __("Pick a supplier.");
	if (!form.value.project) e.project = __("Pick a project.");
	if (!validLines.value.length) e.lines = __("Add at least one item with a quantity.");
	else if (!validLines.value.some((l) => Number(l.rate) > 0))
		e.lines = __("Enter the supplier's rate on at least one item.");
	if (form.value.valid_till && form.value.valid_till < form.value.transaction_date)
		e.valid_till = __("Valid till cannot be before the quotation date.");
	errors.value = e;
	return Object.keys(e).length === 0;
}

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	try {
		const q = await saveSupplierQuotation({
			name: editingId.value || undefined,
			supplier: form.value.supplier,
			project: form.value.project,
			request_for_quotation: form.value.request_for_quotation || undefined,
			transaction_date: form.value.transaction_date,
			valid_till: form.value.valid_till || "",
			quotation_number: form.value.quotation_number || "",
			payment_terms: form.value.payment_terms || "",
			notes: form.value.notes || "",
			taxes_and_charges: form.value.taxes_and_charges || "",
			items: validLines.value.map((l) => ({
				item_code: l.item_code,
				description: l.description,
				qty: Number(l.qty),
				uom: l.uom || null,
				rate: Number(l.rate) || 0,
				lead_time_days: l.lead_time_days === "" ? null : l.lead_time_days,
				cost_code: l.cost_code || null,
				// Keeps the line tied to the request line it answers, and to its Material Request line.
				request_for_quotation_item: l.request_for_quotation_item || null,
				material_request: l.material_request || null,
				material_request_item: l.material_request_item || null,
			})),
		});
		showToast(isEdit.value ? __("Quotation saved.") : __("Quotation created."));
		router.push(`/procurement/supplier-quotations/${q.name}`);
	} catch (err) {
		showToast(err.message || __("Failed to save quotation"), "error");
	} finally {
		saving.value = false;
	}
}
function onCancel() {
	router.back();
}

const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Procurement"), to: "/procurement" },
	{ label: __("Supplier Quotations"), to: "/procurement/supplier-quotations" },
	isEdit.value
		? { label: editingId.value, to: `/procurement/supplier-quotations/${editingId.value}` }
		: { label: __("New") },
	...(isEdit.value ? [{ label: __("Edit") }] : []),
]);
const pageTitle = computed(() =>
	isEdit.value ? __("Edit {0}", [editingId.value]) : __("New Supplier Quotation")
);
const saveLabel = computed(() =>
	saving.value ? __("Saving…") : isEdit.value ? __("Save changes") : __("Save draft")
);
</script>

<template>
	<DeskPage :title="pageTitle" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canSaveForm"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			{{
				isEdit
					? __("You don't have permission to edit this supplier quotation.")
					: __("You don't have permission to create a supplier quotation.")
			}}
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saveLabel"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<div
				v-if="rfq"
				class="mb-4 px-4 py-2 bg-info-50 border border-info-200 rounded-md text-xs text-info-700"
			>
				{{ __("Answering") }}
				<span class="font-mono">{{ rfq.request_for_quotation }}</span>
				<template v-if="rfq.subject"> — {{ rfq.subject }}</template>
			</div>

			<DeskSection id="quotation" :title="__('Quotation')" :cols="3">
				<DeskField
					:label="__('Request for quotation')"
					:hint="
						isEdit
							? __('Locked while editing.')
							: __('Optional. Picking one brings its items across.')
					"
				>
					<DeskLinkPicker
						:model-value="form.request_for_quotation"
						doctype="Request for Quotation"
						label-field="name"
						value-field="name"
						:search-fields="['name', 'subject']"
						:filters="[['docstatus', '=', 1]]"
						:disabled="isEdit"
						:placeholder="__('— None —')"
						@update:model-value="(v) => loadFromRfq(v)"
					/>
				</DeskField>
				<DeskField :label="__('Supplier')" required :error="errors.supplier">
					<!-- Against a request, only the suppliers it was sent to may answer it. -->
					<DeskSelect v-if="rfq" v-model="form.supplier" data-test="sq-supplier">
						<option value="">{{ __("— Select supplier —") }}</option>
						<option v-for="s in rfq.suppliers" :key="s.supplier" :value="s.supplier">
							{{ s.supplier_name }}{{ s.quote_status === "Received" ? " ✓" : "" }}
						</option>
					</DeskSelect>
					<DeskLinkPicker
						v-else
						v-model="form.supplier"
						doctype="Supplier"
						label-field="supplier_name"
						value-field="name"
						:search-fields="['supplier_name', 'name']"
						:placeholder="__('— Select supplier —')"
					/>
				</DeskField>
				<DeskField
					:label="__('Project')"
					required
					:error="errors.project"
					:hint="rfq ? __('Set by the request.') : ''"
				>
					<DeskLinkPicker
						v-model="form.project"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						:search-fields="['project_name', 'name']"
						:disabled="!!rfq"
						:placeholder="__('— Select project —')"
					/>
				</DeskField>
				<DeskField :label="__('Quotation date')">
					<DeskInput v-model="form.transaction_date" type="date" />
				</DeskField>
				<DeskField :label="__('Valid till')" :error="errors.valid_till">
					<DeskInput v-model="form.valid_till" type="date" />
				</DeskField>
				<DeskField :label="__('Supplier\'s quotation no.')">
					<DeskInput
						v-model="form.quotation_number"
						:placeholder="__('Their reference')"
					/>
				</DeskField>
			</DeskSection>

			<!-- Item lines -->
			<section class="mt-6">
				<div class="flex items-center justify-between mb-2 gap-3">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						{{ __("Items and rates") }}
					</h3>
					<button
						type="button"
						class="text-xs text-brand-700 hover:underline"
						@click="addLine"
					>
						+ {{ __("Add item") }}
					</button>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
					<table class="w-full text-xs" style="min-width: 980px">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2" style="min-width: 200px">
									{{ __("Item") }}
								</th>
								<th class="text-left px-3 py-2">{{ __("Description") }}</th>
								<th class="text-left px-3 py-2" style="min-width: 150px">
									{{ __("Cost code") }}
								</th>
								<th class="text-right px-3 py-2 w-20">{{ __("Qty") }}</th>
								<th class="text-left px-3 py-2 w-28">{{ __("UOM") }}</th>
								<th class="text-right px-3 py-2 w-28">{{ __("Rate") }}</th>
								<th class="text-right px-3 py-2 w-24">{{ __("Lead (days)") }}</th>
								<th class="text-right px-3 py-2 w-28">{{ __("Amount") }}</th>
								<th class="text-center px-2 py-2 w-8"></th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(line, idx) in form.lines"
								:key="idx"
								class="border-t border-ink-100"
							>
								<td class="px-3 py-2" style="min-width: 200px">
									<DeskLinkPicker
										v-model="line.item_code"
										doctype="Item"
										label-field="item_name"
										value-field="name"
										:search-fields="['item_name', 'item_code', 'name']"
										:placeholder="__('— Item —')"
										@update:model-value="onPickItem(line)"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model="line.description"
										class="w-full bg-transparent text-xs py-1.5 focus:outline-none"
										:placeholder="__('Make, grade offered…')"
									/>
								</td>
								<td class="px-3 py-2" style="min-width: 150px">
									<CostCodePicker
										v-model="line.cost_code"
										:project-id="form.project"
										:placeholder="__('— Cost code —')"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model.number="line.qty"
										type="number"
										min="0"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
									/>
								</td>
								<td class="px-3 py-2" style="min-width: 110px">
									<DeskLinkPicker
										v-model="line.uom"
										doctype="UOM"
										label-field="name"
										value-field="name"
										placeholder="—"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model.number="line.rate"
										type="number"
										min="0"
										step="0.01"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
										:placeholder="__('Not quoted')"
										data-test="sq-rate"
									/>
								</td>
								<td class="px-3 py-2">
									<input
										v-model.number="line.lead_time_days"
										type="number"
										min="0"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
										placeholder="—"
									/>
								</td>
								<td
									class="px-3 py-2 text-right tabular-nums text-ink-900 font-medium"
								>
									{{ fmtINR(lineAmount(line)) }}
								</td>
								<td class="px-2 py-2 text-center">
									<button
										type="button"
										class="text-ink-400 hover:text-danger-600"
										:title="__('Remove')"
										@click="removeLine(idx)"
									>
										✕
									</button>
								</td>
							</tr>
						</tbody>
						<tfoot>
							<tr class="border-t-2 border-ink-200 bg-ink-50">
								<td
									colspan="7"
									class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
								>
									{{ __("Net total") }}
								</td>
								<td
									class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
								>
									{{ fmtINR(net) }}
								</td>
								<td></td>
							</tr>
						</tfoot>
					</table>
				</div>
				<p v-if="errors.lines" class="text-xs text-danger-700 mt-1">{{ errors.lines }}</p>
				<p class="text-[11px] text-ink-500 mt-2">
					{{
						__(
							"Leave the rate empty on an item the supplier did not quote: the comparison shows it as not quoted."
						)
					}}
				</p>
			</section>

			<DeskSection id="taxes" :title="__('Taxes and charges')" :cols="3" class="mt-6">
				<DeskField
					:label="__('Tax template')"
					:hint="
						__(
							'The taxes the supplier quoted. They carry into an order raised from this quotation.'
						)
					"
				>
					<DeskLinkPicker
						v-model="form.taxes_and_charges"
						doctype="Purchase Taxes and Charges Template"
						label-field="title"
						value-field="name"
						:search-fields="['title', 'name']"
						:filters="[['disabled', '=', 0]]"
						:placeholder="__('— No tax —')"
					/>
				</DeskField>
				<DeskField :label="__('Taxes')">
					<div class="text-sm tabular-nums text-ink-900 py-1.5">{{ fmtINR(tax) }}</div>
				</DeskField>
				<DeskField :label="__('Grand total')">
					<div class="text-sm tabular-nums font-semibold text-ink-900 py-1.5">
						{{ fmtINR(net + tax) }}
					</div>
				</DeskField>
			</DeskSection>

			<DeskSection
				id="supplier-terms"
				:title="__('Supplier\'s terms')"
				:cols="2"
				class="mt-6"
			>
				<DeskField :label="__('Payment terms')">
					<DeskInput
						v-model="form.payment_terms"
						:placeholder="__('e.g. 30 days from invoice')"
					/>
				</DeskField>
				<DeskField :label="__('Notes')">
					<DeskTextarea
						v-model="form.notes"
						:rows="2"
						:placeholder="__('Delivery conditions, exclusions…')"
					/>
				</DeskField>
			</DeskSection>
		</DeskForm>
	</DeskPage>
</template>
