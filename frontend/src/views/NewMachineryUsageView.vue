<script setup>
// Log Machinery Usage — mirrors the demo. Picking a machine auto-fills rate + unit.

import { reactive, ref, computed, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { createDataAdapter } from "@/data/adapters";
import { fmtINR } from "@/utils/format";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";

const router = useRouter();
const route = useRoute();
const adapter = createDataAdapter(useDataStore());

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
		hint: [m.machinery_type, m.ownership].filter(Boolean).join(" · "),
	})),
);
const projectRes = useDocTypeList("Project", {
	fields: ["name", "project_name"],
	orderBy: "project_name asc",
	pageLength: 0,
	cache: "buildsuite-project-options",
});
const projectOptions = computed(() =>
	(projectRes.data || []).map((p) => ({ value: p.name, label: p.project_name, hint: p.name })),
);

const today = new Date().toISOString().slice(0, 10);
const form = reactive({
	machine: route.query.machine || "",
	project: "",
	task: "",
	date: today,
	quantity: 1,
	unit: "Days",
	rate: 0,
	fuel_cost: 0,
});
const { errors, applyServerErrors, setErrors } = useFormErrors({
	machine: "machine",
	project: "project",
});
const saving = ref(false);

// Auto-fill rate + unit from the picked machine (also on ?machine= prefill).
const selectedMachine = computed(() =>
	(machineryRes.data || []).find((m) => m.name === form.machine),
);
watch(
	selectedMachine,
	(m) => {
		if (m) {
			form.rate = m.rate || 0;
			form.unit = m.rate_unit === "Hour" ? "Hours" : "Days";
		}
	},
	{ immediate: true },
);

const total = computed(
	() => (Number(form.quantity) || 0) * (Number(form.rate) || 0) + (Number(form.fuel_cost) || 0),
);

function validate() {
	const e = {};
	if (!form.machine) e.machine = "Machine is required.";
	if (!form.project) e.project = "Project is required.";
	setErrors(e);
	return Object.keys(e).length === 0;
}

function onCancel() {
	router.back();
}

async function onSave() {
	if (!validate()) return;
	saving.value = true;
	try {
		const res = await adapter.create("Machinery Usage", {
			machine: form.machine,
			project: form.project,
			task: form.task,
			date: form.date,
			quantity: form.quantity,
			unit: form.unit,
			rate: form.rate,
			fuel_cost: form.fuel_cost,
		});
		router.push(`/machinery-usage/${res.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to log usage", "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Equipment", to: "/equipment" },
	{ label: "Machinery Usage", to: "/machinery-usage" },
	{ label: "New" },
];
</script>

<template>
	<DeskPage title="Log Machinery Usage" :breadcrumbs="breadcrumbs">
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Saving…' : 'Log usage'"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<DeskSection title="Usage" :cols="3">
				<DeskField label="Machine" required :error="errors.machine">
					<DeskSearchableSelect
						v-model="form.machine"
						:options="machineryOptions"
						placeholder="Pick a machine…"
						search-placeholder="Search machine…"
					/>
				</DeskField>
				<DeskField label="Project" required :error="errors.project">
					<DeskSearchableSelect
						v-model="form.project"
						:options="projectOptions"
						placeholder="Pick a project…"
						search-placeholder="Search project…"
						allow-clear
					/>
				</DeskField>
				<DeskField label="Task">
					<DeskLinkPicker
						v-model="form.task"
						doctype="Task"
						label-field="subject"
						value-field="name"
						:filters="form.project ? [['project', '=', form.project]] : []"
						placeholder="Task…"
					/>
				</DeskField>

				<DeskField label="Date"><DeskInput v-model="form.date" type="date" /></DeskField>
				<DeskField label="Quantity">
					<DeskInput v-model.number="form.quantity" type="number" min="0" step="0.5" />
				</DeskField>
				<DeskField label="Unit">
					<DeskSelect v-model="form.unit">
						<option>Days</option>
						<option>Hours</option>
					</DeskSelect>
				</DeskField>

				<DeskField label="Rate (₹)">
					<DeskInput v-model.number="form.rate" type="number" min="0" />
				</DeskField>
				<DeskField label="Fuel cost (₹)">
					<DeskInput v-model.number="form.fuel_cost" type="number" min="0" />
				</DeskField>
				<DeskField label="Total">
					<div class="text-sm text-ink-900 font-medium tabular-nums pt-1.5">
						{{ fmtINR(total) }}
					</div>
				</DeskField>
			</DeskSection>
		</DeskForm>
	</DeskPage>
</template>
