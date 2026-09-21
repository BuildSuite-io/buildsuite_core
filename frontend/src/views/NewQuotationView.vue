<script setup>
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import { useCustomerOptions } from "@/composables/useCustomerOptions";
import { useFormErrors } from "@/composables/useFormErrors";
import { useProjectOptions } from "@/composables/useProjectOptions";
import QuotationLineModal from "@/components/QuotationLineModal.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { showToast } from "@/utils/appToast";
// A terms template is the same record whoever pulls it in; invoice.py owns the reader.
import { getInvoiceTerms } from "@/data/invoiceApi";
import { daysBetween, fmtCurrency } from "@/utils/format";

// Same form for both: with an id it edits that draft, without one it creates.
const props = defineProps({ id: { type: String, default: "" } });
const router = useRouter();
const editing = computed(() => !!props.id);

function isoDaysFromNow(days) {
	const date = new Date();
	date.setDate(date.getDate() + days);
	return date.toISOString().slice(0, 10);
}

// A yyyy-mm-dd string parses as UTC midnight, so adding whole days and reading the date back
// out in UTC never drifts. `daysBetween` parses the same way, which makes the two a matched
// pair — days in on save, days back out on edit.
function isoPlusDays(iso, days) {
	if (!iso) return "";
	const date = new Date(iso);
	date.setTime(date.getTime() + (Number(days) || 0) * 86400000);
	return date.toISOString().slice(0, 10);
}

// A line is a scope of work, not a stock item. `source` records which button added it.
function blankLine() {
	return { description: "", uom: "Nos", qty: 1, rate: 0, source: "Manual" };
}

// Field names match the doctype bar one: the offer is made in days ("this price holds 30
// days"), so that is what the form asks for. The doctype's `valid_till` date is worked out
// from it on save — which also makes an expiry before the issue date impossible to enter.
const form = reactive({
	title: "",
	transaction_date: isoDaysFromNow(0),
	validity_days: 30,
	party_name: "",
	customer_type: "",
	project: "",
	items: [blankLine()],
	tc_name: "",
	terms: "",
	internal_note: "",
});

// Read straight off the doctype — no endpoint. Only the line text needs translating: the form
// calls it `description`, and on a Quotation Item that text lives in `item_name`.
const adapter = createDataAdapter(useDataStore());
const resource = props.id ? adapter.read("Quotation", props.id) : null;
watch(
	() => resource?.doc,
	(doc) => {
		if (!doc) return;
		for (const k of Object.keys(form)) {
			if (k === "items" || doc[k] == null) continue;
			form[k] = doc[k];
		}
		// `validity_days` is the form's own field, not the doctype's — read it back off the
		// two dates. A quotation saved with no expiry keeps none.
		form.validity_days = doc.valid_till
			? daysBetween(doc.transaction_date, doc.valid_till)
			: "";
		// Copied, not aliased: `doc` lives in the shared document cache and the grid below
		// writes cells in place.
		form.items = (doc.items || []).map((l) => ({
			description: l.item_name || "",
			uom: l.uom,
			qty: l.qty,
			rate: l.rate,
			source: l.source || "Manual",
			code: l.code,
			source_ref: l.source_ref,
		}));
		if (!form.items.length) form.items = [blankLine()];
	},
	{ immediate: true }
);

const { customerOptions } = useCustomerOptions();
const { projectOptions } = useProjectOptions();

function addLine() {
	form.items.push(blankLine());
}

function removeLine(i) {
	form.items.splice(i, 1);
}

function lineAmount(l) {
	return (Number(l.qty) || 0) * (Number(l.rate) || 0);
}

const subtotal = computed(() => form.items.reduce((a, l) => a + lineAmount(l), 0));

// A template copies its text in; editing afterwards makes the terms ours, so the link drops.
async function onPickTerms(name) {
	form.tc_name = name || "";
	if (!name) return;
	try {
		form.terms = (await getInvoiceTerms(name)).terms || "";
	} catch {
		showToast("Could not read that terms template.", "error");
	}
}

function onTermsEdited() {
	form.tc_name = "";
}

const pickerOpen = ref(false);

function addFromLibrary(line) {
	form.items.push(line);
}

const { errors, applyServerErrors, setErrors } = useFormErrors({
	party_name: "party_name",
	title: "title",
	transaction_date: "transaction_date",
	valid_till: "validity_days",
});
const saving = ref(false);

function validate() {
	const found = {};
	if (!form.party_name) found.party_name = "Pick the customer this is for.";
	if (!form.title.trim()) found.title = "Say what the quotation is for.";
	if (!form.transaction_date) found.transaction_date = "An issue date is required.";
	if (form.validity_days !== "" && Number(form.validity_days) < 0)
		found.validity_days = "Cannot be negative — a price cannot expire before it is offered.";
	// Rows with no description are dropped on save, so only the ones that will be sent count.
	const lines = form.items.filter((l) => l.description.trim());
	if (!lines.length) {
		found.items = "Add at least one line with a description.";
	} else if (lines.some((l) => !(Number(l.qty) > 0))) {
		// The library modal already refuses this; a typed row would otherwise save a line
		// priced at nothing, which reads as an offer to do the work free.
		found.items = "Every line needs a quantity above zero.";
	}
	setErrors(found);
	return Object.keys(found).length === 0;
}

// Every ERPNext sales line hangs off an Item. A quotation line is a scope of work, not stock,
// so they all point at one generic service item and the description carries the real text.
const SERVICE_ITEM = "Professional Services";

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	const payload = {
		quotation_to: "Customer",
		party_name: form.party_name,
		title: form.title.trim(),
		customer_type: form.customer_type || null,
		project: form.project || null,
		transaction_date: form.transaction_date,
		valid_till:
			form.validity_days === "" ? null : isoPlusDays(form.transaction_date, form.validity_days),
		tc_name: form.tc_name || null,
		terms: form.terms || null,
		internal_note: form.internal_note || null,
		items: form.items
			.filter((l) => l.description.trim())
			.map((l) => ({
				item_code: SERVICE_ITEM,
				item_name: l.description.trim().slice(0, 140),
				description: l.description.trim(),
				uom: l.uom || "Nos",
				qty: Number(l.qty) || 1,
				rate: Number(l.rate) || 0,
				source: l.source || "Manual",
				code: l.code || null,
				source_ref: l.source_ref || null,
			})),
	};
	try {
		// Sending the whole `items` array replaces the child table, so an edit never appends.
		const doc = editing.value
			? await adapter.update("Quotation", props.id, payload)
			: await adapter.create("Quotation", payload);
		router.push(`/quotations/${encodeURIComponent(doc?.name || props.id)}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Could not save the quotation.", "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Estimation", to: "/estimation" },
	{ label: "Quotations", to: "/quotations" },
	{ label: editing.value ? props.id : "New" },
]);
</script>

<template>
	<DeskPage :title="editing ? `Edit ${id}` : 'New Quotation'"
		subtitle="Type the items straight in, or pull them from an assembly."
		:breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar :save-label="editing ? 'Save changes' : 'Create quotation'"
					:saving-label="editing ? 'Saving…' : 'Creating…'" :saving="saving" @save="onSave"
					@cancel="router.back()" />
			</template>

			<DeskSection title="Who and what" :cols="2">
				<div class="md:col-span-2">
					<DeskField label="For" required :error="errors.title">
						<DeskInput
							v-model="form.title"
							placeholder="e.g. Interior fit-out — Level 8, Brigade Tech Gardens"
						/>
					</DeskField>
				</div>

				<DeskField label="Customer" required :error="errors.party_name">
					<DeskSearchableSelect
						v-model="form.party_name"
						:options="customerOptions"
						placeholder="Pick a customer…"
						search-placeholder="Search customers…"
					/>
				</DeskField>

				<DeskField label="Customer type">
					<DeskSelect v-model="form.customer_type">
						<option value="">— Select —</option>
						<option>Homebuyer</option>
						<option>Private Client</option>
						<option>Main Contractor</option>
					</DeskSelect>
				</DeskField>

				<DeskField
					label="Project"
					hint="Optional — a quotation usually goes out before there is a project."
				>
					<DeskSearchableSelect
						v-model="form.project"
						:options="projectOptions"
						allow-clear
						placeholder="Not linked to a project"
						search-placeholder="Search projects…"
					/>
				</DeskField>
			</DeskSection>

			<!-- No margin or tax fields: neither is applied yet, and a number on screen reads as
				 a number in the price. They arrive with the working that uses them. -->
			<DeskSection title="Dates" :cols="2">
				<DeskField label="Date issued" required :error="errors.transaction_date">
					<DeskInput v-model="form.transaction_date" type="date" />
				</DeskField>

				<DeskField label="Valid for (days)" :error="errors.validity_days"
					hint="Counted from the issue date. Leave blank for no expiry.">
					<DeskInput v-model="form.validity_days" type="number" min="0" />
				</DeskField>
			</DeskSection>

			<DeskSection title="Items" :cols="1">
				<div class="border border-ink-200 overflow-hidden" style="border-radius: 8px">
					<div class="overflow-x-auto">
						<table class="w-full text-sm" style="min-width: 780px">
							<thead>
								<tr
									class="bg-ink-50 border-b border-ink-200 text-[11px] uppercase tracking-wider text-ink-500"
								>
									<th class="text-left font-medium px-3 py-2 w-24">Source</th>
									<th class="text-left font-medium px-3 py-2">Description</th>
									<th class="text-left font-medium px-3 py-2 w-32">Unit</th>
									<th class="text-right font-medium px-3 py-2 w-24">Qty</th>
									<th class="text-right font-medium px-3 py-2 w-32">Rate</th>
									<th class="text-right font-medium px-3 py-2 w-36">Amount</th>
									<th class="w-10"></th>
								</tr>
							</thead>

							<tbody>
								<tr
									v-for="(l, i) in form.items"
									:key="i"
									class="border-b border-ink-100"
								>
									<td class="px-3 py-2">
										<StatusBadge :status="l.source" size="xs" />
									</td>
									<td class="px-3 py-2">
										<input
											v-model="l.description"
											class="w-full bg-transparent text-sm text-ink-900 py-1 focus:outline-none"
											placeholder="What the line is for"
										/>
									</td>
									<td class="px-3 py-2">
										<DeskLinkPicker
											v-model="l.uom"
											doctype="UOM"
											label-field="name"
											value-field="name"
											placeholder="Unit"
										/>
									</td>
									<td class="px-3 py-2">
										<input
											v-model.number="l.qty"
											type="number"
											min="0"
											step="any"
											class="w-full bg-transparent text-sm text-right tabular-nums py-1 focus:outline-none"
										/>
									</td>
									<td class="px-3 py-2">
										<input
											v-model.number="l.rate"
											type="number"
											min="0"
											step="any"
											class="w-full bg-transparent text-sm text-right tabular-nums py-1 focus:outline-none"
										/>
									</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-900">
										{{ fmtCurrency(lineAmount(l)) }}
									</td>
									<td class="px-2 py-2 text-center">
										<button
											type="button"
											class="text-ink-400 hover:text-danger-700"
											title="Remove line"
											@click="removeLine(i)"
										>
											&times;
										</button>
									</td>
								</tr>
							</tbody>

							<tfoot>
								<tr class="border-t border-ink-100">
									<td colspan="7" class="px-3 py-2">
										<div class="flex items-center gap-3">
											<button
												type="button"
												class="text-xs text-brand-700 hover:underline font-medium"
												@click="addLine"
											>
												+ Add row
											</button>
											<span class="text-ink-300 text-xs">·</span>
											<button
												type="button"
												class="text-xs text-ink-600 hover:text-brand-700 hover:underline"
												@click="pickerOpen = true"
											>
												+ Add from library
											</button>
											<span class="text-[11px] text-ink-400"
												>an assembly</span
											>
										</div>
									</td>
								</tr>
								<tr
									v-if="form.items.length"
									class="border-t-2 border-ink-200 bg-ink-50"
								>
									<td
										colspan="5"
										class="px-3 py-2 text-right text-[11px] font-semibold text-ink-600 uppercase tracking-wider"
									>
										Subtotal
									</td>
									<td
										class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
									>
										{{ fmtCurrency(subtotal) }}
									</td>
									<td></td>
								</tr>
							</tfoot>
						</table>
					</div>
				</div>
				<p v-if="errors.items" class="text-xs text-danger-700 mt-2">{{ errors.items }}</p>
			</DeskSection>

			<DeskSection title="Terms" :cols="1">
				<DeskField
					label="Start from a template"
					hint="Pulls the clause in as editable text — change it afterwards and it stays yours."
				>
					<DeskLinkPicker
						:model-value="form.tc_name"
						doctype="Terms and Conditions"
						label-field="name"
						value-field="name"
						placeholder="Load standard terms from the library…"
						@update:model-value="onPickTerms"
					/>
				</DeskField>

				<DeskField
					label="Terms &amp; conditions"
					:hint="
						form.tc_name
							? 'Pulled from a template. Editing it here does not change the library.'
							: 'Typed for this quotation.'
					"
				>
					<DeskTextarea
						v-model="form.terms"
						:rows="6"
						placeholder="Type the terms, or load a standard set above."
						@input="onTermsEdited"
					/>
				</DeskField>
			</DeskSection>

			<DeskSection title="Internal notes" :cols="1">
				<DeskField label="Notes" hint="Not printed — for whoever picks this up next.">
					<DeskTextarea v-model="form.internal_note" :rows="3" />
				</DeskField>
			</DeskSection>
		</DeskForm>

		<QuotationLineModal
			v-model:open="pickerOpen"
			@add="addFromLibrary"
		/>
	</DeskPage>
</template>
