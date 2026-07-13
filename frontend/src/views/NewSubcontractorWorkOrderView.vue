<script setup>
// Subcontractor Work Order form — create + edit. Header fields (all Link
// fields use DeskLinkPicker) + an editable Schedule of Values grid. Each
// SOV line carries scope, a BOQ cost code (CostCodePicker), qty/uom, rate
// and a computed amount. Saved via the whitelisted save_work_order (the
// SOV child table can't go through the generic adapter). Status is
// workflow-driven, so it is never set from this form.

import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { frappeRequest } from "frappe-ui-frappe-request";
import { showToast } from "@/utils/appToast";
import { getWorkOrder, saveWorkOrder } from "@/data/subcontractApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import CostCodePicker from "@/components/CostCodePicker.vue";
import { fmtINR } from "@/utils/format";

const route = useRoute();
const router = useRouter();

const editingId = computed(() => route.params.id || null);
const isEdit = computed(() => !!editingId.value);

function emptyLine() {
	return { scope: "", cost_code: null, uom: "", qty: 0, rate: 0 };
}

function todayIso() {
	return new Date().toISOString().slice(0, 10);
}

const form = ref({
	subcontractor: route.query.subcontractor || "",
	project: route.query.project || "",
	date: todayIso(),
	delivery_type: "",
	retention_percent: 5,
	terms_template: "",
	terms: "",
	lines: [emptyLine()],
});
const errors = ref({});
const saving = ref(false);
const loading = ref(false);

// Reconstruct the CostCodePicker object shape from the stored line fields.
function costCodeFromLine(l) {
	if (!l.cost_code_type) return null;
	return {
		type: (l.cost_code_type || "").toLowerCase(),
		group_code: l.cost_code_group || "",
		item_code: l.cost_code_item || null,
		label: l.cost_code_label || "",
	};
}

// Load an existing WO into the form in edit mode.
watch(
	editingId,
	async (id) => {
		if (!id) return;
		loading.value = true;
		try {
			const wo = await getWorkOrder(id);
			form.value = {
				subcontractor: wo.subcontractor || "",
				project: wo.project || "",
				date: wo.date || todayIso(),
				delivery_type: wo.delivery_type || "",
				retention_percent: wo.retention_percent ?? 5,
				terms_template: wo.terms_template || "",
				terms: wo.terms || "",
				lines: (wo.lines || []).map((l) => ({
					scope: l.scope || "",
					cost_code: costCodeFromLine(l),
					uom: l.uom || "",
					qty: l.qty || 0,
					rate: l.rate || 0,
				})),
			};
			if (!form.value.lines.length) form.value.lines = [emptyLine()];
		} catch (err) {
			showToast(err.message || "Failed to load work order", "error");
		} finally {
			loading.value = false;
		}
	},
	{ immediate: true },
);

const total = computed(() =>
	form.value.lines.reduce((a, l) => a + (Number(l.qty) || 0) * (Number(l.rate) || 0), 0),
);

function lineAmount(line) {
	return (Number(line.qty) || 0) * (Number(line.rate) || 0);
}
function addLine() {
	form.value.lines.push(emptyLine());
}
function removeLine(idx) {
	form.value.lines.splice(idx, 1);
}

// Importing a Terms and Conditions template fills the editable terms box.
async function onPickTermsTemplate(id) {
	form.value.terms_template = id;
	if (!id) return;
	try {
		const res = await frappeRequest({
			url: "frappe.client.get_value",
			params: { doctype: "Terms and Conditions", filters: id, fieldname: "terms" },
		});
		if (res?.terms) form.value.terms = res.terms;
	} catch {
		/* leave terms as-is if the template can't be read */
	}
}

function validate() {
	const e = {};
	if (!form.value.subcontractor) e.subcontractor = "Pick a subcontractor.";
	if (!form.value.project) e.project = "Pick a project.";
	if (!form.value.lines.length) e.lines = "Add at least one schedule-of-values line.";
	errors.value = e;
	return Object.keys(e).length === 0;
}

// Map a CostCodePicker selection onto the backend line fields.
function lineForSave(line) {
	const cc = line.cost_code;
	const out = {
		scope: line.scope,
		uom: line.uom,
		qty: Number(line.qty) || 0,
		rate: Number(line.rate) || 0,
		cost_code_type: "",
		cost_code_group: "",
		cost_code_item: "",
		cost_code_label: "",
	};
	if (cc && typeof cc === "object") {
		out.cost_code_type = cc.type === "item" ? "Item" : "Group";
		out.cost_code_group = cc.group_code || "";
		out.cost_code_item = cc.item_code || "";
		out.cost_code_label = cc.label || "";
	}
	return out;
}

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	try {
		const payload = {
			name: editingId.value || undefined,
			subcontractor: form.value.subcontractor,
			project: form.value.project,
			date: form.value.date,
			delivery_type: form.value.delivery_type || null,
			retention_percent: form.value.retention_percent,
			terms_template: form.value.terms_template || null,
			terms: form.value.terms,
			lines: form.value.lines.map(lineForSave),
		};
		const wo = await saveWorkOrder(payload);
		router.push(`/subcontractor-work-orders/${wo.name}`);
	} catch (err) {
		showToast(err.message || "Failed to save work order", "error");
	} finally {
		saving.value = false;
	}
}
function onCancel() {
	router.back();
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Work Orders", to: "/subcontractor-work-orders" },
	isEdit.value
		? { label: editingId.value, to: `/subcontractor-work-orders/${editingId.value}` }
		: { label: "New" },
	...(isEdit.value ? [{ label: "Edit" }] : []),
]);
const pageTitle = computed(() => (isEdit.value ? `Edit ${editingId.value}` : "New Work Order"));
const saveLabel = computed(() =>
	saving.value ? "Saving…" : isEdit.value ? "Save changes" : "Create work order",
);
</script>

<template>
	<DeskPage :title="pageTitle" :breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saveLabel"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<DeskSection title="Header" :cols="3">
				<DeskField label="Subcontractor" required :error="errors.subcontractor">
					<DeskLinkPicker
						v-model="form.subcontractor"
						doctype="Subcontractor"
						label-field="subcontractor_name"
						value-field="name"
						:search-fields="['subcontractor_name', 'name']"
						placeholder="Pick a subcontractor…"
					/>
				</DeskField>
				<DeskField label="Project" required :error="errors.project">
					<DeskLinkPicker
						v-model="form.project"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						:search-fields="['project_name', 'name']"
						placeholder="Pick a project…"
					/>
				</DeskField>
				<DeskField label="Date" required
					><DeskInput v-model="form.date" type="date"
				/></DeskField>
				<DeskField label="Delivery type">
					<DeskLinkPicker
						v-model="form.delivery_type"
						doctype="Subcontract Delivery Type"
						label-field="name"
						value-field="name"
						placeholder="Pick a delivery type…"
					/>
				</DeskField>
				<DeskField label="Retention %"
					><DeskInput
						v-model.number="form.retention_percent"
						type="number"
						min="0"
						max="20"
						step="0.5"
				/></DeskField>
			</DeskSection>

			<!-- Schedule of values editor -->
			<section class="mt-6">
				<div class="flex items-center justify-between mb-2 gap-3">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						Schedule of values
					</h3>
					<button
						type="button"
						class="text-xs text-brand-700 hover:underline"
						@click="addLine"
					>
						+ Add line
					</button>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
					<table class="w-full text-xs" style="min-width: 720px">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-3 py-2">Scope</th>
								<th class="text-left px-3 py-2">Cost code</th>
								<th class="text-right px-3 py-2">Qty</th>
								<th class="text-left px-3 py-2">UOM</th>
								<th class="text-right px-3 py-2">Rate</th>
								<th class="text-right px-3 py-2">Amount</th>
								<th class="text-center px-2 py-2 w-8"></th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(line, idx) in form.lines"
								:key="idx"
								class="border-t border-ink-100"
							>
								<td class="px-3 py-3">
									<input
										v-model="line.scope"
										class="w-full bg-transparent text-xs py-1.5 focus:outline-none"
										placeholder="Describe the work — free text"
									/>
								</td>
								<td class="px-3 py-3" style="min-width: 160px">
									<CostCodePicker
										v-model="line.cost_code"
										:project-id="form.project"
										placeholder="Pick code…"
									/>
								</td>
								<td class="px-3 py-3">
									<input
										v-model.number="line.qty"
										type="number"
										min="0"
										class="w-20 bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
									/>
								</td>
								<td class="px-3 py-3" style="min-width: 120px">
									<DeskLinkPicker
										v-model="line.uom"
										doctype="UOM"
										label-field="name"
										value-field="name"
										placeholder="—"
									/>
								</td>
								<td class="px-3 py-3">
									<input
										v-model.number="line.rate"
										type="number"
										min="0"
										step="0.01"
										class="w-24 bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
									/>
								</td>
								<td
									class="px-3 py-3 text-right tabular-nums text-ink-900 font-medium"
								>
									{{ fmtINR(lineAmount(line)) }}
								</td>
								<td class="px-2 py-3 text-center">
									<button
										type="button"
										class="text-ink-400 hover:text-danger-600"
										title="Remove"
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
									colspan="5"
									class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
								>
									Total
								</td>
								<td
									class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-ink-900"
								>
									{{ fmtINR(total) }}
								</td>
								<td></td>
							</tr>
						</tfoot>
					</table>
				</div>
				<p v-if="errors.lines" class="text-xs text-danger-700 mt-1">{{ errors.lines }}</p>
			</section>

			<!-- Terms & conditions -->
			<DeskSection title="Terms & conditions" :cols="1">
				<DeskField
					label="Import from template"
					hint="Pick a standard template to fill the box below. You can edit the text after importing."
				>
					<DeskLinkPicker
						:model-value="form.terms_template"
						doctype="Terms and Conditions"
						label-field="name"
						value-field="name"
						placeholder="— Choose a terms template —"
						@update:model-value="onPickTermsTemplate"
					/>
				</DeskField>
				<DeskField label="Terms">
					<DeskTextarea
						v-model="form.terms"
						:rows="8"
						placeholder="Terms & conditions printed on the work order…"
					/>
				</DeskField>
			</DeskSection>
		</DeskForm>
	</DeskPage>
</template>
