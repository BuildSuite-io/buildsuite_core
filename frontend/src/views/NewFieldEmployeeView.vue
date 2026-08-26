<script setup>
// New Field Employee form. A field employee is a native ERPNext Employee with
// the BuildSuite `is_labour` flag set — so payroll and HR stay native. Gender,
// date of birth and joining date are ERPNext's own mandatory fields, not ours.

import { reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { usePermissions } from "@/composables/usePermissions";
import { saveFieldEmployee } from "@/data/fieldEmployeeApi";
import { validateFieldEmployee } from "@/utils/workforceForms";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import FieldEmployeeFormFields from "@/components/FieldEmployeeFormFields.vue";
import AllocatedProjectsTable from "@/components/AllocatedProjectsTable.vue";

const router = useRouter();
const { canCreate } = usePermissions();
// `company` is mandatory on Employee and has no doctype default, so pre-fill it
// with the site's default company. The user can still pick a different one.
const activeCompany = useActiveCompany();

const today = new Date().toISOString().slice(0, 10);

const form = reactive({
	first_name: "",
	last_name: "",
	gender: "",
	date_of_birth: "",
	date_of_joining: today,
	status: "Active",
	custom_trade: "",
	custom_contractor: "",
	cell_number: "",
	company: activeCompany.value || "",
	custom_wage: null,
	custom_wage_for_overtime: null,
	allocated_projects: [],
});

// The default company arrives from an async fetch. Apply it only while the field
// is still untouched, so it never overwrites a company the user already picked.
watch(activeCompany, (c) => {
	if (c && !form.company) form.company = c;
});

const { errors, applyServerErrors, setErrors } = useFormErrors({
	first_name: "first_name",
	gender: "gender",
	date_of_birth: "date_of_birth",
	date_of_joining: "date_of_joining",
	company: "company",
	custom_wage: "custom_wage",
});
const saving = ref(false);

function validate() {
	const e = validateFieldEmployee(form);
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
		// The endpoint owns `is_labour` and the naming series, so they aren't sent.
		const res = await saveFieldEmployee({ ...form });
		showToast("Field employee created");
		router.push(`/field-employees/${res.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to create field employee", "error");
	} finally {
		saving.value = false;
	}
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Workforce", to: "/workforce" },
	{ label: "Field Employees", to: "/field-employees" },
	{ label: "New" },
];
</script>

<template>
	<DeskPage title="New Field Employee" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canCreate('fieldEmployee')"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			You don't have permission to create a field employee.
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Creating…' : 'Create'"
					:saving="saving"
					@save="onSave"
					@cancel="onCancel"
				/>
			</template>

			<FieldEmployeeFormFields :form="form" :errors="errors" />

			<AllocatedProjectsTable
				:rows="form.allocated_projects"
				editable
				@add="form.allocated_projects.push({ project: '' })"
				@remove="(i) => form.allocated_projects.splice(i, 1)"
			/>
		</DeskForm>
	</DeskPage>
</template>
