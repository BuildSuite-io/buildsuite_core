<script setup>
// Editable grid for a child table (Table fieldtype). Columns come from the child
// DocType's in_list_view fields; each cell is a DocTypeFieldControl, so Link,
// Dynamic Link, Select, Check, Date and numeric cells all work (a row's Dynamic
// Link resolves its target from the sibling cell in the same row). Add / remove
// rows; new rows seed their field defaults.
import { computed } from "vue";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import DocTypeFieldControl from "./DocTypeFieldControl.vue";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	doctype: { type: String, required: true }, // the child DocType (field.options)
	disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);

const { meta } = useDoctypeMeta(props.doctype);

const HARD_SKIP = new Set([
	"Section Break",
	"Column Break",
	"Tab Break",
	"HTML",
	"Button",
	"Table",
	"Table MultiSelect",
]);

const columns = computed(() => {
	const fields = (meta.value?.fields || []).filter(
		(f) => !HARD_SKIP.has(f.fieldtype) && !f.hidden && !f.read_only
	);
	const inList = fields.filter((f) => f.in_list_view);
	return (inList.length ? inList : fields).slice(0, 8);
});

const rows = computed(() => props.modelValue || []);

function seededRow() {
	const row = {};
	for (const f of meta.value?.fields || []) {
		if (f.default !== undefined && f.default !== null && f.default !== "") {
			row[f.fieldname] = f.fieldtype === "Check" ? (Number(f.default) ? 1 : 0) : f.default;
		} else if (f.fieldtype === "Check") {
			row[f.fieldname] = 0;
		}
	}
	return row;
}
function addRow() {
	emit("update:modelValue", [...rows.value, seededRow()]);
}
function removeRow(i) {
	const next = rows.value.slice();
	next.splice(i, 1);
	emit("update:modelValue", next);
}
</script>

<template>
	<div class="border border-ink-200 rounded-lg overflow-x-auto">
		<table class="w-full text-xs" style="min-width: 480px">
			<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
				<tr>
					<th class="px-2 py-2 w-8 text-left">#</th>
					<th v-for="c in columns" :key="c.fieldname" class="px-2 py-2 text-left font-medium">
						{{ c.label || c.fieldname }}<span v-if="c.reqd" class="text-danger-600"> *</span>
					</th>
					<th class="w-8"></th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(row, i) in rows" :key="i" class="border-t border-ink-100 align-top">
					<td class="px-2 py-1 text-ink-400 tabular-nums pt-2.5">{{ i + 1 }}</td>
					<td v-for="c in columns" :key="c.fieldname" class="px-2 py-1">
						<DocTypeFieldControl
							v-model="row[c.fieldname]"
							:field="c"
							:context="row"
							:disabled="disabled"
							compact
						/>
					</td>
					<td class="px-2 py-1 text-center pt-2">
						<button
							v-if="!disabled"
							type="button"
							class="text-ink-400 hover:text-danger-600"
							title="Remove row"
							@click="removeRow(i)"
						>
							×
						</button>
					</td>
				</tr>
				<tr v-if="!rows.length">
					<td :colspan="columns.length + 2" class="px-2 py-3 text-center text-ink-400">
						No rows yet.
					</td>
				</tr>
			</tbody>
		</table>
		<div v-if="!disabled" class="px-2 py-1.5 border-t border-ink-100">
			<button type="button" class="text-xs text-brand-600 hover:underline" @click="addRow">
				+ Add row
			</button>
		</div>
	</div>
</template>
