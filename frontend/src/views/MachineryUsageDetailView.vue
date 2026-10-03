<script setup>
// Machinery Usage detail — view / edit / delete. Total is computed for display.

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { usePermissions } from "@/composables/usePermissions";
import { useFormErrors } from "@/composables/useFormErrors";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useProjectNames } from "@/composables/useProjectNames";
import { showToast } from "@/utils/appToast";
import { createDataAdapter } from "@/data/adapters";
import { fmtINR, fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskLink from "@/components/desk/DeskLink.vue";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const adapter = createDataAdapter(useDataStore());
const { canEdit, canDelete } = usePermissions();
const { projectName } = useProjectNames();
const { errors, applyServerErrors, setErrors } = useFormErrors({ machine: "machine" });

const resource = adapter.read("Machinery Usage", props.id, { fields: ["*"] });
const doc = computed(() => resource?.doc || null);

const machineryRes = useDocTypeList("Machinery", {
	fields: ["name", "machinery_name", "machinery_type", "ownership", "rate", "rate_unit"],
	orderBy: "machinery_name asc",
	pageLength: 0,
	cache: "buildsuite-machinery-options",
});
const machineryOptions = computed(() =>
	(machineryRes.data || []).map((m) => ({
		value: m.name,
		label: m.machinery_name,
		hint: [m.machinery_type, __(m.ownership)].filter(Boolean).join(" · "),
	}))
);
// Machinery is hash-named, so show its label instead — like projectName() below.
const machineName = (id) => machineryOptions.value.find((o) => o.value === id)?.label || id;
const projectRes = useDocTypeList("Project", {
	fields: ["name", "project_name"],
	orderBy: "project_name asc",
	pageLength: 0,
	cache: "buildsuite-project-options",
});
const projectOptions = computed(() =>
	(projectRes.data || []).map((p) => ({ value: p.name, label: p.project_name, hint: p.name }))
);

const editing = ref(false);
const saving = ref(false);
const form = ref({});

function snapshot() {
	const d = doc.value;
	if (!d) return {};
	return {
		machine: d.machine || "",
		project: d.project || "",
		task: d.task || "",
		date: d.date || "",
		quantity: d.quantity || 0,
		unit: d.unit || "Days",
		rate: d.rate || 0,
		fuel_cost: d.fuel_cost || 0,
	};
}
watch(
	doc,
	(v) => {
		if (v && !editing.value) form.value = snapshot();
	},
	{ immediate: true }
);
// In edit mode, changing the project clears the task (the picker is scoped to the project,
// and the server rejects a cross-project task).
watch(
	() => form.value.project,
	(_new, _old) => {
		if (editing.value) form.value.task = "";
	}
);

function totalOf(o) {
	return (Number(o.quantity) || 0) * (Number(o.rate) || 0) + (Number(o.fuel_cost) || 0);
}
const viewTotal = computed(() => (doc.value ? fmtINR(totalOf(doc.value)) : "—"));

function startEdit() {
	form.value = snapshot();
	setErrors({});
	editing.value = true;
}
function cancelEdit() {
	editing.value = false;
}
function validate() {
	const e = {};
	if (!form.value.machine) e.machine = __("Machine is required.");
	setErrors(e);
	return Object.keys(e).length === 0;
}
async function saveEdit() {
	if (!validate()) return;
	saving.value = true;
	try {
		const f = form.value;
		await adapter.update("Machinery Usage", props.id, {
			machine: f.machine,
			project: f.project,
			task: f.task,
			date: f.date,
			quantity: f.quantity,
			unit: f.unit,
			rate: f.rate,
			fuel_cost: f.fuel_cost,
		});
		await resource?.reload?.();
		editing.value = false;
	} catch (err) {
		showToast(applyServerErrors(err) ?? __("Failed to update usage"), "error");
	} finally {
		saving.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: __("Delete usage entry?"),
		message: __("This usage log entry will be removed permanently."),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Machinery Usage", props.id);
		router.push("/machinery-usage");
	} catch (err) {
		showToast(applyServerErrors(err) ?? __("Failed to delete usage"), "error");
	}
}

const breadcrumbs = computed(() => [
	{ label: __("BuildSuite Core"), to: "/" },
	{ label: __("Equipment"), to: "/equipment" },
	{ label: __("Machinery Usage"), to: "/machinery-usage" },
	{ label: doc.value ? `${machineName(doc.value.machine)} · ${fmtDate(doc.value.date)}` : props.id },
]);
</script>

<template>
	<DeskPage
		v-if="doc"
		:title="`${machineName(doc.machine)} — ${fmtDate(doc.date)}`"
		:subtitle="`${doc.quantity} ${doc.unit} · ${viewTotal}`"
		:breadcrumbs="breadcrumbs"
	>
		<template #actions>
			<button
				v-if="!editing && canEdit('machineryUsage')"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="startEdit"
			>
				{{ __("Edit") }}
			</button>
			<button
				v-if="!editing && canDelete('machineryUsage')"
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				@click="onDelete"
			>
				{{ __("Delete") }}
			</button>
			<button
				v-if="editing"
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="cancelEdit"
			>
				{{ __("Cancel") }}
			</button>
			<button
				v-if="editing && canEdit('machineryUsage')"
				type="button"
				class="desk-save-btn"
				:disabled="saving"
				@click="saveEdit"
			>
				{{ saving ? __("Saving…") : __("Save") }}
			</button>
		</template>

		<!-- View mode -->
		<div v-if="!editing">
			<DeskSection :title="__('Usage')" :cols="3">
				<DeskField :label="__('Machine')">
					<DeskLink :to="`/machinery/${doc.machine}`">{{ machineName(doc.machine) }}</DeskLink>
				</DeskField>
				<DeskField :label="__('Project')"
					><div class="text-sm text-ink-700">
						{{ projectName(doc.project) || "—" }}
					</div></DeskField
				>
				<DeskField :label="__('Task')"
					><div class="text-sm text-ink-700">{{ doc.task || "—" }}</div></DeskField
				>
				<DeskField :label="__('Date')"
					><div class="text-sm text-ink-800">{{ fmtDate(doc.date) }}</div></DeskField
				>
				<DeskField :label="__('Quantity')"
					><div class="text-sm text-ink-800 tabular-nums">
						{{ doc.quantity }} {{ doc.unit }}
					</div></DeskField
				>
				<DeskField :label="__('Rate')"
					><div class="text-sm text-ink-800 tabular-nums">
						{{ fmtINR(doc.rate) }}
					</div></DeskField
				>
				<DeskField :label="__('Fuel cost')"
					><div class="text-sm text-ink-800 tabular-nums">
						{{ fmtINR(doc.fuel_cost) }}
					</div></DeskField
				>
				<DeskField :label="__('Total')"
					><div class="text-sm text-ink-900 font-medium tabular-nums">
						{{ viewTotal }}
					</div></DeskField
				>
			</DeskSection>
		</div>

		<!-- Edit mode -->
		<div v-else>
			<DeskSection :title="__('Usage')" :cols="3">
				<DeskField :label="__('Machine')" required :error="errors.machine">
					<DeskSearchableSelect
						v-model="form.machine"
						:options="machineryOptions"
						:placeholder="__('Pick a machine…')"
						:search-placeholder="__('Search machine…')"
					/>
				</DeskField>
				<DeskField :label="__('Project')">
					<DeskSearchableSelect
						v-model="form.project"
						:options="projectOptions"
						:placeholder="__('Pick a project…')"
						:search-placeholder="__('Search project…')"
						allow-clear
					/>
				</DeskField>
				<DeskField :label="__('Task')">
					<DeskLinkPicker
						v-model="form.task"
						doctype="Task"
						label-field="subject"
						value-field="name"
						:filters="form.project ? [['project', '=', form.project]] : []"
						:placeholder="__('Task…')"
					/>
				</DeskField>

				<DeskField :label="__('Date')"><DeskInput v-model="form.date" type="date" /></DeskField>
				<DeskField :label="__('Quantity')"
					><DeskInput v-model.number="form.quantity" type="number" min="0" step="0.5"
				/></DeskField>
				<DeskField :label="__('Unit')">
					<DeskSelect v-model="form.unit"
						><option value="Days">{{ __("Days") }}</option>
						<option value="Hours">{{ __("Hours") }}</option></DeskSelect
					>
				</DeskField>

				<DeskField :label="__('Rate (₹)')"
					><DeskInput v-model.number="form.rate" type="number" min="0"
				/></DeskField>
				<DeskField :label="__('Fuel cost (₹)')"
					><DeskInput v-model.number="form.fuel_cost" type="number" min="0"
				/></DeskField>
			</DeskSection>
		</div>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">{{ __("Loading usage…") }}</div>
</template>
