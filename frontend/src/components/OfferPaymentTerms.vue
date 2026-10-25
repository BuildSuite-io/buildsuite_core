<script setup>
// Payment schedule card on a tender or a quotation. Ported from the demo's
// OfferPaymentTerms. Loading a template COPIES its milestones onto the offer, so
// editing the template later never moves an offer that already went out.
// Every change is emitted as `save` — the page persists it (no Save button).

import { computed, ref, watch } from "vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import PaymentScheduleEditor from "@/components/PaymentScheduleEditor.vue";
import { getRecord } from "@/data/doctypeRecordApi";
import { listPaymentTermTemplates } from "@/data/paymentTermsApi";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { parseFrappeError } from "@/utils/frappeError";
import { __ } from "@/utils/translate";

const MILESTONE_FIELDS = [
	"payment_milestone",
	"payable",
	"stage",
	"days_after_project_start",
	"percentage",
	"client_sign_off",
];

const props = defineProps({
	doc: { type: Object, required: true },
	kind: { type: String, default: "Tender" }, // "Tender" | "Quotation"
	// Price before tax — each milestone's amount is its share of this.
	base: { type: Number, default: null },
	currency: { type: String, default: undefined },
});
const emit = defineEmits(["save"]);

const confirmDialog = useConfirm();
const templateOptions = ref([]);

const rows = computed(() => props.doc.payment_milestones || []);

function showError(err, fallback) {
	showToast(parseFrappeError(err).summary ?? fallback, "error");
}

watch(
	() => props.doc.project_category,
	async (category) => {
		try {
			const list = await listPaymentTermTemplates(category);
			templateOptions.value = (list || []).map((t) => ({ value: t.name, label: t.name }));
		} catch (err) {
			templateOptions.value = [];
			showError(err, __("Could not load payment term templates"));
		}
	},
	{ immediate: true },
);

function copyRow(row) {
	return Object.fromEntries(MILESTONE_FIELDS.map((f) => [f, row[f]]));
}

async function loadTemplate(name) {
	if (!name) return;
	if (rows.value.length) {
		const ok = await confirmDialog({
			title: __("Replace the payment schedule"),
			message: __("Loading a template replaces the milestones already on this {0}.", [
				props.kind.toLowerCase(),
			]),
			confirmLabel: __("Replace"),
		});
		if (!ok) return;
	}
	let tpl;
	try {
		tpl = await getRecord("BuildSuite Payment Term Template", name);
	} catch (err) {
		showError(err, __("Could not load the template"));
		return;
	}
	emit("save", {
		payment_term_template: name,
		payment_milestones: (tpl.milestones || []).map(copyRow),
	});
}

function removeSchedule() {
	emit("save", { payment_term_template: null, payment_milestones: [] });
}
</script>

<template>
	<div class="border border-ink-200 bg-white" style="border-radius: 2px">
		<div
			class="px-3 py-2 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center gap-2"
		>
			<span class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
				{{ __("Payment schedule") }}
			</span>
			<span
				class="text-[10px] px-1.5 py-0.5 bg-ink-100 text-ink-600"
				style="border-radius: 9999px"
				>{{ __("Optional") }}</span
			>
			<span
				v-if="doc.payment_term_template"
				class="text-[10px] px-1.5 py-0.5 bg-brand-50 text-brand-700"
				style="border-radius: 9999px"
				>{{ __('From "{0}"', [doc.payment_term_template]) }}</span
			>
			<button
				v-if="rows.length"
				type="button"
				class="ml-auto text-xs text-ink-500 hover:text-danger-700"
				@click="removeSchedule"
			>
				{{ __("Remove schedule") }}
			</button>
		</div>

		<div class="p-3 space-y-3">
			<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
				<DeskField :label="__('Project Category')">
					<DeskLinkPicker
						:model-value="doc.project_category"
						doctype="Project Category"
						:placeholder="__('All categories')"
						@update:model-value="(v) => emit('save', { project_category: v || null })"
					/>
				</DeskField>
				<DeskField :label="__('Load a template')">
					<DeskSearchableSelect
						:model-value="null"
						:options="templateOptions"
						:placeholder="__('Pick a template…')"
						:search-placeholder="__('Search templates…')"
						@update:model-value="loadTemplate"
					/>
				</DeskField>
			</div>

			<PaymentScheduleEditor
				:rows="rows"
				:base="base"
				:currency="currency"
				@update:rows="(v) => emit('save', { payment_milestones: v })"
			/>
			<p v-if="base != null" class="text-xs text-ink-500">
				{{
					__(
						"Amounts are shares of the price before tax. Tax is added when each milestone is invoiced.",
					)
				}}
			</p>
		</div>
	</div>
</template>
