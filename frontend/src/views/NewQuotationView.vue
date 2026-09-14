<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
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
import { getQuotation, getQuotationTerms, saveQuotation } from "@/data/quotationApi";
import { fmtCurrency } from "@/utils/format";

// Same form for both: with an id it edits that draft, without one it creates.
const props = defineProps({ id: { type: String, default: "" } });
const router = useRouter();
const editing = computed(() => !!props.id);

function isoDaysFromNow(days) {
	const date = new Date();
	date.setDate(date.getDate() + days);
	return date.toISOString().slice(0, 10);
}

// A line is a scope of work, not a stock item. `source` records which button added it.
function blankLine() {
	return { description: "", uom: "Nos", qty: 1, rate: 0, source: "Manual" };
}

// Field names match the doctype, so the save payload needs no translation.
const form = reactive({
	title: "",
	transaction_date: isoDaysFromNow(0),
	valid_till: isoDaysFromNow(30),
	party_name: "",
	customer_type: "",
	project: "",
	items: [blankLine()],
	tc_name: "",
	terms: "",
	internal_note: "",
});

onMounted(async () => {
	if (!props.id) return;
	try {
		Object.assign(form, await getQuotation(props.id));
	} catch (err) {
		showToast(err.message || "Could not load that quotation.", "error");
		router.replace("/quotations");
	}
});

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
		form.terms = (await getQuotationTerms(name)).terms || "";
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
});
const saving = ref(false);

function validate() {
	const found = {};
	if (!form.party_name) found.party_name = "Pick the customer this is for.";
	if (!form.title.trim()) found.title = "Say what the quotation is for.";
	if (!form.transaction_date) found.transaction_date = "An issue date is required.";
	if (!form.items.some((l) => l.description.trim())) {
		found.items = "Add at least one line with a description.";
	}
	setErrors(found);
	return Object.keys(found).length === 0;
}

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	try {
		const { name } = await saveQuotation({
			...form,
			name: props.id || undefined,
			title: form.title.trim(),
			items: form.items.filter((l) => l.description.trim()),
		});
		router.push(`/quotations/${encodeURIComponent(name)}`);
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

			<DeskSection title="Dates and pricing" :cols="4">
				<DeskField label="Date issued" required :error="errors.transaction_date">
					<DeskInput v-model="form.transaction_date" type="date" />
				</DeskField>

				<DeskField label="Valid till" hint="The price is held firm up to this date.">
					<DeskInput v-model="form.valid_till" type="date" />
				</DeskField>

				<!-- Disabled until the margin and tax work lands, so nobody reads them as applied. -->
				<DeskField label="Margin %" hint="Applied to the subtotal. Not applied yet.">
					<DeskInput model-value="10" type="number" disabled />
				</DeskField>

				<DeskField label="Tax %" hint="Charged on subtotal plus margin. Not applied yet.">
					<DeskInput model-value="18" type="number" disabled />
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
