<script setup>
// Measurement Book form — create + edit. Pre-fills the WO from
// ?work_order=… on the URL. The entries editor records description +
// WO line + Nos × L × B × D, with the quantity derived live (or typed
// directly to override). Only Draft books are editable (the backend
// enforces this; the detail page gates the Edit button on status).

import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { usePermissions } from "@/composables/usePermissions";
import { getWorkOrder, getMeasurementBook, saveMeasurementBook } from "@/data/subcontractApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import CostCodePicker from "@/components/CostCodePicker.vue";

const route = useRoute();
const router = useRouter();
const { canCreate, canEdit } = usePermissions();

const editingId = computed(() => route.params.id || null);
const isEdit = computed(() => !!editingId.value);
// Edit mode needs edit rights; create mode needs create rights.
const canSaveForm = computed(() =>
	isEdit.value ? canEdit("measurementBook") : canCreate("measurementBook")
);

function emptyEntry() {
	return {
		description: "",
		cost_code: null,
		work_order_line: "",
		uom: "",
		nos: 1,
		length: 0,
		breadth: 0,
		depth: 1,
		quantity: 0,
		is_deduction: false,
		_autoQty: true,
	};
}

function todayIso() {
	return new Date().toISOString().slice(0, 10);
}

const form = ref({
	work_order: route.query.work_order || "",
	project: "",
	date: todayIso(),
	measured_by: "",
	remarks: "",
	entries: [emptyEntry()],
});
const woLines = ref([]); // [{ name, scope, cost_code_*, uom }]
// Project + Subcontractor surface read-only on the header, derived from the WO.
const woProjectName = ref("");
const woSubName = ref("");
const errors = ref({});
const saving = ref(false);
const loading = ref(false);

function costCodeFromFields(src) {
	if (!src?.cost_code_type) return null;
	return {
		type: (src.cost_code_type || "").toLowerCase(),
		group_code: src.cost_code_group || "",
		item_code: src.cost_code_item || null,
		label: src.cost_code_label || "",
	};
}

// Load the WO (project + SOV lines) when the work order changes.
async function loadWorkOrder(wo, { autofillFirst = false } = {}) {
	if (!wo) {
		woLines.value = [];
		woProjectName.value = "";
		woSubName.value = "";
		return;
	}
	try {
		const doc = await getWorkOrder(wo);
		form.value.project = doc.project || "";
		woProjectName.value = doc.project_name || doc.project || "";
		woSubName.value = doc.subcontractor_name || doc.subcontractor || "";
		woLines.value = doc.lines || [];
		// Single-line WO: default the first blank entry to that line.
		if (
			autofillFirst &&
			form.value.entries.length === 1 &&
			!form.value.entries[0].description
		) {
			const first = woLines.value[0];
			if (first) {
				const e = form.value.entries[0];
				e.work_order_line = first.name;
				e.cost_code = costCodeFromFields(first);
				e.uom = first.uom || "";
			}
		}
	} catch {
		woLines.value = [];
	}
}

// Load an existing MB in edit mode, else react to WO picks in create mode.
watch(
	editingId,
	async (id) => {
		if (id) {
			loading.value = true;
			try {
				const mb = await getMeasurementBook(id);
				if (mb.status !== "Draft") {
					router.replace(`/measurement-books/${id}`);
					return;
				}
				form.value = {
					work_order: mb.work_order || "",
					project: mb.project || "",
					date: mb.date || todayIso(),
					measured_by: mb.measured_by || "",
					remarks: mb.remarks || "",
					entries: (mb.entries || []).map((e) => ({
						description: e.description || "",
						cost_code: costCodeFromFields(e),
						work_order_line: e.work_order_line || "",
						uom: e.uom || "",
						nos: e.nos ?? 1,
						length: e.length ?? 0,
						breadth: e.breadth ?? 0,
						depth: e.depth ?? 1,
						quantity: e.quantity ?? 0,
						is_deduction: !!e.is_deduction,
						_autoQty: false,
					})),
				};
				if (!form.value.entries.length) form.value.entries = [emptyEntry()];
				woLines.value = mb.wo_lines || [];
				woProjectName.value = mb.project_name || mb.project || "";
				woSubName.value = mb.subcontractor_name || "";
			} catch (err) {
				showToast(err.message || "Failed to load measurement book", "error");
			} finally {
				loading.value = false;
			}
		} else {
			loadWorkOrder(form.value.work_order, { autofillFirst: true });
		}
	},
	{ immediate: true }
);

// In create mode, reloading WO lines when the user changes the WO picker.
function onWorkOrderChange(wo) {
	form.value.work_order = wo;
	loadWorkOrder(wo, { autofillFirst: true });
}

const woLineOptions = computed(() =>
	woLines.value.map((l) => ({ value: l.name, label: l.scope || l.name }))
);

// Changing the WO line on a row recomputes its dependent fields (cost code +
// UOM) from the newly selected line, so they never stay stale on the old line.
function onEntryLineChange(entry) {
	const line = woLines.value.find((l) => l.name === entry.work_order_line);
	if (!line) {
		entry.cost_code = null;
		entry.uom = "";
		return;
	}
	entry.cost_code = costCodeFromFields(line);
	entry.uom = line.uom || "";
}

function roundQty(n) {
	return Math.round((Number(n) || 0) * 1000) / 1000;
}
function derivedQty(e) {
	return roundQty(
		(Number(e.nos) || 0) *
			(Number(e.length) || 0) *
			(Number(e.breadth) || 0) *
			(Number(e.depth) || 0)
	);
}
function previewQty(e) {
	if (e._autoQty || !Number(e.quantity)) return derivedQty(e);
	return Number(e.quantity);
}
function onDimChange(e) {
	if (e._autoQty) e.quantity = derivedQty(e);
}
function onQtyOverride(e) {
	e._autoQty = false;
}
function clearOverride(e) {
	e._autoQty = true;
	e.quantity = derivedQty(e);
}

const measuredTotal = computed(() =>
	form.value.entries.reduce((a, e) => a + (e.is_deduction ? -1 : 1) * previewQty(e), 0)
);

function addRow() {
	form.value.entries.push(emptyEntry());
}
function removeRow(idx) {
	form.value.entries.splice(idx, 1);
}

// A complete entry needs Description, WO line and UOM (cost code is optional).
function entryIncomplete(e) {
	return !(e.description || "").trim() || !e.work_order_line || !(e.uom || "").trim();
}
function validate() {
	const e = {};
	if (!form.value.work_order) e.work_order = "Pick a work order.";
	if (!form.value.entries.length) {
		e.entries = "Add at least one measurement entry.";
	} else if (form.value.entries.some(entryIncomplete)) {
		e.entries = "Each entry needs a description, WO line and UOM.";
	}
	errors.value = e;
	return Object.keys(e).length === 0;
}

function entryForSave(e) {
	const cc = e.cost_code;
	const out = {
		description: e.description,
		work_order_line: e.work_order_line,
		uom: e.uom,
		nos: Number(e.nos) || 0,
		length: Number(e.length) || 0,
		breadth: Number(e.breadth) || 0,
		depth: Number(e.depth) || 0,
		quantity: previewQty(e),
		is_deduction: e.is_deduction ? 1 : 0,
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
		const mb = await saveMeasurementBook({
			name: editingId.value || undefined,
			work_order: form.value.work_order,
			project: form.value.project,
			date: form.value.date,
			measured_by: form.value.measured_by || null,
			remarks: form.value.remarks,
			entries: form.value.entries.map(entryForSave),
		});
		router.push(`/measurement-books/${mb.name}`);
	} catch (err) {
		showToast(err.message || "Failed to save measurement book", "error");
	} finally {
		saving.value = false;
	}
}
function onCancel() {
	router.back();
}

const pageTitle = computed(() =>
	isEdit.value ? `Edit ${editingId.value}` : "New Measurement Book"
);
const saveLabel = computed(() =>
	saving.value ? "Saving…" : isEdit.value ? "Save changes" : "Create MB"
);
const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Subcontract", to: "/subcontract" },
	{ label: "Measurement Books", to: "/measurement-books" },
	...(isEdit.value
		? [
				{ label: editingId.value, to: `/measurement-books/${editingId.value}` },
				{ label: "Edit" },
		  ]
		: [{ label: "New" }]),
]);
</script>

<template>
	<DeskPage :title="pageTitle" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canSaveForm"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			You don't have permission to {{ isEdit ? "edit this" : "create a" }} measurement book.
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

			<DeskSection title="Header" :cols="3">
				<DeskField label="Work order" required :error="errors.work_order">
					<DeskLinkPicker
						:model-value="form.work_order"
						doctype="Subcontractor Work Order"
						label-field="name"
						value-field="name"
						placeholder="Pick a work order…"
						@update:model-value="onWorkOrderChange"
					/>
				</DeskField>
				<!-- Read-only, derived from the work order. -->
				<DeskField label="Project" hint="Derived from the work order.">
					<div
						class="text-sm pt-1.5"
						:class="form.work_order ? 'text-ink-900' : 'text-ink-400'"
					>
						{{ form.work_order ? woProjectName || form.project || "—" : "—" }}
					</div>
				</DeskField>
				<DeskField label="Subcontractor" hint="Derived from the work order.">
					<div
						class="text-sm pt-1.5"
						:class="form.work_order ? 'text-ink-900' : 'text-ink-400'"
					>
						{{ form.work_order ? woSubName || "—" : "—" }}
					</div>
				</DeskField>
				<DeskField label="Date" required
					><DeskInput v-model="form.date" type="date"
				/></DeskField>
				<DeskField label="Measured by">
					<DeskLinkPicker
						v-model="form.measured_by"
						doctype="User"
						label-field="full_name"
						value-field="name"
						placeholder="— Optional —"
					/>
				</DeskField>
				<DeskField label="Remarks" class="md:col-span-2"
					><DeskInput v-model="form.remarks"
				/></DeskField>
			</DeskSection>

			<!-- Entries editor -->
			<section class="mt-6">
				<div class="flex items-center justify-between mb-2 gap-3">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">
						Entries — Quantity = Nos × L × B × D, or type directly
					</h3>
					<button
						type="button"
						class="text-xs text-brand-700 hover:underline"
						@click="addRow"
					>
						+ Add entry
					</button>
				</div>
				<div class="bg-white border border-ink-200 rounded-lg overflow-x-auto">
					<table class="w-full text-xs" style="min-width: 900px">
						<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
							<tr>
								<th class="text-left px-2 py-2 w-8">#</th>
								<th class="text-left px-2 py-2 min-w-[160px]">
									Description <span class="text-danger-600">*</span>
								</th>
								<th class="text-left px-2 py-2 min-w-[130px]">
									WO line <span class="text-danger-600">*</span>
								</th>
								<th class="text-left px-2 py-2 min-w-[130px]">Cost code</th>
								<th class="text-right px-2 py-2 w-14">Nos</th>
								<th class="text-right px-2 py-2 w-16">L</th>
								<th class="text-right px-2 py-2 w-16">B</th>
								<th class="text-right px-2 py-2 w-14">D</th>
								<th class="text-right px-2 py-2 w-20">Qty</th>
								<th class="text-left px-2 py-2 w-20">
									UOM <span class="text-danger-600">*</span>
								</th>
								<th class="text-center px-2 py-2 w-14">Deduct</th>
								<th class="text-center px-2 py-2 w-8"></th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="(e, idx) in form.entries"
								:key="idx"
								class="border-t border-ink-100"
								:class="e.is_deduction ? 'bg-danger-50/30' : ''"
							>
								<td class="px-2 py-1 text-ink-500">{{ idx + 1 }}</td>
								<td class="px-2 py-1">
									<input
										v-model="e.description"
										class="w-full bg-transparent text-xs py-1.5 focus:outline-none"
										placeholder="What was measured"
									/>
								</td>
								<td class="px-2 py-1">
									<select
										v-model="e.work_order_line"
										class="w-full bg-transparent dark:bg-[#242424] text-xs text-ink-900 py-1.5 focus:outline-none"
										@change="onEntryLineChange(e)"
									>
										<option value="">—</option>
										<option
											v-for="opt in woLineOptions"
											:key="opt.value"
											:value="opt.value"
										>
											{{ (opt.label || "").slice(0, 40) }}
										</option>
									</select>
								</td>
								<td class="px-2 py-1">
									<CostCodePicker
										v-model="e.cost_code"
										:project-id="form.project"
										placeholder="Pick code…"
									/>
								</td>
								<td class="px-2 py-1">
									<input
										v-model.number="e.nos"
										type="number"
										min="0"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
										@input="onDimChange(e)"
									/>
								</td>
								<td class="px-2 py-1">
									<input
										v-model.number="e.length"
										type="number"
										min="0"
										step="0.01"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
										@input="onDimChange(e)"
									/>
								</td>
								<td class="px-2 py-1">
									<input
										v-model.number="e.breadth"
										type="number"
										min="0"
										step="0.01"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
										@input="onDimChange(e)"
									/>
								</td>
								<td class="px-2 py-1">
									<input
										v-model.number="e.depth"
										type="number"
										min="0"
										step="0.01"
										class="w-full bg-transparent text-xs text-right tabular-nums py-1.5 focus:outline-none"
										@input="onDimChange(e)"
									/>
								</td>
								<td class="px-2 py-1">
									<input
										v-model.number="e.quantity"
										type="number"
										min="0"
										step="0.01"
										class="w-full text-xs text-right tabular-nums py-1.5 focus:outline-none bg-transparent"
										:title="
											e._autoQty
												? 'Derived from Nos × L × B × D — type to override.'
												: 'Override active (clear to re-derive).'
										"
										@input="onQtyOverride(e)"
									/>
									<button
										v-if="!e._autoQty"
										type="button"
										class="text-[9px] text-brand-700 hover:underline"
										@click="clearOverride(e)"
									>
										clear override
									</button>
								</td>
								<td class="px-2 py-1" style="min-width: 110px">
									<DeskLinkPicker
										v-model="e.uom"
										doctype="UOM"
										label-field="name"
										value-field="name"
										placeholder="—"
									/>
								</td>
								<td class="px-2 py-1 text-center">
									<input
										v-model="e.is_deduction"
										type="checkbox"
										class="accent-danger-600"
										title="Mark as a deduction (subtracts from measured total)"
									/>
								</td>
								<td class="px-2 py-1 text-center">
									<button
										type="button"
										class="text-ink-400 hover:text-danger-600"
										title="Remove"
										@click="removeRow(idx)"
									>
										✕
									</button>
								</td>
							</tr>
						</tbody>
						<tfoot>
							<tr class="border-t-2 border-ink-200 bg-ink-50">
								<td
									colspan="8"
									class="px-3 py-2 text-right text-xs font-semibold text-ink-700 uppercase tracking-wider"
								>
									Measured total
								</td>
								<td
									class="px-3 py-2 text-right tabular-nums text-sm font-semibold text-info-700"
								>
									{{ measuredTotal.toLocaleString("en-IN") }}
								</td>
								<td colspan="3"></td>
							</tr>
						</tfoot>
					</table>
				</div>
				<p v-if="errors.entries" class="text-xs text-danger-700 mt-1">
					{{ errors.entries }}
				</p>
			</section>
		</DeskForm>
	</DeskPage>
</template>
