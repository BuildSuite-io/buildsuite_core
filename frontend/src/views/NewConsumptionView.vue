<script setup>
// Record / edit a Material Consumption, draft only.
// The store is derived from the project, never picked.

import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useProjectOptions } from "@/composables/useProjectOptions";
import {
	getMaterialConsumption,
	getSiteStock,
	saveMaterialConsumption,
} from "@/data/materialConsumptionApi";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import CostCodePicker from "@/components/CostCodePicker.vue";

const props = defineProps({ id: { type: String, default: "" } });
const router = useRouter();
const { projectOptions } = useProjectOptions();

const editing = computed(() => !!props.id);
const form = reactive({ project: "", cost_code: null, lines: [] });
const saving = ref(false);
const warehouse = ref("");
const stock = ref([]);
const loadingStock = ref(false);
const addPick = ref(null);

// reqId: a slower reply for the old project must not land last.
let stockReq = 0;
async function loadStock(project) {
	const my = ++stockReq;
	warehouse.value = "";
	stock.value = [];
	if (!project) return;
	loadingStock.value = true;
	try {
		const res = await getSiteStock(project);
		if (my !== stockReq) return;
		warehouse.value = res.warehouse || "";
		stock.value = res.rows || [];
	} catch (err) {
		if (my === stockReq) showToast(err.message || "Could not load site stock", "error");
	} finally {
		if (my === stockReq) loadingStock.value = false;
	}
}

// Cost code and stock both belong to one project, so both reset. In edit mode
// onMounted owns the load — a second one here would race it and the guard would
// drop whichever lost, leaving the lines built from empty stock.
watch(
	() => form.project,
	(project) => {
		if (editing.value) return;
		form.cost_code = null;
		form.lines = [];
		addPick.value = null;
		loadStock(project);
	}
);

onMounted(async () => {
	if (!editing.value) return;
	try {
		const doc = await getMaterialConsumption(props.id);
		if (doc.docstatus !== 0) {
			// A posted entry has moved stock — cancelled, never edited.
			router.replace(`/material-consumption/${props.id}`);
			return;
		}
		form.project = doc.project || "";
		form.cost_code = doc.cost_code_label
			? {
					type: (doc.cost_code_type || "").toLowerCase(),
					group_code: doc.cost_code_group || "",
					item_code: doc.cost_code_item || null,
					label: doc.cost_code_label,
			  }
			: null;
		await loadStock(form.project);
		// A draft deducts nothing, so availability still includes it.
		form.lines = (doc.items || []).map((it) => {
			const s = stock.value.find((r) => r.item_code === it.item_code);
			return {
				item_code: it.item_code,
				item_name: it.item_name || it.item_code,
				uom: it.uom || s?.uom || "",
				available: s?.available ?? 0,
				qty: it.qty,
			};
		});
	} catch (err) {
		showToast(err.message || "Could not load this entry", "error");
	}
});

const added = computed(() => new Set(form.lines.map((l) => l.item_code)));

const pickerOptions = computed(() =>
	stock.value
		.filter((r) => !added.value.has(r.item_code))
		.map((r) => ({
			value: r.item_code,
			label: r.item_name,
			// Code trails the qty so search matches either.
			hint: `${r.available} ${r.uom} available · ${r.item_code}`,
		}))
);

function addItem(code) {
	const row = stock.value.find((r) => r.item_code === code);
	if (row) form.lines.push({ ...row, qty: null });
	addPick.value = null;
}

// `max` stops the spinner, not typing or pasting.
function setQty(line, value) {
	const n = Number(value);
	line.qty = !Number.isFinite(n) || n <= 0 ? null : Math.min(n, line.available);
}

// Clamped: an old draft can hold more than the store still has.
function leftAfter(line) {
	const qty = Math.min(Number(line.qty) || 0, line.available);
	return Math.max(0, line.available - qty);
}

const filledLines = computed(() => form.lines.filter((l) => Number(l.qty) > 0));
const canSave = computed(() => !!form.project && filledLines.value.length > 0);

async function onSave() {
	saving.value = true;
	try {
		const res = await saveMaterialConsumption({
			name: props.id || undefined,
			project: form.project,
			cost_code: form.cost_code,
			items: filledLines.value.map((l) => ({
				item_code: l.item_code,
				qty: Number(l.qty),
				uom: l.uom,
			})),
		});
		showToast(editing.value ? "Consumption updated" : "Consumption recorded");
		router.push(`/material-consumption/${res.name}`);
	} catch (err) {
		showToast(err.message || "Failed to save the consumption", "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Procurement", to: "/procurement" },
	{ label: "Material Consumption", to: "/material-consumption" },
	{ label: editing.value ? props.id : "New" },
]);
</script>

<template>
	<DeskPage
		:title="editing ? `Edit ${props.id}` : 'Record Consumption'"
		subtitle="Issues site material out of stock. Cost-code it against the BOQ if you want it costed."
		:breadcrumbs="breadcrumbs"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="
						saving ? 'Saving…' : editing ? 'Save changes' : 'Record consumption'
					"
					:can-save="canSave"
					:saving="saving"
					@save="onSave"
					@cancel="router.back()"
				/>
			</template>

			<DeskSection title="Booking" :cols="2">
				<DeskField
					label="Project"
					required
					:hint="
						editing ? 'Locked while editing — the record stays on its project.' : ''
					"
				>
					<DeskSearchableSelect
						v-model="form.project"
						:options="projectOptions"
						:disabled="editing"
						placeholder="— Select project —"
						search-placeholder="Search projects…"
					/>
				</DeskField>

				<DeskField
					label="Cost code"
					hint="Optional. Set it to book this material against a BOQ group or line; leave it blank to record the issue without cost-coding it."
				>
					<CostCodePicker
						v-model="form.cost_code"
						:project-id="form.project"
						placeholder="— Not cost-coded —"
					/>
				</DeskField>
			</DeskSection>

			<DeskSection v-if="form.project" title="Items consumed" :cols="1">
				<!-- No store: an empty picker would look like an empty store. -->
				<p v-if="!warehouse && !loadingStock" class="text-sm text-danger-700">
					This project has no store, so nothing can be issued from it.
				</p>

				<template v-else-if="stock.length">
					<div class="w-96 max-w-full">
						<DeskSearchableSelect
							:model-value="addPick"
							:options="pickerOptions"
							placeholder="+ Add item — search name or code…"
							search-placeholder="Search site stock…"
							@update:model-value="addItem"
						/>
					</div>

					<div
						v-if="form.lines.length"
						class="border border-ink-200 overflow-hidden mt-4"
						style="border-radius: 8px"
					>
						<div
							class="grid grid-cols-[1fr_110px_140px_110px_44px] gap-2 items-center px-3 py-2 bg-ink-50 border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
						>
							<span>Item</span>
							<span class="text-right">In stock</span>
							<span class="text-right">Issue now</span>
							<span class="text-right">Left after</span>
							<span></span>
						</div>
						<div
							v-for="(line, i) in form.lines"
							:key="line.item_code"
							class="grid grid-cols-[1fr_110px_140px_110px_44px] gap-2 items-center px-3 py-2.5 border-b border-ink-100 last:border-0"
						>
							<div class="min-w-0">
								<div class="text-sm text-ink-900 truncate">
									{{ line.item_name }}
								</div>
								<div class="text-[11px] text-ink-400">{{ line.uom }}</div>
							</div>
							<div class="text-xs tabular-nums text-ink-600 text-right">
								{{ line.available }}
							</div>
							<DeskInput
								:model-value="line.qty"
								type="number"
								min="0"
								:max="line.available"
								placeholder="0"
								class="!text-right"
								@update:model-value="setQty(line, $event)"
							/>
							<div
								class="text-xs tabular-nums text-right"
								:class="
									leftAfter(line) === 0
										? 'text-warning-700 font-medium'
										: 'text-ink-600'
								"
							>
								{{ leftAfter(line) }}
							</div>
							<button
								type="button"
								class="text-ink-400 hover:text-danger-600 text-sm justify-self-end"
								:aria-label="`Remove ${line.item_name}`"
								@click="form.lines.splice(i, 1)"
							>
								✕
							</button>
						</div>
					</div>

					<p v-if="form.lines.length" class="text-[11px] text-ink-400 mt-2">
						You can't issue more than is at site — quantities cap at receipts received
						less what's already been consumed.
					</p>
					<div
						v-else
						class="border border-dashed border-ink-200 py-6 text-center text-sm text-ink-500 mt-4"
						style="border-radius: 8px"
					>
						Nothing added yet. Use the picker above to choose what left the store.
					</div>
				</template>

				<p v-else-if="!loadingStock" class="text-sm text-ink-500">
					Nothing in site stock for this project — record deliveries first; received
					material shows up here.
				</p>
			</DeskSection>
		</DeskForm>
	</DeskPage>
</template>
