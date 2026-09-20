<script setup>
// The library picker for quotation lines — today, the Assembly catalogue at its resolved
// rate. Manual is not offered: "+ Add row" types straight into the grid with no dialog.
// The quantity always stays the user's — a library knows the work, not how much of it.

import { computed, reactive, ref, watch } from "vue";
import { useDocTypeList } from "@/composables/useDocTypeList";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import { fmtCurrency } from "@/utils/format";

const props = defineProps({ open: Boolean });
const emit = defineEmits(["update:open", "add"]);

const BLANK = { assembly: "", code: "", description: "", uom: "Nos", qty: 1, rate: 0 };
const row = reactive({ ...BLANK });
const error = ref("");

// Shares `buildsuite-assembly-options` with EstimateTemplateDetailView, so opening this picker
// costs no extra request once either screen has loaded the catalogue. The query has to stay
// identical to that one — a shared key means whichever loads first is what both screens read,
// so a narrower field list here would quietly rob the other of a column.
const assembliesRes = useDocTypeList("Assembly", {
	fields: ["name", "assembly_name", "category", "rate_per_unit", "uom"],
	filters: [["disabled", "=", 0]],
	orderBy: "assembly_name asc",
	pageLength: 0,
	cache: "buildsuite-assembly-options",
});

const assemblyOptions = computed(() =>
	(assembliesRes.data || []).map((a) => ({
		value: a.name,
		label: a.assembly_name,
		group: a.category,
		hint: `${a.name} · ${a.uom} · ${fmtCurrency(a.rate_per_unit)}`,
	})),
);

const amount = computed(() => (Number(row.qty) || 0) * (Number(row.rate) || 0));

watch(
	() => props.open,
	(isOpen) => {
		if (!isOpen) return;
		Object.assign(row, BLANK);
		error.value = "";
	},
);

function pickAssembly(name) {
	const assembly = (assembliesRes.data || []).find((a) => a.name === name);
	if (!assembly) return;
	row.assembly = name;
	row.code = assembly.name;
	row.description = assembly.assembly_name;
	row.uom = assembly.uom || BLANK.uom;
	row.rate = Number(assembly.rate_per_unit) || 0;
}

function close() {
	emit("update:open", false);
}

function submit() {
	if (!row.assembly) {
		error.value = "Pick something from the assembly list.";
		return;
	}
	if (!row.description.trim()) {
		error.value = "Say what the line is for.";
		return;
	}
	if (!(Number(row.qty) > 0)) {
		error.value = "Quantity has to be more than nothing.";
		return;
	}
	// `code` is the estimator's own and stays editable; `source_ref` is the trail back to the
	// catalogue, so it comes from the picked assembly and never from the box above.
	emit("add", {
		source: "Assembly",
		code: row.code.trim(),
		source_ref: row.assembly,
		description: row.description.trim(),
		uom: row.uom,
		qty: Number(row.qty),
		rate: Number(row.rate),
	});
	close();
}
</script>

<template>
	<Teleport to="body">
		<div v-if="open"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-4 overflow-y-auto"
			@click="close">
			<div class="bg-white w-full max-w-2xl mt-16 shadow-fp-lg" style="border-radius: 12px"
				@click.stop>
				<header class="px-5 py-3 border-b border-ink-100 flex items-center justify-between">
					<div>
						<div class="text-sm font-semibold text-ink-900">Add a line</div>
						<div class="text-[11px] text-ink-500">
							Pick it out of the library — the quantity is always yours to enter. To
							type one from scratch, use
							<span class="text-ink-700">+ Add row</span> on the grid.
						</div>
					</div>
					<button type="button" class="text-ink-400 hover:text-ink-900 text-xl leading-none px-1"
						title="Close" @click="close">
						&times;
					</button>
				</header>

				<div class="px-5 py-4 space-y-4">
					<DeskField label="Assembly" required>
						<DeskSearchableSelect :model-value="row.assembly" :options="assemblyOptions"
							placeholder="Pick an assembly…" search-placeholder="Search assemblies…"
							@update:model-value="pickAssembly" />
					</DeskField>

					<DeskField label="Description" required>
						<DeskTextarea v-model="row.description" :rows="2"
							placeholder="What the line is for" />
					</DeskField>

					<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
						<DeskField label="Code">
							<DeskInput v-model="row.code" placeholder="optional" />
						</DeskField>
						<DeskField label="Unit">
							<DeskLinkPicker v-model="row.uom" doctype="UOM" label-field="name"
								value-field="name" placeholder="Unit" />
						</DeskField>
						<DeskField label="Quantity" required>
							<DeskInput v-model.number="row.qty" type="number" min="0" step="any" />
						</DeskField>
						<DeskField label="Rate" required>
							<DeskInput v-model.number="row.rate" type="number" min="0" step="any" />
						</DeskField>
					</div>

					<div class="flex items-center justify-between bg-ink-50 px-3 py-2"
						style="border-radius: 6px">
						<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">
							Line amount
						</span>
						<span class="text-sm font-semibold text-ink-900 tabular-nums">
							{{ fmtCurrency(amount) }}
						</span>
					</div>

					<p v-if="error" class="text-xs text-danger-700">{{ error }}</p>
				</div>

				<footer class="px-5 py-3 border-t border-ink-100 flex items-center justify-end gap-2">
					<button type="button"
						class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
						style="border-radius: 6px" @click="close">
						Cancel
					</button>
					<button type="button" class="desk-save-btn !text-xs" @click="submit">
						Add line
					</button>
				</footer>
			</div>
		</div>
	</Teleport>
</template>
