<script setup>
// Reusable "+ Add filter" bar for DeskList (client-side) views — the same dynamic-filter builder
// DocTypeListView has, packaged so any list can drop it in. Renders the button, the filter chips
// (click a chip to edit, X to remove, a Clear-all when there are any) and the DeskFilterEditor
// popover. Two-way binds the active filters via `v-model:filters`; the parent applies them with
// matchesDynamicFilters(row, filters) from utils/dynamicFilters.
import { ref } from "vue";
import DeskFilterEditor from "@/components/desk/DeskFilterEditor.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";

const props = defineProps({
	// Filterable fields: [{ fieldname, label, fieldtype, options }]
	fields: { type: Array, default: () => [] },
	// Active filters (v-model:filters): [{ fieldname, label, fieldtype, options, condition, value }]
	filters: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:filters"]);

const editorOpen = ref(false);
const editingIndex = ref(-1);

function openAdd() {
	editingIndex.value = -1;
	editorOpen.value = true;
}
function editChip(i) {
	editingIndex.value = i;
	editorOpen.value = true;
}
function onApply(filter) {
	const next = props.filters.slice();
	if (editingIndex.value >= 0) next.splice(editingIndex.value, 1, filter);
	else next.push(filter);
	emit("update:filters", next);
	editorOpen.value = false;
	editingIndex.value = -1;
}
function removeChip(i) {
	const next = props.filters.slice();
	next.splice(i, 1);
	emit("update:filters", next);
}
function clearAll() {
	emit("update:filters", []);
}

const CONDITION_SYMBOL = {
	"=": "=", "!=": "≠", like: "like", "not like": "not like", in: "in", "not in": "not in",
	is: "is", ">": ">", "<": "<", ">=": "≥", "<=": "≤", Between: "between", Timespan: "in",
};
function chipLabel(f) {
	let text;
	if (f.condition === "is") text = f.value === "not set" ? "Not Set" : "Set";
	else if (f.condition === "Between" && Array.isArray(f.value)) text = `${f.value[0]} – ${f.value[1]}`;
	else if (Array.isArray(f.value)) text = f.value.join(", ");
	else if (f.fieldtype === "Check") text = f.value === "0" || f.value === 0 ? "No" : "Yes";
	else text = String(f.value ?? "");
	return `${f.label} ${CONDITION_SYMBOL[f.condition] || f.condition} ${text}`.trim();
}
</script>

<template>
	<div class="flex items-center gap-2 flex-wrap">
		<span
			v-for="(f, i) in filters"
			:key="i"
			class="cursor-pointer"
			title="Click to edit"
			@click="editChip(i)"
		>
			<DeskFilterChip :label="chipLabel(f)" @remove.stop="removeChip(i)" />
		</span>
		<button
			v-if="filters.length"
			type="button"
			class="text-[11px] text-ink-500 hover:text-ink-800 px-1"
			@click="clearAll"
		>
			Clear
		</button>
		<div class="relative">
			<button
				type="button"
				class="text-xs text-brand-700 hover:text-brand-800 font-medium whitespace-nowrap"
				@click="openAdd"
			>
				+ Add filter
			</button>
			<template v-if="editorOpen">
				<div class="fixed inset-0 z-30" @click="editorOpen = false"></div>
				<div class="absolute left-0 top-7 z-40">
					<DeskFilterEditor
						:fields="fields"
						:initial="editingIndex >= 0 ? filters[editingIndex] : null"
						@apply="onApply"
						@cancel="editorOpen = false"
					/>
				</div>
			</template>
		</div>
	</div>
</template>
