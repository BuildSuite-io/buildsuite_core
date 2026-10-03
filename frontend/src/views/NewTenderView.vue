<script setup>
// New or edit tender — an `id` prop means edit. Header and item rows go in one call.

import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { useFormErrors } from "@/composables/useFormErrors";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DocTypeChildTable from "@/components/doctype/DocTypeChildTable.vue";
import TenderLinePicker from "@/components/TenderLinePicker.vue";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import { useProjectOptions } from "@/composables/useProjectOptions";
import { toDateInputValue } from "@/utils/dateInput";
import { __ } from "@/utils/translate";

const props = defineProps({ id: { type: String, default: "" } });

const router = useRouter();
const adapter = createDataAdapter(useDataStore());
const { projectOptions } = useProjectOptions();
const editing = computed(() => !!props.id);

const { meta, selectOptions, fieldDefault } = useDoctypeMeta("BuildSuite Tenders");
const issuedByOptions = computed(() => selectOptions("issued_by"));
const envelopeOptions = computed(() => selectOptions("envelope_structure"));

const breadcrumbs = [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Estimation"), to: "/estimation" },
	{ label: __("Tenders"), to: "/tenders" },
	{ label: props.id || __("New") },
];

const form = reactive({
	title: "",
	issuing_body: "",
	issued_by: "",
	project: "",
	date_issued: toDateInputValue(new Date()),
	tender_reference: "",
	submission_deadline: "",
	portal: "",
	envelope_structure: "",
	emd_amount: "",
	emd_instrument: "",
	emd_valid_until: "",
	performance_guarantee_percent: "",
	margin_percent: "",
	tax_percent: "",
	buildsuite_tenders_items: [],
	notes: "",
});

// Meta arrives async, so ||= — anything already typed wins. Skipped when editing: a saved
// tax of 0 is falsy and would be overwritten by the doctype's 18.
watch(
	meta,
	() => {
		if (editing.value) return;
		for (const f of ["issued_by", "envelope_structure", "margin_percent", "tax_percent"]) {
			form[f] ||= fieldDefault(f);
		}
	},
	{ immediate: true }
);

// Known keys only, so no docstatus/owner rides along into the payload.
const resource = props.id ? adapter.read("BuildSuite Tenders", props.id) : null;
watch(
	() => resource?.doc,
	(doc) => {
		if (!doc) return;
		// Child tables are COPIED, not aliased. `doc` lives in the shared document cache, and
		// DocTypeChildTable writes cells in place — assigning the array itself would let the
		// form edit the record the detail page is reading.
		for (const k of Object.keys(form)) {
			if (doc[k] == null) continue;
			form[k] = Array.isArray(doc[k]) ? doc[k].map((r) => ({ ...r })) : doc[k];
		}
	},
	{ immediate: true }
);

const { errors, applyServerErrors, setErrors } = useFormErrors({
	title: "title",
	issuing_body: "issuing_body",
	tender_reference: "tender_reference",
	submission_deadline: "submission_deadline",
});
const saving = ref(false);

// Lines pulled from the assembly catalogue land in the same grid as typed ones — `source`
// marks where each came from.
const pickerOpen = ref(false);
function addLibraryLine(row) {
	// Replace, don't push — same as DocTypeChildTable's own add/remove.
	form.buildsuite_tenders_items = [...form.buildsuite_tenders_items, row];
}

// Untouched rows are dropped. `source` is seeded on every new row, so it does not count.
const items = computed(() =>
	form.buildsuite_tenders_items.filter((r) =>
		["description", "unit", "qty", "rate", "photo"].some((k) => r[k])
	)
);

function validate() {
	const e = {};
	if (!form.title.trim()) e.title = __("Say what the tender is for.");
	if (!form.issuing_body.trim()) e.issuing_body = __("Who issued it?");
	if (!form.tender_reference.trim())
		e.tender_reference = __("The issuing body's reference — a bid can be rejected on this alone.");
	if (!form.submission_deadline)
		e.submission_deadline = __("Needs a deadline. Miss it and the bid cannot be entered.");
	else if (form.date_issued && form.submission_deadline < form.date_issued)
		e.submission_deadline = __("Can't be before the date issued.");
	if (Number(form.emd_amount) < 0) e.emd_amount = __("Cannot be negative.");
	if (Number(form.performance_guarantee_percent) < 0)
		e.performance_guarantee_percent = __("Cannot be negative.");
	if (!items.value.length) e.buildsuite_tenders_items = __("Add at least one item.");
	else if (items.value.some((r) => !(r.description || "").trim()))
		e.buildsuite_tenders_items = __("Every item needs a description.");
	setErrors(e);
	return !Object.keys(e).length;
}

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	const payload = {
		title: form.title.trim(),
		issuing_body: form.issuing_body.trim(),
		issued_by: form.issued_by,
		project: form.project || null,
		date_issued: form.date_issued || null,
		tender_reference: form.tender_reference.trim(),
		submission_deadline: form.submission_deadline,
		portal: form.portal.trim(),
		envelope_structure: form.envelope_structure,
		emd_amount: Number(form.emd_amount) || 0,
		emd_instrument: form.emd_instrument.trim(),
		emd_valid_until: form.emd_valid_until || null,
		performance_guarantee_percent: Number(form.performance_guarantee_percent) || 0,
		margin_percent: Number(form.margin_percent) || 0,
		tax_percent: Number(form.tax_percent) || 0,
		buildsuite_tenders_items: items.value,
		notes: form.notes,
	};
	try {
		if (editing.value) {
			await adapter.update("BuildSuite Tenders", props.id, payload);
			showToast(__("Tender saved"), "success");
			router.push(`/tenders/${props.id}`);
		} else {
			const res = await adapter.create("BuildSuite Tenders", payload);
			showToast(__("Tender created"), "success");
			router.push(`/tenders/${res.name}`);
		}
	} catch (err) {
		showToast(applyServerErrors(err) ?? __("Failed to save tender"), "error");
	} finally {
		saving.value = false;
	}
}
</script>

<template>
	<DeskPage :title="editing ? __('Edit {0}', [props.id]) : __('New Tender')"
		:subtitle="__('Type the items straight in, or pull them from an assembly or an estimate. Terms sections are added on the tender itself.')"
		:breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar :save-label="editing ? __('Save changes') : __('Create tender')" :saving="saving" @save="onSave" @cancel="router.back()" />
			</template>

			<DeskSection :title="__('Who and what')" :cols="2">
				<DeskField :label="__('For')" required :error="errors.title" class="md:col-span-2">
					<DeskInput v-model="form.title" :placeholder="__('e.g. Station finishes package — Kochi Metro Phase 2')" />
				</DeskField>
				<DeskField :label="__('Issuing body')" required :error="errors.issuing_body">
					<DeskInput v-model="form.issuing_body" :placeholder="__('e.g. KMRL')" />
				</DeskField>
				<DeskField :label="__('Issued by')">
					<DeskSelect v-model="form.issued_by">
						<option v-for="o in issuedByOptions" :key="o" :value="o">{{ __(o) }}</option>
					</DeskSelect>
				</DeskField>
				<DeskField :label="__('Project')" :hint="__('Optional — a tender is bid long before there is a project.')">
					<DeskSearchableSelect v-model="form.project" :options="projectOptions" allow-clear
						:placeholder="__('Not linked to a project')" :search-placeholder="__('Search projects…')" />
				</DeskField>
				<DeskField :label="__('Date issued')">
					<DeskInput v-model="form.date_issued" type="date" />
				</DeskField>
			</DeskSection>

			<DeskSection :title="__('Submission')" :cols="2">
				<DeskField :label="__('Tender reference')" required :error="errors.tender_reference">
					<DeskInput v-model="form.tender_reference" :placeholder="__('e.g. KMRL/P2/CIV/2026/17')" />
				</DeskField>
				<DeskField :label="__('Submission deadline')" required :error="errors.submission_deadline"
					:hint="__('A quote past validity can be chased. A tender past its deadline cannot be entered at all.')">
					<DeskInput v-model="form.submission_deadline" type="date" :min="form.date_issued" />
				</DeskField>
				<DeskField :label="__('Portal')" :hint="__('Where the bid is uploaded.')">
					<DeskInput v-model="form.portal" :placeholder="__('e.g. GePNIC / state e-procurement')" />
				</DeskField>
				<DeskField :label="__('Envelope structure')"
					:hint="__('How the bid is packaged: technical and financial together, or opened in stages.')">
					<DeskSelect v-model="form.envelope_structure">
						<option v-for="o in envelopeOptions" :key="o" :value="o">{{ __(o) }}</option>
					</DeskSelect>
				</DeskField>
			</DeskSection>

			<DeskSection :title="__('Earnest money and guarantee')" :cols="2">
				<DeskField :label="__('EMD amount (₹)')" :error="errors.emd_amount"
					:hint="__('Money genuinely lodged — it shows as at stake until the bid is decided.')">
					<DeskInput v-model="form.emd_amount" type="number" min="0" step="any" :placeholder="__('blank if none')" />
				</DeskField>
				<DeskField :label="__('EMD instrument')" :hint="__('Bank guarantee, DD, online transfer.')">
					<DeskInput v-model="form.emd_instrument" :placeholder="__('e.g. Bank guarantee — Federal Bank')" />
				</DeskField>
				<DeskField :label="__('EMD valid until')">
					<DeskInput v-model="form.emd_valid_until" type="date" />
				</DeskField>
				<DeskField :label="__('Performance guarantee %')" :error="errors.performance_guarantee_percent"
					:hint="__('What we would have to furnish on award.')">
					<DeskInput v-model="form.performance_guarantee_percent" type="number" min="0" step="any"
						:placeholder="__('blank if none')" />
				</DeskField>
			</DeskSection>

			<DeskSection :title="__('Pricing')" :cols="2">
				<DeskField :label="__('Margin %')" :hint="__('Applied to the subtotal.')">
					<DeskInput v-model="form.margin_percent" type="number" min="0" step="any" />
				</DeskField>
				<DeskField :label="__('Tax %')" :hint="__('Charged on subtotal plus margin.')">
					<DeskInput v-model="form.tax_percent" type="number" min="0" step="any" />
				</DeskField>
			</DeskSection>

			<DeskSection :title="__('Items')" :cols="1">
				<DocTypeChildTable v-model="form.buildsuite_tenders_items" doctype="BuildSuite Tenders Items" />
				<div class="mt-2">
					<button type="button"
						class="text-xs text-brand-700 hover:underline font-medium"
						@click="pickerOpen = true">
						{{ __("+ Add from library") }}
					</button>
					<span class="text-[11px] text-ink-400 ml-2">{{ __("an assembly from the catalogue") }}</span>
				</div>
				<p v-if="errors.buildsuite_tenders_items" class="text-xs text-danger-700 mt-2">
					{{ errors.buildsuite_tenders_items }}
				</p>
				<p class="text-[11px] text-ink-500 mt-2">
					{{ __("Margin and tax are applied to the subtotal — sell rate and amount are worked out on save.") }}
				</p>
			</DeskSection>

			<DeskSection :title="__('Internal notes')" :cols="1">
				<DeskField :label="__('Notes')" :hint="__('Not printed — for whoever picks this up next.')">
					<DeskTextarea v-model="form.notes" :rows="3" />
				</DeskField>
			</DeskSection>
		</DeskForm>

		<TenderLinePicker :open="pickerOpen" @close="pickerOpen = false" @add="addLibraryLine" />
	</DeskPage>
</template>
