<script setup>
// Dynamic filter editor — a field + condition + value builder, modelled on Frappe's
// `frappe.ui.Filter` (apps/frappe/frappe/public/js/frappe/ui/filters/filter.js):
//   • the same condition list and per-fieldtype `invalid_condition_map`, so only the
//     operators Frappe allows for a fieldtype are offered;
//   • the value control switches by fieldtype/condition (Link picker, Select, date,
//     Between = two dates, Timespan list, "is" = set/not set, "in" = comma list).
// Emits `apply` with { fieldname, label, fieldtype, options, condition, value } or `cancel`.
import { ref, computed, watch } from "vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

const props = defineProps({
	// [{ fieldname, label, fieldtype, options }]
	fields: { type: Array, default: () => [] },
	// existing filter to edit, or null to add a new one
	initial: { type: Object, default: null },
});
const emit = defineEmits(["apply", "cancel"]);

// --- Frappe condition model (verbatim from filter.js) ---------------------------
const ALL_CONDITIONS = [
	["=", "Equals"],
	["!=", "Not Equals"],
	["like", "Like"],
	["not like", "Not Like"],
	["in", "In"],
	["not in", "Not In"],
	["is", "Is"],
	[">", "Greater Than"],
	["<", "Less Than"],
	[">=", "Greater Than Or Equal To"],
	["<=", "Less Than Or Equal To"],
	["Between", "Between"],
	["Timespan", "Timespan"],
];
const CHECK_INVALID = ALL_CONDITIONS.map((c) => c[0]).filter((c) => c !== "=");
const INVALID_CONDITION_MAP = {
	Date: ["like", "not like"],
	Datetime: ["like", "not like", "in", "not in", "=", "!="],
	Data: ["Between", "Timespan"],
	Time: ["Between", "Timespan"],
	Select: ["like", "not like", "Between", "Timespan"],
	Link: ["Between", "Timespan", ">", "<", ">=", "<="],
	Currency: ["Between", "Timespan"],
	Color: ["Between", "Timespan"],
	Check: CHECK_INVALID,
	Code: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"HTML Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"Markdown Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	Password: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	Rating: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Int: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Float: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Percent: ["like", "not like", "Between", "in", "not in", "Timespan"],
};
// Frappe's special_condition_labels for date-like fields.
const DATE_LABELS = { "<": "Before", ">": "After", "<=": "On or Before", ">=": "On or After" };

const TIMESPANS = [
	"last week",
	"last month",
	"last quarter",
	"last 6 months",
	"last year",
	"yesterday",
	"today",
	"tomorrow",
	"this week",
	"this month",
	"this quarter",
	"this year",
	"next week",
	"next month",
	"next quarter",
	"next 6 months",
	"next year",
];

const sortedFields = computed(() =>
	[...props.fields].sort((a, b) => String(a.label).localeCompare(String(b.label)))
);

const fieldname = ref(props.initial?.fieldname || sortedFields.value[0]?.fieldname || "");
const condition = ref(props.initial?.condition || "");
const value = ref(props.initial?.value ?? "");

const selectedField = computed(
	() => props.fields.find((f) => f.fieldname === fieldname.value) || null
);
const fieldtype = computed(() => selectedField.value?.fieldtype || "Data");

const conditions = computed(() => {
	const invalid = INVALID_CONDITION_MAP[fieldtype.value] || [];
	return ALL_CONDITIONS.filter((c) => !invalid.includes(c[0])).map(([op, label]) => [
		op,
		(["Date", "Datetime"].includes(fieldtype.value) && DATE_LABELS[op]) || label,
	]);
});

// The value control to render for the current fieldtype + condition.
const valueKind = computed(() => {
	if (condition.value === "is") return "isset";
	if (condition.value === "in" || condition.value === "not in") return "multi";
	if (condition.value === "Timespan") return "timespan";
	if (condition.value === "Between") return "between";
	switch (fieldtype.value) {
		case "Link":
		case "Dynamic Link":
			return "link";
		case "Select":
			return "select";
		case "Check":
			return "check";
		case "Date":
			return "date";
		case "Datetime":
			return "datetime";
		case "Int":
		case "Float":
		case "Currency":
		case "Percent":
			return "number";
		default:
			return "text";
	}
});

const selectOptions = computed(() =>
	String(selectedField.value?.options || "")
		.split("\n")
		.map((o) => o.trim())
		.filter((o) => o.length)
);

function resetValueForKind() {
	if (valueKind.value === "between") value.value = ["", ""];
	else if (valueKind.value === "isset") value.value = "set";
	else if (valueKind.value === "check") value.value = "1";
	else value.value = "";
}

// Keep condition valid when the field changes; reset value when the control shape changes.
watch(fieldname, () => {
	if (!conditions.value.some((c) => c[0] === condition.value)) {
		condition.value = conditions.value[0]?.[0] || "=";
	}
	resetValueForKind();
});
watch(condition, () => resetValueForKind());

// Initialise a valid condition on first render.
if (!condition.value || !conditions.value.some((c) => c[0] === condition.value)) {
	condition.value = conditions.value[0]?.[0] || "=";
	if (props.initial == null) resetValueForKind();
}

const canApply = computed(() => {
	if (!fieldname.value || !condition.value) return false;
	if (valueKind.value === "isset") return true;
	if (valueKind.value === "between") return value.value?.[0] && value.value?.[1];
	return value.value !== "" && value.value != null;
});

function apply() {
	if (!canApply.value) return;
	emit("apply", {
		fieldname: fieldname.value,
		label: selectedField.value?.label || fieldname.value,
		fieldtype: fieldtype.value,
		options: selectedField.value?.options || "",
		condition: condition.value,
		value: Array.isArray(value.value) ? [...value.value] : value.value,
	});
}
</script>

<template>
	<div
		class="bg-white border border-ink-200 shadow-lg p-3 w-[30rem] max-w-full"
		style="border-radius: 10px"
	>
		<div class="flex items-start gap-2">
			<!-- Field -->
			<DeskSelect v-model="fieldname" class="!w-40 flex-shrink-0">
				<option v-for="f in sortedFields" :key="f.fieldname" :value="f.fieldname">
					{{ f.label }}
				</option>
			</DeskSelect>

			<!-- Condition -->
			<DeskSelect v-model="condition" class="!w-32 flex-shrink-0">
				<option v-for="[op, label] in conditions" :key="op" :value="op">{{ label }}</option>
			</DeskSelect>

			<!-- Value -->
			<div class="flex-1 min-w-0">
				<DeskLinkPicker
					v-if="valueKind === 'link'"
					v-model="value"
					:doctype="selectedField?.options || 'DocType'"
					placeholder="Select…"
				/>
				<DeskSelect v-else-if="valueKind === 'select'" v-model="value">
					<option value="">—</option>
					<option v-for="o in selectOptions" :key="o" :value="o">{{ o }}</option>
				</DeskSelect>
				<DeskSelect v-else-if="valueKind === 'check'" v-model="value">
					<option value="1">Yes</option>
					<option value="0">No</option>
				</DeskSelect>
				<DeskSelect v-else-if="valueKind === 'isset'" v-model="value">
					<option value="set">Set</option>
					<option value="not set">Not Set</option>
				</DeskSelect>
				<DeskSelect v-else-if="valueKind === 'timespan'" v-model="value">
					<option value="">—</option>
					<option v-for="t in TIMESPANS" :key="t" :value="t">{{ t }}</option>
				</DeskSelect>
				<div v-else-if="valueKind === 'between'" class="flex items-center gap-1">
					<input v-model="value[0]" type="date" class="desk-input flex-1" />
					<span class="text-ink-400 text-xs">–</span>
					<input v-model="value[1]" type="date" class="desk-input flex-1" />
				</div>
				<input
					v-else-if="valueKind === 'date'"
					v-model="value"
					type="date"
					class="desk-input w-full"
				/>
				<input
					v-else-if="valueKind === 'datetime'"
					v-model="value"
					type="datetime-local"
					class="desk-input w-full"
				/>
				<input
					v-else-if="valueKind === 'number'"
					v-model="value"
					type="number"
					class="desk-input w-full"
					placeholder="Value"
				/>
				<input
					v-else-if="valueKind === 'multi'"
					v-model="value"
					type="text"
					class="desk-input w-full"
					placeholder="Comma-separated values"
				/>
				<input
					v-else
					v-model="value"
					type="text"
					class="desk-input w-full"
					placeholder="Value"
					@keyup.enter="apply"
				/>
			</div>
		</div>

		<div class="flex items-center justify-end gap-2 mt-3">
			<button
				type="button"
				class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md"
				@click="emit('cancel')"
			>
				Cancel
			</button>
			<button
				type="button"
				class="text-xs desk-save-btn"
				:disabled="!canApply"
				:class="{ 'opacity-50 cursor-not-allowed': !canApply }"
				@click="apply"
			>
				Apply
			</button>
		</div>
	</div>
</template>
