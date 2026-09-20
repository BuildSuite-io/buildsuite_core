<script setup>
// "Add a line" — the library route onto a tender's item grid. Pick a source that already knows
// the description and the rate, then correct anything before it lands.
//
// Only ASSEMBLY is offered today. BOQ is listed as a source but filtered out while the tender
// has no estimate behind it, because a tab with nothing behind it is worse than one that is not
// there. Once the tender carries a source estimate, BOQ is one more entry in SOURCES and a
// second branch below.
//
// The assembly PREFILLS the fields; it does not lock them. The catalogue knows what a square
// metre of plaster costs, not what this bid needs — so every field stays editable, and the
// quantity is never guessed.

import { computed, ref, watch } from "vue";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { fmtCurrency } from "@/utils/format";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";

const props = defineProps({
	open: { type: Boolean, default: false },
	// The estimate this tender was priced off. Absent today — it gates the BOQ source.
	sourceBoq: { type: String, default: null },
});
const emit = defineEmits(["close", "add"]);

const SOURCES = ["Assembly", "BOQ"];
const available = computed(() => SOURCES.filter((s) => s !== "BOQ" || !!props.sourceBoq));

const source = ref("Assembly");
const assembly = ref("");
const code = ref("");
const description = ref("");
const unit = ref("");
const qty = ref(1);
const rate = ref(0);
const error = ref("");

const lineAmount = computed(() => (Number(qty.value) || 0) * (Number(rate.value) || 0));

// Shares `buildsuite-assembly-options` with EstimateTemplateDetailView, so opening this picker
// costs no extra request once either screen has loaded the catalogue.
const assembliesRes = useDocTypeList("Assembly", {
	fields: ["name", "assembly_name", "category", "rate_per_unit", "uom"],
	filters: [["disabled", "=", 0]],
	orderBy: "assembly_name asc",
	pageLength: 0,
	cache: "buildsuite-assembly-options",
});
const assemblies = computed(() => assembliesRes.data || []);
const assemblyMap = computed(() =>
	Object.fromEntries(assemblies.value.map((a) => [a.name, a]))
);
const assemblyOptions = computed(() =>
	assemblies.value.map((a) => ({
		value: a.name,
		label: `${a.name} · ${a.assembly_name}`,
		group: a.category,
		hint: `${fmtCurrency(a.rate_per_unit)} per ${a.uom}`,
	}))
);

function reset() {
	source.value = available.value[0] || "Assembly";
	assembly.value = "";
	code.value = "";
	description.value = "";
	unit.value = "";
	qty.value = 1;
	rate.value = 0;
	error.value = "";
}
watch(() => props.open, (isOpen) => isOpen && reset());

// Prefill, do not lock — whatever the estimator has already typed in a field is theirs.
function onAssemblyPicked(id) {
	assembly.value = id;
	const a = assemblyMap.value[id];
	if (!a) return;
	// Assembly is autonamed field:assembly_code, so `name` IS the code.
	code.value = a.name || "";
	description.value = a.assembly_name || "";
	unit.value = a.uom || "";
	rate.value = a.rate_per_unit || 0;
	error.value = "";
}

function add() {
	if (!assembly.value) return (error.value = "Pick an assembly first.");
	if (!description.value.trim()) return (error.value = "A line needs a description.");

	// sell_rate and amount are deliberately left out — calculate_items() derives them from the
	// tender's margin on save, and anything set here would only be overwritten.
	emit("add", {
		source: "Assembly",
		source_ref: assembly.value,
		code: code.value.trim() || null,
		description: description.value.trim(),
		unit: unit.value || null,
		qty: Number(qty.value) || 0,
		rate: Number(rate.value) || 0,
	});
	emit("close");
}
</script>

<template>
	<Teleport to="body">
		<div v-if="open" class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
			@click.self="emit('close')">
			<div class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
				style="border-radius: 12px; max-height: calc(100vh - 3rem)" @click.stop>
				<header class="px-5 py-3 border-b border-ink-200 flex items-start justify-between gap-4">
					<div>
						<h2 class="text-sm font-semibold text-ink-900">Add a line</h2>
						<p class="text-xs text-ink-500 mt-0.5">
							Pick it out of the library — the quantity is always yours to enter. To type one
							from scratch, use <span class="font-medium text-ink-700">+ Add Row</span> on the
							grid.
						</p>
					</div>
					<button type="button" class="text-ink-500 hover:text-ink-900 text-lg leading-none shrink-0"
						aria-label="Close" @click="emit('close')">
						×
					</button>
				</header>

				<div class="px-5 pt-3 pb-5 space-y-3 overflow-y-auto min-h-0">
					<div class="flex items-center gap-4 border-b border-ink-200">
						<button v-for="s in available" :key="s" type="button"
							class="text-xs pb-2 -mb-px border-b-2"
							:class="source === s
								? 'border-brand-600 text-brand-700 font-medium'
								: 'border-transparent text-ink-500 hover:text-ink-700'"
							@click="source = s">
							{{ s }}
						</button>
					</div>

					<p v-if="!sourceBoq" class="text-xs text-ink-500">
						BOQ lines appear once this tender is priced off an estimate.
					</p>

					<template v-if="source === 'Assembly'">
						<DeskField label="Assembly" required>
							<DeskSearchableSelect :model-value="assembly" :options="assemblyOptions"
								placeholder="Pick an assembly…" search-placeholder="Search by code or name…"
								allow-clear @update:model-value="onAssemblyPicked" />
						</DeskField>

						<DeskField label="Description" required>
							<DeskTextarea v-model="description" :rows="2" placeholder="What the line is for" />
						</DeskField>

						<div class="grid grid-cols-4 gap-3">
							<DeskField label="Code">
								<DeskInput v-model="code" placeholder="optional" />
							</DeskField>
							<DeskField label="Unit">
								<DeskLinkPicker v-model="unit" doctype="UOM" placeholder="nos" />
							</DeskField>
							<DeskField label="Quantity" required>
								<DeskInput v-model="qty" type="number" min="0" step="any" />
							</DeskField>
							<DeskField label="Rate (₹)" required>
								<DeskInput v-model="rate" type="number" min="0" step="any" />
							</DeskField>
						</div>

						<div
							class="bg-ink-50 border border-ink-200 px-3 py-2 flex items-center justify-between"
							style="border-radius: 6px">
							<span class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
								Line amount
							</span>
							<span class="text-sm font-semibold text-ink-900 tabular-nums">
								{{ fmtCurrency(lineAmount) }}
							</span>
						</div>
						<p class="text-[11px] text-ink-400">
							Cost before margin — the tender's margin is added to the rate on save.
						</p>
					</template>

					<p v-if="error" class="text-xs text-danger-700">{{ error }}</p>
				</div>

				<footer class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2">
					<button type="button"
						class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
						style="border-radius: 6px" @click="emit('close')">
						Cancel
					</button>
					<button type="button" class="desk-save-btn !text-xs" @click="add">Add line</button>
				</footer>
			</div>
		</div>
	</Teleport>
</template>
