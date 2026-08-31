<script setup>
// One meta-driven field control, shared by the main form (DocTypeForm) and the
// child-table grid (DocTypeChildTable). Picks a Desk control by fieldtype and
// resolves a Dynamic Link's target DocType from a sibling value in `context`.
import { computed } from "vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

const props = defineProps({
	field: { type: Object, required: true },
	modelValue: { default: "" },
	// Sibling field values (the form object or the child row) — for Dynamic Link.
	context: { type: Object, default: () => ({}) },
	disabled: { type: Boolean, default: false },
	compact: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);

const NUMERIC = new Set(["Int", "Float", "Currency", "Percent"]);
const TEXTAREA = new Set([
	"Small Text",
	"Text",
	"Long Text",
	"Code",
	"Text Editor",
	"HTML Editor",
	"Markdown Editor",
	"JSON",
]);

const kind = computed(() => {
	const t = props.field.fieldtype;
	if (t === "Link" || t === "Dynamic Link") return "link";
	if (t === "Select") return "select";
	if (t === "Check") return "check";
	if (t === "Date") return "date";
	if (t === "Datetime") return "datetime";
	if (TEXTAREA.has(t)) return props.compact ? "data" : "textarea";
	if (NUMERIC.has(t)) return "number";
	return "data";
});

// Link → options is the target DocType; Dynamic Link → options names the sibling
// field that holds the target DocType.
const linkDoctype = computed(() =>
	props.field.fieldtype === "Dynamic Link"
		? props.context[props.field.options] || ""
		: props.field.options || "DocType"
);
const linkDisabled = computed(
	() => props.disabled || (props.field.fieldtype === "Dynamic Link" && !linkDoctype.value)
);

const options = computed(() =>
	(props.field.options || "")
		.split("\n")
		.map((o) => o.trim())
		.filter(Boolean)
);

const val = computed({
	get: () => props.modelValue,
	set: (v) => emit("update:modelValue", v),
});
function onNumber(v) {
	emit("update:modelValue", v === "" || v === null || v === undefined ? null : Number(v));
}
function onCheck(e) {
	emit("update:modelValue", e.target.checked ? 1 : 0);
}
</script>

<template>
	<DeskLinkPicker
		v-if="kind === 'link'"
		v-model="val"
		:doctype="linkDoctype || 'DocType'"
		value-field="name"
		:disabled="linkDisabled"
		:placeholder="field.fieldtype === 'Dynamic Link' && !linkDoctype ? 'Pick type first' : 'Search…'"
	/>
	<DeskSelect v-else-if="kind === 'select'" v-model="val" :disabled="disabled">
		<option value="">—</option>
		<option v-for="o in options" :key="o" :value="o">{{ o }}</option>
	</DeskSelect>
	<label
		v-else-if="kind === 'check'"
		class="inline-flex items-center gap-2 text-xs text-ink-700 h-[34px]"
	>
		<input type="checkbox" :checked="!!modelValue" :disabled="disabled" @change="onCheck" />
		<span v-if="!compact">Yes</span>
	</label>
	<DeskInput v-else-if="kind === 'date'" v-model="val" type="date" :disabled="disabled" />
	<DeskInput
		v-else-if="kind === 'datetime'"
		v-model="val"
		type="datetime-local"
		:disabled="disabled"
	/>
	<DeskTextarea v-else-if="kind === 'textarea'" v-model="val" :rows="3" :disabled="disabled" />
	<DeskInput
		v-else-if="kind === 'number'"
		:model-value="modelValue"
		type="number"
		:disabled="disabled"
		@update:model-value="onNumber"
	/>
	<DeskInput v-else v-model="val" :disabled="disabled" />
</template>
